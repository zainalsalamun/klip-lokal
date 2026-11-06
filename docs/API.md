# Referensi API lokal

Base URL: `http://127.0.0.1:8765`. Tidak ada autentikasi. API ditujukan untuk satu pengguna lokal. Contoh berikut menggunakan Terminal dengan aplikasi sudah berjalan. Respons kesalahan biasanya JSON `{"error":"pesan"}`; rute berkas yang tidak valid mengembalikan teks 404. Kesalahan Flask yang tidak ditangani dapat mengembalikan HTML.

## GET /api/health

Respons 200: `{"app":"klip-lokal","status":"ok","active_jobs":0}`. Dipakai launcher untuk memastikan server yang benar sudah siap. `active_jobs` menghitung pekerjaan aktif dalam proses server ini.

## GET /

Mengembalikan halaman HTML aplikasi.

## GET /api/jobs

Mengembalikan `{"jobs":[...]}` berisi ringkasan pekerjaan terbaru lebih dahulu berdasarkan `created_at` (ISO 8601 UTC). Field: `id`, `title`, `created_at`, `updated_at`, `status`, `progress`, `done`, `source_url`, `source_name`, `duration`, `count`, `language`, `resolution`, `error`, `clip_count`. Parameter query: `page` (default 1, minimum 1), `page_size` (default 10, 1–50), `q` (pencarian judul/link/nama sumber hingga 200 karakter, case-insensitive), dan `status` (`all`, `processing`, `done`, `failed`). Respons menyertakan `total`, `filtered_total`, `page`, `page_size`, `total_pages`, dan `active_job_id` yang tidak dipengaruhi filter. Halaman di luar rentang disesuaikan ke halaman terakhir; pencarian kosong menghasilkan halaman 1 dengan array kosong. Parameter tidak valid mengembalikan 400. Daftar tidak berisi array klip; ambil detail dari `GET /api/jobs/<id>` untuk URL hasil. Record lama dapat memiliki metadata `null`. File JSON rusak dilewati. Daftar membaca disk sehingga tetap tersedia setelah restart. Proses yang terputus ditampilkan sebagai gagal. Ringkasan metadata dicache hingga 1.024 entri per proses dan dibaca ulang bila file berubah; tidak ada isi video/transkrip lengkap dalam respons daftar.

## GET /global dan GET /api/global/ideas

`/global` menampilkan Studio Global. `/api/global/ideas` memberikan `ideas`, `sources`, `kind="editorial"`, dan `updated` (tanggal kurasi, bukan tanggal pengukuran tren). Kartu berisi `topic`, `name`, `duration`, `hook`, `angle`, `reason`, `search`, `check`. Tidak ada feed tren live.

## POST /api/jobs

Content type: `multipart/form-data`. Mengembalikan 202 setelah pekerjaan diterima; proses video berjalan asynchronous.

| Field | Tipe | Default | Aturan |
| --- | --- | --- | --- |
| `url` | string | kosong | URL YouTube HTTP/HTTPS dengan hostname yang diizinkan |
| `video` | file | tidak ada | Sumber alternatif jika URL kosong |
| `duration` | integer | 30 | Salah satu 15, 30, 45, 60 |
| `count` | integer | 3 | Salah satu 1, 3, 5 |
| `audience` | string | local | `local` atau `global_en`; Global memakai subtitle/caption Inggris dan suara asli |
| `topic` | string | general | `general`, `habits`, `tech`, `career`, `culture`; mode lokal menormalkan ke general |
| `resolution` | string | 720 | `480`, `720`, `1080` (ukuran keluaran: 480×854, 720×1280, 1080×1920) |
| `language` | string | auto | `auto`, `id`, `en` |

Wajib menyediakan `url` atau `video`. Jika keduanya ada, URL dipakai. Batas seluruh request 2 GiB. Pengunduh juga diberi batas ukuran sumber 2 GiB, tetapi batas download bergantung pada informasi yang disediakan extractor.

```sh
curl -X POST http://127.0.0.1:8765/api/jobs \
  -F 'url=https://www.youtube.com/watch?v=VIDEO_ID' \
  -F duration=30 -F count=3 -F language=id -F resolution=1080
```

Untuk file lokal, ganti path contoh dengan file yang ada:

```sh
curl -X POST http://127.0.0.1:8765/api/jobs \
  -F 'video=@/path/ke/video.mp4' \
  -F duration=15 -F count=1 -F language=auto
```

