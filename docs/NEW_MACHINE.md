# Instalasi di komputer baru

Setiap pengguna memasang aplikasi, runtime, dan model pada komputernya sendiri. Source tidak bergantung pada akun, path, environment Python atau model di laptop pembuat aplikasi. Jangan menyalin `.venv`, `node_modules` atau folder home pengguna lain.

## Dukungan saat ini

| Lingkungan | Status |
| --- | --- |
| macOS Apple Silicon | Instalasi dan penggunaan telah diuji |
| macOS Intel | Setup menargetkan macOS, tetapi belum diuji pada mesin Intel |
| Windows / Linux | Ollama tersedia untuk sistem tersebut, tetapi aplikasi lengkap/launcher Klip belum didukung end-to-end. Setup berhenti sebelum memasang paket agar tidak memberi kesan dukungan yang belum diverifikasi |

Ollama lintas platform tidak berarti seluruh aplikasi otomatis lintas platform. Porting membutuhkan validasi launcher, runtime Node downloader, codec dan pipeline media.

## 1. Pasang prasyarat

Pada macOS, pasang Git, **Python 3.11–3.13**, Node.js/npm, dan [Ollama resmi](https://ollama.com/download/mac). Jika sudah memakai Homebrew, opsi instalasinya:

```sh
brew install git python@3.13 node ollama
```

Buka ulang Terminal, lalu periksa:

```sh
python3 --version
npm --version
ollama --version
```

Bootstrap boleh dijalankan memakai `python3` yang berbeda, tetapi environment aplikasi harus Python 3.11–3.13. Bootstrap mencari `python3.13`, `python3.12`, `python3.11` sebelum Python default. Jadi adanya Python 3.14+ tidak memaksa dependensi dipasang pada versi tersebut. Jika versi yang kompatibel belum tersedia, setup menampilkan petunjuk dan berhenti.

Tidak harus memakai Homebrew: Python dan Node dapat dipasang dari installer resmi, dan Ollama dari tautan di atas. Script proyek tidak memasang paket sistem atau menjalankan installer administrator secara diam-diam.

## 2. Clone dan setup

Ganti URL dengan repository yang ingin digunakan:

```sh
git clone URL_REPOSITORY klip-lokal
cd klip-lokal
npm run setup
npm run setup:ai
npm run doctor
npm run dev
```

Buka `http://127.0.0.1:8765`. Biarkan Terminal terbuka selama menggunakan mode `dev`.

- `setup`: membuat `.venv`, memasang pin `requirements.txt`, dan memasang Node 22 khusus proyek. Tidak memulai server atau mengunduh model caption.
- `setup:ai`: menjalankan setup dasar jika diperlukan, memeriksa/menjalankan Ollama lokal, lalu mengunduh Qwen3 1.7B sekitar 1,4 GB. Jika runtime belum terpasang, tampil petunjuk instalasi; lanjutkan setelah Ollama dipasang.
- `doctor`: memeriksa platform, environment Python, impor dependensi, runtime Node, ruang kosong, RAM (informasi), endpoint Ollama dan model caption. Tidak memasang paket, memulai service, melakukan inferensi atau mengunduh model. Exit code 0 berarti pemeriksaan yang dijalankan lolos; 1 berarti ada kebutuhan yang belum siap.
- `dev`: menjalankan bootstrap dasar dan server foreground. Alternatif latar belakang macOS: `./Mulai.command` setelah setup.

Untuk hanya memakai pembuatan video dan caption manual, AI boleh dilewati:

```sh
npm run setup
npm run doctor -- --skip-ai
npm run dev
```

Klip tetap dapat diekspor tanpa Ollama; caption AI akan menampilkan alasan belum tersedia.

## 3. Kapasitas dan unduhan

Qwen3 1.7B dipakai sebagai default yang telah diuji pada laptop RAM 8 GB. Mesin dengan RAM lebih besar tetap dapat memakai model sama; tidak harus meniru spesifikasi laptop pembuat. Performa bergantung pada arsitektur, memori yang sedang tersedia, dan aplikasi lain. RAM di bawah 8 GB belum diverifikasi; gunakan tanpa AI bila tidak memadai. Model dilepas dari RAM setelah permintaan caption, sedangkan file model tetap berada di disk.

Doctor memakai ambang indikatif 4 GiB ruang kosong. Ini bukan jaminan cukup untuk semua video: sumber unggahan dapat mencapai 2 GB, dan audio, klip, dependensi serta cache menambah penggunaan. Siapkan ruang ekstra sesuai panjang/jumlah video.

Ada **dua model terpisah**:

| Model | Kapan diunduh | Lokasi default |
| --- | --- | --- |
| Whisper base | Pemrosesan suara pertama jika cache kosong | `data/models/` pada checkout tersebut |
| Qwen3 1.7B | `npm run setup:ai` | Penyimpanan Ollama pengguna, biasanya `~/.ollama/models` |

Internet diperlukan untuk instalasi awal, kedua unduhan model dan mengambil video YouTube. Setelah semua cache model siap, unggahan video sendiri dan caption lokal dapat digunakan tanpa koneksi internet. Doctor tidak membuktikan Whisper sudah di-cache atau kualitas hasil video; lakukan satu pemrosesan pendek saat pertama memasang aplikasi.

## 4. Aman diulang dan pembaruan

- Setup mencatat hash requirements di `.venv/.klip-requirements.sha256`. Jika requirements berubah atau impor gagal, dependensi dipasang kembali. Marker tidak ditulis ketika instalasi gagal.
- `.venv` dengan Python tidak kompatibel tidak dihapus otomatis. Simpan/rename environment lama, pasang Python yang benar, lalu ulangi setup. Data pekerjaan tidak perlu dihapus.
- Model yang sudah tersedia tidak diunduh ulang. Jika unduhan terputus, ulangi `npm run setup:ai`; Ollama menangani cache unduhannya. Setup memverifikasi model muncul pada endpoint lokal setelah unduhan selesai.
- Jangan memperbarui dependensi atau menghentikan server ketika video/caption sedang diproses. Periksa `npm run doctor` untuk instalasi dan controller `status` untuk pekerjaan server.
- Saat pindah checkout/laptop, source cukup di-clone; data/history boleh dipindahkan terpisah bila diinginkan. Model Ollama tidak dimasukkan ke Git dan tidak ikut dihapus oleh Hapus history.

## Jika npm memblokir runtime Node

Runtime Node proyek memakai install script paket `node` untuk memasang binary sesuai arsitektur. Bila konfigurasi npm memblokir install script, setup menampilkan error, bukan menganggap instalasi berhasil. Periksa log npm dan kebijakan install script yang berlaku di komputer/repository. Jangan mematikan proteksi global secara otomatis; tinjau paket tersebut sebelum mengizinkan script sesuai kebijakan setempat, lalu ulangi setup.

## Batas verifikasi

Pengujian checkout bersih menggunakan folder sementara dengan `.venv` dan runtime Node baru pada macOS Apple Silicon. Ollama dan model yang sudah terpasang pada mesin uji dipakai kembali. Pengujian ini tidak membuktikan instalasi Ollama pertama di semua OS, GPU, atau jaringan; alur model belum ada/unduhan terputus juga dicakup tes transport terisolasi.

Lanjutan: [SETUP](SETUP.md), [LOCAL_AI](LOCAL_AI.md), [TROUBLESHOOTING](TROUBLESHOOTING.md), [TESTING](TESTING.md).

Untuk VPS Ubuntu 24.04 x86_64 tersedia jalur terpisah pada [deployment VPS pribadi](DEPLOYMENT_VPS.md), memakai Gunicorn, Caddy dan systemd. Instalasi Linux tersebut memakai deploy/install.sh.
