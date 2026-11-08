"""Live proxy contract tests. Optional Caddy/Gunicorn, isolated source and data."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        caddy = os.environ.get("KELIP_TEST_CADDY") or shutil.which("caddy")
        if not caddy or not importlib.util.find_spec("gunicorn"):
            raise unittest.SkipTest("Pasang Gunicorn dan tentukan KELIP_TEST_CADDY untuk tes proxy live.")
        cls.tmp = tempfile.TemporaryDirectory(prefix="kelip-deployment-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.folder = Path(cls.tmp.name)
        for name in ("kelip", "templates", "static"):
            shutil.copytree(ROOT / name, cls.folder / name, ignore=shutil.ignore_patterns("__pycache__"))
        cls.opener = build_opener(ProxyHandler({}))
        backend_port, proxy_port = free_port(), free_port()
        while proxy_port == backend_port:
            proxy_port = free_port()
        cls.url = f"http://127.0.0.1:{proxy_port}"
        env = dict(os.environ, KELIP_DOMAIN="kelip.test", KELIP_ADMIN_USER="admin",
                   XDG_CONFIG_HOME=str(cls.folder / "config"), XDG_DATA_HOME=str(cls.folder / "share"))
        env["KELIP_ADMIN_HASH"] = subprocess.check_output(
            [caddy, "hash-password", "--plaintext", "fixture-password"], text=True).strip()
        fixture_config = (ROOT / "deploy/Caddyfile").read_text()
        fixture_config = fixture_config.replace("{$KELIP_DOMAIN} {", cls.url + " {", 1)
        fixture_config = fixture_config.replace("127.0.0.1:8765", f"127.0.0.1:{backend_port}")
        config = cls.folder / "Caddyfile"
        config.write_text("""{
 admin off
 auto_https off
}
""" + fixture_config)
        backend = cls.start([
            sys.executable, "-m", "gunicorn", "--config", str(ROOT / "deploy/gunicorn.conf.py"),
            "--chdir", str(cls.folder), "--bind", f"127.0.0.1:{backend_port}", "kelip.app:app",
        ], env)
        cls.wait_ready(f"http://127.0.0.1:{backend_port}/api/health", backend)
        proxy = cls.start([caddy, "run", "--config", str(config), "--adapter", "caddyfile"], env)
        cls.wait_ready(cls.url, proxy, expected=401)

    @classmethod
    def start(cls, args, env):
        log = tempfile.TemporaryFile()
        cls.addClassCleanup(log.close)
        process = subprocess.Popen(args, cwd=cls.folder, env=env, stdout=log, stderr=log)
        def stop():
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        cls.addClassCleanup(stop)
        process.fixture_log = log
        return process

    @classmethod
    def wait_ready(cls, url, process, expected=200):
        for _ in range(100):
            if process.poll() is not None:
                process.fixture_log.seek(0)
                raise AssertionError(process.fixture_log.read().decode())
            try:
                with cls.opener.open(url, timeout=1) as response:
                    if response.status == expected:
                        return
            except HTTPError as error:
                if error.code == expected:
                    return
            except OSError:
                pass
            time.sleep(.1)
        raise AssertionError("Fixture server tidak siap.")

    def request(self, path, *, auth=True, method="GET", headers=None):
        headers = dict(headers or {})
        if auth:
            credentials = base64.b64encode(b"admin:fixture-password").decode()
            headers["Authorization"] = "Basic " + credentials
        data = b"" if method == "POST" else None
        try:
            return self.opener.open(Request(self.url + path, data=data, headers=headers, method=method), timeout=5)
        except HTTPError as error:
            return error

    def test_all_routes_require_login(self):
        for path in ("/", "/api/jobs", "/static/app.js", "/files/" + "a" * 32 + "/clip-1.mp4",
                     "/api/watermark-assets/fixture/preview"):
            with self.subTest(path=path), self.request(path, auth=False) as response:
                self.assertEqual(response.status, 401)

    def test_authenticated_app_and_persistent_data_location(self):
        with self.request("/api/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["app"], "klip-lokal")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        with self.request("/api/jobs") as response:
            self.assertEqual(json.load(response)["jobs"], [])
        self.assertTrue((self.folder / "data").is_dir())

    def test_cross_site_mutations_are_rejected(self):
        for headers in ({"Origin": "https://evil.test"}, {"Origin": "null"},
                        {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers), self.request("/api/jobs", method="POST", headers=headers) as response:
                self.assertEqual(response.status, 403)
        with self.request("/api/jobs", method="POST", headers={"Origin": "https://kelip.test"}) as response:
            # Flask receives the authenticated request and rejects the empty form.
            self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
