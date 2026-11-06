# Analisis gerakan crop dan kualitas HD — Kelip Studio

Tanggal:5 November2026. Permintaan: analisis screen recording sekitar69detik, crop pembicara tampak patah-patah dan kualitas menurun meskipun1080p dipilih. Pemeriksaan read-only terhadap recording, source/output dan command crop pekerjaan yang sesuai. Tidak mengunduh ulang, mengubah job, atau merender ulang hasil pengguna. Pipeline belum diubah pada tugas analisis ini.

## Temuan utama

| Ukuran aktual | Hasil |
|---|---|
| Screen recording |3360×2100, H.264, sekitar49.71fps rata-rata,69.29detik |
| Sumber pekerjaan yang terlihat |640×360,30fps, video sekitar330kb/s |
| Pilihan metadata/output |1080p; ketiga MP4 benar1080×1920 dan30fps |
| Interval posisi crop |Median0.267detik, sekitar3.75pembaruan/detik |
| Lompatan crop maksimum |120piksel output pada ketiga klip |

Recording menampilkan pemutaran bergantian tiga hasil, perpindahan shot, dan cutaway. Screen recording saja tidak cukup untuk mengukur kehilangan detail asli, sehingga ukuran/bitrate sumber dan hasil lokal juga diperiksa.

## Gerakan crop bertangga

speaker_crop.py menganalisis wajah/mulut dengan next_time=frame.time+.25. Pada sumber30fps, sampel jatuh setiap8frame (0.267detik). SpeakerTracker memang menghaluskan target antar-sampel, tetapi app.py menulis sendcmd diskret tanpa interpolasi posisi antar-frame. Akibatnya kamera menahan posisi kira-kira8frame, lalu melompat ke posisi berikutnya. Smoothing target pada4Hz belum menghasilkan gerak kamera30Hz.

| Klip | Jumlah titik | Median interval | Median langkah absolut | Maksimum langkah |
|---|---:|---:|---:|---:|
|1|113|0.267s|13px|120px|
|2|119|0.267s|10px|120px|
|3|117|0.267s|10px|120px|

Contoh klip1: lompatan120px pada waktu klip7.493s dengan interval0.266s. Ini menjelaskan sensasi patah-patah meski frame video sendiri tetap30fps. Perubahan shot/cutaway pada sumber perlu dipisahkan dari perpindahan crop; tidak semua perubahan visual dalam recording berasal dari tracker.

Perbaikan yang disarankan: pertahankan analisis wajah rendah frekuensi untuk laptop8GB, tetapi interpolasikan trajectory crop pada setiap frame mengikuti FPS/PTS video; gunakan easing/batas kecepatan dan akselerasi berbasis waktu, dead-zone untuk gerakan kecil, serta penanganan cutaway/pergantian shot agar tidak memaksa pan di antara scene yang tidak terkait. Tidak perlu menambah model atau melakukan face detection30kali/detik untuk memperoleh trajectory30fps.

## HD output berasal dari sumber360p

app.py memilih format yt-dlp best[height<=1080][ext=mp4]/best[height<=1080]. Selector best memilih format yang mengandung video dan audio bersama; bukan jalur video-only HD+bestaudio terpisah. Pada pekerjaan ini sumber yang benar-benar tersimpan adalah640×360. Tidak dilakukan pengecekan daftar format YouTube saat analisis, sehingga belum dibuktikan berapa resolusi tertinggi yang tersedia pada video tersebut.

Setelah konversi9:16, bagian sumber yang dipakai kira-kira203×360piksel, lalu dibesarkan menjadi1080×1920 (sekitar5.33kali per dimensi). Dimensi output memenuhi pilihan1080p, tetapi detail wajah tidak menjadi1080p asli. Inilah penyebab utama gambar lembut/pecah yang terukur. Bahkan sumber landscape1080p masih memerlukan pembesaran untuk portrait1080×1920; sumber lebih tinggi dapat membantu dengan biaya unduh/proses lebih besar.

Perbaikan yang disarankan: download video-only kualitas terbaik sesuai batas sumber yang dipilih + audio terbaik, merge dengan FFmpeg; simpan dimensi/FPS/format sumber dan tampilkan peringatan bila output membutuhkan upscale besar. Output resolution dan kualitas sumber perlu dibedakan di UI. Sumber lama360p tidak dapat dipulihkan menjadi detail asli hanya dengan mengganti CRF atau labelHD.

Referensi primer format selector dan merge: [dokumentasi yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/README.md#format-selection).

## Encoding sekunder

Render saat ini memakai libx264/veryfast/CRF23. Pengaturan ini dapat menambah kehilangan detail; ekspor watermark juga mengenkode ulang. Pada rekaman ini kualitas sumber360p tetap menjadi masalah utama, bukan bukti bahwa seluruh penurunan disebabkan encoder. Kandidat perbaikan kualitas CRF18–20 dan scaling eksplisit perlu dibandingkan pada source yang sama, dengan pengukuran ukuran file/waktu render laptop8GB. Jangan menjanjikan perbaikan detail yang sudah hilang dari sumber.

## Urutan tindak lanjut

1. Benahi pemilihan kualitas unduhan sumber dan metadata/peringatan upscale.
2. Pisahkan analisis pembicara dari trajectory kamera; ekspor posisi per-frame dengan smoothing berbasis waktu.
3. Perbaiki encoding/scaling setelah sumber dan gerak benar, lalu bandingkan cuplikan pendek sebelum/sesudah pada sumber yang sama.
4. Regresi harus memeriksa perpindahan crop per-frame dan kecepatan/akselerasi, ketajaman/dimensi input-output, frame rate/audio/subtitle, serta waktu render. Gunakan salinan/fixture, jangan menimpa MP4 pengguna.

Artefak lokal analisis berada di outputs/crop-review/ (di-ignore): overview frame recording dan CSV trajectory masing-masing klip. Tidak ada perubahan source aplikasi dalam tugas ini.

Tindak lanjut sudah diimplementasikan: [perbaikan crop dan sumber HD](CROP_QUALITY_FIX.md). Data pengukuran di atas adalah baseline sebelum perbaikan.
