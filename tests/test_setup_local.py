import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from kelip import setup_local as setup
from kelip import local_caption as ai


class SetupTests(unittest.TestCase):
    def test_finds_supported_python_even_if_default_is_too_new(self):
        with patch.object(setup,'probe_python',side_effect=lambda args: args==['python3.12']):
            self.assertEqual(setup.select_python(),'python3.12')
        with patch.object(setup,'probe_python',return_value=False):
            with self.assertRaises(setup.SetupError): setup.select_python()

    def test_pip_failure_does_not_mark_dependencies_ready_and_retry_is_safe(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'ROOT',Path(directory)),patch.object(setup,'imports_ready',return_value=True):
            root=Path(directory);(root/'.venv').mkdir();(root/'requirements.txt').write_text('package==1\n')
            with patch.object(setup,'run',side_effect=setup.SetupError('failed')):
                with self.assertRaises(setup.SetupError): setup.sync_dependencies('python')
            self.assertFalse((root/'.venv/.klip-requirements.sha256').exists())
            with patch.object(setup,'run') as install:
                setup.sync_dependencies('python');self.assertEqual(install.call_count,1)
                setup.sync_dependencies('python');self.assertEqual(install.call_count,1)
                (root/'requirements.txt').write_text('package==2\n')
                setup.sync_dependencies('python');self.assertEqual(install.call_count,2)

    def test_existing_incompatible_venv_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'ROOT',Path(directory)),patch.object(setup.sys,'platform','darwin'),patch.object(setup,'probe_python',return_value=False):
            python=setup.venv_python();python.parent.mkdir(parents=True);python.write_text('keep')
            with self.assertRaises(setup.SetupError):setup.setup()
            self.assertEqual(python.read_text(),'keep')

    def test_unsupported_platform_installs_nothing(self):
        with patch.object(setup.sys,'platform','linux'),patch.object(setup,'run') as run:
            with self.assertRaises(setup.SetupError):setup.setup()
            run.assert_not_called()

    def test_model_already_present_needs_no_cli_or_download(self):
        with patch.object(ai,'ensure_runtime',return_value={'models':[{'name':ai.MODEL}]}),patch.object(ai.opener,'open') as download,patch.object(ai,'binary',return_value=None):
            self.assertEqual(ai.setup_model(),0);download.assert_not_called()

    def test_model_download_stream_verified_and_errors_are_actionable(self):
        progress=io.BytesIO(b'{"status":"pulling","completed":50,"total":100}\n{"status":"success"}\n')
        with patch.object(ai,'ensure_runtime',return_value={'models':[]}),patch.object(ai.opener,'open',return_value=progress),patch.object(ai,'request',return_value={'models':[{'name':ai.MODEL}]}):
            self.assertEqual(ai.setup_model(),0)
        with patch.object(ai,'ensure_runtime',return_value={'models':[]}),patch.object(ai.opener,'open',return_value=io.BytesIO(b'{"error":"network failed"}\n')):
            with self.assertRaises(ai.CaptionUnavailable): ai.setup_model()
        for system,url in [('Darwin','download/mac'),('Windows','download/windows'),('Linux','docs.ollama.com/linux')]:
            with patch.object(ai.platform,'system',return_value=system):self.assertIn(url,ai.installation_hint())

    def test_successful_npm_exit_without_runtime_is_not_reported_as_ready(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(setup,'ROOT',Path(directory)),patch.object(setup.sys,'platform','darwin'),patch.object(setup,'probe_python',return_value=True),patch.object(setup,'sync_dependencies'),patch.object(setup,'node_ready',return_value=False),patch.object(setup.shutil,'which',return_value='npm'),patch.object(setup,'run') as run:
            python=setup.venv_python();python.parent.mkdir(parents=True);python.write_text('fixture')
            with self.assertRaises(setup.SetupError):setup.setup()
            self.assertEqual(run.call_count,1)
