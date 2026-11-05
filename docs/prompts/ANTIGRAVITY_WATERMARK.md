# Prompt Antigravity — Watermark

Status: handoff usulan, belum diimplementasikan. Baca dependensi pada PRD sebelum menjalankan. Prompt tidak mengizinkan pengerjaan seluruh editor/thumbnail sebagai scope tambahan tersembunyi.

```text
Tambahkan watermark opsional pada Klip lokal sesuai docs/prd/KLIP_WATERMARK.md.

Baca AGENTS.md, SKILLS.md, PRD watermark, PRD editor dan PRD thumbnail, lalu inspeksi implementasi aktual dan git status. Pertahankan perubahan/untracked file yang sudah ada; jangan reset atau menghapus data pengguna.

Mulai dengan audit dependensi: clip_id/revisi dari editor M1, renderer gambar thumbnail dan lifecycle ekspor video M3. Pilih tahap watermark yang benar-benar bisa diintegrasikan pada fondasi yang tersedia. Jika renderer belum ada, kerjakan aset/preset/draft/preview yang valid saja dan tandai integrasi ekspor belum tersedia; jangan membangun seluruh milestone editor di luar tugas ini atau membuat tombol ekspor palsu.

MVP watermark:
- Nonaktif secara default. Satu overlay: teks maksimal 60 karakter atau logo statis PNG alpha/JPG maksimal 5 MiB dan 4096x4096.
- Validasi isi/decode, MIME, dimensi, animasi dan decompression bomb. Normalisasi aset ke file immutable internal; tidak menerima URL/path client, SVG/HTML/GIF atau font upload.
- Sembilan anchor posisi, lebar 5–30% kanvas, opasitas 10–100%, margin 0–10% dimensi terpendek, rasio aspek tetap dan bounding box dalam frame.
- Default aktif: kanan atas, lebar 15%, opacity 70%, margin 3%. Preview dan peringatan benturan judul/subtitle; tidak menggeser konten lain otomatis.
- Draft/preset server dengan ID, snapshot dan optimistic concurrency. Preset berubah tidak mengubah draft/output lain. Caption dan judul tidak diubah sebagai efek watermark.
- Watermark berada pada koordinat output setelah crop/scale, di atas subtitle/judul. Font tersedia lokal/bundled dengan lisensi sesuai; tidak bergantung laptop pembuat.
- Integrasi ekspor memakai temporary output, publikasi versi setelah sukses, coordinator berat dan idempotency yang sama. Tidak mengunduh, mentranskripsi atau membuat caption ulang. Gagal/aset hilang tidak menghasilkan sukses tanpa watermark atau menghapus versi lama.
- Library aset/preset di luar folder job dan tetap diabaikan scanner history. Hapus satu history tidak menghapus logo bersama. Tidak ada garbage collection/penghapusan aset otomatis pada MVP.

Tidak menambah model AI, cloud, telemetry, public bind, framework UI baru, watermark animasi, penghapus watermark pihak lain atau penerapan massal ke seluruh history. Jangan commit/push/deploy atau mematikan pekerjaan aktif.

Buat rencana singkat berdasarkan fondasi yang ada, lalu implementasikan tahap yang disepakati scope prompt ini dan verifikasi WM-01 sampai WM-12 yang relevan. Nyatakan acceptance criteria yang belum dapat dikerjakan karena dependensi; jangan mengklaim semua selesai bila baru preview.

Gunakan video/gambar fixture milik tes dan temporary directory. Uji compositing frame/gambar nyata (alpha, posisi, skala, teks), audio/subtitle tetap ada, gagal render, konflik revisi dan aset bersama. Verifikasi UI desktop/sempit, update API/USAGE/SETUP/ARCHITECTURE sesuai perubahan, dan laporkan command/hasil nyata serta batas implementasi.
```

Acuan: [PRD watermark](../prd/KLIP_WATERMARK.md), [PRD editor](../prd/KLIP_REVIEW_EDITOR.md), [PRD thumbnail](../prd/KLIP_THUMBNAIL.md).
