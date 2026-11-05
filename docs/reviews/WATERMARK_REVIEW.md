# Review fondasi watermark

Review 5 November 2026. Implementasi aset/preset/draft sebelum renderer thumbnail dan M3 sesuai rollout PRD. Ekspor belum tersedia; jangan mengklaim semua WM-01–WM-12 selesai. Review ini tidak mengubah source aplikasi atau data pengguna.

## P2 — Revisi caption dan watermark saling membuat konflik dalam satu kartu

captionEditor dan watermarkEditor masing-masing menangkap currentRevision dari metadata_revision pada saat render. Kedua endpoint menaikkan metadata_revision yang sama. Setelah menyimpan watermark rev1→2, editor caption masih mengirim expected_revision=1; sebaliknya juga terjadi. Penulisan clip.metadata_revision tidak memperbarui variabel closure editor tetangga. Pengguna mendapat konflik padahal hanya memakai satu tab. PRD watermark juga menyatakan revisi caption tidak berubah hanya karena watermark diganti.

Reproduksi: buka kartu rev1, simpan watermark, edit caption lalu Simpan. Expected: caption tersimpan tanpa konflik dari operasi sendiri. Actual berdasarkan jalur source: endpoint caption menerima rev1 sementara server rev2 dan memberi 409. Gunakan revisi terpisah sesuai PRD atau koordinasi revisi bersama yang eksplisit; tetap lindungi konflik antar-tab dan inferensi AI. Tambahkan regresi dua arah.

## P2 — Pakai versi server tidak menyinkronkan form watermark

Handler showConflictUI hanya mengganti currentWm/savedWm, toggle, body, preview dan status. textInput, select warna/gaya, slider, grid posisi dan thumbnail logo tetap menampilkan konfigurasi lama. UI bisa menyatakan bersih tetapi kontrol menunjukkan nilai yang berbeda dari draft yang akan disimpan. Pemulihan perlu satu fungsi sinkronisasi semua kontrol, digunakan juga saat memuat preset. Uji konflik dengan teks, tipe logo, posisi, slider dan margin nol yang berbeda.

## P2 — Preview posisi dan ukuran tidak mengikuti geometri backend

updatePreview tidak menetapkan top=50% untuk center_left/center_right, meskipun memberi translateY(-50%). Margin vertikal memakai persen tinggi kanvas, sedangkan backend memakai dimensi terpendek. Nilai margin nol diganti default 3% oleh ekspresi margin_ratio || 0.03. Teks preview memakai font tetap 9px dan maxWidth, bukan geometri teks renderer; belum layak disebut preview akurat.

Gunakan satu kontrak geometri preview/render, pertahankan nol dengan nullish default, dan verifikasi 9 anchor pada 480/720/1080 serta kedua rasio sebelum mengklaim parity.

## Batas klaim deteksi benturan dan acceptance

detect_subtitle_clash hanya mengecek string bottom; bukan irisan geometris dengan area subtitle ASS. Contoh lokal: logo 100×500, width_ratio=.3, center pada 720×1280 menghasilkan box (252,100,216,1080), tetapi detektor mengembalikan False. UI juga hanya mengecek bottom. Nyatakan ini peringatan posisi sederhana atau implementasikan intersection berdasarkan dimensi logo dan area subtitle nyata.

WM terkait ekspor/snapshot/render failure/idempotensi belum dapat dinyatakan lolos end-to-end karena pipeline terkait belum ada. Uji compositing raster dan mock tidak membuktikan MP4, audio/subtitle, ataupun siklus ekspor baru. Laporan upload juga menyebut minimum16px/rasio dekompresi200:1, sementara source menerima minimum10px dan tidak memeriksa rasio tersebut; selaraskan laporan dengan kode.

## Prompt tindak lanjut Antigravity

```text
Baca AGENTS.md, SKILLS.md, docs/prd/KLIP_WATERMARK.md dan review ini. Reproduksi temuan pada source terkini. Scope hanya memperbaiki fondasi watermark yang sudah dibuat: revisi caption/watermark, sinkronisasi seluruh kontrol setelah konflik, dan geometri preview termasuk posisi center_left/center_right serta margin nol. Tambahkan regresi dua editor dalam satu kartu dan konflik antar-tab; gunakan fixture sementara. Bedakan deteksi bottom sederhana dari overlap geometris. Perbaiki klaim acceptance sesuai cakupan draft/preset/aset; renderer thumbnail dan M3 masih pending. Jangan membangun pipeline ekspor, mulai milestone lain, mengubah history pengguna, menghentikan job aktif, atau commit/push. Verifikasi browser desktop/sempit; laporkan dengan jelas tes mock, browser fixture, dan integrasi live yang benar-benar dijalankan.
```