Respons 202:

```json
{"id":"0123456789abcdef0123456789abcdef"}
```

Kode kesalahan: 400 untuk input/parameter tidak valid atau unggahan gagal disimpan; 409 bila ada pekerjaan aktif; 413 bila request terlalu besar. Respons 202 bukan jaminan pemrosesan berhasil: periksa endpoint status.

## GET /api/jobs/<id>

ID adalah 32 karakter heksadesimal kecil. Status ditemukan dari memori, atau dari `data/<id>/job.json` bila proses server baru dimulai. ID tidak ditemukan mengembalikan 404.

```sh
curl http://127.0.0.1:8765/api/jobs/0123456789abcdef0123456789abcdef
```

Contoh selesai (nilai ilustrasi):

```json
{
  "id":"0123456789abcdef0123456789abcdef",
  "title":"Judul video",
  "status":"Selesai",
  "progress":100,
  "resolution":"720",
  "done":true,
  "clips":[{
    "start":12.3,
    "end":42.3,
    "text":"Kutipan transkrip kandidat",
    "caption":"Kebiasaan kecil membantu menjaga konsistensi setiap hari.",
    "score":10.25,
    "file":"clip-1.mp4",
    "resolution":"720",
    "width":720,
    "height":1280,
    "url":"/files/0123456789abcdef0123456789abcdef/clip-1.mp4"
  }]
}
```

`audience` dan `topic` disimpan pada pekerjaan serta ringkasan history. Klip Global juga memiliki `audience=global_en`. `caption` pada setiap klip berisi caption posting. Record lama yang belum memiliki caption mendapat draft saat dibaca. Klip memiliki `clip_id` stabil dan `metadata_revision` integer. Edit manual disimpan ke metadata server melalui `PATCH /api/jobs/<id>/clips/<clip_id>/caption`. `schema_version=2` digunakan untuk pekerjaan baru dan hasil migrasi. `resolution` adalah pilihan ekspor. Record lama yang belum memiliki pilihan resolusi dianggap `720`. Klip baru memuat `resolution`, `width`, `height`; klip lama bisa belum memiliki field tersebut. `start` dan `end` adalah detik pada sumber. `score` adalah skor heuristik tanpa batas 0–100, bukan probabilitas. `progress` adalah milestone tahap. `title` baru tersedia setelah persiapan sumber. `clips` awalnya array kosong dan baru diisi seluruhnya setelah semua ekspor berhasil.

Jika gagal, `done=true`, `status="Gagal"` dan `error` berisi pesan; progres tetap pada tahap terakhir. Untuk proses terputus yang dibaca dari disk, `done` dan `error` disesuaikan pada respons, tetapi label status menjadi `Gagal` sementara progres terakhir tetap ada. Daftar tersedia melalui `GET /api/jobs`. Belum ada endpoint retry atau cancel. Penghapusan tersedia melalui DELETE di bawah.

## DELETE /api/jobs/<id>

Menghapus permanen seluruh direktori pekerjaan, termasuk sumber, audio, transkrip, subtitle, klip dan metadata. Mengembalikan 200 dengan `{"id":"...","deleted":true}`. Cache model dan direktori pekerjaan lain tidak diubah. Endpoint tidak menghapus salinan hasil yang telah diunduh ke folder lain.

UI meminta konfirmasi pengguna terlebih dahulu; pemanggil API bertanggung jawab memastikan ID target benar. Respons 409 bila pekerjaan masih aktif dalam proses server ini, 404 bila ID/folder tidak ditemukan atau merupakan symlink, dan 500 bila filesystem menolak penghapusan. Pekerjaan yang terputus pada server lama dapat dihapus setelah restart. Tidak ada restore, soft delete atau undo.

## GET /files/<id>/<name>

Nama yang diizinkan: `clip-1.mp4` sampai `clip-5.mp4`, serta pasangan `.ass`. Tanpa parameter, berkas dapat diputar inline. Tambahkan `?download=1` untuk attachment. Nama berkas lain, ID tidak valid, atau berkas belum ada mengembalikan 404. Sumber dan transkrip tidak diekspos melalui endpoint ini.

```sh
curl -o clip-1.mp4 \
  'http://127.0.0.1:8765/files/0123456789abcdef0123456789abcdef/clip-1.mp4?download=1'
```

