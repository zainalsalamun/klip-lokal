# Instalasi dan menjalankan

## Prasyarat

Target yang telah diverifikasi adalah macOS Apple Silicon dengan Python 3.13.3. Gunakan Python 3.11–3.13 untuk instalasi baru. Diperlukan `python3`, `npm`, ruang disk untuk dependensi/model serta sumber dan hasil video, dan internet saat setup. Belum diuji pada Windows atau Linux. Launcher `.command` khusus macOS.

FFmpeg disediakan paket `imageio-ffmpeg`; tidak perlu memasang FFmpeg global. Node 22 dipasang khusus proyek di `runtime/node_modules/node/bin/node`, sehingga Node global tidak diganti. Tidak perlu API key. Model Whisper base memerlukan unduhan tambahan pada pemrosesan pertama bila cache belum ada.

Periksa prasyarat:

```sh
python3 --version
npm --version
```

## Clone dan folder kerja

Ganti `URL_REPOSITORY` dengan URL Git sebenarnya, lalu jalankan:

```sh
git clone URL_REPOSITORY klip-lokal
cd klip-lokal
```

Semua perintah berikut dijalankan dari root repository. Jika sudah berada di root proyek, tidak perlu `cd` lagi. Nama folder dan lokasi clone bebas; `klip-lokal` hanya nama folder contoh.

## Launcher macOS

```sh
chmod +x Mulai.command
./Mulai.command
```

Launcher membuat `.venv` jika belum ada, memasang dependensi bila impor utama belum tersedia, dan memasang runtime Node bila binarinya belum ada. Kemudian `serverctl.py start` menjalankan Flask melalui job launchd sesi pengguna (`local.klip.server`), menunggu health check berhasil, baru browser dibuka ke http://127.0.0.1:8765. Terminal boleh ditutup setelah server siap. Tidak ada login item yang dipasang: setelah restart/logout, jalankan launcher lagi. Log tersimpan di `data/server.log`.

Klik dua kali `Berhenti.command` untuk menghentikan server. Controller menolak penghentian bila ada pekerjaan aktif. Alternatif Terminal:

```sh
.venv/bin/python serverctl.py start
.venv/bin/python serverctl.py status
.venv/bin/python serverctl.py stop
```

Menjalankan launcher lagi saat server sehat akan memakai server yang sama. Bila server crash, jalankan launcher kembali. Server manual `.venv/bin/python app.py` tetap memerlukan Terminal terbuka dan dihentikan dengan Control-C.

Launcher memeriksa keberadaan dependensi, bukan selalu menyelaraskan versinya dengan requirements. Setelah mengubah requirements, jalankan instalasi manual di bawah.

## Mode Terminal editor

```sh
npm run dev
```

Atau `./dev.sh` / `npm start`. Mode ini berjalan foreground: Terminal harus tetap terbuka dan Ctrl+C menghentikan server. Script menyiapkan dependensi jika belum tersedia, lalu menghentikan server launcher sebelum mengambil port yang sama. Jika ada video aktif, penghentian ditolak dan mode Terminal tidak dimulai. Tunggu pekerjaan selesai lalu ulangi. Server manual lain harus dihentikan di Terminal asalnya.

Mode ini tidak membuka browser otomatis dan tidak memakai auto-reload. Buka alamat yang tercetak di Terminal. Perubahan Python memerlukan restart; perubahan HTML/CSS/JavaScript memerlukan refresh browser.

## Instalasi manual / perangkat baru

Salin source, `requirements.txt`, folder `templates/`, `static/`, dan `runtime/package*.json`. Jangan menyalin `.venv`, `runtime/node_modules`, atau cache npm antarperangkat. Data/model boleh dipindahkan terpisah jika memang ingin mempertahankannya.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --cache "$PWD/.npm-cache" --prefix runtime ci --no-audit --no-fund
.venv/bin/python app.py
```

Buka http://127.0.0.1:8765. Jika tidak memiliki lockfile npm, gunakan `npm install` sebagai pengganti `npm ci`. Untuk pemakaian offline dengan unggahan video, dependensi dan model harus sudah tersedia; font antarmuka akan beralih ke font sistem bila Google Fonts tidak dapat diakses.

## Versi dan pembaruan

Versi Python tingkat atas dikunci di `requirements.txt`. Lockfile Node ada di `runtime/package-lock.json`. PyAV dikunci ke 16.1.0 karena kombinasi faster-whisper 1.2.1 dan PyAV 19 gagal saat decoding pada pengujian ini (`metadata_errors`).

Untuk memasang kembali versi yang ditentukan:

```sh
.venv/bin/python -m pip install -r requirements.txt
npm --cache "$PWD/.npm-cache" --prefix runtime ci --no-audit --no-fund
```

Pembaruan yt-dlp kadang diperlukan ketika YouTube berubah. Ubah versi dalam requirements secara sengaja, pasang ulang, lalu ulangi uji unduhan dan pipeline sebelum mengandalkan versi baru. Jangan mengganti semua pin secara bersamaan tanpa verifikasi.

## Konfigurasi

Versi ini belum memiliki file `.env` atau pengaturan konfigurasi melalui UI. Host/port, model, codec dan resolusi ditetapkan di `app.py`; lokasi perubahan ada di [panduan pengembangan](DEVELOPMENT.md). `HF_HUB_DISABLE_XET=1` dipasang sebagai default lingkungan oleh aplikasi untuk menghindari masalah unduhan model melalui Xet yang terlihat saat setup. Cache model ada di `data/models/`.

Pelacakan pembicara memerlukan `opencv-python-headless` (tercantum di requirements). Instalasi lama: jalankan `.venv/bin/python -m pip install -r requirements.txt`, lalu restart server saat tidak ada video aktif. Launcher juga memeriksa import `cv2`. Model Haar sudah disertakan paket, tanpa unduhan model tambahan.


Untuk caption yang merangkum topik, gunakan [setup AI lokal](LOCAL_AI.md). Ollama dan model caption terpisah dari model Whisper. Video tetap dapat diekspor jika AI caption belum siap.
