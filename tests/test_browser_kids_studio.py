"""
Pengujian interaksi DOM, filter ide, form brief, OCC, dan layout browser Studio Anak
menggunakan Google Chrome nyata (Headless).
"""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2

import kids_content

CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


class RealBrowserKidsStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CHROME_PATH.exists():
            raise unittest.SkipTest("Google Chrome tidak ditemukan di /Applications/Google Chrome.app")

    def test_kids_literal_text_pending_save_and_navigation(self):
        script = (Path(__file__).parent / "kids_ui_regression.js").read_text()
        self._run_chrome_test(script)

    def _run_chrome_test(self, test_script_js, window_size="1280,800", virtual_time=3000):
        root = Path(__file__).resolve().parent.parent
        tmpl_src = (root / "templates" / "index.html").read_text()
        tmpl = jinja2.Template(tmpl_src)
        page_html = tmpl.render(
            global_mode=False,
            kids_mode=True,
            asset_version="test",
            subtitle_styles={"classic": {"label": "Klasik", "description": "Teks tebal"}},
            ideas=kids_content.IDEAS,
            categories=kids_content.CATEGORIES,
            sources=kids_content.SOURCES,
        )

        style_css = (root / "static" / "style.css").read_text()
        custom_select_js = (root / "static" / "custom-select.js").read_text()
        app_js = (root / "static" / "app.js").read_text()

        # Inject capture for unhandled errors
        error_capture = """
        <script>
        window.browserErrors = [];
        window.addEventListener('error', e => {
          const detail = (e.message || '') + ' at line ' + (e.lineno || '?') + ':' + (e.colno || '?') + '\\n' + (e.error ? e.error.stack : '');
          window.browserErrors.push(detail);
        });
        window.addEventListener('unhandledrejection', e => window.browserErrors.push(String(e.reason && e.reason.stack ? e.reason.stack : e.reason)));
        </script>
        """

        full_html = page_html.replace(
            '<head>',
            f'<head>{error_capture}',
        ).replace(
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
            if (!cond) {{
              const err = 'ASSERTION FAILED: ' + msg;
              testLogs.push(err);
              throw new Error(err);
            }}
            testLogs.push('PASS: ' + msg);
          }}

          try {{
            {test_script_js}
            document.getElementById('test-results').textContent = JSON.stringify({{
              success: true,
              logs: testLogs,
              browserErrors: window.browserErrors || []
            }});
          }} catch (err) {{
            document.getElementById('test-results').textContent = JSON.stringify({{
              success: false,
              error: String(err && err.stack ? err.stack : err),
              logs: testLogs,
              browserErrors: window.browserErrors || []
            }});
          }}
        }})();
        </script>
        """

        full_html = full_html.replace("</body>", f"{runner_script}</body>")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            html_file = tmp_path / "browser_page_test.html"
            user_data_dir = tmp_path / "chrome_user_data"
            html_file.write_text(full_html)

            cmd = [
                str(CHROME_PATH),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--window-size={window_size}",
                f"--virtual-time-budget={virtual_time}",
                f"--user-data-dir={user_data_dir}",
                f"file://{html_file}",
                "--dump-dom",
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
            dom_out = res.stdout

            marker = '<pre id="test-results" style="display:none;">'
            if marker not in dom_out:
                self.fail(f"Test runner tidak menemukan output di DOM. Stderr: {res.stderr[:500]}")

            json_str = dom_out.split(marker, 1)[1].split("</pre>", 1)[0]
            data = json.loads(json_str)

            if not data.get("success"):
                self.fail(f"Pengujian di browser gagal: {data.get('error')}\nLogs: {data.get('logs')}\nBrowserErrors: {data.get('browserErrors')}")

            # Pastikan tidak ada unhandled exception / null-form error di console
            self.assertEqual(data.get("browserErrors"), [], f"Ditemukan error console tak tertangani: {data.get('browserErrors')}")

            return data

    def test_browser_zero_null_form_errors_and_navigation(self):
        """Memastikan Studio Anak di Chrome tidak memiliki error null form dan navigasi header sesuai."""
        js = """
        await new Promise(r => setTimeout(r, 200));

        assert(document.body.classList.contains('kids-studio'), 'Body memiliki class kids-studio');
        const headerTitle = document.querySelector('header>span').textContent;
        assert(headerTitle.includes('Studio Anak'), 'Header memuat teks Studio Anak: ' + headerTitle);

        const kidsNav = document.querySelector('#app-sidebar .nav.active[href="/kids"]');
        assert(Boolean(kidsNav), 'Sidebar link Studio Anak dalam keadaan active');

        const cards = document.querySelectorAll('.kids-idea-card');
        assert(cards.length >= 10, 'Katalog ide memuat minimal 10 kartu ide: ' + cards.length);
        """
        self._run_chrome_test(js)

    def test_browser_catalog_category_filters(self):
        """Memastikan filter kategori bekerja dinamis pada kartu ide di DOM."""
        js = """
        await new Promise(r => setTimeout(r, 200));

        const filterWarna = document.querySelector('.kids-filter-btn[data-category="warna"]');
        assert(Boolean(filterWarna), 'Tombol filter warna tersedia');
        filterWarna.click();

        const allCards = [...document.querySelectorAll('.kids-idea-card')];
        const visibleCards = allCards.filter(c => !c.hidden);
        assert(visibleCards.length > 0, 'Ada kartu yang tampil setelah filter warna');
        for (const c of visibleCards) {
          assert(c.dataset.category === 'warna', 'Kartu yang tampil berkategori warna: ' + c.dataset.category);
        }

        // Kembalikan ke filter semua
        const filterAll = document.querySelector('.kids-filter-btn[data-category="all"]');
        filterAll.click();
        const allVisible = allCards.filter(c => !c.hidden);
        assert(allVisible.length === allCards.length, 'Semua kartu kembali tampil saat filter all dipilih');
        """
        self._run_chrome_test(js)

    def test_browser_use_idea_and_brief_crud_lifecycle(self):
        """Menguji tombol 'Pakai ide', pengisian form, character count, simpan brief, dan penanganan konflik."""
        js = """
        await new Promise(r => setTimeout(r, 200));

        // Intercept network call api() untuk fixture browser terkontrol
        let savedBriefOnServer = null;
        let serverRev = 1;
        let simulateConflictNext = false;

        window.api = async (path, options = {}) => {
          const method = options.method || 'GET';
          if (path === '/api/kids/briefs' && method === 'GET') {
            return { briefs: savedBriefOnServer ? [savedBriefOnServer] : [], total: savedBriefOnServer ? 1 : 0, total_pages: 1, page: 1 };
          }
          if (path === '/api/kids/briefs' && method === 'POST') {
            const body = JSON.parse(options.body);
            savedBriefOnServer = {
              brief_id: 'b1b2c3d4e5f678901234567890123456',
              revision: 1,
              ...body,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            };
            return { brief: savedBriefOnServer };
          }
          if (path.startsWith('/api/kids/briefs/') && method === 'PATCH') {
            if (simulateConflictNext) {
              simulateConflictNext = false;
              const err = new Error('HTTP 409 Conflict');
              err.cause = { status: 409 };
              throw err;
            }
            const body = JSON.parse(options.body);
            serverRev++;
            savedBriefOnServer = {
              ...savedBriefOnServer,
              ...body,
              revision: serverRev,
              updated_at: new Date().toISOString()
            };
            return { brief: savedBriefOnServer };
          }
          if (path.startsWith('/api/kids/briefs/') && method === 'GET') {
            return { brief: savedBriefOnServer };
          }
          return { jobs: [] };
        };

        // 1. Klik 'Pakai ide ini' pada kartu pertama
        const firstUseBtn = document.querySelector('.use-kids-idea');
        assert(Boolean(firstUseBtn), 'Tombol Pakai ide ditemukan');
        firstUseBtn.click();

        const titleInput = document.querySelector('#brief-title');
        const goalInput = document.querySelector('#brief-goal');
        const catSelect = document.querySelector('#brief-category');
        const durSelect = document.querySelector('#brief-duration');

        assert(titleInput.value.length > 0, 'Judul terisi dari ide: ' + titleInput.value);
        assert(goalInput.value.length > 0, 'Tujuan belajar terisi');
        assert(catSelect.value.length > 0, 'Kategori terpilih');

        // 2. Klik simpan brief (POST baru)
        const saveBtn = document.querySelector('#save-brief-btn');
        saveBtn.click();
        await new Promise(r => setTimeout(r, 100));

        const feedback = document.querySelector('#brief-feedback');
        assert(feedback.textContent.includes('Brief tersimpan (Revisi 1)'), 'Feedback sukses simpan pertama: ' + feedback.textContent);
        const statusTag = document.querySelector('#brief-status-tag');
        assert(statusTag.textContent.includes('Tersimpan (Revisi 1)'), 'Status tag tersimpan: ' + statusTag.textContent);

        // 3. Edit judul -> dirty state
        titleInput.value = titleInput.value + ' - Tambahan';
        titleInput.dispatchEvent(new Event('input', { bubbles: true }));
        assert(statusTag.textContent.includes('Ada perubahan belum disimpan'), 'Status tag berubah dirty');

        // 4. Simulasikan konflik 409
        simulateConflictNext = true;
        saveBtn.click();
        await new Promise(r => setTimeout(r, 150));

        const conflictBanner = document.querySelector('#brief-conflict-banner');
        assert(!conflictBanner.hidden, 'Banner konflik 409 muncul di UI');

        // 5. Klik 'Pakai versi server'
        const useServerBtn = document.querySelector('#brief-use-server-btn');
        useServerBtn.click();
        assert(conflictBanner.hidden, 'Banner konflik tertutup setelah memakai versi server');
        assert(feedback.textContent.includes('Versi server dimuat'), 'Feedback mengonfirmasi versi server dimuat');
        """
        self._run_chrome_test(js)

    def test_browser_narrow_viewport_layout(self):
        """Memastikan tampilan pada layar sempit (375x667) responsif tanpa horizontal overflow."""
        js = """
        await new Promise(r => setTimeout(r, 200));

        const scrollW = document.documentElement.scrollWidth;
        const clientW = document.documentElement.clientWidth;
        assert(scrollW <= clientW + 2, 'Tidak ada horizontal overflow pada viewport sempit (scrollWidth=' + scrollW + ', clientWidth=' + clientW + ')');

        const editorCard = document.querySelector('.brief-editor-card');
        assert(Boolean(editorCard), 'Brief editor card ada');
        const actionsLeft = document.querySelector('.brief-actions-left');
        assert(Boolean(actionsLeft), 'Tombol aksi brief tersedia');
        """
        self._run_chrome_test(js, window_size="375,667")


if __name__ == "__main__":
    unittest.main()
