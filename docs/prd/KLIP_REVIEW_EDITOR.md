# PRD — Tinjau & Perbaiki Klip

Status: **draft usulan, belum diimplementasikan**. Versi dokumen: 1.0. Tanggal: 5 November 2026. Pemilik keputusan produk: pengguna proyek. Target awal tetap aplikasi lokal satu pengguna pada macOS Apple Silicon; laptop RAM 8 GB menjadi lingkungan acuan yang perlu diuji, bukan jaminan performa.

Dokumen ini menyatakan kebutuhan rilis berikutnya, bukan kontrak API yang sudah tersedia. Lihat [analisis prioritas](../PRODUCT_REVIEW.md), [arsitektur saat ini](../ARCHITECTURE.md), dan [API saat ini](../API.md).

## 1. Masalah dan tujuan

Pengguna sudah dapat membuat beberapa kandidat klip vertikal, tetapi hasil otomatis belum selalu sesuai. Caption dapat salah ringkas atau perlu diperbaiki; subtitle dapat salah kata; batas potongan dan crop dapat meleset. Edit caption saat ini hanya tersimpan di localStorage. Koreksi video belum tersedia melalui editor.

Tujuan: pengguna dapat meninjau, mengoreksi, menyimpan, dan mengekspor ulang **satu klip** tanpa mengunduh sumber, mentranskripsi ulang, atau merusak hasil lain.

Sasaran utama adalah pembuat klip podcast/edukasi lokal dan pengguna Studio Global yang memerlukan subtitle/caption Inggris dengan suara asli.

### Ukuran keberhasilan yang diusulkan

- Semua skenario penerimaan di bawah lolos pada fixture terkontrol.
- Edit caption yang dinyatakan tersimpan tetap ada setelah refresh/restart dan dibuka pada browser lain di laptop yang sama.
- Ekspor ulang satu klip tidak menjalankan downloader/Whisper dan tidak mengubah file klip lain; buktikan dengan spy serta hash/mtime artefak.
- Kegagalan ekspor tidak menghapus hasil terakhir yang berhasil.
- Respons simpan edit hanya mengerjakan metadata, tidak menunggu AI atau FFmpeg. Catat latensi pengujian lokal; ambang performa final ditetapkan setelah baseline, bukan diklaim sudah tercapai.
- Uji media nyata pada RAM 8 GB mencatat waktu render dan penggunaan memori. Jangan memakai durasi video panjang sebagai unit test default.

## 2. Ruang lingkup dan milestone

| Milestone | Termasuk | Belum termasuk |
| --- | --- | --- |
| M1 — Simpan caption | ID klip stabil, edit caption persisten, indikator simpan, konflik revisi, pemulihan draft browser lama | Subtitle/timeline/render ulang |
| M2 — Draft editor | Editor subtitle per segmen, trim, crop tengah/manual/perkiraan pembicara, preset subtitle, preview sumber | Ekspor final memakai draft; tombol ekspor belum boleh mengaku aktif |
| M3 — Ekspor per klip | Render asynchronous memakai snapshot draft, versi hasil, status/gagal/ulang, unduh versi terpilih | Antrean multi-video/cancel/resume penuh |

M1 harus dapat dirilis sendiri. M2/M3 tidak boleh mulai hanya karena tercantum di PRD; prompt implementasi menentukan milestone yang dikerjakan.

### Non-goals

Tidak menambah dubbing, cloud inference, akun, upload ke platform sosial, skor viral, model besar default, database baru, alignment per kata atau dukungan Windows/Linux. Crop manual bukan editor video multitrack. Tidak ada janji preview identik piksel demi piksel dengan render ASS.

## 3. Alur pengguna

