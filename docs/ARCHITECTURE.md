# Arsitektur dan cara kerja

## Siklus server lokal

`Mulai.command` menyiapkan dependensi lalu memanggil `serverctl.py start`. Controller memakai `launchctl submit` dengan label `local.klip.server`, path interpreter/source absolut, dan output ke `data/server.log`. Job terpisah dari proses Terminal/chat; tidak ada instalasi login item. Controller menunggu `/api/health` sebelum browser dibuka. `Berhenti.command` memanggil controller stop, yang menolak bila health check melaporkan pekerjaan aktif. Ini bukan mekanisme graceful shutdown transaksional: jangan memulai pekerjaan baru ketika sedang menghentikan server. Setelah logout/reboot, mulai kembali secara manual.

## Komponen

Browser menampilkan template Jinja dengan CSS dan JavaScript biasa. Flask menerima sumber sebagai multipart, membuat ID UUID hex, lalu menjalankan worker thread daemon. JavaScript memeriksa status kira-kira setiap 1,8 detik. Penyimpanan berbasis folder; tidak ada database, broker antrean, atau layanan AI jarak jauh.

```text
Browser → POST /api/jobs → worker thread
                            ↓
                 yt-dlp / file unggahan
                            ↓
                 FFmpeg: WAV mono 16 kHz
                            ↓
                 faster-whisper base CPU int8
                            ↓
                 skor kandidat dari transkrip
                            ↓
                 ASS + FFmpeg → MP4 9:16
Browser ← GET status ← job.json + status memori
Browser → GET /files/<id>/clip-N.mp4
```

## Pipeline

1. Validasi URL, parameter dan ketersediaan worker. Buat direktori `data/<uuid>/`.
2. Unduh format gabungan terbaik hingga tinggi 1080, mendahulukan MP4; atau simpan unggahan. Pemilihan ini tidak selalu memperoleh resolusi tertinggi yang tersedia lewat stream video/audio terpisah.
3. Ekstrak audio mono WAV 16 kHz dengan FFmpeg yang dipaketkan imageio-ffmpeg.
4. Muat Whisper `base` sekali per proses server. Jalankan CPU `int8`, `vad_filter=True`, `beam_size=3`; simpan transkrip segmen.
5. Pilih jendela kandidat, beri skor, lalu ambil kandidat skor tertinggi yang tidak saling beririsan.
6. Tulis ASS dan render setiap klip secara berurutan. Skala hingga menutup 720×1280 lalu crop tengah, `setsar=1`, bakar subtitle, enkode H.264 (`veryfast`, CRF 23) dan AAC. `+faststart` membantu pemutaran MP4.
7. Tulis status akhir beserta daftar hasil.

## Skor kandidat

Setiap awal segmen menghasilkan kandidat mulai 0,15 detik sebelumnya (minimum 0). Kandidat mengumpulkan segmen berikutnya yang mulai sebelum batas durasi. Akhirnya dibatasi durasi pilihan atau akhir segmen terakhir. Kandidat kurang dari `min(10, durasi × 0,6)` detik dibuang.

Skor = `2 × jumlah kata hook + 2 × min(kata/detik, 3) + 3 × rasio kata unik`, ditambah 1 jika mengandung `?` atau `!`. Daftar hook Indonesia/Inggris ada di regex fungsi `candidates()`. Kata dan skor berasal dari seluruh teks segmen yang terpilih, termasuk kemungkinan bagian segmen di luar batas klip.

Kandidat diurutkan menurun menurut skor, lalu dipilih secara greedy tanpa overlap sampai jumlah maksimum terpenuhi. Tidak ada analisis gambar, wajah, emosi, tema, pembuka/penutup kalimat, atau prediksi viralitas. Hasil dapat memotong kalimat. Algoritme ini adalah titik awal yang dapat diganti model semantik di masa depan.

## Subtitle

ASS memakai kanvas 720×1280, font Arial 42, putih, outline gelap, posisi bawah dengan margin vertikal 220. Karakter kurung kurawal dan backslash dibuang agar transkrip tidak menjadi tag ASS. Kelompok sampai delapan kata diberi waktu rata dari segmen yang beririsan dengan klip. Tidak ada word alignment. FFmpeg menerima nama ASS relatif dengan working directory folder pekerjaan untuk menghindari escaping path filter.

## Status dan konkurensi

Dictionary `jobs` menyimpan status memori. `lock` menjaga pemeriksaan pekerjaan aktif dan pembaruan status; `model_lock` melindungi pemuatan/pemakaian model. Hanya satu pekerjaan aktif per proses server. Menjalankan banyak proses server akan mematahkan asumsi tersebut, karena setiap proses memiliki dictionary dan lock sendiri.

`update()` menulis JSON ke disk langsung, bukan melalui rename atomik. Status bisa rusak bila proses/disk berhenti saat penulisan; belum ada mekanisme pemulihan transaksi. Job awal belum disimpan sebelum worker melakukan pembaruan pertama. Worker daemon berhenti bersama server. Tidak ada cancel, resume, batas waktu global FFmpeg/transkripsi, atau cleanup otomatis.

## Batas deployment

Server development Flask hanya bind loopback. Tidak ada autentikasi, CSRF token, isolasi subprocess, pembatasan CPU/disk, maupun multi-user ownership. Jangan mengubah bind menjadi publik sebagai cara hosting. Deployment online memerlukan antrean worker, autentikasi, validasi media dan sumber, batas sumber daya, penyimpanan, pembatalan, logging dan kebijakan retensi yang sesuai.