Jangan membangun integrasi yang bergantung pada teks label `status`; gunakan `done` dan keberadaan `error`. Skema belum diberi versi dan dapat berubah selama pengembangan.


Klip baru menyertakan `framing`: `mode` bernilai `speaker_estimate` atau `center`, beserta `note` dan opsional `face_samples`/`detail`. Field tidak ada pada hasil lama. Durasi request merupakan target; `end-start` dapat lebih pendek atau lebih panjang hingga 20% (maksimal 6 detik ditambah padding 0,15 detik) untuk mempertahankan segmen ucapan utuh.


`POST /api/jobs` menerima field form opsional `subtitle_style`: `classic` (default), `bold_yellow`, `boxed`, atau `minimal`. Nilai selain daftar ini ditolak 400. Field disimpan pada pekerjaan, ringkasan history, dan setiap klip hasil. `GET /api/jobs/<id>` memberi `classic` untuk record lama yang belum memiliki field ini. Tidak ada perubahan pada file hasil lama; perubahan gaya membutuhkan pekerjaan baru.


Caption baru dirangkum oleh AI lokal dari pembahasan tiap klip, bukan potongan awal transkrip. Target 6–12 kata, maksimal 16 kata / 120 karakter, tanpa CTA/hashtag otomatis. Hasil lama dapat dirangkum lewat **Buat caption AI lokal**. Draft hasil edit meminta konfirmasi sebelum diganti. Lihat [AI lokal](LOCAL_AI.md).


### `PATCH /api/jobs/<id>/clips/<clip_id>/caption`

Menyimpan caption manual secara persisten ke metadata server dengan *optimistic concurrency control*. Body JSON wajib memuat:
- `caption`: string UTF-8, maksimal 2.000 karakter. Teks kosong `""` diperbolehkan sebagai keputusan eksplisit pengguna.
- `expected_revision`: integer positif yang cocok dengan `metadata_revision` saat ini pada klip target.

Respons 200:
```json
{
  "clip_id": "9f8e7d...",
  "caption": "Teks caption manual",
  "caption_source": "manual",
  "caption_language": "unverified",
  "caption_updated_at": "2026-11-05T02:00:00Z",
  "metadata_revision": 2,
  "caption_note": "Edit manual · tersimpan"
}
```

Status kesalahan:
- `400`: Payload bukan JSON, field `caption` atau `expected_revision` tidak valid/hilang, atau panjang teks melebihi 2.000 karakter.
- `404`: Pekerjaan atau klip tidak ditemukan.
- `409`: Konflik revisi (`expected_revision` tidak cocok dengan revisi server). Respons menyertakan `conflict: true`, `current_revision`, `server_caption`, dan `server_source`. Teks lokal tidak ditimpa otomatis.
- `500`: Kesalahan penulisan disk atomik.

### `POST /api/jobs/<id>/clips/<index>/caption` (dan `/clips/<clip_id>/caption`)

`index` mulai dari 0 atau menggunakan `clip_id`. Merangkum transkrip klip lewat Ollama lokal dan menyimpan caption pada metadata, tanpa ekspor ulang video. Respons 200: `caption`, `caption_source=ai_local`, `caption_model`, `caption_evidence` (kutipan pendukung), `caption_status=ready`, `metadata_revision`, dan `caption_note`. 404 untuk job/klip tidak ada, 409 jika video aktif atau jika caption telah diperbarui secara manual saat AI sedang merangkum (edit manual dipertahankan), 422 jika transkrip kurang jelas/tidak didukung bukti, 503 jika runtime/model/hasil AI belum tersedia. Kegagalan tidak menimpa caption sebelumnya. Setiap panggilan model dibatasi 180 detik, dengan maksimal satu panggilan tambahan untuk memperbaiki bahasa, ditambah waktu start runtime. Klip baru otomatis mencoba AI setelah ekspor; kegagalan AI menyimpan status `needs_review`/`unavailable` serta alasan tanpa menggagalkan MP4.


Caption AI baru menyertakan `caption_language=id` untuk Studio lokal dan `en` untuk Global. Bahasa salah ditolak setelah maksimal satu percobaan perbaikan. Field belum tentu ada pada history lama; regenerasi caption menerapkan aturan baru.

## Watermark Video

Fitur watermark opsional untuk menyematkan identitas teks atau logo grafis pada klip. Watermark disimpan sebagai draft pada metadata klip server dengan kendali konkurensi optimistik terpisah (`watermark_revision`), sehingga perubahan watermark tidak mengubah revisi caption ataupun memicu konflik pada editor caption dalam kartu yang sama.