1. Buka hasil dari menu Riwayat di sidebar; daftar tetap di area utama.
2. Pada kartu klip, edit caption dan simpan. Tampilkan target bahasa dari audience pekerjaan: Indonesia untuk lokal, Inggris untuk Global.
3. Mulai M2, tombol **Edit klip** membuka editor di area utama dengan video, rentang waktu dan panel teks/framing. Pengguna dapat kembali ke hasil tanpa kehilangan draft yang sudah tersimpan.
4. Simpan draft. Perubahan visual/timing ditandai **Perubahan belum diekspor**; file MP4 aktif tetap versi sebelumnya.
5. Mulai M3, pilih **Ekspor ulang klip ini**. Tampilkan status dan progres tahap; jangan menampilkan persen/ETA yang tidak diukur.
6. Jika berhasil, versi baru tersedia dengan pengaturan yang dipakai. Versi lama tetap dapat dibuka. Jika gagal, alasan dan tombol coba ulang tersedia; file terakhir tetap dapat diunduh.

## 4. Kebutuhan fungsional

### FR-01 — Identitas dan kompatibilitas (M1)

- Klip memiliki `clip_id` stabil yang tidak bergantung pada urutan daftar, judul, atau URL ekspor.
- Record lama tanpa ID mendapat pemetaan deterministik berdasarkan ID pekerjaan dan posisi awal klip, misalnya UUIDv5 dengan namespace proyek tetap. ID tersebut dipersistensikan pada write pertama, bukan membuat ID baru tiap GET.
- Jangan mengurutkan ulang list lama selama migrasi. Klip baru langsung menyimpan ID.
- GET history lama tetap berhasil; URL `clip-1.mp4` lama tetap valid. Jangan mewajibkan ekspor ulang untuk migrasi metadata.

### FR-02 — Caption manual persisten (M1)

- Editor memuat caption tersimpan dari server; edit manual boleh berbeda bahasa karena itu pilihan pengguna. Pembatasan bahasa otomatis berlaku untuk AI, bukan melarang ketikan manual.
- Tombol **Simpan caption** menyimpan teks UTF-8 ke metadata klip, maksimum 2.000 karakter untuk edit manual. Caption otomatis tetap mengikuti batas singkat yang sudah ada.
- Teks kosong diperbolehkan sebagai keputusan eksplisit pengguna. Bedakan kosong dengan field tidak dikirim.
- State: tersimpan, ada perubahan, menyimpan, gagal, konflik. Salin/TXT memakai isi editor saat ini; jika belum tersimpan, status itu tetap terlihat.
- Regenerasi AI tidak menimpa draft manual/teks belum disimpan tanpa konfirmasi. AI gagal tidak mengubah caption tersimpan.
- Tampilkan sumber caption (`manual` atau `ai_local`), target bahasa otomatis dan waktu simpan. Jangan menyatakan caption manual sudah divalidasi AI.

### FR-03 — Draft browser lama (M1)

- Deteksi key `klip-caption:<url>` yang masih ada. Tawarkan **Pulihkan draft browser** atau **Pakai versi tersimpan**, dengan penjelasan bahwa belum ada sinkronisasi sampai Simpan berhasil.
- Jangan mengunggah atau menghapus draft browser lama secara diam-diam. Hapus key yang dipilih hanya setelah simpan berhasil atau pengguna eksplisit membuangnya.
- Error jaringan tidak boleh menghapus teks yang sedang diedit. Pindah halaman dengan perubahan yang belum disimpan harus menawarkan tetap di editor atau keluar tanpa menyimpan.

### FR-04 — Subtitle per segmen (M2)

- Draft memuat salinan segmen yang relevan untuk klip, bukan mengubah transkrip sumber bersama.
- Pengguna dapat mengoreksi teks serta waktu mulai/akhir segmen dalam rentang klip. Gunakan timestamp absolut dalam detik pada sumber untuk penyimpanan; UI boleh menampilkan waktu relatif dengan label jelas.
- Validasi angka finite, durasi positif, urutan segmen, tanpa overlap, dan tidak melampaui rentang klip. Segmen teks kosong boleh dipakai untuk menyembunyikan subtitle pada rentang tersebut.
- Perubahan rentang tidak diam-diam menggeser kata. Segmen di luar rentang boleh disimpan dalam draft tetapi tidak dirender; segmen yang terpotong batas perlu ditandai agar ditinjau. Pengguna harus memperbaiki batas segmen yang menyilang sebelum ekspor.
- Segmen draft, subtitle asli dan versi ekspor harus dapat dibedakan. Tidak ada klaim sinkronisasi per kata.

