# PRD — Thumbnail dan Cover Klip

Status: **draft usulan, belum diimplementasikan**. Versi dokumen 1.0, 5 November 2026. Pelengkap [PRD editor](KLIP_REVIEW_EDITOR.md); dapat dikerjakan setelah fondasi ID klip stabil pada M1 tersedia. Jika fondasi belum ada, implementer harus menyelesaikan/merencanakan dependensi itu terlebih dahulu.

## 1. Tujuan

Pengguna dapat membuat thumbnail/cover yang sesuai isi klip dari frame video asli, menambahkan judul singkat dan mengunduh gambar tanpa mengulang transkripsi atau render MP4.

Fokus awal adalah hasil yang dapat dikoreksi pengguna dan ringan untuk laptop RAM 8 GB. Tidak memakai model pembuat gambar baru, wajah sintetis, cloud inference atau upload otomatis ke platform. AI untuk judul bukan bagian MVP; judul manual membuat pengguna tetap dapat bekerja ketika AI caption tidak tersedia.

## 2. Alur pengguna

1. Pada kartu hasil/history, pilih **Buat thumbnail**.
2. Panel di area utama menampilkan tiga kandidat frame dari video klip dan kontrol pilih waktu sendiri.
3. Pilih format cover vertikal atau thumbnail landscape, atur crop, isi judul dan pilih template.
4. Preview memperlihatkan frame, tata letak teks dan panduan area aman.
5. Simpan desain, lalu pilih **Ekspor PNG** atau **Ekspor JPG**. Desain dan hasil tersimpan per klip dan tersedia setelah refresh/restart.
6. Pembuatan cover tidak mengubah video, subtitle atau caption posting.

## 3. Scope MVP

| Fitur | Perilaku |
| --- | --- |
| Kandidat frame | Ambil sekitar 25%, 50%, 75% durasi MP4 klip aktif; frame hitam/tidak terbaca diberi status dan bisa diganti manual |
| Pilih waktu | Slider/input detik relatif terhadap awal MP4 klip aktif; server memvalidasi rentang memakai durasi media aktual |
| Format | Cover 9:16 1080×1920; thumbnail 16:9 1280×720 |
| Crop | Fit tanpa memotong dengan latar netral, atau fill dengan posisi crop manual yang dibatasi; preview konsisten dengan ekspor |
| Judul | Teks manual, maksimal 80 karakter, hingga 3 baris dalam layout; rekomendasi editorial 3–8 kata, bukan batas wajib |
| Template | Bersih (teks putih/outline), Kontras (judul kuning), Editorial (panel teks gelap) |
| Warna/posisi | Pilihan terbatas yang teruji, posisi teks atas/tengah/bawah, area aman dan indikator overflow |
| Ekspor | PNG/JPG dengan dimensi tepat; preview bukan pengganti pemeriksaan file ekspor |
| Simpan | Draft desain di metadata server, ID klip stabil dan optimistic concurrency |

Dimensi di atas adalah preset produk, bukan klaim persyaratan universal platform. File diunduh pengguna; pemilihan/upload thumbnail pada aplikasi media sosial berada di luar scope. Frame 25/50/75% adalah kandidat heuristik, bukan klaim “frame terbaik”.

### Ditunda

Peringkat frame berbasis wajah/ketajaman, judul AI, batch thumbnail, unggah logo/font, library aset, latar sintetis, generative image model, template buatan pengguna dan integrasi publikasi. Prioritaskan kualitas frame/teks manual dahulu.

## 4. Perilaku dan edge case

