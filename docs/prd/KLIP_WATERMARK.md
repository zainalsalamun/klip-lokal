# PRD — Watermark Video dan Thumbnail

Status: **draft usulan, belum diimplementasikan**. Versi 1.0, 5 November 2026. Pelengkap [editor klip](KLIP_REVIEW_EDITOR.md) dan [thumbnail](KLIP_THUMBNAIL.md). Semua kontrak di sini adalah rancangan, bukan endpoint tersedia.

## 1. Tujuan dan dependensi

Pengguna dapat membubuhkan identitas miliknya pada hasil video dan gambar menggunakan teks atau logo. Watermark bersifat opsional dan nonaktif secara default; hasil lama tidak berubah otomatis.

Fondasi: clip_id stabil dan revisi metadata dari editor M1. Ekspor video membutuhkan lifecycle/render versi dari M3. Integrasi thumbnail menunggu renderer thumbnail tersedia. Editor aset/preset dapat dikerjakan lebih awal, tetapi jangan menampilkan ekspor yang seolah berfungsi sebelum renderer terkait tersedia. Tidak perlu membangun editor video/thumbnail penuh dalam tugas watermark.

## 2. Alur pengguna

1. Buka pengaturan **Watermark** pada editor klip atau thumbnail.
2. Aktifkan watermark, pilih **Teks** atau **Logo**.
3. Isi teks atau unggah logo milik pengguna, lalu atur posisi, ukuran, transparansi dan jarak tepi.
4. Tinjau overlay pada preview, termasuk area subtitle/judul. Simpan pengaturan pada draft.
5. Pilih **Ekspor versi baru** untuk membakar watermark ke MP4/PNG/JPG. Sumber asli dan hasil lama tetap utuh.
6. Pengguna boleh menyimpan pengaturan sebagai preset lokal dan menerapkannya secara eksplisit ke draft lain.

Watermark adalah overlay tampilan, bukan proteksi penyalinan atau bukti kepemilikan. Tidak ada fitur menghapus watermark milik pihak lain.

## 3. Scope MVP

| Fitur | Perilaku |
| --- | --- |
| Jenis | Satu watermark aktif per draft: teks atau satu logo statis |
| Teks | Maksimal 60 karakter, satu baris; pilihan warna putih/hitam, outline atau panel sederhana |
| Logo | PNG dengan transparansi atau JPG; unggah maksimum 5 MiB dan maksimal 4096×4096 piksel; validasi decode, bukan hanya ekstensi |
| Posisi | Kiri atas, tengah atas, kanan atas, kiri tengah, tengah, kanan tengah, kiri bawah, tengah bawah, kanan bawah |
| Ukuran | Lebar watermark 5–30% lebar kanvas output; rasio aspek logo dipertahankan |
| Opasitas | 10–100%; preview memperlihatkan nilainya |
| Margin | 0–10% dari dimensi terpendek kanvas; kotak watermark harus tetap di dalam frame |
| Cakupan | Draft video atau draft thumbnail yang sedang diedit; preset bisa dipakai ulang tanpa menautkan perubahan secara langsung |
| Preview | Menampilkan watermark, area aman dan peringatan potensi benturan dengan subtitle/judul |
| Simpan | Draft server dengan revisi; perubahan watermark menandai output terkait belum diekspor |
| Ekspor | Watermark menyatu dalam video/gambar versi baru; tidak menambah file audio atau mengubah subtitle/caption |

Default ketika baru diaktifkan: kanan atas, opasitas 70%, lebar 15%, margin 3%. Default ini tetap bisa bentrok dengan konten; preview dan kontrol manual menjadi sumber koreksi pengguna.

### Non-goals

Tidak ada watermark animasi, GIF/SVG/HTML, pengambilan logo lewat URL, banyak overlay sekaligus, pelacakan objek untuk logo, watermark tak terlihat, cloud storage, editor desain bebas atau penambahan model AI. Tidak ada penerapan otomatis ke seluruh history.

## 4. Detail perilaku

### Teks dan logo