### FR-05 — Trim dan preview sumber (M2)

- Input awal/akhir pada timeline berada di sumber asli, dengan validasi `0 <= start < end <= durasi_sumber`.
- Batas awal yang diusulkan 5–120 detik per klip edit; terpisah dari pilihan durasi otomatis saat membuat job. Validasi backend menjadi sumber kebenaran.
- Preview dapat seek sebelum/sesudah potongan lama. Utamakan proxy ringan atau streaming sumber dengan HTTP Range; jangan memuat seluruh video ke memori/browser.
- Jika sumber lama hilang, tampilkan **Sumber tidak tersedia untuk edit video**. Caption dan hasil MP4 lama tetap bisa dibuka/disimpan/diunduh.

### FR-06 — Framing dan preset (M2)

- Pilihan crop: tengah, perkiraan pembicara yang ada, dan manual horizontal. Posisi manual dinormalisasi 0–1 pada rentang gerak crop; 0 paling kiri, 0,5 tengah, 1 paling kanan. Backend menghitung pixel setelah scaling dan clamp.
- Pada sumber portrait tanpa ruang gerak horizontal, slider dinonaktifkan dengan alasan; tidak membuat crop di luar gambar.
- Gunakan preset resolusi dan gaya subtitle yang sudah ada. Jangan mengubah nilai default lama.
- Preview menampilkan panduan frame dan gaya. Labelkan preview sebagai ilustrasi bila belum memakai render ASS sebenarnya. Audio tetap asli.

### FR-07 — Render ulang dan versi (M3)

- Render hanya klip terpilih dari sumber dan snapshot draft yang sudah disimpan. Downloader, Whisper dan AI caption tidak dijalankan ulang oleh tindakan ekspor video.
- Simpan `draft_revision` yang diekspor. Jika pengguna mengedit saat render berjalan, hasil render mengacu snapshot lama dan UI tetap menunjukkan ada perubahan baru yang belum diekspor.
- Gunakan file output sementara; hanya publikasikan output selesai dan metadata versi setelah FFmpeg berhasil. Jangan menimpa MP4 aktif di tempat.
- Satu pekerjaan berat (video/ekspor/caption AI) pada satu waktu. Gunakan coordinator yang sama, bukan lock masing-masing yang tidak mengetahui worker lain. Benturan ditolak 409 dengan pesan yang dapat ditindaklanjuti; antrean durable bukan scope rilis ini.
- Request render diterima 202 dan dipantau via status. Handler HTTP tidak menunggu render. Resource, subprocess dan flag busy harus dilepas pada semua jalur kegagalan.
- Retry tidak menggandakan render yang masih aktif. Gunakan idempotency key dari client untuk retry request ekspor yang sama.
- Versi lama tidak dihapus otomatis. UI menunjukkan versi aktif dan sumber pengaturannya. Penghapusan history menghapus semua versi pekerjaan seperti perilaku saat ini; penghapusan satu versi terpisah ditunda.

## 5. Model data dan kontrak usulan

Ini contoh rancangan untuk diadaptasi terhadap kode aktual, bukan endpoint yang sudah ada.

```text
job.schema_version = 2
clip.clip_id
clip.metadata_revision = integer
clip.caption / caption_source / caption_language / caption_updated_at
clip.editor_draft = {start, end, segments[], crop_mode, crop_x, resolution, subtitle_style}
clip.draft_revision = integer
clip.exports[] = {export_id, draft_revision, state, file, created_at, settings_snapshot, error}
clip.active_export_id
```

Simpan perubahan metadata atomik di bawah lock pekerjaan. Revisi caption/edit berbeda dari revisi draft video agar mengubah caption tidak membuat MP4 ditandai basi. Simpan `caption_language` manual sebagai belum divalidasi bila tidak ada deteksi; jangan memalsukan hasil deteksi.