## Review kedua — perbaikan dan sisa jalur dimensi logo

Pemeriksaan 5 November 2026: revisi domain caption/watermark sudah terpisah, syncAllControlsFromConfig dipakai untuk pemulihan konflik/preset, center_left/right dan margin nol sudah ditangani. Reviewer menjalankan 17 tes watermark, 10 tes caption persistence dan tes Node UI dirty state; semuanya lolos. Browser tidak dijalankan ulang. Temuan awal terkait bagian tersebut ditutup dalam cakupan pemeriksaan ini.

### P2 — Dimensi logo tidak sampai ke detektor benturan frontend/backend

Backend app.py memanggil cv2.imread saat PATCH watermark untuk memperoleh dimensi, tetapi modul app.py tidak mengimpor cv2. NameError ditelan oleh except Exception: pass; asset_w/asset_h tetap None. Helper geometri benar ketika diberi dimensi langsung, tetapi endpoint tidak menggunakan dimensi logo nyata.

Frontend updatePreview menghitung targetH dari currentWm.asset_width/asset_height atau fallback rasio1:1. Handler upload hanya menyimpan asset_id, tidak width/height dari respons. Normalisasi konfigurasi backend juga tidak mengembalikan dua properti tersebut. Setelah upload, refresh, pemulihan konflik atau preset, detektor kembali menghitung logo sebagai persegi meski elemen img menampilkan rasio aslinya. Tidak ada img.onload untuk memperbarui benturan memakai naturalWidth/naturalHeight. Respons clash_detected backend tidak dipakai UI.

Reproduksi yang perlu menjadi regresi endpoint dan browser: unggah logo sintetis100×500; aktifkan logo pada center, lebar30%, kanvas720×1280. Bounding box benar (252,100,216,1080) masuk zona bawah, tetapi jalur tanpa dimensi menghitung fallback dan dapat tidak memperingatkan. Ulangi sesudah save/refresh/preset/konflik. Tes helper dengan argumen dimensi saja belum membuktikan jalur ini.

Prompt tindak lanjut:

```text
Perbaiki hanya sisa jalur dimensi logo pada review kedua WATERMARK_REVIEW.md. Pastikan backend membaca dimensi aset tervalidasi tanpa menelan NameError dan frontend menghitung benturan dari dimensi logo nyata sesudah upload/load/refresh/preset/konflik. Jangan mempercayai dimensi client untuk validasi backend. Jika memakai image.onload, tangani kegagalan dan respons gambar lama agar tidak menimpa preview terbaru. Tambahkan regresi endpoint PATCH (bukan helper saja) serta browser memakai logo tinggi100×500, center30%, termasuk refresh/pemulihan. Pertahankan revisi independen dan tiga perbaikan yang sudah lolos. Tidak membangun ekspor M3/thumbnail, mengubah history pengguna, menghentikan job aktif, atau commit/push.
```


## Review ketiga — jalur dimensi logo diperbaiki

Pemeriksaan source 5 November 2026: ekstraksi dimensi dipindahkan ke watermark.get_asset_dimensions; normalisasi konfigurasi mengambil dimensi dari disk, endpoint memakai hasil tersebut, dan metadata lama memperoleh backfill. Frontend menyimpan dimensi upload dan memanfaatkan dimensi gambar dengan guard ID/sequence. Temuan jalur dimensi pada review kedua ditutup dalam cakupan source dan regresi yang diperiksa.

Reviewer menjalankan ulang 18 tes watermark, 10 tes caption persistence dan tes Node UI dirty state; semuanya lolos. Tes browser tidak dijalankan ulang oleh reviewer; angka browser pada laporan implementer bukan hasil verifikasi independen reviewer. Tidak ada temuan penghambat baru dalam pemeriksaan terarah ini. Status layak untuk uji lokal fitur draft/aset/preset; bukan audit keamanan menyeluruh atau bukti ekspor. Integrasi live lintas tab dan pemeriksaan visual tetap dibedakan dari fixture. Ekspor MP4 dan thumbnail masih menunggu pipeline terkait. Source aplikasi dan data pengguna tidak diubah dalam review ini.
