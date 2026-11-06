# Pengembangan dan verifikasi

## Struktur source

Baca [CONTRIBUTING](../CONTRIBUTING.md) dan [AGENTS](../AGENTS.md) sebelum mengubah source. Command dan pemilihan pemeriksaan dirangkum di [TESTING](TESTING.md); alasan desain ada di [DECISIONS](DECISIONS.md).

```text
klip-lokal/
  app.py                    server, pipeline, scoring, subtitle dan route
  local_caption.py          ringkasan caption melalui Ollama lokal
  speaker_crop.py           perkiraan pembicara dan posisi crop
  subtitle_styles.py        preset ASS dan label pilihan
  global_content.py         topik dan ide editorial
  AGENTS.md                 panduan coding agent
  CONTRIBUTING.md            alur kontribusi developer
  package.json              dev / start / setup:ai
  dev.sh                    bootstrap dan server foreground
  Mulai.command             launcher server latar belakang macOS
  Berhenti.command          penghentian server
  serverctl.py              start/stop/status melalui launchd
  requirements.txt          pin dependensi Python
  templates/index.html      antarmuka Jinja
  static/app.js             form, polling dan kartu hasil
  static/custom-select.js   menu pilihan, keyboard dan sinkronisasi select
  static/style.css          desain responsif
  runtime/package.json      runtime Node khusus pengunduh
  runtime/package-lock.json lock dependency Node
  docs/                     dokumentasi
  data/                     artefak kerja dan model; diabaikan Git
  .venv/                    lingkungan Python; diabaikan Git
```

`preview.png` adalah screenshot antarmuka, bukan bagian runtime. Seluruh path runtime diturunkan dari lokasi source, sehingga checkout dapat ditempatkan di folder pilihan pengguna. Proyek belum memiliki CI.

## Menjalankan saat mengembangkan

```sh
cd klip-lokal
npm run dev
```

`npm run dev` menyiapkan dependensi dan menghentikan server launcher secara otomatis bila tidak ada pekerjaan aktif. Perintah ini menjalankan server foreground, log terlihat langsung, dan dihentikan dengan Control-C. Alternatif langsung: `./dev.sh`.

Debug/reloader sengaja nonaktif karena worker/model disimpan dalam proses. Restart server saat idle setelah mengubah Python atau template Jinja. Muat ulang browser setelah perubahan aset; hard refresh bila cache masih menampilkan versi lama. Jangan menjalankan beberapa server untuk folder data yang sama.

## Titik konfigurasi di app.py

| Yang diubah | Lokasi |
| --- | --- |
| Host/port | `app.run()` di akhir berkas |
| Ukuran request | `MAX_CONTENT_LENGTH` |
| Model dan compute | `WhisperModel()` dalam `process()` |
| Bahasa/durasi/jumlah yang diterima | Validasi `create()`; selaraskan opsi HTML |
| Skor kandidat | `candidates()` |
| Tampilan subtitle | `subtitle_styles.py` dan `write_subs()` |
| Caption AI lokal | `local_caption.py`, endpoint regenerasi dan editor di JS |
| Resolusi, crop, codec | `RESOLUTIONS` dan `render_clip()` |
| Download format/runtime | Opsi `yt_dlp.YoutubeDL()` |

Jika port berubah, sesuaikan alamat pada `Mulai.command`, URL serta probe socket di `serverctl.py`, dan dokumentasi. Kanvas ASS tetap 720×1280; renderer menskalakannya mengikuti ukuran hasil. Jika menambah preset resolusi, selaraskan `RESOLUTIONS`, opsi HTML, dan `outputSizes` di JavaScript. Belum ada konfigurasi melalui environment untuk parameter tersebut.

## Pemeriksaan cepat

```sh
.venv/bin/python -m compileall -q app.py
runtime/node_modules/node/bin/node --check static/app.js
.venv/bin/python -m pip check
```

Pemeriksaan route tanpa memulai unduhan:

