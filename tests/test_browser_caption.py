"""
Pengujian interaksi DOM dan layout browser menggunakan Google Chrome nyata (Headless).

Cakupan yang dibuktikan berkas ini:
1. Sinkronisasi status busy vs dirty pada DOM Chrome (tombol Simpan tetap disabled saat request pending, anti-double click, retry setelah error 500, disabled saat bersih setelah sukses 200).
2. Layout responsif layar sempit (375x667): perataan tombol aksi (.btn-save-caption, .btn-copy-caption, .btn-download-txt, .btn-ai-caption), wrapping, dan pencegahan horizontal overflow.
3. Penjaga navigasi aplikasi nyata (beforeunload preventDefault saat dirty, konfirmasi window.confirm saat klik #new-job dan openJob, serta penanganan konflik 409 dan pemulihan versi server).

Batas pengujian:
Pengujian ini menggunakan template index.html dan static/app.js aplikasi nyata di dalam headless Chrome dengan router API JavaScript fixture. Ini BUKAN pengujian dua tab browser multi-proses independen terhadap instance Flask server yang berjalan secara live. Batasan integrasi lintas proses tersebut tetap memerlukan verifikasi manual / live smoke testing terpisah.
"""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2

CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class RealBrowserCaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CHROME_PATH.exists():
            raise unittest.SkipTest("Google Chrome tidak ditemukan di /Applications/Google Chrome.app")

    def _run_chrome_test(self, test_script_js, window_size="1280,800", virtual_time=2500):
        root = Path(__file__).resolve().parent.parent
        tmpl_src = (root / "templates" / "index.html").read_text()
        tmpl = jinja2.Template(tmpl_src)
        page_html = tmpl.render(
            global_mode=False,
            asset_version="test",
            subtitle_styles={"classic": {"label": "Klasik", "description": "Teks tebal"}},
            ideas=[],
            sources=[],
        )

        style_css = (root / "static" / "style.css").read_text()
        custom_select_js = (root / "static" / "custom-select.js").read_text()
        app_js = (root / "static" / "app.js").read_text()

        # Inline CSS dan JS aplikasi nyata ke dalam halaman
        full_html = page_html.replace(
            '<link rel="stylesheet" href="/static/style.css?v=test">',
            f"<style>{style_css}</style>",
        ).replace(
            '<script src="/static/custom-select.js?v=test"></script><script src="/static/app.js?v=test"></script>',
            f"<script>{custom_select_js}</script><script>{app_js}</script>",
        )

        runner_script = f"""
        <pre id="test-results" style="display:none;"></pre>
        <script>
        (async () => {{
          const testLogs = [];
          function assert(cond, msg) {{
            if (!cond) throw new Error('Assertion failed: ' + msg);
            testLogs.push('OK: ' + msg);
          }}

          try {{
            {test_script_js}
            document.getElementById('test-results').textContent = JSON.stringify({{
              pass: true,
              logs: testLogs
            }});
          }} catch (err) {{
            document.getElementById('test-results').textContent = JSON.stringify({{
              pass: false,
              error: err.message,
              stack: err.stack
            }});
          }}
        }})();
        </script>
        """

        full_html += runner_script

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            html_file = tmp_path / "browser_page_test.html"
            user_data_dir = tmp_path / "chrome_user_data"
            html_file.write_text(full_html)

            cmd = [
                str(CHROME_PATH),
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                f"--window-size={window_size}",
                f"--virtual-time-budget={virtual_time}",
                f"--user-data-dir={user_data_dir}",
                f"file://{html_file}",
                "--dump-dom",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Chrome process error: {res.stderr}")

            stdout = res.stdout
            start_tag = '<pre id="test-results" style="display:none;">'
            end_tag = "</pre>"
            start_idx = stdout.find(start_tag)
            self.assertNotEqual(start_idx, -1, f"Tag test-results tidak ditemukan di DOM dump:\n{stdout[:500]}")
            end_idx = stdout.find(end_tag, start_idx)
            json_text = stdout[start_idx + len(start_tag):end_idx]

            self.assertTrue(json_text.strip(), "JSON hasil tes kosong")
            data = json.loads(json_text)
            if not data.get("pass"):
                self.fail(f"Uji Chrome gagal: {data.get('error')}\n{data.get('stack')}")
            return data.get("logs", [])

    def test_real_browser_save_button_busy_vs_dirty_desktop(self):
        """Memverifikasi tombol Simpan tetap disabled saat pending, menolak klik ganda, dan pulih setelah error/sukses."""
        script = """
        let deferredResolve, deferredReject;
        let apiCallCount = 0;
        window.api = function(url, opts) {
          if (url && url.includes('/api/watermark-presets')) {
            return Promise.resolve({ presets: [] });
          }
          apiCallCount++;
          return new Promise((resolve, reject) => {
            deferredResolve = resolve;
            deferredReject = reject;
          });
        };

        const testJob = {
          id: 'job_busy_1',
          title: 'Uji Busy Desktop',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_busy_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip',
            caption: 'Caption awal server',
            metadata_revision: 1
          }]
        };
        render(testJob);

        const box = document.querySelector('.caption-editor');
        const ta = box.querySelector('textarea');
        const saveBtn = box.querySelector('.btn-save-caption');
        const aiBtn = box.querySelector('.btn-ai-caption');
        const statusBadge = box.querySelector('.caption-status-badge');

        assert(saveBtn.disabled === true, 'Tombol Simpan awalnya nonaktif');
        assert(!box.classList.contains('has-unsaved'), 'Awalnya tidak has-unsaved');

        // Pengguna mengetik perubahan
        ta.value = 'Perubahan teks manual di desktop Chrome';
        ta.dispatchEvent(new Event('input'));

        assert(saveBtn.disabled === false, 'Tombol Simpan aktif setelah mengetik');
        assert(box.classList.contains('has-unsaved'), 'has-unsaved aktif setelah mengetik');
        assert(hasUnsavedCaptionEdits() === true, 'hasUnsavedCaptionEdits bernilai true');

        // Klik Simpan: request in flight (pending)
        saveBtn.click();

        // Saat pending:
        assert(apiCallCount === 1, 'api dipanggil tepat 1 kali');
        assert(saveBtn.disabled === true, 'Tombol Simpan nonaktif selama request pending');
        assert(aiBtn.disabled === true, 'Tombol AI nonaktif selama request pending');
        assert(ta.disabled === true, 'Textarea nonaktif selama request pending');
        assert(box.classList.contains('has-unsaved'), 'has-unsaved tetap true saat pending');
        assert(statusBadge.textContent.includes('Menyimpan caption ke server'), 'Badge status menunjukkan saving');

        // Klik kedua saat pending harus ditolak (anti double submission)
        saveBtn.click();
        assert(apiCallCount === 1, 'Klik berulang saat pending ditolak');

        // Simulasi error penyimpanan dari server (500)
        deferredReject(new Error('500 Gagal menulis job.json'));
        await new Promise(r => setTimeout(r, 60));

        // Setelah error:
        assert(saveBtn.disabled === false, 'Tombol Simpan kembali aktif setelah error');
        assert(aiBtn.disabled === false, 'Tombol AI kembali aktif setelah error');
        assert(ta.disabled === false, 'Textarea kembali aktif setelah error');
        assert(ta.value === 'Perubahan teks manual di desktop Chrome', 'Draft teks tidak hilang');
        assert(box.classList.contains('has-unsaved'), 'has-unsaved tetap bertahan setelah error');
        assert(statusBadge.textContent.includes('Gagal menyimpan caption'), 'Badge status menunjukkan error');

        // Retry simpan dan sukses
        saveBtn.click();
        assert(apiCallCount === 2, 'Retry memicu pemanggilan api kedua');
        assert(saveBtn.disabled === true, 'Tombol Simpan kembali nonaktif saat retry pending');

        deferredResolve({
          caption: 'Perubahan teks manual di desktop Chrome',
          caption_source: 'manual',
          metadata_revision: 2,
          caption_updated_at: new Date().toISOString()
        });
        await new Promise(r => setTimeout(r, 60));

        // Setelah sukses:
        assert(saveBtn.disabled === true, 'Tombol Simpan nonaktif setelah sukses (dirty false)');
        assert(!box.classList.contains('has-unsaved'), 'has-unsaved dibersihkan setelah sukses');
        assert(hasUnsavedCaptionEdits() === false, 'hasUnsavedCaptionEdits bernilai false setelah sukses');
        assert(statusBadge.textContent.includes('Tersimpan · Edit manual'), 'Badge status menunjukkan tersimpan');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 5)

    def test_real_browser_narrow_screen_controls_wrapping(self):
        """Memverifikasi tampilan editor caption, wrapping tombol aksi, dan pencegahan overflow pada layar sempit (375x667)."""
        script = """
        window.api = () => Promise.resolve({});

        const testJob = {
          id: 'job_narrow_1',
          title: 'Uji Layar Sempit',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_narrow_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip narrow',
            caption: 'Caption mobile test',
            metadata_revision: 1
          }]
        };
        render(testJob);

        const box = document.querySelector('.caption-editor');
        const rect = box.getBoundingClientRect();
        const clientWidth = document.documentElement.clientWidth;

        assert(rect.width <= clientWidth, 'Editor caption berada di dalam lebar viewport: ' + rect.width + ' <= ' + clientWidth);
        assert(rect.right <= clientWidth, 'Editor caption tidak meluap secara horizontal');

        const actions = box.querySelector('.caption-actions');
        const saveBtn = box.querySelector('.btn-save-caption');
        const copyBtn = box.querySelector('.btn-copy-caption');
        const saveTxtBtn = box.querySelector('.btn-download-txt');
        const aiBtn = box.querySelector('.btn-ai-caption');

        assert(Boolean(saveBtn), 'Tombol Simpan tersedia');
        assert(Boolean(copyBtn), 'Tombol Salin tersedia');
        assert(Boolean(saveTxtBtn), 'Tombol Unduh TXT tersedia');
        assert(Boolean(aiBtn), 'Tombol AI tersedia');

        // Pastikan setiap tombol berada dalam batas kontainer aksi
        const actionsRect = actions.getBoundingClientRect();
        for (const btn of [saveBtn, copyBtn, saveTxtBtn, aiBtn]) {
          const btnRect = btn.getBoundingClientRect();
          assert(btnRect.width > 40, 'Tombol memiliki ukuran sentuh yang memadai');
          assert(btnRect.right <= actionsRect.right + 2, 'Tombol tidak meluap ke kanan luar actions');
        }

        const statusBadge = box.querySelector('.caption-status-badge');
        assert(statusBadge.getBoundingClientRect().width <= rect.width, 'Badge status tidak melebihi lebar kontainer');
        """
        logs = self._run_chrome_test(script, window_size="375,667")
        self.assertGreater(len(logs), 4)

    def test_real_browser_navigation_guards_and_conflict_resolution(self):
        """Memverifikasi penjaga navigasi aplikasi nyata (beforeunload, #new-job, openJob) serta penyelesaian konflik 409."""
        script = """
        let serverJobState = {
          caption: 'Caption awal di server',
          caption_source: 'ai_local',
          metadata_revision: 1
        };

        window.api = async function(url, opts) {
          const body = opts && opts.body ? JSON.parse(opts.body) : {};
          if (opts && opts.method === 'PATCH') {
            if (body.expected_revision && body.expected_revision !== serverJobState.metadata_revision) {
              const err = new Error('Konflik revisi');
              err.data = {
                conflict: true,
                current_revision: serverJobState.metadata_revision,
                server_caption: serverJobState.caption,
                server_source: serverJobState.caption_source
              };
              err.status = 409;
              throw err;
            }
            serverJobState.caption = body.caption;
            serverJobState.caption_source = 'manual';
            serverJobState.metadata_revision += 1;
            return {
              caption: serverJobState.caption,
              caption_source: serverJobState.caption_source,
              metadata_revision: serverJobState.metadata_revision,
              caption_updated_at: new Date().toISOString()
            };
          }
          if (url.includes('/api/jobs/')) {
            return {
              id: 'other_job',
              title: 'Pekerjaan lain',
              status: 'done',
              done: true,
              clips: []
            };
          }
          return {};
        };

        // Render klip awal
        const testJob = {
          id: 'job_nav_1',
          title: 'Uji Navigasi',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_nav_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks transkrip',
            caption: serverJobState.caption,
            metadata_revision: serverJobState.metadata_revision
          }]
        };
        render(testJob);

        const box = document.querySelector('.caption-editor');
        const ta = box.querySelector('textarea');
        const saveBtn = box.querySelector('.btn-save-caption');
        const conflictBanner = box.querySelector('.caption-conflict-banner');

        // 1. Verifikasi beforeunload saat bersih
        const cleanEvt = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(cleanEvt);
        assert(!cleanEvt.defaultPrevented, 'beforeunload tidak dicegah saat draft bersih');

        // 2. Ketik perubahan -> draft kotor
        ta.value = 'Draft penting pengguna';
        ta.dispatchEvent(new Event('input'));
        assert(hasUnsavedCaptionEdits() === true, 'hasUnsavedCaptionEdits bernilai true');

        // 3. Verifikasi beforeunload aplikasi nyata saat kotor
        const dirtyEvt = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(dirtyEvt);
        assert(dirtyEvt.defaultPrevented, 'beforeunload dicegah saat draft kotor');

        // 4. Verifikasi penjaga navigasi #new-job aplikasi nyata
        let confirmPromptMsg = null;
        window.confirm = (msg) => {
          confirmPromptMsg = msg;
          return false; // Pengguna memilih Batal
        };
        document.querySelector('#new-job').click();
        assert(confirmPromptMsg !== null, 'window.confirm dipanggil saat klik #new-job');
        assert(confirmPromptMsg.includes('Ada perubahan caption yang belum disimpan ke server'), 'Pesan konfirmasi #new-job sesuai');
        assert(hasUnsavedCaptionEdits() === true, 'Draft tidak hilang saat konfirmasi #new-job dibatalkan');

        // 5. Verifikasi penjaga openJob aplikasi nyata
        selectedJobId = testJob.id;
        let openJobConfirmMsg = null;
        window.confirm = (msg) => {
          openJobConfirmMsg = msg;
          return false; // Pengguna memilih Batal
        };
        await openJob('other_job_id');
        assert(openJobConfirmMsg !== null, 'window.confirm dipanggil saat openJob');
        assert(openJobConfirmMsg.includes('Ada perubahan caption yang belum disimpan ke server'), 'Pesan konfirmasi openJob sesuai');
        assert(hasUnsavedCaptionEdits() === true, 'Draft tidak hilang saat konfirmasi openJob dibatalkan');

        // 6. Simulasi sesi lain telah menyimpan perubahan di server
        serverJobState.caption = 'Versi terbaru yang disimpan sesi lain';
        serverJobState.metadata_revision = 2;

        const globalLink = document.querySelector('#app-sidebar a[href="/global"]');
        globalLink.click();
        const dialog = document.querySelector('.studio-draft-dialog');
        assert(dialog.open && dialog.textContent.includes('caption'), 'Pindah studio menampilkan pilihan simpan caption');
        dialog.querySelector('.delete-dialog-cancel').click();
        assert(!dialog.open && ta.value === 'Draft penting pengguna', 'Batal mempertahankan draft');

        // Simpan dari dialog navigasi. Revisi lama memicu 409 dan mencegah pindah.
        globalLink.click();
        document.querySelector('.studio-draft-dialog[open] .studio-draft-save').click();
        await new Promise(r => setTimeout(r, 60));
        assert(!document.querySelector('.studio-draft-dialog[open]'), 'Kegagalan simpan mengembalikan pengguna ke editor');

        assert(!conflictBanner.hidden, 'Banner konflik ditampilkan di DOM');
        assert(conflictBanner.textContent.includes('Konflik revisi'), 'Pesan konflik ditampilkan');
        assert(conflictBanner.textContent.includes('Versi terbaru yang disimpan se'), 'Preview revisi server ditampilkan');
        assert(ta.value === 'Draft penting pengguna', 'Draft teks pengguna tetap utuh saat terjadi konflik');
        assert(box.classList.contains('has-unsaved'), 'Draft tetap dirty saat terjadi konflik');
        assert(hasUnsavedCaptionEdits() === true, 'Penjaga navigasi tetap aktif saat banner konflik terbuka');

        // 7. Pilih tindakan "Pakai versi server"
        const actions = conflictBanner.querySelectorAll('button');
        assert(actions.length === 2, 'Dua tombol aksi tersedia di banner konflik');
        const loadServerBtn = actions[0];
        assert(loadServerBtn.textContent.includes('Pakai versi server'), 'Tombol Pakai versi server tersedia');

        loadServerBtn.click();
        assert(ta.value === 'Versi terbaru yang disimpan sesi lain', 'Teks server dimuat ke textarea');
        assert(conflictBanner.hidden, 'Banner konflik ditutup setelah memilih versi server');
        assert(!box.classList.contains('has-unsaved'), 'Status dirty bersih setelah memilih versi server');
        assert(saveBtn.disabled === true, 'Tombol Simpan nonaktif setelah memilih versi server');
        assert(hasUnsavedCaptionEdits() === false, 'Penjaga navigasi bersih setelah memilih versi server');

        // Gunakan tujuan fragment agar hasil pengujian tetap berada di halaman fixture.
        globalLink.setAttribute('href', '#studio-fixture');
        ta.value = 'Caption disimpan saat pindah studio';
        ta.dispatchEvent(new Event('input'));
        globalLink.click();
        document.querySelector('.studio-draft-dialog[open] .studio-draft-save').click();
        await new Promise(r => setTimeout(r, 60));
        assert(serverJobState.caption === ta.value && !hasUnsavedCaptionEdits(), 'Simpan dan pindah menyimpan caption');
        assert(location.hash === '#studio-fixture', 'Navigasi dilanjutkan setelah simpan sukses');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 8)


if __name__ == "__main__":
    unittest.main()