- Sumber gambar adalah **MP4 klip aktif**, sehingga pengguna tidak memilih frame di luar isi klip. Klip lama tetap dapat membuat cover bila sumber asli terhapus tetapi MP4 hasil masih ada.
- Timestamp desain disimpan relatif terhadap versi MP4, dengan `source_export_id` atau identitas artefak legacy. Jika versi video aktif berubah, desain lama tetap terikat pada video lama dan ditandai **Perlu ditinjau untuk versi baru**; jangan diam-diam menggeser frame.
- Subtitle yang sudah terbakar dalam MP4 akan ikut muncul. Sediakan panduan posisi judul agar tidak bertabrakan; menghilangkan subtitle dari frame bukan scope awal.
- Jika MP4 hilang/rusak/tidak mempunyai frame valid, tampilkan error spesifik tanpa menghilangkan desain atau gambar yang pernah berhasil diekspor.
- Decoder dapat mengambil frame terdekat dengan waktu yang diminta. Kembalikan timestamp frame aktual; jangan menjanjikan akurasi di antara frame video.
- Jangan memuat seluruh video atau ratusan frame ke memori. Decode terbatas, downscale kandidat untuk preview, lalu render gambar final ketika diminta.
- Warna teks/outline/latar harus cukup terbaca pada contoh frame terang dan gelap. Jangan menjanjikan teks cocok untuk setiap latar otomatis.
- Preview menampilkan peringatan overflow bila judul tidak muat. Ekspor ditolak sampai teks/layout diperbaiki; jangan memangkas judul diam-diam.
- Draft belum disimpan, menyimpan, gagal dan konflik terlihat jelas. Navigasi tidak boleh menghilangkan edit tanpa pemberitahuan.
- Caption dan judul thumbnail adalah field terpisah. Jangan otomatis menggunakan transkrip mentah sebagai judul, atau menimpa caption ketika judul berubah.
- Jangan memberi judul yang menjanjikan fakta di luar video. UI menyarankan judul sesuai pembahasan tanpa klaim jaminan viral.

## 5. Data dan API usulan

Kontrak berikut belum tersedia. Implementer menyelaraskannya dengan ID/revisi pada editor M1.

```text
clip.thumbnail_draft = {
  revision, source_export_id, frame_time_requested, frame_time_actual,
  format, fit_mode, crop_x, crop_y,
  title, template, text_position, palette
}
clip.thumbnail_exports[] = {
  thumbnail_id, draft_revision, source_export_id,
  width, height, image_format, file, created_at
}
```

| Endpoint usulan | Fungsi |
| --- | --- |
| `GET /api/jobs/<jid>/clips/<clip_id>/thumbnail` | Draft/default, versi video, kandidat dan kemampuan edit |
| `POST /api/jobs/<jid>/clips/<clip_id>/thumbnail/frame` | Decode satu frame pada timestamp tervalidasi; kembalikan ID/URL preview, bukan path disk mentah |
| `PATCH /api/jobs/<jid>/clips/<clip_id>/thumbnail` | Simpan draft dengan expected revision; 409 jika konflik |
| `POST /api/jobs/<jid>/clips/<clip_id>/thumbnail/exports` | Render desain tersimpan ke PNG/JPG memakai snapshot revisi |

Revisi thumbnail terpisah dari caption/draft MP4. Request ekspor yang diulang harus idempotent agar tidak menumpuk file identik. Publikasikan file lewat temporary output lalu rename setelah sukses; simpan hanya metadata output yang benar-benar tersedia. Kegagalan tidak menimpa gambar terakhir yang valid.

Untuk MVP, decode/render gambar dapat menjadi request sinkron yang dibatasi ukuran/waktu; jika benchmark menunjukkan request terlalu lama, ubah ke 202 + status. Jangan menambahkan thread tak terbatas. Tolak dengan busy 409 ketika pekerjaan berat lain sedang aktif dan gunakan coordinator bersama jika M3 editor sudah tersedia.

## 6. Batas teknis