### POST /api/watermark-assets

Mengunggah aset logo pengguna (PNG/JPG) untuk dipakai sebagai watermark.
Content type: `multipart/form-data`, field: `file`.

Aturan validasi:
- Ukuran file maksimum: 5 MiB (5.242.880 byte).
- Dimensi gambar: minimal 10×10 piksel, maksimal 4096×4096 piksel.
- Format: PNG atau JPEG valid. Format animasi seperti Animated PNG (APNG) ditolak.
- Pencegahan decompression bomb: rasio dekompresi dibatasi maksimal 200:1 dan total piksel maksimal 16.777.216 (4096×4096).

Respons 201:
```json
{
  "asset_id": "a1b2c3d4e5f67890",
  "filename": "logo.png",
  "mime_type": "image/png",
  "width": 500,
  "height": 500,
  "aspect_ratio": 1.0,
  "size_bytes": 10240,
  "url": "/api/watermark-assets/a1b2c3d4e5f67890/preview"
}
```

Status kesalahan:
- `400`: Tidak ada file, ekstensi tidak diizinkan, format rusak/bukan gambar nyata, rasio aspek ekstrem (>20 atau <0.05), atau terdeteksi APNG/bomb.
- `413`: Ukuran file melebihi 5 MiB.

### GET /api/watermark-assets/<asset_id>/preview

Mengambil file gambar aset logo untuk preview di browser. Menolak path traversal dan asset ID di luar heksadesimal 16 karakter. Mengembalikan 404 jika file aset tidak ditemukan.

### GET /api/watermark-presets

Mengambil daftar preset watermark tersimpan dari `data/watermark-presets.json`.

Respons 200:
```json
{
  "presets": [
    {
      "preset_id": "default-brand",
      "name": "Branding Pojok Kanan Atas",
      "config": {
        "enabled": true,
        "type": "text",
        "text": "@KlipLokal",
        "text_color": "white",
        "text_treatment": "outline",
        "position": "top_right",
        "opacity": 0.70,
        "width_ratio": 0.15,
        "margin_ratio": 0.03
      },
      "created_at": "2026-11-05T00:00:00Z",
      "updated_at": "2026-11-05T00:00:00Z"
    }
  ]
}
```

### POST /api/watermark-presets

Menyimpan preset watermark baru.
Body JSON:
- `name`: string nama preset (1–50 karakter).
- `config`: objek konfigurasi watermark yang valid.

Respons 201: objek preset yang berhasil disimpan.

### PATCH /api/watermark-presets/<preset_id>

Memperbarui nama atau konfigurasi preset yang sudah ada.
Body JSON: `name` (opsional) dan `config` (opsional).

### PATCH /api/jobs/<id>/clips/<clip_id>/watermark

Menyimpan draft konfigurasi watermark pada klip tertentu dengan *optimistic concurrency control*.

Body JSON wajib memuat:
- `watermark`: objek konfigurasi watermark (`enabled`, `type`, `text`, `text_color`, `text_treatment`, `asset_id`, `position`, `opacity`, `width_ratio`, `margin_ratio`). Nilai `margin_ratio: 0.0` didukung penuh untuk posisi rapat tepi (flush).
- `expected_revision`: integer positif yang cocok dengan `watermark_revision` saat ini pada klip target.

Respons 200:
```json
{
  "clip_id": "9f8e7d...",
  "watermark": { ... },
  "watermark_revision": 2,
  "metadata_revision": 1,
  "clash_detected": false,
  "clash_message": "",
  "watermark_updated_at": "2026-11-05T03:00:00Z"
}
```

Catatan deteksi benturan: `clash_detected` dihitung dari irisan geometris bounding box watermark dengan area subtitle ASS (zona bawah kanvas vertikal y=72%–100%), sehingga logo tinggi di posisi `center` maupun watermark di posisi bawah akan terdeteksi secara akurat.

Status kesalahan:
- `400`: Payload tidak valid atau konfigurasi melanggar batasan geometris/tipe.
- `404`: Pekerjaan atau klip tidak ditemukan.
- `409`: Konflik revisi (`expected_revision` tidak cocok dengan `watermark_revision` server). Menyertakan `conflict: true`, `current_revision`, dan `server_watermark`.
- `500`: Gagal menyimpan ke disk secara atomik.

