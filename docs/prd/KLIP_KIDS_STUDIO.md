# PRD — Studio Anak

Status: **K1 dan K2 diimplementasikan; K3 terhubung ke editor caption/watermark dan ekspor turunan sederhana**. Trim/subtitle manual M2 serta editor desain thumbnail penuh belum tersedia. Versi 1.0, 5 November 2026. Target yang dipilih pengguna: kreator dewasa yang membuat konten **anak usia 3–5 tahun, bahasa Indonesia, pasar Indonesia**. Studio ini bukan aplikasi pemutar untuk anak atau sistem pemantauan tontonan anak.

Dasar rekomendasi dan sumber platform: [riset konten anak](../KIDS_CONTENT_RESEARCH.md). Arah produk: ide yang dapat diproduksi dan hasil yang mudah diperiksa, bukan mengejar tontonan kompulsif atau menjanjikan video viral.

## 1. Tujuan

Kreator dapat menemukan ide anak yang konkret, menyimpan brief produksi, dan mengolah video sumber bahasa Indonesia menjadi kandidat klip yang sesuai tujuan yang dipilih untuk ditinjau. Mode ini tidak otomatis membuktikan kesesuaian usia atau memperbaiki materi sumber yang tidak sesuai.

MVP tidak membuat animasi, musik atau dubbing dari nol. Tidak ada scraping riwayat penonton, profil anak, integrasi akun YouTube, penerbitan otomatis, klaim lolos moderasi atau model baru. Platform yang sudah teruji tetap macOS Apple Silicon.

## 2. Milestone

| Tahap | Scope | Bukti selesai |
| --- | --- | --- |
| K1 — Ide dan brief | Menu Studio Anak, katalog editorial, detail ide, brief lokal persisten | Katalog/filter, simpan/muat/ekspor brief dan kompatibilitas halaman lama |
| K2 — Integrasi clipper | Metadata profil anak, input sumber, kandidat untuk ditinjau, caption Indonesia, state keterbatasan audio | Pipeline tidak menukar mode/bahasa dan tidak mengaku melakukan pemeriksaan visual anak |
| K3 — Integrasi editor/publikasi lokal | Tautan edit/thumbnail/watermark yang sudah diimplementasikan | Perubahan mengikuti revisi/versioning dan tidak menambah tombol ekspor palsu |

K1 dapat dirilis tanpa worker baru atau editor M1. K2 perlu inspeksi kontrak request/metadata saat implementasi. K3 bergantung pada renderer/editor dari PRD terkait; tidak membangun seluruh fitur tersebut di dalam tugas Studio Anak.

## 3. Alur dan UI

Sidebar menambah menu **Studio Anak** yang membuka `/kids`. Riwayat tetap berupa menu navigasi; daftar history tetap berada di area utama.

Halaman menampilkan:

1. Header “Studio Anak — 3–5 tahun · Bahasa Indonesia”. Ini target MVP, bukan hasil deteksi penonton.
2. Katalog ide editorial: warna, angka, bentuk, hewan, lagu/gerak, rutinitas, cerita/emosi dan kreativitas. Tidak memakai label trending/live tanpa sumber data yang mendukung.
3. Kartu berisi judul, tujuan tunggal, outline singkat, kebutuhan rekaman/aset, durasi usulan dan status “cocok dicoba dengan clipper ucapan” atau “rencana produksi; perlu pemilihan manual”.
4. Tombol **Pakai ide** mengisi brief, bukan mengunduh referensi atau mengklaim isi sumber cocok.
5. Brief: judul kerja, tujuan, kategori, objek/karakter yang dibuat sendiri, pembukaan–kegiatan–penutup, catatan sumber/aset dan durasi target. Target usia/bahasa tampil jelas.
6. Mulai K2, tombol **Gunakan video sendiri** menuju form sumber dengan metadata brief terpilih. Video bahasa Indonesia disiapkan kreator; audio asli dipertahankan.
7. Hasil memakai label **Kandidat untuk ditinjau** dan memperlihatkan tujuan brief, transkrip serta caption. Pembaca tidak boleh menyimpulkan label kids berarti sertifikat kesesuaian.