- Teks adalah plain text. Escape untuk compositor/ASS/FFmpeg sesuai jalur render; jangan menginterpolasi teks ke command shell.
- Gunakan font lokal/bundled berlisensi sesuai seperti renderer lain; jangan bergantung pada font pribadi pembuat aplikasi.
- Logo didecode dan dinormalisasi ke gambar raster internal; pertahankan alpha PNG, terapkan orientasi yang relevan, buang metadata yang tidak diperlukan.
- Tolak file rusak, gambar animasi, rasio ekstrem yang tidak bisa ditempatkan, MIME/isi tak cocok, dimensi berlebihan dan decompression bomb. Ukuran maksimum juga berlaku di backend.
- Bila teks/logo tidak muat pada ukuran yang dipilih, tampilkan validasi; jangan memotong isi diam-diam. Menjaga lebar 5–30% tidak berarti otomatis menjamin logo tinggi tetap muat.

### Koordinat dan komposisi

- Simpan ukuran/margin sebagai nilai normalisasi, bukan pixel preview. Renderer menghitungnya pada kanvas output setelah crop/scale video.
- Video: crop/scale → subtitle → watermark. Gambar: crop/fit → judul → watermark. Watermark berada dalam koordinat hasil akhir, bukan posisi wajah pada sumber.
- Peringatan overlap bukan jaminan memahami isi gambar. Saat bertabrakan dengan area subtitle/judul, pengguna dapat memindahkan watermark; jangan menggeser subtitle, judul atau wajah otomatis.
- Terapkan opasitas ke alpha gambar tanpa latar kotak yang tidak diminta. JPG logo tidak mempunyai transparansi bawaan, jadi latarnya tetap terlihat; jelaskan di UI.
- Opasitas teks/outline/panel memakai aturan yang konsisten antara preview dan ekspor. Bila preview CSS hanya ilustrasi, labelkan; verifikasi media final tetap wajib.

### Preset dan aset

- Preset tersimpan lokal di server dan memakai ID stabil. Mengubah preset tidak mengubah draft/ekspor yang sudah mengambil snapshot preset itu.
- Upload baru tidak otomatis mengganti logo pada klip lain. Pengguna memilih cakupan penerapan pada draft saat ini.
- Logo yang hilang/rusak membuat ekspor terkait gagal dengan alasan jelas; jangan menghasilkan versi sukses tanpa watermark secara diam-diam. Pengguna dapat menonaktifkan watermark secara eksplisit lalu mengekspor ulang.
- Menonaktifkan watermark pada draft tidak menghapus logo/preset dan tidak mengubah output lama.
- Hapus history menghapus konfigurasi dan artefak milik pekerjaan itu, tetapi tidak menghapus preset/logo library yang dipakai pekerjaan lain.
- Penghapusan aset library tidak termasuk MVP. Tidak ada garbage collector otomatis. Tampilkan penggunaan aset/preset yang relevan agar pengguna tahu mengapa file tetap disimpan.

### Siklus hidup output

- Watermark video diterapkan hanya lewat ekspor ulang satu klip. Jangan menjalankan downloader, Whisper atau AI caption ulang.
- Watermark thumbnail diterapkan hanya saat ekspor gambar baru. Jangan merender ulang MP4 sebagai efek mengubah watermark thumbnail.
- Render memakai snapshot konfigurasi dan aset immutable. Penggantian logo selama render tidak boleh mengubah hasil yang sedang berjalan.
- Gunakan temporary output, lalu publikasi versi setelah sukses. Gagal/disk penuh tidak boleh menimpa hasil sebelumnya.
- Ekspor menggunakan coordinator pekerjaan berat yang sama, idempotency dan batas konkurensi dari editor/thumbnail. Jangan membuat worker baru yang mengabaikan job aktif.

## 5. Data dan API usulan

```text
watermark_asset = {asset_id, sha256, width, height, image_format, file, created_at}
watermark_preset = {preset_id, revision, name, configuration, updated_at}
watermark_configuration = {
  enabled, type, text, asset_id,
  position, width_ratio, opacity, margin_ratio,
  text_color, text_treatment
}
editor_draft.watermark = snapshot_configuration
thumbnail_draft.watermark = snapshot_configuration
export.settings_snapshot.watermark = configuration_and_asset_digest
```

Revisi watermark mengikuti draft output terkait: editor video atau thumbnail. Caption manual tidak ikut berubah revisi hanya karena watermark diganti. Aset immutable diberi ID internal; jangan menerima path disk dari client. File normalisasi tidak ditimpa saat upload baru, walaupun nama asli sama.

