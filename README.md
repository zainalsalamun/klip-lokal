# Kelip Studio — clipper dengan AI lokal

**Kelip Studio** menggunakan logo **k✳lip.**, dengan simbol ✳ mewakili huruf E. Fokus pengembangan saat ini adalah aplikasi lokal.

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

Untuk komputer baru, ikuti [panduan perangkat baru](docs/NEW_MACHINE.md). Setelah Python 3.11–3.13, npm dan Ollama dipasang:

```sh
npm run setup
npm run setup:ai
npm run doctor
npm run dev
```

`setup` membuat environment dan memasang dependensi proyek. `setup:ai` memeriksa runtime lokal dan mengunduh model jika belum tersedia. `doctor` memeriksa kesiapan tanpa mengubah instalasi. Setup dapat diulang; model yang sudah ada dipakai kembali. Ollama perlu dipasang pengguna terlebih dahulu dari sumber resmi. Windows/Linux belum didukung end-to-end oleh aplikasi.


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
2. Tentukan target durasi 15/30/45/60 detik, jumlah kandidat 1/3/5, bahasa suara, dan resolusi hasil.
3. Pilih **Gaya subtitle**: Klasik (default), Kuning tebal, Kotak gelap, Minimal, Biru cyan, Hijau lime, Pink cerah, Oranye hangat, Kotak ungu, atau Kotak terang. Preview tersedia sebelum memproses.
4. Klik **Cari momen & buat klip** dan tunggu proses selesai.
5. Urutkan kandidat dan putar hasil untuk meninjau isi, crop dan subtitle. Unduh MP4 langsung dari kartu atau buka **Edit & ekspor** untuk mengatur caption, watermark dan thumbnail.
6. Klik **Buat klip baru** untuk video berikutnya. Hasil sebelumnya tersedia lewat menu **Riwayat klip**, termasuk setelah refresh/restart. Daftar memakai area utama, 10 video per halaman, pencarian dan filter status.
7. Klik **Hapus** pada history yang tidak diperlukan untuk menghapus seluruh berkas pekerjaan dari disk, lalu konfirmasi. Pekerjaan aktif tidak bisa dihapus.

Tidak memerlukan API key atau langganan AI. Whisper berjalan di CPU laptop.

## Dokumentasi

Lihat [peta dokumentasi](docs/README.md). Developer mulai dari [CONTRIBUTING.md](CONTRIBUTING.md); coding agent membaca [AGENTS.md](AGENTS.md) dan memilih alur kerja melalui [SKILLS.md](SKILLS.md).

| Dokumen | Isi |
| --- | --- |
| [Komputer baru](docs/NEW_MACHINE.md) | Alur clone, prasyarat, setup, model dan doctor |
| [Instalasi dan menjalankan](docs/SETUP.md) | Prasyarat, instalasi manual, launcher, model, pembaruan |
| [AI caption lokal](docs/LOCAL_AI.md) | Ollama, setup model, privasi dan batas akurasi |
| [Pengujian](docs/TESTING.md) | Command, cakupan tes dan verifikasi nyata |
| [Keputusan arsitektur](docs/DECISIONS.md) | Alasan desain dan konsekuensinya |
| [Usulan pengembangan](docs/ROADMAP.md) | Kandidat pekerjaan berikutnya, bukan fitur tersedia |
| [Studio Global](docs/GLOBAL.md) | Subtitle/caption Inggris, suara asli, ide konten dan batas kualitas |
| [Panduan pengguna](docs/USAGE.md) | Input, pilihan, hasil, penyimpanan dan privasi |
| [Arsitektur](docs/ARCHITECTURE.md) | Pipeline, algoritme pemilihan, subtitle, konkurensi |
| [Referensi API](docs/API.md) | Endpoint, parameter, respons dan contoh curl |
| [Pengembangan dan verifikasi](docs/DEVELOPMENT.md) | Struktur source, konfigurasi, smoke check, uji lengkap |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Masalah instalasi, YouTube, model, audio, ekspor dan port |

## Rencana pengembangan

[Analisis prioritas](docs/PRODUCT_REVIEW.md), [PRD Tinjau & Perbaiki Klip](docs/prd/KLIP_REVIEW_EDITOR.md), dan [prompt Antigravity](docs/prompts/ANTIGRAVITY_REVIEW_EDITOR.md) menyiapkan usulan tahap berikutnya. Fitur usulan belum tersedia sampai diimplementasikan dan diverifikasi.

## Kemampuan dan batasan