UI ditujukan untuk kreator dewasa. Tidak ada isian nama/umur individual, sekolah, alamat, foto profil atau riwayat tontonan anak.

## 4. Kebutuhan fungsional

### K1 — Katalog dan brief

- Minimal 10 ide awal dari tabel riset; teks Indonesia asli/terkurasi, bukan hasil klaim AI telah memeriksa permintaan pasar.
- Filter kategori; state kosong dan kegagalan muat. Satu kartu dapat mempunyai beberapa kategori tetapi satu tujuan belajar utama.
- Katalog menyimpan `idea_id`, kategori, target usia, bahasa, judul, tujuan, outline, durasi usulan, kebutuhan aset, kelayakan workflow dan provenance.
- Judul brief maksimal 120 karakter, tujuan 300, outline/catatan masing-masing maksimal 2.000. Validasi tipe, enum dan ukuran request di server.
- Brief disimpan ke disk dengan ID stabil, revisi dan write atomik. Dua tab dengan revisi sama mendapat konflik, bukan overwrite diam-diam.
- Tersedia salin/ekspor brief TXT/JSON tanpa model AI atau koneksi jaringan. Ekspor brief bukan ekspor video.
- Brief tersimpan terpisah dari direktori job supaya dapat dibuat sebelum ada video; scanner history tidak memperlakukannya sebagai job.
- Sumber statistik/claim terverifikasi dicatat beserta tanggal/periode. Ide biasa memakai provenance `editorial`; jangan mengisi statistik palsu.

### K2 — Integrasi sumber dan kandidat

- `content_profile` baru bersifat orthogonal terhadap `audience` existing. Kids MVP menggunakan `content_profile=kids`, `audience=local`, `language=id`. Jangan menambahkan nilai `kids` langsung ke enum audience yang saat ini mengontrol bahasa.
- Target umur `3_5` dan bahasa keluaran `id` disimpan eksplisit. Kombinasi kids + Global/English ditolak 400 dalam MVP, bukan diganti diam-diam. General lokal/Global yang ada tidak berubah.
- Sumber yang dipersiapkan untuk workflow ini adalah rekaman/konten anak bahasa Indonesia milik kreator atau berizin. Pemilihan `language=id` bukan bukti aplikasi telah mendeteksi/menjamin bahasa sumber.
- Simpan snapshot brief/ide pada job; edit brief sesudahnya tidak mengubah tujuan pekerjaan lama. History dapat menampilkan badge Anak · 3–5 tanpa mengubah identitas pekerjaan.
- Gunakan pipeline pemrosesan existing sebagai dasar. Hasil tetap kandidat, bukan skor kesesuaian anak. Jangan mengklaim mendeteksi objek, memahami pembelajaran visual atau menyaring semua konten tidak sesuai dari transkrip.
- Target durasi memakai opsi produksi yang sudah diterima API. Prioritaskan unit pembelajaran utuh; bila pilihan otomatis memotong pengenalan/jawaban, kreator meninjau dan memakai editor setelah tersedia. Jangan menambah klaim batas ucapan/visual sempurna.
- Sumber tanpa ucapan jelas/berisi nyanyian dominan menampilkan batas kemampuan dan jalur rencana/manual. Katalog lagu/gerak bukan janji ASR akan memilih ketukan/lirik/gerak dengan akurat. Tidak menambah pembuat musik atau karaoke.
- Caption otomatis wajib Indonesia, singkat dan didukung pembahasan nyata; tujuan brief bukan bukti bahwa materi itu terlihat dalam video. Tidak mengarang hasil belajar hanya dari judul ide.
- Tidak menambahkan CTA komentar, ajakan membeli, penyerahan data diri, klaim hasil belajar terjamin atau judul mengejutkan. Penilaian materi tetap pada kreator, bukan validasi otomatis yang palsu.
- Kegagalan caption tidak menggagalkan MP4. Caption manual tetap dapat diedit; gunakan penyimpanan M1 bila tersedia, jangan membuat kontrak kedua yang bertentangan.

