# Pengembangan dan verifikasi

## Struktur source

```text
klip-lokal/
  app.py                    server, pipeline, scoring, subtitle dan route
  package.json              perintah npm run dev / npm start
  dev.sh                    bootstrap dan server foreground
  Mulai.command             launcher server latar belakang macOS
  Berhenti.command          penghentian server
  serverctl.py              start/stop/status melalui launchd
  requirements.txt          pin dependensi Python
  templates/index.html      antarmuka Jinja
  static/app.js             form, polling dan kartu hasil
  static/style.css          desain responsif
  runtime/package.json      runtime Node khusus pengunduh
  runtime/package-lock.json lock dependency Node
  docs/                     dokumentasi
  data/                     artefak kerja dan model; diabaikan Git
  .venv/                    lingkungan Python; diabaikan Git
```

`preview.png` adalah screenshot antarmuka, bukan bagian runtime. Folder keluaran chat lama merupakan symlink ke source di `/Users/macbookpro/development/klip-lokal`; tidak ada dua salinan source yang perlu diselaraskan. Proyek belum diinisialisasi sebagai repositori Git dan belum memiliki CI.

## Menjalankan saat mengembangkan

```sh
cd /Users/macbookpro/development/klip-lokal
npm run dev
```

`npm run dev` menyiapkan dependensi dan menghentikan server launcher secara otomatis bila tidak ada pekerjaan aktif. Perintah ini menjalankan server foreground, log terlihat langsung, dan dihentikan dengan Control-C. Alternatif langsung: `./dev.sh`.

Debug/reloader sengaja nonaktif karena worker/model disimpan dalam proses. Restart server setelah mengubah Python. Muat ulang browser setelah perubahan template atau aset; hard refresh bila cache masih menampilkan versi lama. Jangan menjalankan beberapa server untuk folder data yang sama.

## Titik konfigurasi di app.py

| Yang diubah | Lokasi |
| --- | --- |
| Host/port | `app.run()` di akhir berkas |
| Ukuran request | `MAX_CONTENT_LENGTH` |
| Model dan compute | `WhisperModel()` dalam `process()` |
| Bahasa/durasi/jumlah yang diterima | Validasi `create()`; selaraskan opsi HTML |
| Skor kandidat | `candidates()` |
| Tampilan subtitle | Header ASS di `write_subs()` |
| Resolusi, crop, codec | `vf` dan argumen subprocess ekspor |
| Download format/runtime | Opsi `yt_dlp.YoutubeDL()` |

Jika port berubah, sesuaikan alamat pada `Mulai.command`, URL serta probe socket di `serverctl.py`, dan dokumentasi. Jika resolusi berubah, sesuaikan `PlayResX/Y`, font dan margin ASS juga. Belum ada konfigurasi melalui environment untuk parameter tersebut.

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
with av.open('/absolute/path/clip-1.mp4') as media:
    video = media.streams.video[0]
    assert (video.width, video.height) == (720, 1280)
    assert len(media.streams.audio) > 0
    print('Resolusi dan audio OK')
PYTEST
```

6. Ulangi dengan URL YouTube publik untuk memeriksa jalur download. Keberhasilan unggahan tidak membuktikan extractor YouTube masih berfungsi.
7. Coba dua request berturut-turut saat proses masih aktif; yang kedua seharusnya 409. Coba refresh browser selama pemrosesan untuk memeriksa pemulihan ID dari localStorage.

## Verifikasi yang telah dilakukan

Pada laptop ini: impor dependensi, dukungan filter subtitle FFmpeg, route dasar, sintaks Python/JavaScript, unduhan YouTube publik, pipeline video percakapan sintetis hingga MP4, serta resolusi dan stream audio hasil telah diperiksa. UI responsif sempit dan pesan form kosong ditinjau di browser. Belum ada suite regression otomatis, pengujian beban, cakupan semua codec, atau evaluasi akurasi transkripsi/pemilihan klip.

## Pengembangan berikutnya

Peningkatan yang belum tersedia meliputi penyelarasan kata subtitle, batas kalimat, pemilihan semantik, crop mengikuti wajah, editor manual, riwayat, cancel/resume dan cleanup. Jika hendak hosting online, pisahkan worker video dari web server dan rancang ulang akses/data; lihat batas deployment di [arsitektur](ARCHITECTURE.md).

## Verifikasi pengelolaan server

Controller `status`, start idempotent, stop dan start kembali telah diuji. Endpoint halaman, JavaScript, favicon dan health memberi respons berhasil. Request unggah melalui HTTP nyata diterima 202, diproses oleh worker launchd hingga selesai, dan MP4 hasil berhasil diunduh.
