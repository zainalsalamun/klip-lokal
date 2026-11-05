# Prompt implementasi untuk Antigravity

Status: handoff, **belum menjalankan implementasi**. Buka repository Klip lokal di Antigravity, lalu salin satu blok prompt sesuai milestone. Jangan menjalankan ketiga milestone sekaligus. Semua path di bawah relatif terhadap root repository yang dibuka.

Dokumen acuan: [PRD](../prd/KLIP_REVIEW_EDITOR.md) dan [analisis produk](../PRODUCT_REVIEW.md).

## Prompt 1 — Mulai dari M1 (direkomendasikan)

```text
Kerjakan aplikasi Klip lokal pada repository yang sedang dibuka.

Baca terlebih dahulu:
- AGENTS.md dan SKILLS.md
- docs/PRODUCT_REVIEW.md
- docs/prd/KLIP_REVIEW_EDITOR.md
- docs/DEVELOPMENT.md, docs/API.md, docs/TESTING.md

Tujuan tugas ini: implementasikan HANYA M1 “Simpan caption” dari PRD Tinjau & Perbaiki Klip. M2, M3 dan usulan P1/P2 belum diizinkan dalam tugas ini.

Mulai dengan inspeksi kode dan git status. Dokumentasi dapat tertinggal: cocokkan dengan implementasi aktual. Pertahankan semua perubahan/untracked file yang sudah ada. Jangan reset, membersihkan working tree, atau menganggap file untracked boleh dihapus.

Buat rencana singkat berdasarkan kode aktual, lalu lanjutkan implementasi dan verifikasi; jangan berhenti hanya dengan rencana.

Hasil yang dibutuhkan:
1. ID klip stabil untuk record baru dan lama, tanpa mengubah URL legacy atau urutan klip. Migrasi metadata tidak destruktif; persist pada write pertama. Sertakan schema version/default yang diperlukan.
2. Endpoint simpan caption manual per clip_id dengan expected_revision dan optimistic concurrency. Maksimal 2.000 karakter, teks kosong valid, validasi tipe/payload, penyimpanan atomik. Caption manual ditandai manual, bukan hasil validasi AI.
3. Editor caption mempunyai tombol Simpan dan status tersimpan/berubah/menyimpan/gagal/konflik. Hasil simpan bertahan setelah refresh, restart, dan browser lain di laptop yang sama.
4. Draft localStorage lama tidak dihapus atau menimpa server diam-diam: tawarkan pulihkan atau pakai versi server. Jangan hilangkan teks saat request gagal atau konflik.
5. Regenerasi caption AI tetap terpisah dari render video, mempertahankan target Indonesia untuk lokal dan Inggris untuk Global. Hasil AI yang selesai terlambat tidak boleh menimpa caption manual dengan revisi lebih baru. Konfirmasi penggantian draft dilakukan di halaman, bukan dialog native yang menghambat alur.
6. UI tetap mengikuti desain yang ada. Sidebar hanya menu Riwayat; isi daftar di area utama. Jangan menambahkan framework UI/build pipeline baru.
7. Update API.md, USAGE.md dan dokumentasi lain yang benar-benar terdampak.

Batasan:
- Jangan mengubah algoritme crop, model AI, transkripsi, atau menambahkan ekspor ulang video untuk M1.
- Jangan menambahkan cloud fallback, telemetry, login, public bind, database baru atau model/dependensi besar.
- Jangan memproses/menghapus video, history, model atau draft pribadi pengguna sebagai fixture tes.
- Jangan restart server jika health menunjukkan video/caption aktif. Jangan menjalankan server kedua pada data/ yang sama.
- Gunakan temporary directory/fixture sendiri untuk pengujian. Gunakan mock transport pada unit test AI; jangan mengunduh model sebagai bagian tes default.
- Jangan commit, push atau deploy. Jangan mengubah konfigurasi global laptop.

Verifikasi:
- Penuhi AC-01 sampai AC-06 pada PRD untuk M1; tambahkan kasus input invalid, caption kosong, server write gagal, konflik dua tab dan AI selesai setelah edit manual.
- Jalankan suite Python yang relevan, tes error JS dan pemeriksaan sintaks/diff sesuai docs/TESTING.md.
- Verifikasi UI desktop dan layar sempit: save, loading/error, pemulihan draft, konflik dan navigasi dengan edit belum disimpan.
- Bedakan tes otomatis mock dengan pengujian browser/model nyata. Jangan mengklaim checks yang tidak dijalankan.

Jika menemukan keputusan rutin, pilih implementasi paling kecil yang memenuhi PRD dan dokumentasikan. Jika ada kendala besar yang mengubah scope/kontrak data, jelaskan deviasi sebelum memperluas pekerjaan.

Akhiri dengan ringkasan perilaku yang berubah, file penting, bukti verifikasi, keterbatasan dan status M1. Jangan lanjut M2 otomatis.
```

## Prompt 2 — M2, setelah M1 diterima

