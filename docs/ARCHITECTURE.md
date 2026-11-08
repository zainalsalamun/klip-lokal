# Arsitektur dan cara kerja

## Siklus server lokal

`Mulai.command` menyiapkan dependensi lalu memanggil `python -m kelip.serverctl start`. Controller memakai `launchctl submit` dengan label `local.klip.server`, direktori proyek dan path interpreter absolut, dan output ke `data/server.log`. Job terpisah dari proses Terminal/chat; tidak ada instalasi login item. Controller menunggu `/api/health` sebelum browser dibuka. `Berhenti.command` memanggil controller stop, yang menolak bila health check melaporkan pekerjaan aktif. Ini bukan mekanisme graceful shutdown transaksional: jangan memulai pekerjaan baru ketika sedang menghentikan server. Setelah logout/reboot, mulai kembali secara manual.

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
2. Unduh video-only hingga target sumber1080/1440/2160 dan audio terbaik, lalu merge melalui FFmpeg bawaan; fallback format gabungan bila diperlukan. Dimensi/FPS/codec sumber aktual dicatat; target tidak menjamin semua resolusi tersedia. Unggahan lokal memakai file aslinya.
3. Ekstrak audio mono WAV 16 kHz dengan FFmpeg yang dipaketkan imageio-ffmpeg.
4. Muat Whisper `base` sekali per proses server. Jalankan CPU `int8`, `vad_filter=True`, `beam_size=3`; simpan transkrip segmen.
5. Pilih jendela kandidat, beri skor, lalu ambil kandidat skor tertinggi yang tidak saling beririsan. Mode AI opsional menilai daftar pendek lewat Ollama lokal sebelum render. Kelip memvalidasi ID dan alasan pilihan, lalu menyimpan urutan final untuk resume. Respons gagal memakai kandidat standar.
6. Tulis ASS dan render setiap klip secara berurutan. Skala hingga menutup resolusi terpilih (480×854, 720×1280, atau 1080×1920) lalu crop yang mengikuti perkiraan pembicara (`kelip/speaker_crop.py`: Haar face detector OpenCV, gerakan area mulut dikurangi gerakan atas wajah, gerbang RMS audio, hysteresis dan smoothing). Analisis wajah sekitar4Hz dipisahkan dari trajectory kamera. Target diinterpolasi dan dihaluskan dengan batas kecepatan/akselerasi serta dead-zone berbasis waktu; sendcmd dibuat per-frame dari PTS decode. Perubahan scene besar pada sampel dapat mereset trajectory sebagai heuristik. Jika deteksi tidak menghasilkan wajah atau analisis gagal, fallback crop tengah dengan catatan framing. Selanjutnya `setsar=1`, bakar subtitle, enkode H.264 (`fast`, CRF18, scaling Lanczos) dan AAC. `+faststart` membantu pemutaran MP4.
7. Tulis status akhir beserta daftar hasil.

## Skor kandidat

Setiap awal segmen menghasilkan kandidat mulai 0,15 detik sebelumnya (minimum 0). Kandidat mengumpulkan segmen berikutnya yang mulai sebelum batas durasi. Akhirnya dibatasi durasi pilihan atau akhir segmen terakhir. Kandidat kurang dari `min(10, durasi × 0,6)` detik dibuang.

Skor = `2 × jumlah kata hook + 2 × min(kata/detik, 3) + 3 × rasio kata unik`, ditambah 1 jika mengandung `?` atau `!`. Daftar hook Indonesia/Inggris ada di regex fungsi `candidates()`. Kata dan skor berasal dari seluruh teks segmen yang terpilih, termasuk kemungkinan bagian segmen di luar batas klip.

Kandidat diurutkan menurun menurut skor, lalu dipilih secara greedy tanpa overlap sampai jumlah maksimum terpenuhi. Tidak ada analisis gambar, wajah, emosi, tema, pembuka/penutup kalimat, atau prediksi viralitas. Hasil dapat memotong kalimat. Algoritme ini adalah titik awal yang dapat diganti model semantik di masa depan.

