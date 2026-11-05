# Pengujian

Jalankan dari root repository dengan environment Python dan runtime Node yang sudah dipasang lewat [SETUP](SETUP.md). Command di bawah bersifat portabel dalam checkout; bila lingkungan agent mewajibkan RTK, gunakan `rtk proxy` di depannya.

## Pemeriksaan otomatis

```sh
.venv/bin/python -m unittest discover -s tests -q
runtime/node_modules/node/bin/node tests/test_api_errors.cjs
runtime/node_modules/node/bin/node tests/test_delete_dialog.cjs
runtime/node_modules/node/bin/node tests/test_ui_dirty_state.cjs
runtime/node_modules/node/bin/node --check static/app.js
runtime/node_modules/node/bin/node --check static/custom-select.js
.venv/bin/python -m pip check
git diff --check
```

Suite Python memakai direktori sementara dan sebagian tes melakukan render FFmpeg nyata. Tes model caption memakai mock transport; tes ini tidak membutuhkan Ollama, mengunduh model atau membuktikan kualitas AI sebenarnya. Hindari server kedua yang memakai `data/` produksi saat menjalankan pengujian.

## Memilih cakupan

| Perubahan | Pemeriksaan relevan |
| --- | --- |
| Riwayat/metadata/hapus | `test_history.py`, `test_history_pagination.py` |
| Resolusi, crop, audio/subtitle hasil | `test_resolution.py`, `test_speech_cuts.py` |
| Preset tampilan subtitle | `test_subtitle_styles.py` dan preview browser |
| Caption dasar/kompatibilitas | `test_caption.py` |
| Caption persisten & optimistic concurrency | `test_caption_persistence.py`, `test_ui_dirty_state.cjs`, `test_browser_caption.py` |
| Watermark (konfigurasi, aset, preset, benturan, render) | `test_watermark.py`, `test_browser_watermark.py` |
| AI caption dan regenerasi API | `test_local_caption.py` serta uji model nyata bila prompt/runtime berubah |
| Studio Global | `test_global_studio.py` |
| Fetch/error frontend | `test_api_errors.cjs` dan state error browser |
| Dokumentasi saja | Tautan lokal, kesesuaian kode, `git diff --check` |

Contoh menjalankan satu modul:

```sh
.venv/bin/python -m unittest discover -s tests -p test_local_caption.py -v
```

## Verifikasi browser

Untuk perubahan UI, periksa alur yang terdampak pada desktop dan layar sempit. State penting: belum ada history, sedang memproses, berhasil, gagal, pencarian kosong, halaman history terakhir, pemilihan dropdown dengan keyboard, draft caption yang diedit dan konfirmasi penggantiannya. Periksa error console dan simpan bukti tampilan bila membantu review.

Gunakan fixture sementara untuk menguji penghapusan. Jangan menghapus history pengguna. Jangan memulai video baru atau restart jika sedang ada pekerjaan aktif. Probe health tersedia di `GET /api/health`; `active_jobs` dan `active_caption` menunjukkan aktivitas server.

## Verifikasi media dan AI nyata

Gunakan video percakapan pendek dengan izin pemakaian yang jelas. Periksa awal/akhir ucapan, crop, stream audio, ukuran frame, subtitle, serta makna caption. Keberhasilan unggahan tidak membuktikan download YouTube bekerja; uji jalur tersebut terpisah bila downloader diubah.

Untuk caption, siapkan contoh Indonesia/Inggris dengan topik berbeda dan contoh transkrip berulang/tidak jelas. Pastikan ringkasan tidak sekadar menyalin pembuka, tetap singkat, kutipan pendukung sesuai, dan kegagalan tidak merusak video/draft sebelumnya. Model dapat menolak ringkasan yang sebenarnya layak dan tetap dapat melakukan kesalahan; laporkan hasil serta batasnya.

## Menulis hasil pemeriksaan

Cantumkan command, hasil, dan pemeriksaan manual yang benar-benar dilakukan. Bedakan tes dengan mock, render media nyata dan inferensi AI nyata. Jumlah tes dapat berubah; gunakan hasil runner terbaru, bukan angka lama dalam dokumentasi. Belum ada benchmark akurasi semua bahasa, beban banyak video, atau cakupan semua codec/platform.


`test_setup_local.py` memeriksa pemilihan Python kompatibel, instalasi yang aman diulang, marker requirements setelah kegagalan, pelestarian environment tidak kompatibel, penolakan platform yang belum didukung, reuse model, dan stream unduhan/validasinya. Pengujian instalasi nyata harus membedakan environment aplikasi baru dengan Ollama/model global yang mungkin sudah tersedia.


Tes `test_delete_dialog.cjs` memakai DOM stub untuk memastikan hanya konfirmasi eksplisit menghasilkan true; Batal, Escape, tutup dan backdrop menghasilkan false, judul tidak dimasukkan sebagai HTML, dan pembukaan ganda ditolak. Ini bukan tes layout/fokus browser. Dialog juga perlu diperiksa secara visual dan dengan keyboard di browser tanpa menghapus history pengguna.


Regresi keamanan/state K1: `test_kids_studio.py` memeriksa markup literal tersimpan, validasi tipe/enum/revisi dan batas32KiB. `tests/kids_ui_regression.js` digunakan oleh `test_browser_kids_studio.py` untuk memastikan teks menjadi textContent, deferred save mengunci form/konteks, klik ganda ditolak, kegagalan mempertahankan dirty, serta navigasi dilindungi. API pada tes UI adalah fixture; hasilnya bukan smoke test dua tab Flask live atau pemeriksaan dialog tutup-tab native.
