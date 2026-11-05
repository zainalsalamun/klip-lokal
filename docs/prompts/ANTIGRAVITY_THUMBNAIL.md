# Prompt Antigravity — Thumbnail dan cover

Status: handoff usulan, belum diimplementasikan. Buka source Klip lokal di Antigravity, lalu salin blok berikut setelah fondasi ID klip stabil/editor M1 tersedia. Jangan menjalankannya bersamaan dengan milestone editor yang belum selesai.

```text
Kerjakan fitur Thumbnail dan Cover Klip pada repository Klip lokal yang sedang dibuka.

Baca AGENTS.md, SKILLS.md, docs/PRODUCT_REVIEW.md, docs/prd/KLIP_THUMBNAIL.md dan docs/TESTING.md. Periksa implementasi aktual dan status Git. Pertahankan perubahan dan file untracked yang sudah ada.

Scope: HANYA MVP pada PRD thumbnail. Jangan mengerjakan seluruh roadmap atau editor M2/M3 dalam tugas ini.

Pastikan clip_id stabil, revisi metadata dan simpan caption pada M1 sudah tersedia. Jika belum, jelaskan dependensinya dan buat rencana penyelesaian terpisah; jangan menambah identitas/migrasi kedua yang bertentangan dengan PRD editor.

Implementasikan:
1. Tombol Buat thumbnail pada hasil/history dan editor di area utama.
2. Kandidat frame sekitar 25/50/75% MP4 klip aktif, serta pilihan timestamp manual. Kandidat adalah heuristik, bukan klaim frame terbaik.
3. Cover 9:16 1080x1920 dan thumbnail 16:9 1280x720. Fit/fill, crop manual terbatas, judul manual maksimal 80 karakter dengan validasi overflow dan hingga 3 baris, tiga template lokal yang dapat dibaca.
4. Preview konsisten dengan renderer, source export ID, requested/actual frame time, draft server dengan optimistic concurrency dan status simpan.
5. Ekspor PNG/JPG idempotent dari snapshot draft tersimpan, dengan file sementara dan publikasi atomik. Jangan menimpa gambar terakhir yang valid saat gagal.
6. Tautkan desain ke versi MP4 sumber. Jika video aktif berubah, tandai desain perlu ditinjau; jangan bergeser frame otomatis. Klip legacy tetap didukung.
7. Gunakan MP4 klip, bukan wajib sumber asli. Tidak mengunduh video, menjalankan Whisper, membuat caption ulang, atau merender ulang MP4 saat membuat cover.
8. Batasi decode/cache/waktu proses. Gunakan busy coordinator yang sama jika tersedia; jangan menambah pekerjaan berat paralel tanpa batas.
9. Gunakan font yang tersedia lokal/bundled dengan lisensi sesuai. Tidak boleh bergantung pada font pribadi laptop pengembang. Jika perlu dependency compositor, jelaskan alasan, pin dan update setup/doctor.

Tidak menambahkan model gambar, judul AI, cloud/API key, logo/font upload, autopost, database atau framework UI baru. Caption dan judul thumbnail terpisah. Pertahankan sidebar sebagai navigasi dan daftar history di area utama.

Validasi input, Range/seek yang relevan, ID/ownership dan allowlist artefak; cegah traversal, symlink keluar data serta shell/HTML injection. Hapus history menghapus thumbnail milik pekerjaan itu saja. Jangan menggunakan/menghapus data pengguna sebagai fixture atau menghentikan job aktif. Jangan commit, push atau deploy.

Buat rencana singkat berdasarkan kode, lalu implementasikan dan uji TH-01 sampai TH-12. Gunakan fixture video pendek dan pemeriksaan file gambar nyata (dimensi, frame, teks/layout), bukan hanya mock command. Verifikasi UI desktop/sempit dan offline font. Jalankan regresi terkait dan perbarui API/USAGE/SETUP bila terdampak.

Akhiri dengan ringkasan perilaku, command/hasil pemeriksaan yang benar-benar dijalankan, screenshot/artefak uji relevan, penggunaan resource yang diukur dan batas yang belum diverifikasi. Jangan mengklaim kompatibilitas upload platform sosial atau akurasi pemilihan frame tanpa bukti.
```

Acuan: [PRD thumbnail](../prd/KLIP_THUMBNAIL.md), [PRD editor](../prd/KLIP_REVIEW_EDITOR.md), [analisis prioritas](../PRODUCT_REVIEW.md).