### K3 — Editor dan hasil gambar

- Tautan edit batas/subtitle hanya aktif bila editor sudah tersedia; jangan membuat versi editor kedua di Studio Anak.
- Thumbnail memakai objek/frame yang benar-benar ada, judul kegiatan yang sesuai dan template yang dapat ditinjau. Gunakan PRD thumbnail, bukan membuat generator ilustrasi karakter otomatis.
- Watermark hanya bila fitur terkait tersedia dan dipilih kreator; gunakan logo identitas sederhana serta kontrak snapshot yang sama. Tidak menampilkan tombol branding interaktif YouTube seolah tersedia melalui aplikasi lokal.
- Tidak otomatis mengubah setting Made for Kids atau mengunggah file ke YouTube. Catatan publikasi menyertakan tautan pengaturan audience resmi untuk kreator.

## 5. Model data dan API usulan

```text
kids_idea = {
  idea_id, category, age_band: '3_5', language: 'id',
  title, learning_goal, outline, suggested_duration,
  asset_notes, workflow_fit, provenance, source_url?, verified_at?
}
kids_brief = {
  brief_id, revision, idea_id?, age_band: '3_5', language: 'id',
  title, learning_goal, outline, asset_notes, target_duration,
  created_at, updated_at
}
job.content_profile = 'general' | 'kids'
job.kids_metadata = null | {age_band, language, brief_id?, brief_snapshot}
```

Job lama default general dan kids_metadata null. Brief snapshot adalah kebutuhan produksi, bukan data anak individual. Job ID/clip ID/URL legacy tetap kompatibel.

| Endpoint usulan | Scope |
| --- | --- |
| `GET /kids` | Halaman Studio Anak |
| `GET /api/kids/ideas?category=...` | Katalog terkurasi Indonesia 3–5 |
| `GET /api/kids/briefs` | Daftar brief lokal dengan pagination; tanpa data video besar |
| `POST /api/kids/briefs` | Simpan brief baru; 201 |
| `GET /api/kids/briefs/<id>` | Detail brief |
| `PATCH /api/kids/briefs/<id>` | Update expected revision; konflik 409 |
| `POST /api/jobs` existing | K2: field tambahan tervalidasi dan snapshot brief; workflow lama tetap diterima |

Contoh penyimpanan: katalog pada modul `kids_content.py`, brief pada `data/kids-briefs/`. Nama ini usulan, bukan file yang sudah ada. Validasi UUID/ID, ukuran payload, traversal dan symlink; isi teks dirender sebagai teks biasa. Tidak ada path disk bebas dari client. Request brief/export tidak memulai worker video.

## 6. Prinsip produk dan kaitan platform

Usulan produk mengutamakan tujuan yang jelas, narasi sesuai gambar, cerita berakhir, dan materi orisinal/berizin. Contoh referensi populer bukan bahan otomatis untuk repost.

Menurut YouTube, konten anak perlu sesuai usia dan bermutu; penetapan audience menjadi tanggung jawab kreator, serta fitur seperti komentar dibatasi pada Made for Kids. Mode lokal ini bukan sertifikasi atau integrasi akun. Rincian dan sumber primer ada pada [riset](../KIDS_CONTENT_RESEARCH.md). Ketentuan platform harus diperiksa kembali saat fitur rilis, terutama bila kelak menambah upload/API eksternal.

Tidak ada klaim bahwa aplikasi mengukur perkembangan anak, merekomendasikan waktu layar, mengetahui apa yang ditonton setiap anak atau memprediksi monetisasi.

## 7. Acceptance criteria

