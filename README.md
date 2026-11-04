# Klip — YouTube clipper lokal

Aplikasi web lokal untuk mengambil video YouTube atau file video, mentranskripsi suara, memilih kandidat klip, dan mengekspor MP4 vertikal dengan subtitle.

**Alamat aplikasi:** http://127.0.0.1:8765

## Instalasi dan running lokal

Prasyarat: **macOS**, **Python 3.11–3.13**, **npm**, serta internet untuk setup awal. Versi ini telah diuji pada macOS Apple Silicon. Launcher memakai zsh dan launchd; Windows/Linux belum didukung oleh script launcher.

Clone repository ke folder pilihanmu. Ganti `URL_REPOSITORY` dengan URL repository Git yang sebenarnya:

```sh
git clone URL_REPOSITORY klip-lokal
cd klip-lokal
```

Jika source sudah terbuka di editor, buka Terminal pada root proyek; tidak perlu menjalankan `cd` lagi.

### Pilihan 1: berjalan langsung di Terminal

```sh
npm run dev
```

Alternatif: `./dev.sh` atau `npm start`. Script menyiapkan dependensi yang belum tersedia, menghentikan server latar belakang yang dikelola launcher jika tidak ada pekerjaan aktif, lalu menjalankan aplikasi. Tidak perlu `npm install` di root proyek untuk menggunakan perintah ini.

Buka **http://127.0.0.1:8765**. Log muncul di Terminal. Biarkan Terminal terbuka dan tekan **Ctrl+C** untuk berhenti. Tidak ada auto-reload; setelah mengubah kode Python, hentikan lalu jalankan lagi.

### Pilihan 2: berjalan di latar belakang (macOS)

```sh
./Mulai.command
```

Atau klik dua kali `Mulai.command` di Finder. Browser terbuka setelah server siap dan Terminal boleh ditutup. Hentikan dengan:

```sh
./Berhenti.command
```

Setelah restart/logout, jalankan `Mulai.command` lagi. Pilih salah satu mode running. Jika permission executable hilang, jalankan `chmod +x dev.sh Mulai.command Berhenti.command`.

Semua script mencari source relatif terhadap lokasinya sendiri. Folder repository boleh berada di lokasi mana pun; tidak ada path khusus komputer tertentu. Untuk instalasi manual, pemulihan environment dan pembaruan dependensi, lihat [panduan instalasi](docs/SETUP.md).

## Penggunaan

1. Tempel link satu video YouTube atau pilih file video dari laptop.
2. Tentukan durasi maksimum 15/30/45/60 detik, jumlah kandidat 1/3/5, bahasa suara, dan resolusi hasil.
3. Klik **Cari momen & buat klip** dan tunggu proses selesai.
4. Pilih **Gaya subtitle** sesuai selera: Klasik (default), Kuning tebal, Kotak gelap, atau Minimal. Preview tersedia sebelum memproses.
5. Putar hasil untuk meninjau crop, isi, dan subtitle; unduh MP4 yang dipilih. Di bawah tiap klip tersedia **Caption posting** yang bisa diedit, disalin atau diunduh sebagai TXT.
5. Klik **Buat klip baru** untuk video berikutnya. Hasil sebelumnya tersedia di **Riwayat klip**, termasuk setelah refresh/restart. Daftar ditampilkan 10 video per halaman, dengan pencarian judul/link dan filter status.
6. Klik **Hapus** pada history yang tidak diperlukan untuk menghapus seluruh berkas pekerjaan dari disk, lalu konfirmasi. Pekerjaan aktif tidak bisa dihapus.

Tidak memerlukan API key atau langganan AI. Whisper berjalan di CPU laptop.

## Dokumentasi

| Dokumen | Isi |
| --- | --- |
| [Instalasi dan menjalankan](docs/SETUP.md) | Prasyarat, instalasi manual, launcher, model, pembaruan |
| [Studio Global](docs/GLOBAL.md) | Subtitle/caption Inggris, suara asli, ide konten dan batas kualitas |
| [Panduan pengguna](docs/USAGE.md) | Input, pilihan, hasil, penyimpanan dan privasi |
| [Arsitektur](docs/ARCHITECTURE.md) | Pipeline, algoritme pemilihan, subtitle, konkurensi |
| [Referensi API](docs/API.md) | Endpoint, parameter, respons dan contoh curl |
| [Pengembangan dan verifikasi](docs/DEVELOPMENT.md) | Struktur source, konfigurasi, smoke check, uji lengkap |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Masalah instalasi, YouTube, model, audio, ekspor dan port |

## Kemampuan dan batasan

- MP4 vertikal: 480p (480×854), 720p (720×1280, default), atau 1080p (1080×1920), video H.264, audio AAC, subtitle menyatu dengan gambar.
- Kandidat diperingkat memakai kata pemancing perhatian, kepadatan percakapan, dan variasi kata. **Belum ada model penilai konteks atau jaminan viral.**
- Crop tengah tetap; belum ada pelacakan wajah atau editor manual. Resolusi tinggi tidak menambah detail sumber yang rendah dan membutuhkan lebih banyak waktu/ruang.
- Waktu subtitle per kelompok kata diperkirakan dari segmen Whisper, bukan waktu setiap kata.
- Satu pekerjaan aktif per proses server. Jumlah kandidat dan durasi hasil dapat lebih kecil dari pilihan.
- Riwayat tersimpan di server dan bisa dibuka kembali. Belum ada resume proses setelah server berhenti atau antrean permanen.
- Unduhan YouTube bergantung pada ketersediaan video dan pembatasan layanan/jaringan.

## Data dan akses

Semua video, audio, transkrip, klip, dan model berada di `data/`. Tidak ada pengiriman audio/video ke layanan AI. Unduhan YouTube, model dari Hugging Face, dependensi, serta font Google Fonts tetap memerlukan koneksi ke penyedia masing-masing. Server hanya mendengarkan di `127.0.0.1`, tanpa sistem akun. Ini aplikasi untuk satu pengguna lokal; hosting publik memerlukan arsitektur dan pengamanan tambahan.

## Status verifikasi

Diuji pada Mac Apple Silicon dengan Python 3.13.3: unduhan video YouTube publik berhasil; pipeline video percakapan sintetis berhasil melalui Whisper, pemilihan kandidat, subtitle dan ekspor. Berkas hasil diverifikasi memiliki video 720×1280 dan audio. Form kosong, link non-YouTube, dan rute berkas yang tidak valid ditolak. Ini bukti alur dasar, bukan pengujian semua format, bahasa, atau video YouTube.

Potongan pekerjaan baru mengikuti batas segmen ucapan dan mengutamakan jeda/akhir kalimat. Crop memperkirakan pembicara dari wajah dan gerakan mulut; hasil tetap perlu ditinjau. Lihat batasan di [panduan penggunaan](docs/USAGE.md).

Komponen utama: [Flask](https://flask.palletsprojects.com/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg), [OpenCV](https://opencv.org/), dan [PyAV](https://pyav.org/). Lisensi masing-masing komponen mengikuti proyek asalnya; proyek ini belum menetapkan lisensi distribusi sendiri.


Caption posting kini berupa rekomendasi satu kalimat singkat, maksimal 16 kata / 121 karakter termasuk elipsis, tanpa CTA dan hashtag otomatis. Rekomendasi mengambil kalimat transkrip yang cukup panjang, lalu membatasi panjangnya; bukan ringkasan semantik AI. Template otomatis versi lama diganti saat dibaca tanpa mengubah file/video lama. Caption hasil edit di browser tetap dipertahankan; tombol **Pakai rekomendasi singkat** mengembalikan rekomendasi pendek.
