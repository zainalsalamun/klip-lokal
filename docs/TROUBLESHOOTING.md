# Troubleshooting

## Halaman tidak terbuka

Jalankan `Mulai.command` dan lihat log Terminal. Pastikan launcher menampilkan `Server siap: http://127.0.0.1:8765`. Periksa `.venv/bin/python serverctl.py status` dan `data/server.log`. `ERR_CONNECTION_REFUSED` berarti tidak ada server yang dapat dihubungi pada port tersebut; jalankan launcher lalu muat ulang. Alamat hanya berfungsi pada laptop yang menjalankan server. Jika membuka aplikasi dari perangkat lain, localhost menunjuk perangkat itu sendiri.

## Port 8765 sudah dipakai

Jangan menjalankan launcher berulang kali. Untuk server launcher, jalankan `Berhenti.command` setelah pekerjaan selesai. Untuk server manual, kembali ke Terminal server sebelumnya dan tekan Control-C jika ingin menggantinya. Untuk melihat proses yang mendengarkan:

```sh
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

Periksa identitas proses sebelum menghentikannya. Alternatif, ubah port di `app.py`, alamat launcher, dan dokumentasi.

## Python/npm tidak ditemukan atau izin launcher

Periksa `python3 --version` dan `npm --version` pada Terminal yang sama. Gunakan Python 3.11–3.13. Launcher memerlukan executable permission; jalankan `chmod +x Mulai.command` di folder proyek. Jika Finder tidak menjalankan skrip, buka Terminal dan jalankan `./Mulai.command` agar pesan error terlihat. Tidak perlu menonaktifkan perlindungan sistem.

## Instalasi npm gagal / ENOENT cache

Launcher menggunakan cache khusus proyek `.npm-cache` agar tidak bergantung pada cache npm global yang sempat bermasalah saat setup. Coba ulang dari root proyek:

```sh
npm --cache "$PWD/.npm-cache" --prefix runtime ci --no-audit --no-fund
```

Pastikan jaringan dapat mengakses registry npm dan unduhan paket. Jangan menghapus cache global atau mengganti Node global hanya untuk memperbaiki aplikasi ini.

## ImportError, modul hilang, atau metadata_errors

Gunakan interpreter `.venv/bin/python`, lalu pasang versi terkunci:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

Kombinasi PyAV 19 dan faster-whisper 1.2.1 pernah gagal dengan `open() got an unexpected keyword argument 'metadata_errors'`; requirements mengunci PyAV 16.1.0. Jangan memperbarui PyAV sendiri tanpa uji pipeline.

Jika proyek dipindahkan lagi ke lokasi lain dan executable venv masih merujuk path lama, buat ulang `.venv` pada lokasi baru dan instal requirements. Lingkungan virtual bukan artefak portabel antarperangkat. Buat lingkungan baru setelah clone, alih-alih menyalin lingkungan virtual dari komputer lain.

## YouTube unavailable, 403, bot check, atau sign-in

Periksa apakah video dapat ditonton dan URL mengarah ke satu video. Pemblokiran dapat dipengaruhi video, wilayah, atau jaringan. Versi pertama ini tidak mengimpor cookie login dan tidak memiliki alur autentikasi YouTube. Gunakan unggahan file lokal jika tersedia. Jika layanan berubah, perbarui yt-dlp secara terkontrol sesuai [setup](SETUP.md), lalu uji ulang.

Periksa runtime lokal:

```sh
runtime/node_modules/node/bin/node --version
```

Harus Node 22 atau versi yang didukung yt-dlp. Path ini dipakai aplikasi; Node global tidak harus diganti.

## Lama pada transkripsi / unduhan model gagal

Pemakaian pertama membutuhkan unduhan model Whisper base dari Hugging Face. Setelah itu model berada di `data/models/`. Pastikan internet dan ruang disk tersedia. Persentase 35% adalah tahap, bukan indikator macet; transkripsi CPU dapat lebih lama dari durasi video. Jangan menutup server ketika ingin proses selesai. Untuk koneksi bermasalah, lihat pesan Terminal dan coba lagi setelah jaringan pulih. Aplikasi menonaktifkan Xet secara default untuk jalur unduhan model.

## Tidak cukup percakapan / subtitle salah

Coba video dengan suara jelas dan percakapan lebih panjang. Video diam, musik, audio terlalu singkat, atau ucapan yang tidak terdeteksi VAD dapat menghasilkan nol kandidat. Pilih bahasa `Indonesia` atau `English` jika autodeteksi keliru. Subtitle bukan terjemahan; timing per kelompok kata adalah perkiraan dari segmen.

## Ekspor gagal atau video tanpa suara

Lihat pesan error pada UI dan log Terminal. Pastikan input memiliki audio dan tidak rusak. Coba MP4 H.264 dengan audio AAC sebagai pembanding. FFmpeg harus memiliki filter subtitle; periksa dengan:

```sh
.venv/bin/python - <<'PYTEST'
import subprocess, imageio_ffmpeg
r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-filters'], capture_output=True, text=True)
print('Subtitle filter tersedia:', ' subtitles ' in r.stdout)
PYTEST
```

## Klip buram, subjek terpotong, atau hasil lebih sedikit

Klip memakai crop tengah tetap; pilih sumber yang subjeknya berada di tengah. Resolusi keluaran tidak menambah detail sumber. Format gabungan YouTube yang didapat dapat beresolusi rendah. Kandidat tanpa overlap, durasi minimum, dan panjang video membatasi jumlah hasil; hasil kurang dari jumlah pilihan adalah perilaku yang diharapkan.

## Disk penuh / pekerjaan terhenti

Hentikan server setelah pekerjaan selesai, lalu tinjau `data/<id>/` di Finder. Hapus folder pekerjaan yang sudah tidak diperlukan; pertahankan hasil yang ingin disimpan dan `data/models/` bila ingin menghindari unduhan ulang. Tidak ada cleanup otomatis. Setelah server berhenti di tengah pekerjaan, mulai request baru; aplikasi belum dapat melanjutkan ekspor lama.

## Informasi saat melaporkan masalah

Sertakan tahap/error, versi Python, pilihan durasi/jumlah/bahasa, apakah input URL atau unggahan, dan apakah video lain juga gagal. Jangan membagikan sumber video privat, transkrip sensitif atau kredensial sebagai log. `job.json` dan `transcript.json` dapat berisi judul dan isi percakapan.

## Pesan koneksi muncul padahal server sehat

Versi antarmuka lama pernah mengklasifikasikan semua TypeError sebagai error jaringan, termasuk akses elemen UI yang belum ada pada template lama. Versi terbaru hanya memberi ConnectionError bila fetch gagal, membedakan respons server dan kegagalan rendering, serta memakai versi aset pada URL CSS/JS untuk mencegah cache lama. Jika pesan lama masih tampil, refresh halaman atau lakukan hard refresh (⌘ShiftR di Chrome Mac). Periksa /api/health dan buka kembali pekerjaan dari history; jangan memproses ulang video yang sudah berstatus selesai.
