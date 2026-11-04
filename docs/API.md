# Referensi API lokal

Base URL: `http://127.0.0.1:8765`. Tidak ada autentikasi. API ditujukan untuk satu pengguna lokal. Contoh berikut menggunakan Terminal dengan aplikasi sudah berjalan. Respons kesalahan biasanya JSON `{"error":"pesan"}`; rute berkas yang tidak valid mengembalikan teks 404. Kesalahan Flask yang tidak ditangani dapat mengembalikan HTML.

## GET /api/health

Respons 200: `{"app":"klip-lokal","status":"ok","active_jobs":0}`. Dipakai launcher untuk memastikan server yang benar sudah siap. `active_jobs` menghitung pekerjaan aktif dalam proses server ini.

## GET /

Mengembalikan halaman HTML aplikasi.

## POST /api/jobs

Content type: `multipart/form-data`. Mengembalikan 202 setelah pekerjaan diterima; proses video berjalan asynchronous.

| Field | Tipe | Default | Aturan |
| --- | --- | --- | --- |
| `url` | string | kosong | URL YouTube HTTP/HTTPS dengan hostname yang diizinkan |
| `video` | file | tidak ada | Sumber alternatif jika URL kosong |
| `duration` | integer | 30 | Salah satu 15, 30, 45, 60 |
| `count` | integer | 3 | Salah satu 1, 3, 5 |
| `language` | string | auto | `auto`, `id`, `en` |

Wajib menyediakan `url` atau `video`. Jika keduanya ada, URL dipakai. Batas seluruh request 2 GiB. Pengunduh juga diberi batas ukuran sumber 2 GiB, tetapi batas download bergantung pada informasi yang disediakan extractor.

```sh
curl -X POST http://127.0.0.1:8765/api/jobs \
  -F 'url=https://www.youtube.com/watch?v=VIDEO_ID' \
  -F duration=30 -F count=3 -F language=id
```

Untuk file lokal, ganti path contoh dengan file yang ada:

```sh
curl -X POST http://127.0.0.1:8765/api/jobs \
  -F 'video=@/absolute/path/video.mp4' \
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
  "done":true,
  "clips":[{
    "start":12.3,
    "end":42.3,
    "text":"Kutipan transkrip kandidat",
    "score":10.25,
    "file":"clip-1.mp4",
    "url":"/files/0123456789abcdef0123456789abcdef/clip-1.mp4"
  }]
}
```

`start` dan `end` adalah detik pada sumber. `score` adalah skor heuristik tanpa batas 0–100, bukan probabilitas. `progress` adalah milestone tahap. `title` baru tersedia setelah persiapan sumber. `clips` awalnya array kosong dan baru diisi seluruhnya setelah semua ekspor berhasil.

Jika gagal, `done=true`, `status="Gagal"` dan `error` berisi pesan; progres tetap pada tahap terakhir. Untuk proses terputus yang dibaca dari disk, `done` dan `error` disesuaikan pada respons, tetapi label status/progres lama dapat tetap ada. Tidak ada endpoint daftar pekerjaan, retry, cancel atau hapus.

## GET /files/<id>/<name>

Nama yang diizinkan: `clip-1.mp4` sampai `clip-5.mp4`, serta pasangan `.ass`. Tanpa parameter, berkas dapat diputar inline. Tambahkan `?download=1` untuk attachment. Nama berkas lain, ID tidak valid, atau berkas belum ada mengembalikan 404. Sumber dan transkrip tidak diekspos melalui endpoint ini.

```sh
curl -o clip-1.mp4 \
  'http://127.0.0.1:8765/files/0123456789abcdef0123456789abcdef/clip-1.mp4?download=1'
```

Jangan membangun integrasi yang bergantung pada teks label `status`; gunakan `done` dan keberadaan `error`. Skema belum diberi versi dan dapat berubah selama pengembangan.
