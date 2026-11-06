# Perbaikan crop halus dan kualitas sumber — Kelip Studio

5 November2026. Menindaklanjuti [analisis recording](CROP_QUALITY_ANALYSIS.md). Hasil lama tidak dimodifikasi.

## Perubahan

- Selector download video-only kualitas terbaik sesuai target1080/1440/2160+bestaudio; fallback combined. FFmpeg imageio bawaan dipasok ke yt-dlp untuk merge. Path hasil postprocessing diverifikasi, lalu dimensi/FPS/codec/bitrate sumber dicatat. Tidak menjamin setiap URL menyediakan HD.
- Deteksi wajah/mulut tetap sekitar4Hz. Target kamera dipisahkan dari sampling; interpolasi dan spring damping berbasis waktu dengan batas speed/acceleration, dead-zone2% lebar output, dan batas frame. Sendcmd memakai setiap PTS frame yang didecode; tidak menaikkan frekuensi model/detektor. Inisialisasi kamera langsung memakai target awal. Perubahan scene besar pada sampel mereset trajectory sebagai heuristik.
- Scale Lanczos, dimensi even, libx264fast/CRF18/yuv420p untuk klip dan watermark. Subtitle preset existing tetap. File dapat lebih besar dan render lebih lama.
- UI memisahkan target sumber dari resolusi hasil, memberi resolusi/FPS aktual serta warning jika upscale>1.05×. Backend lama diminta restart sebelum frontend baru mengirim job.

## Verifikasi

96 tes Python non-browser dan empat suite Node existing lolos, termasuk tujuh tes media baru. Node syntax check dan git diff --check juga bersih. Selector yt-dlp nyata tanpa network membuktikan HD terpisah dipilih; fixture HTTP loopback benar-benar diunduh dan digabung FFmpeg sehingga memiliki video720p serta audio. Tidak mengunduh ulang video pengguna/YouTube eksternal pada tugas ini.

Render tekstur statis mengisolasi gerakan kamera dari gerakan subjek; phase correlation pada hasil MP4 menunjukkan posisi perantara, bukan hanya command yang tampak benar. Pengujian lain memeriksa bounded speed/acceleration, timestamp VFR pada trajectory, scene reset, deteksi sekitar8sampel untuk60frame, codec/audio/subtitle dan resolusi existing.

Perbandingan fixture sintetis5detik/30fps/480×854: sebelum19titik dengan lompatan maksimum53px; sesudah150command dengan maksimum7px. Source/target fixture sama. Angka ini bukan pengukuran sebelum/sesudah pada podcast pengguna dan bukan benchmark akurasi pembicara. Fixture baru sekitar329KB vs180KB pada pengaturan sebelumnya; framing berbeda akibat smoothing, jadi perbedaan ukuran tidak mengisolasi CRF.

Browser pada server fixture terpisah: dropdown target4K tersinkron ke select asli; sumber aktual960×540/30fps dan warning1.58× tampil; pada375px tidak ada horizontal overflow. Kedua video perbandingan berhasil diputar di browser. Semua artefak di outputs/crop-smooth-comparison/ di-ignore.

## Batas dan cara memakai

Restart aplikasi ketika tidak ada proses aktif (Ctrl+C, lalu npm run dev), kemudian refresh halaman. Buat pekerjaan baru dan pilih target sumber sesuai kapasitas. MP4 lama dari360p tidak menjadi tajam otomatis; perlu sumber lebih baik dan pemrosesan ulang baru. Tracking tetap heuristik, cut detection hanya pada sampel, dan tidak menjamin setiap scene/speaker sempurna. Source4K memakai lebih banyak bandwidth, disk dan CPU; default1080 lebih ringan untuk laptop8GB.

Tidak ada data/history/model pengguna yang dihapus, model baru dipasang, atau perubahan server produksi yang dihentikan. Tidak ada commit/push pada tugas ini.