| ID | Skenario | Hasil wajib |
| --- | --- | --- |
| KD-01 | Buka menu/route Studio Anak | Target 3–5 Indonesia jelas; navigasi/history lama tetap berfungsi |
| KD-02 | Filter katalog, hasil kosong, ide terpilih | Kategori benar, state jelas, brief tidak menciptakan/mengunduh video |
| KD-03 | Simpan/muat brief, restart/browser lain | Data tetap ada, ID/revisi stabil dan teks Unicode aman |
| KD-04 | Dua tab atau payload invalid | Konflik 409; enum/ukuran/timestamp/tipe invalid ditolak tanpa kehilangan draft |
| KD-05 | Ekspor brief offline | TXT/JSON benar tanpa panggilan model, network atau render |
| KD-06 | Job general lama, lokal dan Global | Tetap kompatibel tanpa mendapat label kids otomatis |
| KD-07 | Kids dikirim dengan audience Global/language English | Ditolak jelas pada MVP; tidak mengubah bahasa diam-diam |
| KD-08 | Job kids selesai | Metadata/snapshot benar; caption Indonesia; audio asli; hasil belum diklaim disetujui untuk anak |
| KD-09 | Lagu/audio tanpa ucapan, transkrip kacau atau AI tidak tersedia | Batas/failure jelas; tidak mengarang ringkasan atau membuat hasil sukses palsu |
| KD-10 | Brief diubah setelah job dibuat | Snapshot job lama tidak berubah |
| KD-11 | Editor/thumbnail/watermark belum tersedia | Tidak ada tombol fungsional palsu atau scope implementasi tersembunyi |
| KD-12 | Teks/klaim populer di katalog | Label editorial, sumber/tanggal jika ada angka; tidak ada ranking/views palsu atau CTA komentar/data diri |

## 8. Verifikasi dan rollout

K1: tes API katalog/brief, validasi, revisi, persistensi dan ekspor; uji UI desktop/sempit/keyboard. K2: tes metadata backward compatibility, kombinasi mode/bahasa dan pipeline dengan mock; media nyata pendek untuk mengecek kelengkapan konsep, narasi/gambar dan batas subtitle/crop. Lagu memerlukan inspeksi terpisah; keberhasilan video ucapan tidak membuktikan lagu didukung.

Gunakan rekaman/ilustrasi sintetis atau milik penguji, tidak perlu melibatkan anak sebagai subjek tes. Jangan mengunduh video referensi populer atau model besar pada unit test. Jangan menghapus data pengguna, mengubah setting akun atau memulai pekerjaan berat selama video/caption aktif.

Tidak ada target views/retention yang diklaim. Ukuran awal adalah ketepatan metadata/bahasa, persistensi brief, jumlah koreksi yang diperlukan dan keberhasilan kreator menyelesaikan satu rencana serta klip yang ditinjau. Evaluasi performa publikasi menjadi pekerjaan terpisah jika pengguna meminta analytics.

Rilis K1 lebih dahulu; K2/K3 diberi tugas terpisah. Pilihan usia 6–9, bahasa Inggris, pencarian tren live, narasi/lagu/animasi generatif dan sistem moderasi otomatis ditunda.


## Implementasi K2/K3 saat ini

K2: brief tersimpan membuka `/kids/source?brief=<id>`, memakai `content_profile=kids`, local/id dan snapshot brief tervalidasi. Kandidat mendapat tambahan skor kecocokan kata tujuan belajar; skor bukan validasi pembelajaran/visual. Sumber lagu/gerak tanpa narasi yang dipilih eksplisit ditolak; ucapan kosong memberi error yang dapat ditinjau. Caption membaca transkrip dan memakai pemeriksaan CTA sederhana, bukan moderasi anak menyeluruh.

K3 tersedia melalui editor caption dan watermark existing serta ekspor turunan async per klip: MP4 dari klip awal dengan watermark tersimpan, cover1080×1920 atau thumbnail1280×720 PNG dari frame klip. Hasil lama tidak dipromosikan/ditimpa; tiap ekspor memiliki ID dan snapshot. Ini bagian ekspor terbatas, bukan seluruh editor/render M2/M3 atau PRD thumbnail (belum ada judul/template/ganti trim/subtitle).