```sh
.venv/bin/python - <<'PYTEST'
from app import app
c = app.test_client()
assert c.get('/').status_code == 200
assert c.post('/api/jobs').status_code == 400
assert c.post('/api/jobs', data={'url': 'https://example.com'}).status_code == 400
assert c.get('/files/bad/source.mp4').status_code == 404
print('Smoke check OK')
PYTEST
```

Smoke check membuktikan impor, rendering dan beberapa validasi; tidak membuktikan transkripsi atau ekspor.

## Uji end-to-end manual

1. Siapkan video percakapan 20–60 detik dengan suara jelas dan izin penggunaan yang sesuai.
2. Jalankan server, unggah video, pilih 15 detik / 1 kandidat / bahasa yang benar.
3. Pastikan proses selesai dan tidak ada `error` pada status.
4. Putar dan unduh MP4; periksa audio, crop, subtitle dan kecocokan isi.
5. Verifikasi resolusi dan audio dengan PyAV, mengganti path contoh dengan berkas hasil:

```sh
.venv/bin/python - <<'PYTEST'
import av
with av.open('data/ID_PEKERJAAN/clip-1.mp4') as media:
    video = media.streams.video[0]
    assert (video.width, video.height) == (720, 1280)
    assert len(media.streams.audio) > 0
    print('Resolusi dan audio OK')
PYTEST
```

6. Ulangi dengan URL YouTube publik untuk memeriksa jalur download. Keberhasilan unggahan tidak membuktikan extractor YouTube masih berfungsi.
7. Coba dua request berturut-turut saat proses masih aktif; yang kedua seharusnya 409. Coba refresh browser selama pemrosesan untuk memeriksa pemulihan ID dari localStorage.

## Verifikasi yang telah dilakukan

Pada laptop ini: impor dependensi, dukungan filter subtitle FFmpeg, route dasar, sintaks Python/JavaScript, unduhan YouTube publik, pipeline video percakapan sintetis hingga MP4, serta resolusi dan stream audio hasil telah diperiksa. UI responsif sempit dan pesan form kosong ditinjau di browser. Tes regresi history tersedia melalui `.venv/bin/python -m unittest discover -s tests -v`: meliputi hasil lama setelah pekerjaan baru/restart, metadata unggahan, record lama/rusak dan validasi pekerjaan bersamaan. Belum ada pengujian beban, cakupan semua codec, atau evaluasi akurasi transkripsi/pemilihan klip.

## Berkas untuk Git

Commit source, dokumentasi, `requirements.txt`, `package.json` dan `runtime/package-lock.json`. `.gitignore` mengecualikan lingkungan virtual, dependensi Node, cache, data/model/hasil video, dan file environment lokal. Hasil pemrosesan dan log berada di `data/`; tidak perlu dimasukkan ke repository. Setiap pengguna membuat dependensinya sendiri setelah clone. Jangan menaruh path absolut komputer pribadi dalam dokumentasi publik atau source.

## Pengembangan berikutnya

Peningkatan yang belum tersedia meliputi penyelarasan kata subtitle, pemilihan semantik, deteksi pembicara berbasis model audio-visual, editor manual, cancel/resume dan cleanup. Jika hendak hosting online, pisahkan worker video dari web server dan rancang ulang akses/data; lihat batas deployment di [arsitektur](ARCHITECTURE.md).

## Verifikasi pengelolaan server

Controller `status`, start idempotent, stop dan start kembali telah diuji. Endpoint halaman, JavaScript, favicon dan health memberi respons berhasil. Request unggah melalui HTTP nyata diterima 202, diproses oleh worker launchd hingga selesai, dan MP4 hasil berhasil diunduh.

## Verifikasi riwayat di browser

Alur **Buat klip baru → kirim link YouTube → selesai** diuji di browser: jumlah riwayat bertambah dari 3 menjadi 4 tanpa kehilangan pekerjaan sebelumnya. Membuka hasil lama serta refresh dengan pilihan history terakhir juga berhasil.

## Uji resolusi

`tests/test_resolution.py` melakukan ekspor FFmpeg nyata untuk 480×854, 720×1280 dan 1080×1920, memverifikasi ukuran frame, stream audio, serta piksel subtitle pada video. Tes juga memeriksa validasi preset, penerusan ke worker dan penyimpanan pilihan setelah memuat ulang data. Jalankan bersama tes history melalui unittest discover.

