# Panduan coding agent

Berlaku untuk seluruh repository Klip lokal. Baca file ini sebelum mengubah kode. Ikuti permintaan pengguna; pertahankan perubahan lain yang sudah ada di working tree. Instruksi khusus lingkungan pengguna tetap berlaku.

## Mulai bekerja

1. Baca [README](README.md), [SKILLS](SKILLS.md), [peta dokumentasi](docs/README.md), dan dokumen fitur terkait.
2. Periksa status Git serta implementasi aktual sebelum berasumsi. Jangan reset, checkout, menghapus, atau menimpa perubahan yang tidak dibuat dalam tugas ini.
3. Gunakan checkout yang sesuai. Jangan membuat worktree, commit, push, atau deploy kecuali diperlukan dan diizinkan oleh tugas.
4. Gunakan `rg` untuk pencarian. Jika lingkungan mewajibkan RTK, awali command dengan `rtk` atau `rtk proxy`; RTK bukan dependensi runtime aplikasi.

## Peta kode

| Berkas | Tanggung jawab |
| --- | --- |
| `app.py` | Flask, validasi API, worker video, metadata/history, ASS, ekspor |
| `global_content.py` | Topik dan ide editorial Studio Global |
| `speaker_crop.py` | Perkiraan pembicara dari wajah/gerakan mulut dan audio |
| `subtitle_styles.py` | Whitelist preset ASS |
| `local_caption.py` | Caption semantik lewat Ollama loopback |
| `templates/index.html` | Template kedua studio dan halaman history |
| `static/app.js` | Form, polling, history, caption, navigasi |
| `static/custom-select.js` | Combobox yang menyinkronkan select asli |
| `static/style.css` | Tampilan dan breakpoint |
| `serverctl.py`, `dev.sh`, `*.command` | Siklus hidup server lokal |

## Batas yang harus dipertahankan

- Aplikasi untuk satu pengguna lokal, bind `127.0.0.1`. Jangan menambahkan cloud fallback, telemetry transkrip, atau bind publik tanpa permintaan pengguna.
- Jangan menghapus video, history, model, cache atau draft pengguna untuk pengujian. Gunakan direktori sementara dan fixture milik tes.
- Periksa health sebelum restart. Jangan menghentikan video atau caption AI yang sedang diproses. Gunakan controller bila server dikelola launcher; server foreground dihentikan lewat Terminal asalnya saat idle.
- Satu worker video aktif per proses. Jangan menambah server kedua yang memakai folder `data/` sama. Tidak ada resume pekerjaan yang terputus.
- Metadata lama harus tetap terbaca dengan default yang sesuai. Penyimpanan metadata harus atomik; jangan menyimpan objek model/lock ke JSON.
- Menu **Riwayat klip** ada di sidebar; pencarian, filter, daftar dan pagination berada di area utama. Jangan memindahkan seluruh daftar ke sidebar.
- Caption Studio lokal bahasa Indonesia; caption/subtitle Global bahasa Inggris, audio asli. Jangan mengganti audio menjadi dubbing tanpa permintaan.
- Preset subtitle `classic` mempertahankan default lama. Sinkronkan preset/resolusi/topik antara validasi, worker, template, JS dan tes. Setelah mengubah select lewat JS, sinkronkan `KlipSelect.refresh()`.
- Crop pembicara adalah heuristik, bukan diarization terverifikasi. Caption AI membaca transkrip, bukan gambar/audio ulang. Jangan menjanjikan akurasi sempurna, kalimat pasti utuh, atau jaminan viral.
- Kegagalan AI caption tidak boleh menggagalkan MP4 yang sudah diekspor. Regenerasi caption tidak boleh merender ulang video. Pertahankan draft manual dan konfirmasi penggantiannya di UI.
- Pisahkan kesalahan koneksi fetch dari error rendering UI. Jangan mengubah semua `TypeError` menjadi pesan server terputus.

## Menjalankan dan memverifikasi

Dari root repository: `npm run dev`. Jangan menyalakan server baru jika server yang diperlukan sudah berjalan. Instalasi baru: `npm run setup`, lalu `npm run setup:ai` dan `npm run doctor`; lihat [NEW_MACHINE](docs/NEW_MACHINE.md). Setup AI mengunduh model bila belum tersedia dan bukan bagian tes default.

Ikuti [panduan pengujian](docs/TESTING.md). Jalankan tes yang relevan dengan perubahan. Untuk perubahan perilaku lintas pipeline/API, jalankan suite Python dan tes error JavaScript. Untuk dokumentasi saja, periksa tautan lokal, kesesuaian kode, dan `git diff --check`; tidak perlu memproses video.

Verifikasi UI yang berubah di browser, termasuk state error/empty/loading yang relevan dan layar sempit. Jangan mengklaim pengujian model nyata jika hanya memakai mock. Jangan memakai data pengguna sebagai fixture yang dapat dihapus.

## Menyelesaikan tugas

Perbarui dokumen yang terdampak; gunakan path relatif pada dokumentasi yang masuk Git. Jangan commit `.venv/`, `data/`, model, log, token, `.env`, atau dependensi terpasang. Jangan mengubah pin dependensi tanpa alasan kompatibilitas dan verifikasi.

Laporkan perubahan, pemeriksaan yang benar-benar dilakukan, serta batas yang masih ada. Jangan mengklaim commit, push, deployment atau CI yang tidak dijalankan. Lihat [kontribusi](CONTRIBUTING.md) untuk format penyerahan perubahan.
