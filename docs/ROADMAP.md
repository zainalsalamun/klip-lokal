# Usulan pengembangan

**Arah saat ini:** Kelip Studio berfokus pada versi lokal. Akun, pembayaran dan SaaS online ditunda. Prioritaskan kualitas hasil, editor koreksi dan penggunaan laptop8GB. Status implementasi terbaru ada pada catatan K2/K3; bagian usulan lama di bawah tetap menjadi referensi perencanaan.

Daftar ini adalah bahan perencanaan, **bukan fitur yang sudah tersedia atau janji jadwal**. Prioritas akhir mengikuti kebutuhan pengguna dan bukti pengujian.

| Usulan | Manfaat | Bukti selesai yang diperlukan |
| --- | --- | --- |
| Evaluasi kualitas transkrip dan caption | Mengukur kesalahan bahasa, pengulangan, klaim tambahan dan penolakan yang terlalu ketat | Dataset contoh yang boleh digunakan, metrik dan hasil sebelum/sesudah |
| Alignment subtitle per kata | Subtitle lebih selaras dengan ucapan | Pemeriksaan audio/video nyata untuk beberapa bahasa dan kecepatan bicara |
| Pemilihan klip berbasis konteks | Mengurangi kandidat yang kehilangan konteks | Penilaian manusia terhadap klip dan pembanding scoring lama |
| Deteksi pembicara lebih akurat | Mengurangi crop ke orang yang tidak sedang berbicara | Uji multipembicara, wajah menyamping, scene cut dan audio tumpang tindih |
| Editor batas klip dan crop manual | Memungkinkan koreksi sebelum ekspor | Validasi rentang, preview, re-ekspor dan pelestarian sumber |
| Cancel/resume dan worker terpisah | Pemulihan pekerjaan panjang | Uji penghentian, restart, idempotensi dan kompatibilitas history |
| Penyimpanan history berbasis database | Mengurangi biaya scan direktori saat data besar | Migrasi yang dapat diverifikasi, pagination/search dan penanganan kegagalan migrasi |
| CI otomatis | Memeriksa regresi di setiap perubahan | Workflow yang benar-benar berjalan, fixture tanpa data pribadi, tanpa unduhan model dalam unit test |

Saat memilih satu usulan, buat issue dengan ruang lingkup dan kriteria penerimaan yang lebih kecil. Refactor, distribusi lintas platform atau hosting publik perlu pembahasan terpisah; jangan dianggap perbaikan rutin yang sudah disetujui.


Prioritas rilis berikutnya direkomendasikan melalui [analisis produk](PRODUCT_REVIEW.md): mulai dari penyimpanan caption persisten dan editor koreksi hasil. [PRD Tinjau & Perbaiki Klip](prd/KLIP_REVIEW_EDITOR.md) memecahnya menjadi M1/M2/M3. [Prompt Antigravity](prompts/ANTIGRAVITY_REVIEW_EDITOR.md) menugaskan satu milestone per tahap. Semua masih usulan, belum implementasi.


Usulan thumbnail/cover tersedia di [PRD thumbnail](prd/KLIP_THUMBNAIL.md). Scope awal: kandidat frame asli, pilih waktu, judul/template, simpan desain dan ekspor PNG/JPG. Belum termasuk generative image atau upload platform.


Kebutuhan tambahan [watermark teks/logo](prd/KLIP_WATERMARK.md) mencakup preset, posisi/ukuran/opasitas serta integrasi video/thumbnail. [Prompt implementasi](prompts/ANTIGRAVITY_WATERMARK.md) memisahkan fondasi aset/preview dari integrasi renderer yang belum tersedia.


[Studio Anak 3–5 Indonesia](prd/KLIP_KIDS_STUDIO.md) diusulkan sebagai modul kreator dengan ide editorial, brief produksi dan integrasi clipper bertahap. Bukan pemutar YouTube Kids, pencatat tontonan anak atau generator animasi/lagu. Lihat [riset](KIDS_CONTENT_RESEARCH.md) dan [prompt](prompts/ANTIGRAVITY_KIDS_STUDIO.md).