Menu dropdown kustom mempertahankan elemen select asli sebagai sumber FormData. Setelah mengubah nilai select melalui kode, panggil `KlipSelect.refresh()`; reset form ditangani otomatis. Interaksi klik, keyboard dan reset telah diperiksa di browser.

## Uji penghapusan riwayat

Tes menggunakan direktori sementara: seluruh artefak target terhapus, metadata tidak lagi muncul, hasil menjadi 404, model/pekerjaan lain tetap ada, pekerjaan aktif ditolak, pekerjaan terputus bisa dihapus, symlink/path tidak valid ditolak dan kesalahan disk ditampilkan. Data video pengguna tidak dihapus dalam tes.

## Caption posting

`local_caption.summarize()` membuat ringkasan topik setelah ekspor klip. Endpoint regenerasi memungkinkan history lama mendapat caption AI tanpa ekspor ulang. `make_caption()`/`legacy_caption()` dan fallback JS mempertahankan kompatibilitas caption lama, yang diberi label belum dirangkum AI. Draft manual disimpan di localStorage; caption AI disimpan pada metadata server. UI meminta konfirmasi di halaman sebelum mengganti draft yang diedit. Lihat [LOCAL_AI](LOCAL_AI.md) dan [TESTING](TESTING.md) untuk batas dan verifikasinya.

## Uji riwayat banyak

`tests/test_history_pagination.py` membuat 1.000 metadata pekerjaan di direktori sementara, memeriksa ukuran respons/halaman, urutan tanpa overlap, pencarian, filter, deteksi pekerjaan aktif di luar halaman, cache dan invalidasinya. Penghapusan baris terakhir di halaman terakhir harus kembali ke halaman valid. Pengujian ini tidak membuat atau memuat 1.000 file video dan bukan benchmark kapasitas penyimpanan.

## Pengembangan Studio Global

Ide terkurasi berada di `global_content.py`. Tambahkan topik secara serentak pada `TOPICS`, kartu ide, opsi template dan dokumentasi. Tes `test_global_studio.py` mencakup route/ide, validasi input, penerusan konfigurasi, pemilihan task transcribe/translate, caption Inggris, penggunaan sumber audio yang sama dan bobot niche. Dokumentasi khusus tersedia di GLOBAL.md.

## Navigasi riwayat

Sidebar hanya berisi menu **Riwayat klip**. Konten history berada di area utama dan dibuka lewat hash `#history`; `syncView()` menukar tampilan studio/history. Search, filter, pagination dan hapus tetap tersedia di halaman lebar. Pada layar ≤820px sidebar navigasi menjadi drawer dengan backdrop, Escape, focus trap dan inert saat tertutup. Membuka hasil mengembalikan tampilan studio.

## Uji klasifikasi error frontend

Jalankan `runtime/node_modules/node/bin/node tests/test_api_errors.cjs` untuk memeriksa pemisahan kegagalan fetch, TypeError UI, penolakan API, respons non-JSON, dan respons sukses. Aset CSS/JS memakai query versi berdasarkan waktu perubahan agar pembaruan template dan script konsisten.


Tes `test_speech_cuts.py` memeriksa segmen ucapan utuh, akhir kalimat, batas durasi, non-overlap dan hysteresis crop. `test_resolution.py` juga memeriksa render crop dinamis nyata menggunakan sumber warna kiri/kanan dan membandingkan piksel frame awal/akhir, bukan hanya command. Heuristik deteksi pembicara tidak menjamin akurasi semua video; belum ada benchmark diarization.


`tests/test_subtitle_styles.py` memeriksa validasi preset, penyimpanan/restart, penerusan opsi worker, fallback history lama, dan render MP4 semua gaya di 480p serta 720p. Frame ekspor dibandingkan agar setiap preset benar-benar berbeda; piksel kuning juga diverifikasi. Preset default mempertahankan ASS style sebelumnya. Untuk menambah gaya, daftarkan di `subtitle_styles.py` dan tambahkan aturan preview CSS dengan nama preset yang sama.