## Subtitle

ASS memakai kanvas referensi 720×1280 yang diskalakan renderer FFmpeg ke resolusi hasil, font Arial 42, putih, outline gelap, posisi bawah dengan margin vertikal 220. Karakter kurung kurawal dan backslash dibuang agar transkrip tidak menjadi tag ASS. Kelompok sampai delapan kata diberi waktu rata dari segmen yang beririsan dengan klip. Tidak ada word alignment. FFmpeg menerima nama ASS relatif dengan working directory folder pekerjaan untuk menghindari escaping path filter.

## Status dan konkurensi

Dictionary `jobs` menyimpan status memori. `lock` menjaga pemeriksaan pekerjaan aktif dan pembaruan status; `model_lock` melindungi pemuatan/pemakaian model. Hanya satu pekerjaan aktif per proses server. Menjalankan banyak proses server akan mematahkan asumsi tersebut, karena setiap proses memiliki dictionary dan lock sendiri.

Job awal beserta metadata sumber/pengaturan dan timestamp disimpan sebelum worker dimulai. `update()` menulis file sementara lalu mengganti `job.json` secara atomik. Riwayat membaca metadata disk dan snapshot memori; record lama mendapat tanggal fallback dari metadata direktori. JSON rusak dilewati. Proses belum selesai yang dibaca dari disk sesudah restart ditampilkan gagal; pekerjaan dapat dilanjutkan manual lewat endpoint resume. Worker daemon berhenti bersama server. Resume memakai source, transkrip lengkap dan checkpoint klip. Tahap yang belum tersimpan diulang. Cancel, batas waktu global FFmpeg/transkripsi dan cleanup otomatis belum tersedia. Cleanup manual tersedia lewat DELETE history: validasi UUID, tolak symlink/pekerjaan aktif, lalu hapus direktori dengan `shutil.rmtree` di bawah lock dan singkirkan record memori. UI meminta konfirmasi sebelum request.

## Batas deployment

Server development Flask hanya bind loopback. Tidak ada autentikasi, CSRF token, isolasi subprocess, pembatasan CPU/disk, maupun multi-user ownership. Jangan mengubah bind menjadi publik sebagai cara hosting. Deployment online memerlukan antrean worker, autentikasi, validasi media dan sumber, batas sumber daya, penyimpanan, pembatalan, logging dan kebijakan retensi yang sesuai.

## Riwayat berjumlah banyak

API memfilter dan memotong ringkasan menjadi halaman 10 entri secara default, maksimal 50. Browser hanya merender satu halaman dan mengambil detail klip saat dibuka. ID aktif dikembalikan terpisah supaya polling tetap berjalan ketika pengguna membuka halaman/filter lain. Cache LRU ringkasan dibatasi 1.024 entri dan memakai mtime nanosekon/ukuran file sebagai invalidasi.

Penyimpanan masih memakai direktori JSON: setiap pencarian tetap memindai nama/stat file dan mengurutkan ringkasan; cache mengurangi parsing ulang. Ini mengurangi payload/DOM, bukan menjadikannya sistem skala tak terbatas. Untuk koleksi sangat besar, indeks database seperti SQLite dan pagination berbasis indeks diperlukan. Riwayat tidak menghapus file video otomatis; gunakan Hapus untuk mengosongkan ruang disk.

## Mode Global

`/global` memakai template yang sama dengan parameter Jinja `global_mode`. Topik dan sumber ide berasal dari `kelip/global_content.py`. Worker menerima audience/topic, memilih task Whisper translate untuk Global atau transcribe untuk lokal, lalu memakai pipeline ekspor yang sama dengan audio sumber. Topic menambah bobot keyword; tidak memanggil model rekomendasi terpisah. Caption awal dan fallback history mengikuti audience.


