# Implementasi Studio Anak K2 dan integrasi K3

5 November 2026. K2 diimplementasikan; K3 menghubungkan editor caption/watermark existing dan ekspor turunan MP4/PNG sederhana. Ini tidak menyelesaikan editor trim/subtitle/crop M2, lifecycle active-version M3 penuh, atau editor judul/template pada PRD thumbnail.

## Perilaku tersedia

- Brief tersimpan membuka form sumber dengan revision token, profil kids, bahasaid dan audience lokal. Snapshot brief disimpan pada job. Bonus kata tujuan belajar hanya membantu ranking kandidat, bukan verifikasi konsep/visual.
- Lagu/gerak tanpa narasi yang dipilih eksplisit ditolak; ucapan kosong memberi pesan batas kemampuan. Audio asli tetap, caption memakai transkrip dan guard CTA sederhana. Kegagalan AI tidak membatalkan MP4.
- Hasil memperlihatkan kandidat/tujuan brief dan badge history Anak3–5. Caption dan watermark bisa diedit memakai editor existing.
- Ekspor watermark async memakai MP4 awal dan snapshot watermark tersimpan. PNG berasal dari waktu frame klip, fit vertikal/landscape dengan watermark opsional. Setiap ekspor punya ID tersendiri dan tidak menimpa file lama. Pengulangan request ID tidak memulai worker ganda.
- Reservation pemrosesan mencegah ekspor bersamaan dengan video/AI dan penghapusan job terkait. Health mencakup ekspor untuk launcher. Metadata status copy-on-write/atomic; restart menandai ekspor terputus saat GET status tanpa mengaku sukses.

## Bukti verifikasi

- 89 tes Python non-browser lolos. Tujuh tes baru test_kids_pipeline_exports.py memeriksa mode/bahasa, snapshot/konflik brief, kompatibilitas general, ranking tujuan, empty speech, caption offline, endpoint ekspor, idempotensi, busy guard dan kegagalan.
- FFmpeg nyata dengan video/audio sintetis: piksel watermark terbakar, dimensi MP4 benar, stream audio masih ada, PNG landscape1280×720, serta hash MP4 sumber tetap. Pipeline kids memakai ASR/Ollama mock; ini bukan validasi kualitas model atau materi anak.
- Tiga suite Node existing lolos; node syntax check dan pip check bersih.
- Browser live terhubung ke server fixture127.0.0.1:8877 dengan data temporary: buka brief → Gunakan video sendiri → form bahasaid/durasi15; buka history berbadge; hasil menunjukkan tujuan; klik ekspor MP4 dan thumbnail menghasilkan link Unduh hasil; gambar benar-benar dimuat1080×1920. Bukan hanya router API dalam halaman.
- Pada viewport375×812, scrollWidth=clientWidth=375 dan kontrol ekspor muat di frame. Screenshot di outputs lokal yang di-ignore. Browser headless suites existing tidak dijalankan ulang.

Data pengguna/brief/history produksi tidak dipakai atau dihapus. Tidak mengunduh model/referensi video, tidak mengubah akun YouTube, tidak menjalankan server kedua pada data yang sama. Server fixture dan tab pengujian ditutup setelah verifikasi.

## Batas praktis

Belum ada editor timeline/manual trim, koreksi subtitle per segmen, desain judul thumbnail, atau resume ekspor. Thumbnail frame bukan gambar generatif. Label kids bukan sertifikasi kesesuaian usia; pemeriksaan isi/visual/hak aset tetap pada kreator dewasa. Pemeriksaan CTA adalah heuristik dan dapat melewatkan konten atau menolak caption yang sebenarnya layak. Pengujian audio sintetis tidak membuktikan kualitas ucapan lagu atau pemahaman pembelajaran.
