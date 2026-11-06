# Smoke test integrasi Studio Anak K2/K3

Tanggal:5 November2026 (WIB). Server live terisolasi127.0.0.1:8877 dengan dua tab browser independen. Data fixture berada di outputs/kids-smoke/ yang di-ignore. Server aplikasi pengguna8765 tidak berjalan dan tidak disentuh. Pengguna menyatakan tidak mempunyai video percakapan Indonesia untuk pengujian; video/audio sintetis dan transkrip kurasi dipakai sebagai pengganti untuk bagian yang sesuai.

| Kasus | Hasil | Bukti/batas |
|---|---|---|
| Snapshot brief sesudah brief berubah | Lulus | PATCH brief revision1→2, snapshot job tetap identik |
| Caption lalu watermark pada kartu sama | Lulus | Caption revision2 dan watermark revision2, tanpa konflik palsu |
| Dua tab live mengubah watermark | Lulus | TabB mendapat409, @BrandB tetap di form; Pakai versi server memuat @BrandA |
| Dua tab live mengubah caption | Lulus |409 mempertahankan draft TabB; pemulihan memuat teks server |
| Logo100×500 center30% | Lulus | Peringatan benturan tampil; top_center15% menghilangkannya |
| Margin0% | Lulus | Overlay top_left memakai left0px/top0px |
| MP4 logo transparan | Lulus | Watermark tampak pada ROI, sumber tidak ditimpa, audio AAC identik |
| Subtitle pada MP4 ekspor | Lulus | Subtitle fixture terbakar tetap ada; selisih rata-rata ROI0.58/255 akibat re-encode |
| Thumbnail9:16 dan16:9 | Lulus | PNG1080×1920 dan1280×720 dari waktu1 detik, unduhan200 |
| Logo terlalu tinggi untuk16:9 | Lulus sebagai penolakan |15% lebar menghasilkan tinggi960>720, ekspor gagal jelas tanpa file palsu;5% muat dan berhasil |
| Refresh dan restart | Lulus | Snapshot job sebelum/sesudah identik, tiga unduhan tetap200, brief rev2/caption rev3/watermark rev4 bertahan |
| Pilihan audio lagu/gerak | Lulus sebagai penolakan |400 sebelum job/worker dibuat |
| Video12 detik tanpa ucapan | Lulus | Whisper base cached nyata+VAD, tanpa mock/download: pesan ucapan belum cukup jelas, nol klip |
| Caption AI lokal | Lulus untuk fixture | Ollama Qwen3:1.7b nyata menghasilkan “Warna merah pada balok mainan” dari transkrip kurasi; bukan hasil ASR video manusia |
| Pelepasan model caption | Lulus | /api/ps tidak mempunyai model loaded sesudah request (keep_alive0) |
| Mobile375×812 | Lulus | scrollWidth=clientWidth375; panel ekspor299px, menu/history dan kontrol dapat dipakai |
| Kualitas potongan/crop/transkripsi percakapan manusia | Belum diuji | Tidak ada file yang diizinkan/tersedia; video sintetis tidak membuktikan kualitas ini |

## Bug yang ditemukan dan diperbaiki

Membuka history Global/English dari `/kids/source` menyalin language=en ke select yang hanya mempunyai id; hasilnya value kosong. `openJob` sekarang hanya mem-prefill form sumber kids jika job kids berasal dari brief yang sama. History yang berbeda tetap dapat ditinjau tetapi tidak mengubah URL, pilihan upload, bahasa atau konfigurasi form brief. Form general mempertahankan perilaku prefill sebelumnya. Reproduksi browser sebelum perbaikan: selectedIndex=-1/value kosong; sesudah: selectedIndex0/valueid. Regresi tests/test_kids_source_history.cjs memakai fungsi openJob aktual dengan DOM stub.

## Pemeriksaan otomatis pada tugas ini

Empat suite Node (API errors, UI dirty state, delete dialog, kids source/history) dan node syntax check lolos. Suite Python89 tes sudah lolos pada implementasi sebelumnya; tidak diklaim dijalankan ulang pada smoke ini. Bagian media, API, model dan restart di atas dijalankan pada server live, bukan Flask test_client/router tiruan. Pemeriksaan console pada tab hasil tidak menemukan error JS.

Artefak lokal: api-results.json, media-results.json, ai-results.json, before-restart.json, restart-results.json, mobile-results.png di outputs/kids-smoke/. Nilai media: mean difference ROI watermark44.01/255, ROI subtitle0.58/255; hash sumber tetap; audio elementary AAC identik. Snapshot ekspor lama tetap memakai ukuran logo awal meski draft selanjutnya diperkecil.

Server fixture dimatikan setelah health idle dan tab pengujian ditutup. Tidak ada data pengguna/history asli yang diubah atau dihapus, tidak ada model diunduh atau akun YouTube diubah. Belum ada commit/push untuk perubahan ini.

## Mengulang fixture tanpa data produksi

```sh
.venv/bin/python tests/serve_kids_smoke.py --data outputs/kids-smoke/live
```

Tanpa --whisper-cache, launcher menolak inferensi/download; cukup untuk tes penyimpanan, dua tab dan ekspor. Untuk uji negatif ASR, berikan path snapshot Whisper yang SUDAH ada melalui --whisper-cache. Launcher memakai marker kepemilikan fixture, menolak direktori nonempty tanpa marker serta folder data/ produksi, dan tidak menginisialisasi ulang data fixture setelah restart. Berhentikan dengan Ctrl+C hanya ketika /api/health idle.