Preset tampilan subtitle didefinisikan di `kelip/subtitle_styles.py`. UI merender daftar dari konfigurasi backend; server memvalidasi whitelist, menyimpan `subtitle_style`, dan meneruskannya ke `write_subs()`. Preset mengganti ASS style (warna, bobot, ukuran, outline/latar) tanpa mengubah segmentasi atau timestamp. Semua memakai kanvas 720×1280 sehingga skala tetap konsisten di setiap resolusi. Preview CSS adalah ilustrasi preset, bukan render ASS.


Setelah ekspor MP4, worker menjalankan `local_caption.summarize()` berurutan pada transkrip tiap klip. Runtime memakai Ollama loopback dengan model Qwen3 1.7B. Output JSON harus memuat caption singkat dan kutipan pendukung yang ada dalam transkrip. Kegagalan AI tidak menggagalkan video. Endpoint regenerasi caption memperbarui metadata secara atomik tanpa menulis video; permintaan tidak memegang lock pekerjaan selama inferensi. Tidak ada cloud fallback.

## Modul Watermark

Modul `kelip/watermark.py` mengelola konfigurasi, aset, preset, geometri penempatan, deteksi benturan, dan komposisi overlay visual pada klip:
1. **Validasi & Penyimpanan Aset**: Unggahan logo dibatasi 5 MiB, format PNG/JPG, dimensi 10×10 hingga 4096×4096 piksel, penolakan animasi (APNG) dan rasio dekompresi bomb (maksimal 200:1 dan 16,7M total piksel). File dinormalisasi dan disimpan di `data/watermark-assets/<asset_id>.<ext>`.
2. **Preset Reusable**: Daftar preset watermark disimpan di `data/watermark-presets.json` dengan penulisan file sementara atomik.
3. **Geometri & Deteksi Benturan**: Kotak batas watermark dihitung dari 9 jangkar posisi, persentase lebar kanvas, dan persentase margin dari dimensi terpendek kanvas (mendukung margin 0% rapat tepi). Deteksi benturan subtitle memeriksa irisan geometris antara bounding box watermark dan area subtitle ASS (zona bawah vertikal y=72%–100%), sehingga logo tinggi di tengah maupun watermark di area bawah terdeteksi secara akurat.
4. **Compositing**: Fungsi `composite_watermark()` memanfaatkan OpenCV dan NumPy untuk merender teks ber-outline/panel atau logo dengan blending alpha kanal transparan langsung ke frame citra.
5. **Konkurensi & Lifecycle**: Klip melacak nomor revisi terpisah: `watermark_revision` untuk watermark dan `caption_revision`/`metadata_revision` untuk caption. Pemisahan ini mencegah konflik revisi antar-editor dalam satu kartu yang sama saat pengguna mengedit keduanya. Ekspor turunan MP4 watermark dan PNG tersedia melalui clip_exports.py; editor/render M2/M3 penuh tetap terpisah.


## Integrasi kids dan ekspor turunan

K2 menyimpan snapshot brief pada job sebelum worker dimulai; perubahan brief sesudah itu tidak direferensikan lagi. Worker memakai transcribe/id, kandidat heuristik dengan bonus kata tujuan belajar, dan caption transcript-only. Pemeriksaan CTA kids bersifat heuristik, bukan model moderasi.

clip_exports.py melakukan komposisi raster watermark yang sama lalu overlay FFmpeg pada MP4 awal, atau ekstraksi frame dan fit ke PNG. Reservation active_export di bawah RLock aplikasi menghalangi createjob, captionrequest dan delete job terkait. Request idempotent, write metadata copy-on-write/atomic; status commit menggabungkan metadata klip terkini agar caption/draft tidak tertimpa. Snapshot watermark tidak berubah selama render. Kegagalan menghapus hanya output baru milik ekspor; file sumber/ekspor lama tetap ada. Satu server/data directory tetap wajib. Tidak ada resume otomatis atau pergantian active render seperti rancangan M3 penuh.
