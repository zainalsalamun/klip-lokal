# Analisis pengembangan Klip lokal

Tanggal: 5 November 2026. Dasar: kode checkout saat penyusunan dan masalah penggunaan dalam pengembangan. Ini penilaian produk, bukan hasil riset pasar atau benchmark akurasi. Dokumen ini tidak mengimplementasikan fitur baru.

## Kesimpulan

Prioritas berikutnya adalah **membuat hasil otomatis mudah diperiksa dan dikoreksi**. Menambah model yang lebih besar sebelum menyediakan editor akan menambah beban instalasi/RAM dan belum tentu menghilangkan kesalahan. Pengguna membutuhkan jalan keluar saat AI atau crop kurang sesuai.

## Kondisi yang terlihat pada source

| Temuan | Bukti pada implementasi | Dampak |
| --- | --- | --- |
| Caption manual masih disimpan di browser | `captionEditor()` pada `static/app.js`, key `klip-caption:` | Edit dapat hilang bila storage dibersihkan atau berpindah browser |
| AI caption sudah memakai bahasa per studio, validasi dan retry | `summarize()`/`parse_summary()` pada `local_caption.py` | Mengurangi salah bahasa, tetapi bukan jaminan isi/grammar benar |
| Subtitle berasal dari segmen dan pembagian kelompok kata | `write_subs()` pada `app.py` | Belum bisa membetulkan ucapan/nama/timing melalui UI |
| Batas klip dan crop otomatis masih heuristik | `candidates()` dan `speaker_crop.py` | Kandidat bisa kehilangan konteks atau framing meleset |
| Regenerasi caption sudah terpisah dari ekspor video | Endpoint caption pada `app.py` | Pola yang baik untuk diperluas ke edit manual yang tersimpan |
| History sudah punya pencarian, pagination dan hapus pekerjaan | Route history dan editor JS | Sudah cukup untuk penggunaan awal; belum ada kuota/ukuran per pekerjaan atau hapus satu klip |
| Worker berada dalam proses Flask | `process()` dan thread pada `create()` | Restart memutus pekerjaan; belum ada cancel/resume atau antrean durable |
| Bootstrap/doctor sudah ada; target teruji macOS Apple Silicon | `setup_local.py` dan `docs/NEW_MACHINE.md` | Jangan mengklaim installer lintas OS sudah siap |

## Rekomendasi prioritas

| Prioritas | Tambahan | Alasan | Kompleksitas relatif |
| --- | --- | --- | --- |
| P0 | Caption manual tersimpan ke server, indikator simpan dan konflik | Mencegah hilangnya koreksi pengguna; bisa dirilis tanpa render/model baru | Kecil–sedang |
| P0 | Editor subtitle, trim, crop manual dan ekspor ulang satu klip | Mengoreksi hasil otomatis tanpa unduh/transkripsi ulang | Besar; pecah milestone |
| P1 | Watermark teks/logo opsional pada video dan thumbnail | Identitas hasil publikasi tanpa model baru; bergantung renderer versi | Sedang |
| P1 | Thumbnail/cover dari frame asli, judul dan template manual | Melengkapi paket publikasi tanpa model gambar tambahan; setelah ID klip stabil | Sedang |
| P1 | Informasi penyimpanan, hapus satu klip dan batas ruang kosong | Penggunaan disk lokal mudah bertambah karena sumber dan hasil | Sedang; perlu aturan artefak bersama |
| P1 | Antrean pekerjaan dan cancel yang jelas | Membuat proses panjang lebih mudah dikendalikan | Besar; terkait worker dan lifecycle subprocess |
| P1 | Evaluasi transkrip/caption dengan contoh terkurasi | Mengukur salah bahasa, klaim tambahan, penolakan dan waktu proses sebelum mengganti model | Sedang dan berkelanjutan |
| P2 | Alignment subtitle per kata dan pemilihan kandidat berbasis konteks | Meningkatkan mutu otomatis setelah pengguna punya editor/fallback | Besar; butuh evaluasi media nyata |
| P2 | Dukungan platform lain/installer yang dikemas | Memperluas pengguna setelah core stabil | Besar; memerlukan pengujian mesin/OS lain |

Kompleksitas merupakan estimasi relatif, bukan janji durasi. Belum ada data penggunaan yang cukup untuk menyatakan urutan ini optimal bagi semua pengguna.

## Yang sebaiknya ditunda

Akun/cloud hosting, autopost media sosial, dubbing, klaim skor viral, analytics channel dan model besar sebagai default. Semuanya menambah biaya, integrasi atau beban hardware yang belum menyelesaikan kebutuhan koreksi hasil saat ini.

## Rilis yang direkomendasikan

Paket P0 bernama kerja **Tinjau & Perbaiki Klip**. Implementasikan bertahap: M1 penyimpanan caption manual; M2 draft editor subtitle/trim/crop; M3 ekspor ulang per klip dengan versi hasil. Hindari satu perubahan besar yang mencakup seluruh roadmap.

Spesifikasi: [PRD](prd/KLIP_REVIEW_EDITOR.md). Prompt siap pakai: [Antigravity](prompts/ANTIGRAVITY_REVIEW_EDITOR.md). Semua fitur dalam kedua dokumen itu masih usulan sampai diimplementasikan dan diverifikasi.


Tambahan usulan pengguna: [thumbnail/cover klip](prd/KLIP_THUMBNAIL.md), dengan [prompt Antigravity terpisah](prompts/ANTIGRAVITY_THUMBNAIL.md). MVP memakai frame asli dan judul manual; tidak membutuhkan model pembuat gambar. Bisa diprioritaskan setelah fondasi M1 tersedia, tanpa harus menunggu seluruh editor video selesai.


Tambahan kebutuhan: [watermark teks/logo](prd/KLIP_WATERMARK.md) dengan [prompt Antigravity](prompts/ANTIGRAVITY_WATERMARK.md). Pengaturan disimpan per draft/preset; hasil lama tidak diubah otomatis. Integrasi video mengikuti ekspor versi M3, sedangkan integrasi gambar mengikuti renderer thumbnail.


Kebutuhan tambahan pengguna: [Studio Anak](prd/KLIP_KIDS_STUDIO.md), khusus kreator konten usia 3–5 tahun berbahasa Indonesia. [Riset dan katalog awal](KIDS_CONTENT_RESEARCH.md) membedakan bukti popularitas historis dari ide editorial. K1 menu/brief bisa dikerjakan mandiri; K2 pipeline dan K3 editor dipisah melalui [prompt Antigravity](prompts/ANTIGRAVITY_KIDS_STUDIO.md). Ini ekspansi produk terpisah, bukan bukti bahwa clipper otomatis menilai kesesuaian anak.