Caption semantik: `local_caption.py` memakai Ollama loopback dengan JSON schema, `think=false`/context 2048 pada percobaan awal dan `think=true`/context 3072 saat memperbaiki bahasa, batas output, kutipan pendukung verbatim dan penolakan transkrip tidak jelas. `tests/test_local_caption.py` menguji payload bahasa/privasi lokal, parsing/validasi, model tidak tersedia, persistensi endpoint, pelestarian video/caption pada kegagalan dan guard video aktif. Unit test memalsukan transport AI; uji model nyata dilakukan terpisah sesudah setup.


Pemeriksaan kualitas awal memakai pengulangan trigram/kata dominan agar transkrip ASR yang sangat repetitif ditolak sebelum inferensi. Uji nyata menemukan prompt saja tidak cukup menolak semua input kacau; validasi ini melengkapi prompt dan kutipan pendukung, bukan jaminan pemahaman semantik.


Bootstrap terpusat ada di `setup_local.py`, dipakai `npm run setup`, `setup:ai`, dan kedua launcher. `npm run doctor` melakukan pemeriksaan baca-saja. Perubahan requirements harus mempertimbangkan marker hash dan `.venv` lama. Lihat [NEW_MACHINE](NEW_MACHINE.md) untuk dukungan platform dan pengujian checkout bersih.


Bahasa caption ditentukan oleh audience: lokal Indonesia, Global Inggris. `langdetect` dengan seed tetap memeriksa keluaran; salah bahasa memicu satu retry lalu penolakan. Prompt/few-shot dipisah per bahasa. Model memilih indeks kalimat untuk evidence agar kutipan sumber tidak diparafrasekan. Tes mencakup penolakan bahasa salah, batas retry, terjemahan caption dengan evidence bahasa sumber, dan validasi indeks.


## Modul Studio Anak (Milestone K1)

1. **Modul Ide & Data**: `kids_content.py` mendefinisikan katalog 10 ide editorial orisinal (`IDEAS`), 10 kategori terkurasi (`CATEGORIES`), sumber acuan kebijakan platform (`SOURCES`), serta fungsi validasi payload, penulisan atomik, dan pembacaan brief.
2. **Penyimpanan Brief Terisolasi**: Brief disimpan di `data/kids-briefs/<brief_id>.json` secara terpisah dari folder pekerjaan video, sehingga scanner riwayat `job_summary()` mengabaikannya secara otomatis.
3. **Pengendalian Konkurensi Optimistik (OCC)**: `PATCH /api/kids/briefs/<id>` mewajibkan parameter `expected_revision`. Ketidakcocokan versi memicu respons HTTP 409 dengan data versi server terkini, memungkinkan antarmuka menyelesaikan konflik tanpa kehilangan draft lokal.
4. **Ekspor Offline**: Fungsi `format_brief_txt` di backend dan implementasi blob di frontend menyediakan ekspor teks dan JSON tanpa memerlukan koneksi jaringan, model AI, atau worker media.
5. **Pengujian**:
   - `tests/test_kids_studio.py`: Pengujian unit dan integrasi API (11 tes) mencakup validasi batas karakter, atomisitas simpan/baca/hapus, OCC 409, dan isolasi dari scanner history.
   - `tests/test_browser_kids_studio.py`: Pengujian antarmuka Chrome Headless nyata (4 tes) membuktikan tidak adanya exception null-form, fungsi filter kategori ide, penanganan konflik 409, dan responsivitas layar sempit 375×667.


## K2/K3 dan ekspor turunan

Form `/kids/source` dan POST job memakai profil orthogonal audience serta snapshot brief. `clip_exports.py` mengekspor dari MP4 awal dengan watermark snapshot dan frame PNG. Endpoint ekspor async berada di app.py; reservation media dan status metadata di bawah RLock, idempotensi request ID wajib. UI clipOutputTools mem-poll status tanpa merender ulang editor yang mempunyai draft. Renderer trim/subtitle M2 dan editor judul/template thumbnail belum tersedia.