| Endpoint usulan | Perilaku |
| --- | --- |
| `POST /api/watermark-assets` | Upload multipart logo, validasi/normalisasi, 201 metadata aman tanpa path mentah |
| `GET /api/watermark-assets/<asset_id>/preview` | Preview aset tervalidasi dengan allowlist; tidak membuka folder bebas |
| `GET /api/watermark-presets` | Daftar preset lokal |
| `POST /api/watermark-presets` | Simpan preset bernama, maksimum nama 80 karakter; 201 |
| `PATCH /api/watermark-presets/<preset_id>` | Update dengan expected revision, konflik 409 |
| Endpoint draft editor/thumbnail yang ada pada PRD terkait | Simpan konfigurasi watermark tervalidasi bersama optimistic concurrency draft |

Contoh lokasi internal: `data/watermark-assets/` dan `data/watermark-presets.json`, di luar direktori job. Implementer harus memastikan scanner history hanya menerima ID job yang sah, bukan membaca library aset sebagai pekerjaan. Penulisan metadata/preset atomik; penanganan request upload gagal membersihkan file sementara miliknya sendiri.

400 untuk konfigurasi/isi invalid, 413 untuk upload berlebih, 404 aset/preset tidak ada, 409 konflik/busy. Request JSON angka NaN/Infinity tidak diterima. Semua rentang divalidasi backend, bukan hanya slider frontend.

## 6. Acceptance criteria

| ID | Skenario | Hasil wajib |
| --- | --- | --- |
| WM-01 | Watermark nonaktif | Ekspor tanpa overlay; history lama tetap dapat digunakan |
| WM-02 | Logo PNG alpha dan JPG pada kedua rasio thumbnail/video | Rasio benar; alpha/opasitas sesuai, tidak ada latar tambahan pada PNG |
| WM-03 | Teks dengan tanda kutip, karakter khusus, path/shell metacharacter | Tidak ada injeksi; teks aman atau invalid dengan alasan jelas |
| WM-04 | Sembilan posisi, ukuran/margin minimum–maksimum | Bounding box selalu di dalam frame atau ditolak bila tidak muat |
| WM-05 | File palsu/rusak, animasi, terlalu besar/banyak piksel | Ditolak sebelum render; temporary file dibersihkan |
| WM-06 | Simpan lalu refresh/restart; dua tab menyimpan revisi sama | State bertahan; konflik tidak menimpa draft diam-diam |
| WM-07 | Preset/logo diubah ketika render berjalan | Hasil tetap memakai snapshot/aset semula |
| WM-08 | Ekspor gagal/disk penuh/aset hilang | Error jelas, output lama tetap tersedia; tidak ada sukses tanpa overlay |
| WM-09 | Watermark diubah pada satu klip/thumbnail | Video lain, caption, subtitle dan draft lain tidak berubah |
| WM-10 | Hapus history fixture yang memakai logo bersama | Artefak job terhapus; logo/preset yang dibutuhkan job lain tetap ada |
| WM-11 | Instalasi baru/offline dan resolusi 480p/720p/1080p | Font/render tersedia lokal; ukuran/posisi dinormalisasi dengan benar |
| WM-12 | Export request diulang atau pekerjaan lain aktif | Tidak ada kerja ganda atau render berat paralel tak terbatas |

Verifikasi gambar dan frame MP4 nyata: dimensi, posisi overlay, alpha/pixel compositing, audio asli dan subtitle tetap ada. Pakai fixture sementara berwarna kontras dan logo sintetis milik tes. Sertakan pemeriksaan visual preview/hasil pada desktop dan layar sempit. Unit test tidak mengunduh model, menggunakan data pengguna, atau menghapus aset pribadi.

## 7. Risiko dan rollout

Logo dapat menutupi wajah/subtitle, opasitas kecil dapat sulit dilihat, dan hasil scaling berbeda antarresolusi. Preset terbatas serta preview manual mengurangi risiko, tetapi tidak menjanjikan watermark selalu terbaca pada setiap frame.

Implementasi bertahap: aset/preset + draft/preview; integrasi ekspor thumbnail saat renderernya tersedia; integrasi ekspor video setelah editor M3. Tahap yang belum didukung harus ditandai tidak tersedia, bukan diakali dengan render seluruh pekerjaan. Tidak ada backfill otomatis pada history.