## Studio Anak (Usia 3–5 Tahun · Bahasa Indonesia)

### GET /kids

Mengembalikan halaman antarmuka Studio Anak (`kids_mode=True`) yang memuat katalog ide editorial dan form perencana brief konten edukasi anak.

### GET /api/kids/ideas

Mengambil daftar ide editorial terkurasi untuk konten anak usia 3–5 tahun berbahasa Indonesia.
Parameter query:
- `category` (opsional): filter berdasarkan kategori (`warna`, `hitung`, `bentuk`, `hewan`, `lagu`, `gerak`, `cerita`, `emosi`, `gambar`, `ukuran`).

Respons 200:
```json
{
  "ideas": [
    {
      "idea_id": "warna-01",
      "category": "warna",
      "age_band": "3_5",
      "language": "id",
      "title": "Mana Benda Merah?",
      "learning_goal": "Mengenali warna merah di antara benda sekitar",
      "outline": "Pembukaan: Salam ramah dan tunjukkan 3 benda berbeda warna...",
      "suggested_duration": 30,
      "asset_notes": "3 benda nyata warna berbeda disiapkan sendiri.",
      "workflow_fit": "cocok dicoba dengan clipper ucapan",
      "workflow_note": "Fokus pada percakapan/tanya-jawab langsung yang jelas terdengar.",
      "provenance": "editorial"
    }
  ],
  "categories": { ... },
  "sources": [ ... ],
  "kind": "editorial",
  "target": "3–5 tahun · Bahasa Indonesia",
  "updated": "2026-11-05"
}
```

### GET /api/kids/briefs

Mengambil daftar brief lokal tersimpan dari `data/kids-briefs/` dengan pagination.
Parameter query:
- `page` (default: 1): nomor halaman (integer ≥ 1).
- `page_size` (default: 10): jumlah item per halaman (1–50).
- `category` (opsional): filter berdasarkan kategori.

