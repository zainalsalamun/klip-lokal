# Peta alur pengembangan

Panduan memilih alur kerja untuk developer dan coding agent Klip lokal. Baca [AGENTS.md](AGENTS.md) untuk aturan repository. Dokumen ini adalah panduan proyek; bukan paket skill yang otomatis terpasang pada editor/agent.

## Memilih alur

| Kebutuhan | Source utama | Referensi dan verifikasi |
| --- | --- | --- |
| Instalasi komputer baru | `kelip/setup_local.py`, `dev.sh`, `Mulai.command`, `package.json` | [NEW_MACHINE](docs/NEW_MACHINE.md), `test_setup_local.py`, setup pada environment terpisah |
| Menjalankan/mendiagnosis server | `kelip/serverctl.py`, `kelip/app.py` | [SETUP](docs/SETUP.md), [TROUBLESHOOTING](docs/TROUBLESHOOTING.md), health dan log saat idle |
| Pemilihan/batas waktu klip | `candidates()` di `kelip/app.py` | [ARCHITECTURE](docs/ARCHITECTURE.md), `test_speech_cuts.py`, periksa audio awal/akhir klip nyata |
| Crop mengikuti pembicara | `kelip/speaker_crop.py`, `render_clip()` | `test_speech_cuts.py`, `test_resolution.py`, video multipembicara dan fallback |
| Tampilan subtitle/resolusi | `kelip/subtitle_styles.py`, `write_subs()`, template dan JS | `test_subtitle_styles.py`, `test_resolution.py`, preview serta MP4 nyata |
| Caption AI lokal | `kelip/local_caption.py`, endpoint caption dan editor JS | [LOCAL_AI](docs/LOCAL_AI.md), `test_local_caption.py`, contoh model nyata jika prompt berubah |
| Studio Anak dan ekspor turunan | `kelip/kids_content.py`, `kelip/clip_exports.py`, endpoint kids/exports dan editor JS | [K2/K3](docs/reviews/KIDS_K2_K3_IMPLEMENTATION.md), `test_kids_pipeline_exports.py`, media fixture dan browser live terisolasi |
| History, pencarian dan hapus | Route metadata di `kelip/app.py`, `static/app.js` | [API](docs/API.md), `test_history.py`, `test_history_pagination.py` |
| Studio Global | `kelip/global_content.py`, worker dan template | [GLOBAL](docs/GLOBAL.md), `test_global_studio.py`; audio tetap asli |
| UI dan dropdown | `templates/index.html`, `static/` | [USAGE](docs/USAGE.md), browser desktop/layar sempit dan keyboard |
| Penanganan error frontend | `api()`, polling dan rendering di JS | `tests/test_api_errors.cjs`, respons jaringan/API dan kesalahan UI |

Nama tes Python pada tabel berada dalam folder `tests/`. Command lengkap tersedia di [TESTING](docs/TESTING.md).

## Alur implementasi

1. Tentukan perilaku akhir dan bagian yang terdampak. Baca implementasi aktual serta dokumen terkait; jangan menganggap usulan pada [ROADMAP](docs/ROADMAP.md) sudah tersedia.
2. Periksa status Git dan pertahankan perubahan lain. Gunakan fixture sementara untuk tes, bukan history pengguna.
3. Ubah source, validasi input, kompatibilitas metadata dan UI yang berkaitan secara konsisten. Hindari perubahan di luar ruang lingkup.
4. Jalankan pemeriksaan yang relevan. Tes otomatis dengan mock tidak membuktikan kualitas transkripsi atau model AI. Perubahan media perlu pemeriksaan hasil render; perubahan UI perlu verifikasi browser.
5. Perbarui dokumen dan laporkan hasil nyata beserta batasnya. Ikuti [CONTRIBUTING](CONTRIBUTING.md) untuk penyerahan perubahan.

## Pemeriksaan khusus per alur

### Instalasi dan runtime

Pisahkan prasyarat sistem, dependensi checkout, model Whisper dan model Ollama. Setup harus aman diulang, melaporkan kegagalan dengan tindakan yang jelas, dan tidak menghapus environment/data pengguna. `doctor` harus tetap baca-saja. Jangan mengklaim Windows/Linux didukung hanya karena Ollama tersedia di sana.

### Pipeline video

Pertahankan stream audio asli, ukuran ekspor yang dipilih, subtitle yang terbakar dan metadata batas klip. Gunakan contoh yang mengandung jeda, kalimat panjang, wajah hilang, scene cut dan pembicara bergantian. Jangan menghentikan pekerjaan aktif untuk restart saat menguji.

### Caption AI

Periksa contoh Indonesia/Inggris, pembuka yang bukan inti pembahasan, transkrip berulang dan klaim tambahan yang tidak didukung. Jangan mengganti penolakan dengan caption hasil tebakan. Model tidak membaca gambar. Kegagalan caption harus tetap menyisakan MP4 yang berhasil dibuat; regenerasi hanya memperbarui metadata.

### UI dan history

Menu history tetap di sidebar, daftar di area utama. Periksa empty/loading/error, filter, pagination terakhir, draft manual, konfirmasi penggantian draft dan akses keyboard. Error JavaScript bukan bukti server terputus. Jangan menghapus history pengguna untuk menguji tombol Hapus.

## Menambah alur baru

Tambahkan kebutuhan, source terkait, dokumen, pemeriksaan dan batasnya pada tabel. Jika alur memerlukan keputusan arsitektur baru, catat alasan serta tradeoff di [DECISIONS](docs/DECISIONS.md). Hindari menggandakan seluruh spesifikasi API atau petunjuk instalasi dalam dokumen ini.