- MP4 vertikal: 480p (480×854), 720p (720×1280, default), atau 1080p (1080×1920), video H.264, audio AAC, subtitle menyatu dengan gambar.
- Kandidat diperingkat memakai kata pemancing perhatian, kepadatan percakapan, dan variasi kata. **Belum ada model penilai konteks atau jaminan viral.**
- Crop memperkirakan pembicara dari wajah/gerakan mulut, dengan fallback tengah; belum ada editor manual. Resolusi tinggi tidak menambah detail sumber yang rendah dan membutuhkan lebih banyak waktu/ruang.
- Waktu subtitle per kelompok kata diperkirakan dari segmen Whisper, bukan waktu setiap kata.
- Satu pekerjaan aktif per proses server. Jumlah kandidat dan durasi hasil dapat lebih kecil dari pilihan.
- Riwayat tersimpan di server dan bisa dibuka kembali. Belum ada resume proses setelah server berhenti atau antrean permanen.
- Unduhan YouTube bergantung pada ketersediaan video dan pembatasan layanan/jaringan.

## Data dan akses

Video, audio, transkrip, klip dan model Whisper berada di `data/`. Model caption berada di penyimpanan Ollama (default `~/.ollama/models`). Tidak ada pengiriman audio/video ke layanan AI. Unduhan YouTube, model dari Hugging Face, dependensi, serta font Google Fonts tetap memerlukan koneksi ke penyedia masing-masing. Server hanya mendengarkan di `127.0.0.1`, tanpa sistem akun. Ini aplikasi untuk satu pengguna lokal; hosting publik memerlukan arsitektur dan pengamanan tambahan.

## Status verifikasi

Diuji pada Mac Apple Silicon dengan Python 3.13.3: unduhan video YouTube publik berhasil; pipeline video percakapan sintetis berhasil melalui Whisper, pemilihan kandidat, subtitle dan ekspor. Berkas hasil diverifikasi memiliki video 720×1280 dan audio. Form kosong, link non-YouTube, dan rute berkas yang tidak valid ditolak. Ini bukti alur dasar, bukan pengujian semua format, bahasa, atau video YouTube.

Potongan pekerjaan baru mengikuti batas segmen ucapan dan mengutamakan jeda/akhir kalimat. Crop memperkirakan pembicara dari wajah dan gerakan mulut; hasil tetap perlu ditinjau. Lihat batasan di [panduan penggunaan](docs/USAGE.md).

Komponen utama: [Flask](https://flask.palletsprojects.com/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg), [OpenCV](https://opencv.org/), dan [PyAV](https://pyav.org/). Lisensi masing-masing komponen mengikuti proyek asalnya; proyek ini belum menetapkan lisensi distribusi sendiri.


Caption baru dirangkum oleh AI lokal dari pembahasan tiap klip, bukan potongan awal transkrip. Target 6–12 kata, maksimal 16 kata / 120 karakter, tanpa CTA/hashtag otomatis. Hasil lama dapat dirangkum lewat **Buat caption AI lokal**. Draft hasil edit meminta konfirmasi sebelum diganti. Lihat [AI lokal](docs/LOCAL_AI.md).


**Caption AI lokal:** pasang Ollama dan jalankan `npm run setup:ai` setelah environment Python tersedia. Model Qwen3 1.7B merangkum topik tiap klip menjadi satu kalimat; hasil lama bisa diproses lewat tombol **Buat caption AI lokal**, tanpa ekspor ulang. Lihat [setup dan batas akurasi](docs/LOCAL_AI.md).


### Studio Anak dan ekspor klip

Buka `/kids`, simpan brief lalu **Gunakan video sendiri** untuk kandidat berbahasa Indonesia usia3–5. Job menyimpan salinan brief; hasil tetap perlu ditinjau kreator dewasa. Kartu hasil menyediakan editor caption/watermark, **Ekspor MP4 watermark**, serta thumbnail PNG dari frame klip (9:16/16:9). Hasil baru tidak menimpa file awal. Trim/subtitle manual dan editor desain thumbnail penuh belum tersedia. Lihat [panduan penggunaan](docs/USAGE.md).


### Crop halus dan kualitas sumber

Pemrosesan baru memakai posisi crop per-frame dengan deteksi pembicara tetap ringan. Target kualitas YouTube1080/1440/2160p terpisah dari ukuran ekspor; video/audio dapat diunduh terpisah dan digabung FFmpeg. Resolusi sumber aktual serta peringatan pembesaran ditampilkan. Hasil lama tidak diubah otomatis. Lihat [analisis dan perbaikan](docs/reviews/CROP_QUALITY_FIX.md).