| Endpoint usulan | Perilaku |
| --- | --- |
| `PATCH /api/jobs/<jid>/clips/<clip_id>/caption` | M1: body `caption`, `expected_revision`; 200 teks/revisi tersimpan |
| `GET /api/jobs/<jid>/clips/<clip_id>/editor` | M2: draft/default lama, revisi, durasi sumber dan ketersediaan preview |
| `PATCH /api/jobs/<jid>/clips/<clip_id>/editor` | M2: simpan draft tervalidasi dengan `expected_draft_revision` |
| `GET /api/jobs/<jid>/source-preview` | M2: preview sumber/proxy lokal dengan validasi ID, MIME dan Range |
| `POST /api/jobs/<jid>/clips/<clip_id>/exports` | M3: revisi draft tersimpan + idempotency key; 202 export ID/status |
| `GET /api/jobs/<jid>/clips/<clip_id>/exports/<export_id>` | M3: status ekspor tertentu |

400 untuk payload invalid, 404 ID/artefak tidak ada, 409 konflik revisi/busy, 500 untuk kegagalan tulis yang tidak boleh terlihat sebagai sukses. Versi render gagal disimpan pada status worker dengan alasan yang aman ditampilkan. Regenerasi caption AI berbasis indeks yang sekarang ada tetap kompatibel sampai migrasi endpoint terpisah dilakukan.

Optimistic concurrency wajib: dua tab dengan revisi sama tidak boleh saling menimpa tanpa pemberitahuan. Konflik menampilkan draft pengguna dan pilihan memuat versi server; tidak melakukan retry overwrite otomatis. Transaksi AI caption yang berjalan juga harus memeriksa revisi sebelum commit, bukan menimpa edit manual yang lebih baru.

## 6. Keamanan, kinerja dan aksesibilitas

- Tetap bind loopback; tidak menambah telemetry, cloud/model baru atau akses jaringan publik.
- Batasi endpoint artefak dengan allowlist pola file/UUID dan kepemilikan job; cegah traversal dan symlink keluar data. Tambahkan dukungan nama ekspor versi secara sengaja; jangan membuka wildcard semua file sumber.
- Validasi ukuran payload editor dan jumlah segmen. Usulan batas: 1 MiB JSON dan 500 segmen per draft.
- Gunakan subprocess arg list; jangan merangkai shell command dari caption, path atau input crop.
- Caption adalah teks biasa, bukan HTML; tampilkan dengan API DOM aman. Escape teks ASS sebagaimana renderer membutuhkan.
- Pemeriksaan ketersediaan ruang sebelum render, serta penanganan disk penuh selama proses, tidak boleh menghapus hasil lama. Estimasi ukuran diberi label perkiraan.
- UI tetap bisa menampilkan status dan navigasi saat render berjalan. Hindari preview otomatis 1080p atau banyak player autoplay pada laptop 8 GB.
- Kontrol berlabel, navigasi keyboard, error dekat input, focus dikembalikan setelah menutup editor, dan state simpan diumumkan melalui live region.

## 7. Skenario penerimaan