- Gunakan pipeline media lokal yang sudah ada. Jika perlu compositor gambar/font tambahan, jelaskan alasan, pin dependensi dan perbarui setup/doctor. Tidak menambah model AI besar.
- Font harus tersedia lokal atau dibundel dengan lisensi yang sesuai; jangan bergantung pada font laptop pengembang atau Google Fonts saat render offline. Rekam fallback yang dipakai.
- Tentukan koordinat layout dalam kanvas output; scaling preview harus memakai rasio sama. Uji kontras/line wrapping dan karakter Indonesia/Inggris.
- Validasi angka finite, preset format/template, panjang teks, rentang crop dan kepemilikan job/clip/export. Path traversal dan symlink keluar data ditolak.
- Teks diperlakukan sebagai data; tidak diinterpolasi ke shell. Batasi request dan waktu decode agar video rusak tidak menggantung server.
- Frame sementara/preview masuk folder pekerjaan yang sama, dengan batas jumlah cache. Hapus history juga menghapus thumbnail/preview pekerjaan; tidak menghapus model atau pekerjaan lain.
- Tetap loopback, tanpa telemetry atau pengiriman gambar/transkrip ke cloud.

## 7. Acceptance criteria

| ID | Skenario | Hasil wajib |
| --- | --- | --- |
| TH-01 | Membuat cover pada klip legacy | Berhasil tanpa mengubah MP4/caption/subtitle |
| TH-02 | Memilih timestamp di luar batas, NaN/Infinity atau video rusak | Ditolak jelas; decoder tidak menggantung |
| TH-03 | Pilih kandidat/waktu manual | Preview dan hasil memakai frame yang sama; waktu aktual diketahui |
| TH-04 | Ekspor kedua preset dalam PNG/JPG | Dimensi benar, file bisa dibuka, crop dan judul sesuai draft |
| TH-05 | Judul panjang, karakter khusus atau baris tidak muat | Tidak ada shell/HTML injection; overflow tidak dipotong diam-diam |
| TH-06 | Simpan, refresh/restart/browser lain | Draft server dan ekspor tetap tersedia |
| TH-07 | Dua tab mengubah revisi yang sama | Konflik 409 tanpa menghapus draft pengguna |
| TH-08 | Render gagal/disk penuh | Gambar terakhir dan metadata lama tetap valid |
| TH-09 | Versi MP4 aktif berubah | Desain lama tidak berpindah frame diam-diam; ditandai perlu ditinjau |
| TH-10 | Sumber asli hilang tetapi MP4 klip ada | Cover tetap dapat dibuat dari MP4 klip |
| TH-11 | Hapus history fixture | Preview/gambar target terhapus, pekerjaan lain dan model tetap ada |
| TH-12 | Instalasi baru/offline setelah dependensi tersedia | Font dan renderer tidak bergantung pada aset laptop pembuat |

Tes unit/integrasi memakai fixture pendek dan direktori sementara. Pemeriksaan gambar meliputi ukuran, frame yang dipilih, keberadaan glyph/outline serta snapshot/layout visual; bukan hanya memeriksa argumen command. Verifikasi UI desktop/sempit, keyboard dan state loading/error. Uji resource nyata pada RAM 8 GB sebelum menyebut fitur ringan.

## 8. Risiko dan rollout

Judul dapat menutupi subtitle bawaan, frame otomatis dapat menunjukkan mata tertutup/blur, dan font antar-mesin dapat mengubah wrapping. Fallback MVP adalah frame dan posisi manual dengan template terbatas. Pilihan default tidak mengklaim memahami subjek atau menjamin performa platform.

Tahap pertama mengerjakan frame + judul manual + ekspor. Tambahan AI/auto-ranking hanya dipertimbangkan setelah baseline dan umpan balik pengguna. Fitur baru tidak memerlukan migrasi atau render ulang seluruh history.


## Integrasi opsional berikutnya

Kebutuhan watermark/logo dirancang terpisah di [PRD watermark](KLIP_WATERMARK.md). Upload logo dan overlay tidak masuk MVP thumbnail awal secara otomatis; saat fitur watermark diimplementasikan, compositor gambar perlu menerapkan snapshot overlay setelah judul tanpa mengubah MP4 sumber.
