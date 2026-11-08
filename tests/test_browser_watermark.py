"""
Pengujian interaksi DOM dan layout Watermark di browser menggunakan Google Chrome nyata (Headless).

Cakupan:
1. Render komponen watermarkEditor pada desktop (1280x800): toggle aktif, pemilihan teks vs logo, grid 9 anchor, slider ukuran/opasitas/margin, preview kanvas dan peringatan benturan subtitle.
2. Sinkronisasi dirty state dan penjaga navigasi (beforeunload & confirm) ketika watermark diedit.
3. Responsif layar sempit (375x667): grid posisi, slider, dan preview kanvas tidak meluap keluar viewport.
"""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2

CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class RealBrowserWatermarkTests(unittest.TestCase):
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
            html_file = tmp_path / "wm_browser_test.html"
            user_data_dir = tmp_path / "chrome_user_data_wm"
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

    def test_export_waits_for_watermark_save_and_uses_new_revision(self):
        script = """
        let failSave = true;
        const calls = [];
        window.api = async (url, opts) => {
          if (opts?.method === 'PATCH') {
            calls.push('save');
            if (failSave) throw Error('Simulasi gagal menyimpan');
            return {watermark: JSON.parse(opts.body).watermark, watermark_revision: 4};
          }
          if (url.endsWith('/exports')) {
            calls.push(JSON.parse(opts.body).expected_watermark_revision);
            return {export:{export_id:'fixture', kind:'video', status:'done'}};
          }
          return {presets:[]};
        };
        render({id:'fixture', done:true, clips:[{clip_id:'clip', url:'fixture.mp4', start:0,
          end:3, text:'Fixture', watermark_revision:3, watermark:{enabled:true,type:'text',text:'Awal'}}]});
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));
        const editor = document.querySelector('.watermark-editor');
        const text = editor.querySelector('input[type="text"]');
        text.value = 'Watermark baru';
        text.dispatchEvent(new Event('input'));
        const exportButton = document.querySelector('.clip-output-tools .watermark-actions button');
        exportButton.click();
        await new Promise(resolve => setTimeout(resolve, 50));
        assert(calls.join() === 'save', 'Gagal simpan mencegah permintaan ekspor');
        assert(editor.classList.contains('has-unsaved') && text.value === 'Watermark baru', 'Draft tetap tersedia');
        failSave = false;
        exportButton.click();
        await new Promise(resolve => setTimeout(resolve, 50));
        assert(calls.join() === 'save,save,4', 'Ekspor memakai revisi hasil simpan');
        assert(document.querySelector('.clip-export-list a'), 'Link hasil tampil setelah sukses');
        """
        self._run_chrome_test(script)

    def test_real_browser_watermark_editor_desktop_flow(self):
        """Memverifikasi toggle aktif, pemilihan teks/posisi, peringatan benturan subtitle, dan penyimpanan draft di Chrome desktop."""
        script = """
        let savedToServer = false;
        window.api = async function(url, opts) {
          if (url.includes('/api/watermark-presets')) {
            return { presets: [] };
          }
          if (opts && opts.method === 'PATCH') {
            const body = JSON.parse(opts.body);
            savedToServer = true;
            return {
              clip_id: 'c_wm_1',
              watermark: body.watermark,
              metadata_revision: 2,
              watermark_updated_at: new Date().toISOString()
            };
          }
          return {};
        };

        const testJob = {
          id: 'job_wm_desk',
          title: 'Uji Watermark Desktop',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_wm_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip uji watermark',
            caption: 'Caption klip',
            metadata_revision: 1,
            watermark: {
              enabled: false,
              type: 'text',
              text: '',
              position: 'top_right',
              width_ratio: 0.15,
              opacity: 0.70,
              margin_ratio: 0.03
            }
          }]
        };
        render(testJob);
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));

        const card = document.querySelector('#clips .clip');
        assert(Boolean(card), 'Card klip tersedia');

        const wmBox = card.querySelector('.watermark-editor');
        assert(Boolean(wmBox), 'watermarkEditor ter-render di card');

        const toggle = wmBox.querySelector('.watermark-toggle-wrap input[type="checkbox"]');
        assert(toggle.checked === false, 'Awalnya watermark nonaktif');

        const body = wmBox.querySelector('.watermark-body');
        assert(body.hidden === true, 'Body konfigurasi tersembunyi saat nonaktif');

        const saveBtn = wmBox.querySelector('.btn-save-watermark');
        assert(saveBtn.disabled === true, 'Tombol Simpan nonaktif awal');

        // 1. Aktifkan watermark
        toggle.click();
        assert(toggle.checked === true, 'Toggle aktif');
        assert(body.hidden === false, 'Body konfigurasi tampil');
        assert(wmBox.classList.contains('has-unsaved'), 'has-unsaved aktif setelah toggle');
        assert(hasUnsavedCaptionEdits() === true, 'hasUnsavedCaptionEdits true');

        // 2. Isi teks watermark
        const textInput = wmBox.querySelector('input[type="text"]');
        textInput.value = '@klip.lokal';
        textInput.dispatchEvent(new Event('input'));

        const previewOverlay = wmBox.querySelector('.watermark-preview-overlay');
        assert(previewOverlay.textContent === '@klip.lokal', 'Teks tampil di preview kanvas');

        // 3. Uji peringatan benturan subtitle di posisi bawah
        const clashWarning = wmBox.querySelector('.watermark-clash-warning');
        assert(clashWarning.hidden === true, 'Peringatan benturan belum tampil di posisi atas');

        const btnBottomRight = wmBox.querySelector('button[data-pos="bottom_right"]');
        btnBottomRight.click();
        assert(clashWarning.hidden === false, 'Peringatan benturan tampil saat posisi bawah dipilih');

        // Pindah kembali ke kanan atas
        const btnTopRight = wmBox.querySelector('button[data-pos="top_right"]');
        btnTopRight.click();
        assert(clashWarning.hidden === true, 'Peringatan benturan hilang saat kembali ke posisi atas');

        // 4. Simpan draft watermark
        assert(saveBtn.disabled === false, 'Tombol Simpan aktif');
        saveBtn.click();
        await new Promise(r => setTimeout(r, 60));

        assert(savedToServer === true, 'Request PATCH dikirim ke server');
        assert(saveBtn.disabled === true, 'Tombol Simpan kembali nonaktif setelah sukses');
        assert(!wmBox.classList.contains('has-unsaved'), 'has-unsaved bersih setelah sukses');
        assert(hasUnsavedCaptionEdits() === false, 'hasUnsavedCaptionEdits false setelah sukses');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 6)

    def test_real_browser_watermark_editor_narrow_screen(self):
        """Memverifikasi tampilan editor watermark dan wrapping pada layar sempit (375x667)."""
        script = """
        window.api = () => Promise.resolve({ presets: [] });

        const testJob = {
          id: 'job_wm_narrow',
          title: 'Uji Watermark Layar Sempit',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_wm_narrow_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip',
            caption: 'Caption klip',
            metadata_revision: 1,
            watermark: {
              enabled: true,
              type: 'text',
              text: 'Brand Mobile',
              position: 'top_right',
              width_ratio: 0.15,
              opacity: 0.70,
              margin_ratio: 0.03
            }
          }]
        };
        render(testJob);
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));

        const wmBox = document.querySelector('.watermark-editor');
        const clientWidth = document.documentElement.clientWidth;
        const rect = wmBox.getBoundingClientRect();

        assert(rect.width <= clientWidth, 'Editor watermark pas dalam viewport: ' + rect.width + ' <= ' + clientWidth);
        assert(rect.right <= clientWidth, 'Editor watermark tidak meluap secara horizontal');

        // Grid 9 anchor
        const grid = wmBox.querySelector('.watermark-grid-9');
        const gridRect = grid.getBoundingClientRect();
        assert(gridRect.width <= rect.width, 'Grid 9 anchor pas dalam kontainer');

        // Preview kanvas 9:16
        const previewCanvas = wmBox.querySelector('.watermark-preview-canvas');
        const canvasRect = previewCanvas.getBoundingClientRect();
        assert(canvasRect.width <= rect.width, 'Preview kanvas pas dalam kontainer');
        assert(canvasRect.height > 100, 'Preview kanvas memiliki tinggi proporsional');

        // Tombol simpan
        const saveBtn = wmBox.querySelector('.btn-save-watermark');
        const saveRect = saveBtn.getBoundingClientRect();
        assert(saveRect.width > 50, 'Tombol Simpan memiliki target sentuh memadai');
        """
        logs = self._run_chrome_test(script, window_size="375,667")
        self.assertGreater(len(logs), 4)

    def test_real_browser_conflict_resolution_and_full_form_sync(self):
        """Memverifikasi bahwa tombol 'Pakai versi server' menyinkronkan SELURUH kontrol form watermark (tipe logo, slider, posisi, margin nol)."""
        script = """
        window.api = async function(url, opts) {
          if (url.includes('/api/watermark-presets')) {
            return { presets: [] };
          }
          if (opts && opts.method === 'PATCH') {
            const err = new Error('Konflik revisi');
            err.status = 409;
            err.data = {
              conflict: true,
              current_revision: 5,
              server_watermark: {
                enabled: true,
                type: 'logo',
                asset_id: 'aabbccddeeff0011',
                position: 'bottom_left',
                width_ratio: 0.28,
                opacity: 0.90,
                margin_ratio: 0.0,
                text: 'Diabaikan karena logo',
                text_color: 'black',
                text_treatment: 'panel'
              }
            };
            throw err;
          }
          return {};
        };

        const testJob = {
          id: 'job_wm_sync',
          title: 'Uji Sinkronisasi Form Penuh',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_wm_sync_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip',
            caption: 'Caption klip',
            metadata_revision: 1,
            watermark_revision: 1,
            watermark: {
              enabled: true,
              type: 'text',
              text: 'Draft Pengguna',
              position: 'top_right',
              width_ratio: 0.15,
              opacity: 0.70,
              margin_ratio: 0.03
            }
          }]
        };
        render(testJob);
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));

        const wmBox = document.querySelector('.watermark-editor');
        const textInput = wmBox.querySelector('input[type="text"]');
        const saveBtn = wmBox.querySelector('.btn-save-watermark');

        // Modifikasi teks agar dirty
        textInput.value = 'Perubahan Mau Disimpan';
        textInput.dispatchEvent(new Event('input'));
        assert(saveBtn.disabled === false, 'Tombol simpan aktif');

        // Klik Simpan -> Memperoleh 409 Conflict
        saveBtn.click();
        await new Promise(r => setTimeout(r, 60));

        const conflictBanner = wmBox.querySelector('.caption-conflict-banner');
        assert(conflictBanner.hidden === false, 'Banner konflik tampil');

        const loadServerBtn = conflictBanner.querySelector('button');
        assert(loadServerBtn.textContent.includes('Pakai versi server'), 'Tombol pakai versi server ada');

        // Klik 'Pakai versi server'
        loadServerBtn.click();
        await new Promise(r => setTimeout(r, 60));

        assert(conflictBanner.hidden === true, 'Banner konflik tertutup setelah klik');
        assert(saveBtn.disabled === true, 'Tombol simpan kembali nonaktif (state bersih)');

        // Verifikasi SELURUH kontrol form telah tersinkronisasi ke data server:
        const btnTypeLogo = wmBox.querySelectorAll('.watermark-segmented button')[1];
        assert(btnTypeLogo.classList.contains('active'), 'Tipe watermark berubah jadi Logo');

        const logoPanel = wmBox.querySelector('input[type="file"]').closest('.watermark-field');
        const textPanel = wmBox.querySelector('input[type="text"]').closest('.watermark-field');
        assert(logoPanel.hidden === false, 'Panel logo tampil');
        assert(textPanel.hidden === true, 'Panel teks tersembunyi');

        // Tombol posisi bottom_left aktif
        const btnBottomLeft = wmBox.querySelector('button[data-pos="bottom_left"]');
        assert(btnBottomLeft.classList.contains('active'), 'Posisi bottom_left aktif');

        // Slider tersinkronisasi
        const sliders = wmBox.querySelectorAll('.watermark-slider-wrap input[type="range"]');
        const wSlider = sliders[0];
        const oSlider = sliders[1];
        const mSlider = sliders[2];

        assert(wSlider.value === '28', 'Slider lebar tersinkronisasi ke 28% (actual: ' + wSlider.value + ')');
        assert(oSlider.value === '90', 'Slider opasitas tersinkronisasi ke 90% (actual: ' + oSlider.value + ')');
        assert(mSlider.value === '0', 'Slider margin NOL tersinkronisasi ke 0% tanpa ter-fallback (actual: ' + mSlider.value + ')');

        // Thumbnail logo tampil
        const logoThumbWrap = wmBox.querySelector('.watermark-logo-preview');
        assert(logoThumbWrap.hidden === false, 'Thumbnail logo tampil');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 7)

    def test_real_browser_preview_geometry_and_center_alignment(self):
        """Memverifikasi bahwa center_left dan center_right memiliki top: 50% dan margin nol rapat ke tepi pada kanvas preview."""
        script = """
        window.api = () => Promise.resolve({ presets: [] });

        const testJob = {
          id: 'job_wm_geo',
          title: 'Uji Geometri Preview',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_wm_geo_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip',
            caption: 'Caption klip',
            watermark_revision: 1,
            watermark: {
              enabled: true,
              type: 'text',
              text: 'GeoTest',
              position: 'center_left',
              width_ratio: 0.20,
              opacity: 0.80,
              margin_ratio: 0.0
            }
          }]
        };
        render(testJob);
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));

        const wmBox = document.querySelector('.watermark-editor');
        const overlay = wmBox.querySelector('.watermark-preview-overlay');

        // 1. Verifikasi center_left: top harus 50%, transform translateY(-50%), left rapat 0px karena margin_ratio=0
        assert(overlay.style.top === '50%', 'center_left menetapkan top: 50%');
        assert(overlay.style.transform.includes('translateY(-50%)'), 'center_left menetapkan transform translateY(-50%)');
        assert(overlay.style.left === '0px', 'margin_ratio 0 menetapkan left: 0px persis rapat tepi');

        // 2. Ganti ke center_right
        const btnCenterRight = wmBox.querySelector('button[data-pos="center_right"]');
        btnCenterRight.click();

        assert(overlay.style.top === '50%', 'center_right menetapkan top: 50%');
        assert(overlay.style.transform.includes('translateY(-50%)'), 'center_right menetapkan transform translateY(-50%)');
        assert(overlay.style.right === '0px', 'center_right margin 0 menetapkan right: 0px rapat tepi');

        // 3. Ganti ke center murni
        const btnCenter = wmBox.querySelector('button[data-pos="center"]');
        btnCenter.click();

        assert(overlay.style.top === '50%', 'center menetapkan top: 50%');
        assert(overlay.style.left === '50%', 'center menetapkan left: 50%');
        assert(overlay.style.transform.includes('translate(-50%, -50%)'), 'center menetapkan transform translate(-50%, -50%)');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 6)

    def test_real_browser_tall_logo_clash_detection_and_lifecycle(self):
        """Memverifikasi deteksi benturan logo tinggi (100x500) di center 30% pada browser nyata, termasuk saat reload, slider, dan pemulihan konflik."""
        script = """
        let patchCalled = false;
        window.api = async function(url, opts) {
          if (url.includes('/api/watermark-presets')) {
            return { presets: [] };
          }
          if (opts && opts.method === 'PATCH') {
            patchCalled = true;
            return {
              clip_id: 'c_wm_tall_1',
              watermark: {
                enabled: true,
                type: 'logo',
                asset_id: 'tall100x500logo',
                asset_width: 100,
                asset_height: 500,
                position: 'center',
                width_ratio: 0.30,
                opacity: 0.80,
                margin_ratio: 0.03
              },
              watermark_revision: 2,
              clash_detected: true,
              clash_message: 'Kotak watermark bertabrakan dengan area subtitle video (bawah).'
            };
          }
          return {};
        };

        const testJob = {
          id: 'job_wm_tall',
          title: 'Uji Logo Tinggi Browser',
          status: 'done',
          done: true,
          audience: 'local',
          clips: [{
            clip_id: 'c_wm_tall_1',
            url: 'data/test.mp4',
            start: 0,
            end: 15,
            text: 'Teks klip',
            caption: 'Caption klip',
            watermark_revision: 1,
            watermark: {
              enabled: true,
              type: 'logo',
              asset_id: 'tall100x500logo',
              asset_width: 100,
              asset_height: 500,
              position: 'center',
              width_ratio: 0.30,
              opacity: 0.80,
              margin_ratio: 0.03
            }
          }]
        };
        render(testJob);
        document.querySelector('.clip-review summary').click();
        await new Promise(resolve => setTimeout(resolve, 50));

        const wmBox = document.querySelector('.watermark-editor');
        const clashWarning = wmBox.querySelector('.watermark-clash-warning');

        // 1. Verifikasi initial render: logo 100x500 di posisi center dengan lebar 30%
        // Bounding box pada preview 140x248: w=42px, h=210px, oy=19px -> oy+h=229px > 178px (subtitle zone).
        // Peringatan benturan HARUS tampil meskipun posisinya adalah 'center' (bukan 'bottom')!
        assert(clashWarning.hidden === false, 'Logo tinggi di center harus terdeteksi bentrok pada initial render');

        // 2. Ubah posisi ke top_center dan perkecil lebar ke 10%
        const btnTopCenter = wmBox.querySelector('button[data-pos="top_center"]');
        const wSlider = wmBox.querySelectorAll('.watermark-slider-wrap input[type="range"]')[0];
        wSlider.value = '10';
        wSlider.dispatchEvent(new Event('input'));
        btnTopCenter.click();

        // Di top_center dengan lebar 10%: w=14px, h=70px, oy=4px -> oy+h=74px < 178px.
        // Peringatan benturan HARUS hilang!
        assert(clashWarning.hidden === true, 'Peringatan benturan harus hilang saat logo dipindahkan ke atas dengan ukuran kecil');

        // 3. Kembalikan ke center dan lebar 25% (masih bentrok dengan subtitle karena logo tinggi rasio 5:1)
        wSlider.value = '25';
        wSlider.dispatchEvent(new Event('input'));
        const btnCenter = wmBox.querySelector('button[data-pos="center"]');
        btnCenter.click();
        assert(clashWarning.hidden === false, 'Peringatan benturan kembali muncul di center 25%');

        // 4. Simpan draft watermark ke backend mock
        const saveBtn = wmBox.querySelector('.btn-save-watermark');
        assert(saveBtn.disabled === false, 'Tombol simpan aktif karena draft kotor');
        saveBtn.click();
        await new Promise(r => setTimeout(r, 60));

        assert(patchCalled === true, 'Endpoint PATCH dipanggil');
        assert(clashWarning.hidden === false, 'Peringatan benturan dari respons backend dipertahankan');
        assert(clashWarning.textContent.includes('bertabrakan'), 'Pesan peringatan benturan sesuai respons server');
        """
        logs = self._run_chrome_test(script, window_size="1280,800")
        self.assertGreater(len(logs), 5)


if __name__ == "__main__":
    unittest.main()
