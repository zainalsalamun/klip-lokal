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
    "caption":"Kutipan transkrip kandidat\n\nApa pendapatmu? Tulis di komentar.\n\n#VideoPendek #Shorts #Reels",
    "score":10.25,
    "file":"clip-1.mp4",
    "resolution":"720",
    "width":720,
    "height":1280,
    "url":"/files/0123456789abcdef0123456789abcdef/clip-1.mp4"
  }]
}
```

`audience` dan `topic` disimpan pada pekerjaan serta ringkasan history. Klip Global juga memiliki `audience=global_en`. `caption` pada setiap klip berisi draft caption posting berbasis transkrip. Record lama yang belum memiliki caption mendapat draft saat dibaca. Edit caption dari UI disimpan di browser dan tidak mengubah field server; belum ada endpoint edit caption. `resolution` adalah pilihan ekspor. Record lama yang belum memiliki pilihan resolusi dianggap `720`. Klip baru memuat `resolution`, `width`, `height`; klip lama bisa belum memiliki field tersebut. `start` dan `end` adalah detik pada sumber. `score` adalah skor heuristik tanpa batas 0–100, bukan probabilitas. `progress` adalah milestone tahap. `title` baru tersedia setelah persiapan sumber. `clips` awalnya array kosong dan baru diisi seluruhnya setelah semua ekspor berhasil.

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


Caption posting kini berupa rekomendasi satu kalimat singkat, maksimal 16 kata / 121 karakter termasuk elipsis, tanpa CTA dan hashtag otomatis. Rekomendasi mengambil kalimat transkrip yang cukup panjang, lalu membatasi panjangnya; bukan ringkasan semantik AI. Template otomatis versi lama diganti saat dibaca tanpa mengubah file/video lama. Caption hasil edit di browser tetap dipertahankan; tombol **Pakai rekomendasi singkat** mengembalikan rekomendasi pendek.