```text
Lanjutkan repository Klip lokal dari implementasi M1 yang sudah diverifikasi.
Baca AGENTS.md, SKILLS.md, docs/prd/KLIP_REVIEW_EDITOR.md dan implementasi aktual M1 terlebih dahulu. Jangan berasumsi M1 lengkap hanya berdasarkan percakapan atau dokumen.

Kerjakan HANYA M2 “Draft editor”:
- Editor klip di area utama dengan kembali ke hasil tanpa kehilangan draft tersimpan.
- Subtitle per segmen dan timestamp absolut terhadap sumber, tanpa mengubah transkrip sumber/klip lain.
- Trim 5–120 detik dalam durasi sumber; backend memvalidasi finite/rentang/urutan/overlap dan batas segmen yang menyilang trim.
- Preview sumber/proxy yang mendukung seek/Range tanpa memuat seluruh video ke RAM. Validasi ID, allowlist berkas, MIME, symlink dan kepemilikan job.
- Crop tengah, perkiraan pembicara yang sudah ada dan posisi manual horizontal 0–1. Tangani portrait tanpa rentang gerak. Gunakan preset subtitle/resolusi existing.
- Penyimpanan draft dengan optimistic concurrency terpisah dari revisi caption; indikator “Perubahan belum diekspor”.
- Sumber hilang tidak menghilangkan caption atau MP4 lama.

Belum mengimplementasikan M3. Jangan membuat tombol ekspor yang terlihat berhasil tetapi belum menghasilkan output. Jika preview belum identik dengan ASS final, labelkan sebagai ilustrasi.

Pertahankan kompatibilitas record/URL lama, data pengguna dan desain sidebar. Tidak ada cloud, framework baru, model baru, database atau perubahan konfigurasi global. Jangan menghentikan pekerjaan aktif, commit/push/deploy, atau memakai data pengguna sebagai fixture.

Buat rencana singkat lalu implementasikan, uji AC-07 sampai AC-10 dan kasus keamanan/revisi yang relevan, serta jalankan regresi M1. Verifikasi browser desktop/sempit dan update dokumentasi. Laporkan bukti serta batas implementasi; jangan lanjut M3 otomatis.
```

## Prompt 3 — M3, setelah M2 diterima

```text
Lanjutkan Klip lokal dari M1/M2 yang telah diverifikasi. Baca AGENTS.md, SKILLS.md dan docs/prd/KLIP_REVIEW_EDITOR.md, lalu audit draft editor dan lifecycle worker aktual.

Kerjakan HANYA M3 “Ekspor per klip”:
- Ekspor asynchronous satu klip dari sumber dan snapshot draft tersimpan. Jangan mengunduh, mentranskripsi, atau membuat caption AI ulang sebagai efek ekspor video.
- Snapshot menyimpan draft_revision; edit selama render tidak mengubah snapshot dan tetap ditandai belum diekspor.
- Output sementara dan publikasi metadata/file setelah sukses. Jangan menimpa MP4 aktif; sediakan versi aktif dan versi sebelumnya.
- Satu coordinator untuk seluruh pekerjaan berat: pemrosesan video, caption AI dan ekspor ulang. Jangan memakai lock terpisah yang masih membolehkan pekerjaan berat tumpang tindih. Request busy ditolak jelas; tidak membangun antrean durable/cancel/resume dalam milestone ini.
- Request ekspor 202, status polling, idempotency key, retry tanpa kerja ganda, cleanup subprocess/resource pada kegagalan. Restart yang memutus ekspor tidak boleh mengaku sukses atau resume.
- Allowlist URL artefak versi dengan ID tervalidasi; pertahankan URL legacy. Sumber tetap terlindungi oleh aturan endpoint lokal.
- Kegagalan/disk penuh tidak menghapus versi terakhir atau mengubah klip lain.

Penuhi AC-11 sampai AC-15 beserta regresi M1/M2. Gunakan render FFmpeg nyata dengan video fixture pendek untuk membuktikan trim/crop/subtitle/dimensi/audio dan bahwa artefak klip lain tetap sama. Unit test tidak memakai model/network dan tidak menghapus data pengguna. Verifikasi UI loading/gagal/versi/draft basi pada desktop serta layar sempit.

Tidak menambah cloud, database, model, auto cleanup, fitur publikasi, dukungan OS baru, atau framework. Jangan commit, push atau deploy. Jangan mematikan pekerjaan pengguna. Update API/USAGE/ARCHITECTURE serta catat keputusan coordinator/versi dan batas rollback.

Buat rencana singkat, lanjutkan implementasi dan pengujian, lalu laporkan hasil nyata. Jangan mengerjakan roadmap P1/P2 otomatis.
```

## Membaca hasil handoff

Setelah setiap milestone, minta implementer menyebutkan acceptance criteria yang lolos, command pengujian, bukti UI/media yang relevan, dan keterbatasan. Jika konteks chat Antigravity baru, berikan kembali prompt milestone serta dokumen acuan; jangan mengandalkan ingatan chat lama. Kata “selesai” tanpa bukti tidak cukup untuk menyimpulkan migrasi atau render sudah aman.