| ID | Skenario | Hasil yang wajib |
| --- | --- | --- |
| AC-01 | Simpan caption manual lalu refresh/restart/browser lain | Teks tersimpan tetap sama dan bertanda manual |
| AC-02 | Draft browser lama berbeda dari caption server | Pilihan pemulihan tampil; tidak ada overwrite tersembunyi |
| AC-03 | Simpan gagal/jaringan putus/disk penuh | Tidak ada status sukses palsu; draft dan versi server lama tetap ada |
| AC-04 | Dua tab menyimpan revisi yang sama | Salah satu mendapat konflik 409; teks lokalnya tidak hilang |
| AC-05 | Regenerasi AI salah bahasa/gagal/sudah ada edit manual | Tidak menimpa manual diam-diam; Indonesia lokal dan Inggris Global tetap berlaku |
| AC-06 | Record lama tanpa clip ID/revisi | Tetap terbaca, ID konsisten antar-GET dan setelah write/restart |
| AC-07 | Subtitle diedit pada klip A | Transkrip sumber dan subtitle klip B tidak berubah |
| AC-08 | Input NaN/Infinity, waktu negatif/terbalik, segmen overlap | Ditolak backend dengan pesan field yang bermasalah |
| AC-09 | Sumber tidak tersedia | Caption dan MP4 lama tetap dapat digunakan; edit/render sumber dinonaktifkan |
| AC-10 | Crop manual pada batas kiri/kanan dan sumber portrait | Frame tetap dalam batas, preview/hasil sesuai pilihan yang didukung |
| AC-11 | Ekspor A berhasil | Dimensi, audio asli, subtitle, trim dan pengaturan benar; klip B tidak berubah |
| AC-12 | Ekspor A gagal atau server terhenti | Hasil lama tetap dapat diunduh; status tidak mengaku selesai; tidak ada resume palsu |
| AC-13 | Draft berubah selama ekspor | Snapshot lama teridentifikasi; draft baru tetap ditandai belum diekspor |
| AC-14 | Request export diulang dengan key sama atau worker lain aktif | Tidak ada kerja ganda; busy/conflict jelas |
| AC-15 | Buka job/clip/export tak dikenal, traversal atau symlink keluar | Tidak ada akses berkas lintas pekerjaan/luar data |

## 8. Rencana verifikasi dan rilis

M1 menambah tes API persistensi, migrasi ID, konflik, draft manual vs AI serta UI state simpan/pemulihan. M2 menambah tes validasi rentang/segmen/crop dan endpoint preview Range. M3 menambah render FFmpeg nyata dengan fixture pendek, kegagalan, snapshot, idempotensi dan busy coordinator. Tes default tidak mengunduh model AI atau menggunakan data pengguna.

Jalankan suite existing sesuai [TESTING](../TESTING.md), uji browser desktop/sempit dan uji media nyata yang relevan. Bedakan hasil mock, FFmpeg nyata, serta AI nyata. Jangan mengklaim angka peningkatan kualitas sebelum mengukurnya.

Rilis setiap milestone secara terpisah setelah kriteria terkait lolos. Update dokumen API/USAGE/ARCHITECTURE saat implementasi selesai. Tidak ada migrasi destruktif atau penghapusan artefak otomatis. Field baru harus dapat diabaikan oleh pembaca lama, tetapi menjalankan kode versi lama untuk menulis metadata v2 tidak dijamin aman; dokumentasikan rollback memakai backup metadata, bukan janji rollback tanpa kehilangan edit.

## 9. Risiko dan keputusan terbuka

| Risiko/pertanyaan | Arah keputusan awal |
| --- | --- |
| Preview tidak persis sama dengan render ASS | Labelkan ilustrasi; MP4 final menjadi bukti utama |
| Metadata makin besar karena versi | Simpan snapshot terbatas pada pengaturan/segmen, ukur ukuran; cleanup versi bukan otomatis |
| Worker render/AI saling berebut RAM | Coordinator tunggal dan batas satu kerja berat sebelum M3 |
| Caption AI dari subtitle draft vs transkrip asal | M1 tetap perilaku sekarang; M2/M3 tandai caption mungkin perlu ditinjau saat subtitle/rentang berubah, jangan regenerasi otomatis |
| Format proxy dan strategi seek | Pilih setelah probe format sumber dan uji CPU/disk; tidak menambah dependency besar sebelum perlu |
| Rute editor/detail metadata | Agent boleh mengusulkan adaptasi, tetapi harus menjaga kontrak lama dan acceptance criteria |

Keputusan rutin yang tetap memenuhi scope dapat diambil implementer. Kontrak/data atau perilaku yang mengubah tujuan produk harus dicatat sebagai deviasi untuk pengguna; jangan memperluas milestone diam-diam.


## Ekstensi watermark yang direncanakan

[PRD watermark](KLIP_WATERMARK.md) menambah konfigurasi overlay opsional pada draft dan settings snapshot ekspor. Ini pekerjaan terpisah setelah fondasi render M3, bukan perluasan otomatis M1/M2/M3. Hasil tanpa watermark tetap menjadi default dan output lama tidak berubah otomatis.
