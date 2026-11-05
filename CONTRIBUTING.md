# Kontribusi

Panduan ini berlaku untuk developer manusia dan coding agent. Agent juga membaca [AGENTS.md](AGENTS.md).

## Setup

Gunakan macOS dan Python 3.11–3.13 sesuai [SETUP](docs/SETUP.md). Dari root checkout:

```sh
npm run dev
```

Server foreground berjalan di `http://127.0.0.1:8765`; log terlihat di Terminal. Setup caption AI bersifat terpisah: [LOCAL_AI](docs/LOCAL_AI.md). Jangan mengunduh model atau memproses video besar hanya untuk memeriksa perubahan dokumentasi.

## Alur perubahan

1. Jelaskan masalah dan perilaku yang diharapkan, termasuk contoh bila perlu.
2. Periksa perubahan lokal yang sudah ada. Gunakan branch sesuai alur repository; jangan memasukkan perubahan tidak terkait.
3. Baca [arsitektur](docs/ARCHITECTURE.md) dan [keputusan desain](docs/DECISIONS.md) sebelum mengubah kontrak penting.
4. Implementasikan perubahan sekecil yang menyelesaikan masalah. Jangan mencampur refactor besar atau pemformatan seluruh file dengan perbaikan kecil.
5. Jalankan pemeriksaan dari [TESTING](docs/TESTING.md), lalu perbarui dokumentasi yang terdampak.
6. Siapkan PR yang menjelaskan perilaku akhir dan validasi. Gunakan [template PR](.github/pull_request_template.md).

## Konvensi

- UI dan panduan pengguna menggunakan bahasa Indonesia. Identitas kode dapat memakai bahasa Inggris yang konsisten dengan modul terkait.
- Jangan menambah framework frontend/build pipeline tanpa kebutuhan yang jelas. UI saat ini memakai Jinja, JavaScript biasa dan CSS.
- Gunakan `pathlib` dan root source untuk path runtime. Dokumentasi publik tidak boleh mengandung direktori pribadi komputer kontributor.
- Konfigurasi yang berasal dari request harus divalidasi dengan whitelist. Perubahan field API/metadata harus mempertimbangkan history lama.
- Pin dependensi Python ada di `requirements.txt`; lock Node runtime ada di `runtime/package-lock.json`. Jangan memasukkan hasil instalasi ke Git.
- Dokumen menjelaskan perilaku yang sudah ada. Usulan fitur diberi label rencana, bukan ditulis sebagai kemampuan yang tersedia.

## Data dan laporan masalah

Jangan melampirkan video, transkrip pribadi, cookie YouTube, credential atau `.env` pada issue/PR. Gunakan contoh sintetis atau cuplikan yang boleh dibagikan dan log yang sudah disunting. Catat OS, versi Python, cara menjalankan dan langkah reproduksi.

Belum ada CI yang dikonfigurasi di repository ini. Hasil pemeriksaan lokal perlu dicantumkan pada PR. Proyek belum menetapkan lisensi distribusi; jangan mengasumsikan izin redistribusi source atau model.
