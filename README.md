# Klip — YouTube clipper lokal

Aplikasi web lokal untuk mengambil video YouTube atau file video, mentranskripsi suara, memilih kandidat klip, dan mengekspor MP4 vertikal dengan subtitle.

**Lokasi source:** `/Users/macbookpro/development/klip-lokal`  
**Alamat aplikasi:** http://127.0.0.1:8765

## Mulai cepat

Klik dua kali **Mulai.command** di Finder. Alternatif melalui Terminal:

```sh
cd /Users/macbookpro/development/klip-lokal
./Mulai.command
```

Server berjalan di latar belakang; Terminal boleh ditutup setelah pesan server siap. Hentikan dengan **Berhenti.command**. Setelah restart laptop, jalankan **Mulai.command** lagi. Di laptop ini dependensi, runtime Node, dan model Whisper base sudah disiapkan. Instalasi ulang pada perangkat lain membutuhkan Python 3.11–3.13, npm, serta internet. Lihat [panduan instalasi](docs/SETUP.md).

## Menjalankan dari Terminal editor

Buka folder source di VS Code atau editor pilihanmu, lalu buka Terminal di folder tersebut:

```sh
cd /Users/macbookpro/development/klip-lokal
npm run dev
```

Alternatif tanpa npm sebagai pemanggil: `./dev.sh`. Script menyiapkan dependensi yang belum tersedia, menghentikan server latar belakang yang dikelola launcher (menolak bila ada video diproses), lalu menjalankan server di Terminal. Buka http://127.0.0.1:8765. Log terlihat langsung; **Ctrl+C** menghentikan server. Setelah mengubah Python, hentikan dan jalankan lagi; tidak ada auto-reload. `npm start` menjalankan mode yang sama. Tidak perlu `npm install` di root proyek untuk memakai perintah ini.

## Penggunaan

1. Tempel link satu video YouTube atau pilih file video dari laptop.
2. Tentukan durasi maksimum 15/30/45/60 detik, jumlah kandidat 1/3/5, dan bahasa suara.
3. Klik **Cari momen & buat klip** dan tunggu proses selesai.
4. Putar hasil untuk meninjau crop, isi, dan subtitle; unduh MP4 yang dipilih.

Tidak memerlukan API key atau langganan AI. Whisper berjalan di CPU laptop.

## Dokumentasi

| Dokumen | Isi |
| --- | --- |
| [Instalasi dan menjalankan](docs/SETUP.md) | Prasyarat, instalasi manual, launcher, model, pembaruan |
| [Panduan pengguna](docs/USAGE.md) | Input, pilihan, hasil, penyimpanan dan privasi |
| [Arsitektur](docs/ARCHITECTURE.md) | Pipeline, algoritme pemilihan, subtitle, konkurensi |
| [Referensi API](docs/API.md) | Endpoint, parameter, respons dan contoh curl |
| [Pengembangan dan verifikasi](docs/DEVELOPMENT.md) | Struktur source, konfigurasi, smoke check, uji lengkap |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Masalah instalasi, YouTube, model, audio, ekspor dan port |

## Kemampuan dan batasan

- MP4 9:16, 720×1280, video H.264, audio AAC, subtitle menyatu dengan gambar.
- Kandidat diperingkat memakai kata pemancing perhatian, kepadatan percakapan, dan variasi kata. **Belum ada model penilai konteks atau jaminan viral.**
- Crop tengah tetap; belum ada pelacakan wajah atau editor manual.
- Waktu subtitle per kelompok kata diperkirakan dari segmen Whisper, bukan waktu setiap kata.
- Satu pekerjaan aktif per proses server. Jumlah kandidat dan durasi hasil dapat lebih kecil dari pilihan.
- Tidak ada resume proses setelah server berhenti, antrean permanen, atau daftar riwayat di antarmuka.
- Unduhan YouTube bergantung pada ketersediaan video dan pembatasan layanan/jaringan.

## Data dan akses

Semua video, audio, transkrip, klip, dan model berada di `data/`. Tidak ada pengiriman audio/video ke layanan AI. Unduhan YouTube, model dari Hugging Face, dependensi, serta font Google Fonts tetap memerlukan koneksi ke penyedia masing-masing. Server hanya mendengarkan di `127.0.0.1`, tanpa sistem akun. Ini aplikasi untuk satu pengguna lokal; hosting publik memerlukan arsitektur dan pengamanan tambahan.

## Status verifikasi

Diuji pada Mac Apple Silicon dengan Python 3.13.3: unduhan video YouTube publik berhasil; pipeline video percakapan sintetis berhasil melalui Whisper, pemilihan kandidat, subtitle dan ekspor. Berkas hasil diverifikasi memiliki video 720×1280 dan audio. Form kosong, link non-YouTube, dan rute berkas yang tidak valid ditolak. Ini bukti alur dasar, bukan pengujian semua format, bahasa, atau video YouTube.

Komponen utama: [Flask](https://flask.palletsprojects.com/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg), dan [PyAV](https://pyav.org/). Lisensi masing-masing komponen mengikuti proyek asalnya; proyek ini belum menetapkan lisensi distribusi sendiri.