Respons 200:
```json
{
  "briefs": [ ... ],
  "total": 3,
  "filtered_total": 3,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

### POST /api/kids/briefs

Menyimpan brief produksi baru ke disk secara atomik.
Body JSON:
- `title` (string, wajib, 1–120 karakter): judul kerja brief.
- `learning_goal` (string, opsional, maks 300 karakter): satu tujuan pembelajaran spesifik.
- `category` (string, opsional): kategori konten.
- `target_duration` (integer, default 30): salah satu dari `15`, `30`, `45`, `60`.
- `outline` (string, opsional, maks 2000 karakter): pembukaan, kegiatan, dan penutup.
- `asset_notes` (string, opsional, maks 2000 karakter): catatan alat peraga / rekaman orisinal.
- `idea_id` (string, opsional): ID ide referensi dari katalog editorial.

Respons 201:
```json
{
  "brief": {
    "brief_id": "b1c2d3...",
    "revision": 1,
    "title": "Mana Benda Merah?",
    "learning_goal": "Mengenali warna merah",
    "category": "warna",
    "target_duration": 30,
    "outline": "...",
    "asset_notes": "...",
    "age_band": "3_5",
    "language": "id",
    "created_at": "2026-11-05T00:00:00Z",
    "updated_at": "2026-11-05T00:00:00Z"
  }
}
```

### GET /api/kids/briefs/<brief_id>

Mengambil detail lengkap satu brief berdasarkan ID (32 karakter heksadesimal).
Respons 200: `{"brief": { ... }}`. Mengembalikan 404 jika tidak ditemukan, atau 400 jika ID tidak valid.

### PATCH /api/kids/briefs/<brief_id>

Memperbarui isi brief dengan *optimistic concurrency control* (OCC).
Body JSON:
- `expected_revision` (integer, wajib): nomor revisi brief yang sedang diedit.
- Bidang yang ingin diubah (`title`, `learning_goal`, `category`, `target_duration`, `outline`, `asset_notes`, `idea_id`).

Respons 200: `{"brief": { ... }}` dengan nilai `revision` naik satu tingkat.
Respons 409 (Konflik Revisi): Jika `expected_revision` tidak sesuai dengan versi server, mengembalikan `{"error": "Konflik revisi brief...", "conflict": true, "current_revision": N, "server_brief": { ... }}`.

### DELETE /api/kids/briefs/<brief_id>

Menghapus file brief dari direktori lokal. Mengembalikan 200: `{"brief_id": "...", "deleted": true}`.

### GET /api/kids/briefs/<brief_id>/export

Mengekspor brief untuk keperluan produksi offline.
Parameter query:
- `format`: `txt` (default) untuk berkas dokumen teks rapi, atau `json` untuk data terstruktur.

Respons 200: Mengembalikan isi file dengan header `Content-Disposition: attachment; filename="brief-<brief_id>.<ext>"`.


### Validasi ketat brief Studio Anak

POST/PATCH `/api/kids/briefs` dibatasi32KiB (413 bila berlebih). Durasi harus JSON integer15/30/45/60; float, boolean dan string angka ditolak400. Kategori harus enum katalog; `age_band`/`language` jika dikirim wajib `3_5`/`id`. `idea_id` opsional null atau ID katalog. `brief_id`, `revision`, `created_at`, `updated_at` dikelola server; gunakan `expected_revision` integer positif non-boolean pada PATCH. Default hanya untuk field yang tidak dikirim; nilai enum salah tidak diganti diam-diam.


## Profil kids pada POST /api/jobs

Form baru: `content_profile=general|kids` (defaultgeneral). Kids wajib `audience=local`, `language=id`, `brief_id` yang ada, dan `brief_revision` sesuai revisi terakhir. `source_kind=speech` (default) atau `music` (ditolak400 karena belum didukung). Brief invalid400, hilang404, revisi usang409. Simpan `kids_metadata={age_band:3_5,language:id,brief_id,brief_snapshot}`; job lama defaultgeneral/null. Ringkasan history hanya menyertakan `content_profile`, bukan seluruh brief. Route `/kids/source?brief=<id>` menyiapkan form dari brief tersimpan.

## Ekspor turunan per klip

`POST /api/jobs/<jid>/clips/<clip_id>/exports` menerima JSON `request_id` hex32 unik, `kind=video|thumbnail`, `expected_watermark_revision` integer positif, `frame_time` detik relatif klip (default0), `ratio=vertical|landscape` (defaultvertical, untuk thumbnail). `video` membutuhkan watermark aktif tersimpan. Snapshot dari server, bukan konfigurasi client.

202: `{export:{export_id,kind,status:running,settings,created_at,...}}`. Request ID sama dengan intent sama mengembalikan record existing200 tanpa render ganda; intent berbeda409. Revisi usang atau media/AI sedang aktif409; payload invalid400, file hilang404.

`GET .../exports/<export_id>` memberi statusrunning/done/failed. Setelah restart, recordrunning tanpa worker aktif dilaporkanfailed/interrupted. `GET .../exports/<export_id>/file?download=1` mengunduh hasil bila done; belum selesai409. MP4 dan PNG disimpan terpisah di job/exports/id; file awal tidak ditimpa dan watermark_revision/caption_revision tidak dinaikkan oleh ekspor. MP4 menggunakan audio streamcopy dari klip, subtitle awal tetap terbakar. Health `active_exports` dan `active_jobs` mencakup pekerjaan ekspor untuk melindungi launcher stop.


## Kualitas sumber dan per-frame crop

POST `/api/jobs` menerima form `source_quality=1080|1440|2160` (default1080); nilai lain400. Field mengatur batas tinggi sumber YouTube, bukan ukuran output `resolution`, dan disimpan pada job/history. Worker mengunduh bestvideo+bestaudio dengan fallback combined serta merge memakai executable FFmpeg bawaan. Format yang terpilih mungkin lebih rendah dari target.

Job baru menyimpan `source_media={width,height,fps,codec,bitrate}` bila dapat dibaca. Setiap klip mempunyai `quality={source_known,source_width,source_height,output_width,output_height,upscale_factor,effective_crop_width,effective_crop_height,warning}` dan framing/encoder metadata. Data lama boleh tidak mempunyai field ini. Warning bukan estimasi ketajaman berbasis AI.

Health capabilities `source_quality` dan `smooth_crop` menandai backend baru. Frontend menolak memulai job terhadap backend lama dan meminta restart setelah pekerjaan aktif selesai, agar source HD/crop halus tidak tampak aktif padahal worker masih versi lama.


`POST /api/jobs` menerima `framing_layout=wide|full`. API default `full` untuk klien lama; form menawarkan `wide` sebagai pilihan awal. Nilai invalid ditolak 400. Metadata job/klip menyimpan layout, dan health capability `wide_crop` menunjukkan dukungan backend.
