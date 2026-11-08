# Panduan pengguna

## Memilih sumber

Tempel URL `youtube.com`, `www.youtube.com`, `m.youtube.com`, atau `youtu.be`, dengan protokol HTTP/HTTPS. Aplikasi mengunduh satu video, bukan playlist. Video privat, dibatasi login/usia/wilayah, dihapus, dan siaran langsung belum menjadi alur yang didukung khusus; gunakan file lokal jika tersedia.

Alternatifnya, klik **Pilih file video**. MP4, MOV dan MKV adalah contoh format yang dapat dibaca FFmpeg, bukan jaminan seluruh codec dalam format itu didukung. Input lokal disimpan sebagai `source.mp4`; aplikasi tidak melakukan konversi container sebelum decoding, dan FFmpeg mendeteksi isi file. Video harus memiliki suara yang dapat ditranskripsi.

Memilih file mengosongkan URL; mengisi URL mengosongkan pilihan file. Pada request API yang berisi keduanya, URL didahulukan. Batas request multipart keseluruhan adalah 2 GiB (2 × 1024³ byte), sehingga file yang mendekati batas dapat ditolak karena overhead request.

## Pilihan

| Pilihan | Nilai | Makna |
| --- | --- | --- |
| Durasi | 15, 30, 45, 60 detik | Target durasi; mengikuti akhir ucapan |
| Jumlah | 1, 3, 5 | Jumlah maksimum klip tanpa tumpang tindih |
| Resolusi hasil | 480p, 720p, 1080p | 480×854, 720×1280 (default), 1080×1920; tersimpan di history |
| Bahasa | Otomatis, Indonesia, English | Bahasa ucapan untuk Whisper; bukan terjemahan |

Menu pilihan memakai tampilan terang yang seragam. Klik opsi untuk memilih; keyboard mendukung panah atas/bawah, Home/End, Enter/Space untuk memilih, Escape untuk menutup, dan Tab untuk berpindah kontrol. Pilih bahasa secara eksplisit jika deteksi otomatis keliru. Video panjang memakai lebih banyak waktu CPU dan disk. Progres menunjukkan tahap pekerjaan, bukan estimasi waktu atau persentase frame yang telah selesai. Persentase dapat lama bertahan pada tahap transkripsi.

## Meninjau hasil

Kartu hasil menampilkan pemutar, waktu di video asli, durasi, cuplikan transkrip, dan **Unduh MP4**. Gunakan **Urutkan klip** untuk memilih urutan rekomendasi, waktu di sumber, atau durasi terpanjang. Skor yang tersedia berasal dari penilaian kandidat berdasarkan transkrip. Hasil lama tanpa skor tetap bisa dibuka.

Buka **Edit & ekspor** pada kartu untuk mengatur caption, watermark, dan thumbnail. Editor dimuat saat panel dibuka. Menutup panel atau mengubah urutan kartu mempertahankan draft pada halaman itu. Gunakan tombol simpan untuk menyimpan draft ke metadata pekerjaan.

Tinjau isi, crop dan subtitle sebelum membagikan hasil. Resolusi bisa dipilih sebelum memproses: 480p lebih ringan, 720p default, 1080p lebih besar. Pilihan ini menentukan ukuran ekspor; tidak mengubah format unduhan sumber. 480×854 merupakan pembulatan dimensi vertikal agar sesuai encoder H.264. Kanvas ASS tetap 720×1280 dan FFmpeg menskalakan subtitle mengikuti ukuran keluaran. Crop memperkirakan pembicara dari deteksi wajah dan gerakan mulut saat audio aktif; bila wajah tidak terdeteksi atau pelacakan gagal, dipakai crop tengah. Video landscape akan kehilangan sisi kiri/kanan. Sumber resolusi rendah dapat terlihat buram setelah diperbesar. Subtitle menyatu dengan gambar dan tidak bisa dimatikan di pemutar; berkas ASS sumber tetap tersedia di folder pekerjaan.

Subtitle dikelompokkan sampai delapan kata. Durasi kelompok dibagi rata di dalam segmen ucapan yang beririsan dengan klip, sehingga ketepatan waktu dan kata tidak setara subtitle manual. Segmen yang terpotong batas klip masih menggunakan teks segmen utuh. Akurasi dapat menurun pada musik, suara tumpang tindih, aksen, dan audio bising.

## Caption posting

Setiap klip memiliki caption terpisah dari subtitle video. AI lokal membaca transkrip klip dan merangkum inti pembahasan menjadi satu kalimat singkat, target 6–12 kata, tanpa CTA/hashtag. Ini membutuhkan Ollama dan model Qwen3 1.7B; lihat [setup AI lokal](LOCAL_AI.md). Caption hasil lama dapat dirangkum lewat **Buat caption AI lokal** tanpa memproses ulang MP4. Bila transkrip kurang jelas atau AI tidak tersedia, aplikasi memberi alasan dan tetap menyediakan editor manual. Tinjau akurasi dan konteks sebelum memposting.

Edit teks pada **Caption posting**, klik **Simpan caption**, **Salin caption**, atau **Unduh TXT**. Tombol **Simpan caption** menyimpan teks secara persisten ke metadata server (`job.json`) sehingga hasil edit tetap bertahan setelah refresh, restart aplikasi, atau dibuka dari browser lain pada laptop yang sama. Teks dibatasi maksimal 2.000 karakter, dan teks kosong diperbolehkan sebagai keputusan pengguna. Caption manual ditandai sebagai edit manual pilihan pengguna, bukan hasil verifikasi AI.

Indikator status menampilkan state caption: *Tersimpan*, *Ada perubahan belum disimpan*, *Menyimpan*, *Konflik*, atau *Gagal*. Jika ditemukan draft browser lama dari versi sebelumnya, editor menampilkan pemberitahuan dengan opsi **Pulihkan draft browser** atau **Pakai versi tersimpan**. Perlindungan konflik revisi (*optimistic concurrency*) memastikan dua tab yang mengedit klip bersamaan tidak saling menimpa diam-diam; teks lokal Anda tidak akan hilang jika terjadi konflik atau gangguan koneksi. Saat pindah studio, dialog menyebutkan draft caption, watermark, atau brief yang masih diedit. Pilih **Simpan dan pindah**, **Pindah tanpa simpan**, atau **Batal**. Jika penyimpanan gagal, kamu kembali ke editor untuk melihat pesan kesalahan. Chrome masih dapat meminta konfirmasi saat tab ditutup atau halaman dimuat ulang dengan draft aktif.

Klip baru menyimpan caption awal pada metadata server dengan ID klip stabil (`clip_id`). Klip lama juga mendapat pemetaan ID konsisten saat dibuka dari riwayat. Menghapus riwayat melalui aplikasi membersihkan berkas pekerjaan dan draft lokal terkait.

## Watermark video (Teks dan Logo)

Setiap klip menyediakan panel **Watermark (Teks / Logo)** opsional yang dapat dibuka dari kartu hasil. Pengguna dapat membubuhkan identitas channel/brand pada klip tanpa merusak video asli.

1. **Aktifkan watermark**: Centang kotak "Aktifkan watermark pada klip ini".
2. **Pilih jenis**:
   - **Teks**: Tulis hingga 60 karakter (satu baris). Pilih warna putih atau hitam, serta gaya teks (*Outline*, *Panel latar*, atau *Polos*).
   - **Logo**: Unggah file PNG (dengan transparansi) atau JPEG hingga 5 MiB (minimal 10×10 piksel hingga maksimal 4096×4096 piksel). Format animasi (APNG) dan rasio dekompresi ekstrem ditolak demi keamanan. Logo yang diunggah dinormalisasi dan disimpan di pustaka aset lokal.
3. **Atur tata letak**:
   - **Posisi 9 jangkar**: Pilih titik penempatan (Kiri Atas, Tengah Atas, Kanan Atas, Kiri Tengah, Tengah, Kanan Tengah, Kiri Bawah, Tengah Bawah, Kanan Bawah). Default: Kanan Atas. Posisi tengah samping (Kiri Tengah / Kanan Tengah) dipusatkan secara vertikal (`top: 50%`).
   - **Lebar**: 5% hingga 30% dari lebar kanvas video (rasio aspek logo dipertahankan).
   - **Transparansi / Opasitas**: 10% hingga 100%.
   - **Jarak tepi (Margin)**: 0% hingga 10% dari dimensi terpendek kanvas. Margin 0% menempelkan watermark persis di tepi frame.
4. **Tinjau preview interaktif & deteksi benturan**:
   - Kanvas vertikal 9:16 memperlihatkan posisi watermark secara proporsional terhadap kanvas ekspor.
   - Kotak merah putus-putus menunjukkan area subtitle bawaan di bagian bawah (y=72%–100%).
   - Sistem mendeteksi benturan secara geometris: jika kotak batas watermark (misalnya logo tinggi di posisi tengah ataupun teks di posisi bawah) beririsan dengan area subtitle, peringatan benturan (*clash warning*) ditampilkan secara otomatis.
5. **Preset watermark**:
   - Simpan pengaturan yang sering dipakai sebagai preset lokal agar mudah diterapkan ke klip lain.
6. **Simpan draft & isolasi revisi**:
   - Klik **Simpan watermark** untuk menyimpan pengaturan ke metadata server (`job.json`) dengan nomor revisi watermark (`watermark_revision`).
   - Revisi watermark terpisah dari revisi caption: mengedit dan menyimpan watermark tidak membatalkan atau memicu konflik pada editor caption di kartu yang sama.
   - Jika terjadi konflik dari tab/sesi lain, opsi **Pakai versi server** akan menyinkronkan seluruh kontrol form (tipe teks/logo, input, dropdown, slider, tombol posisi, dan thumbnail logo) ke versi server terkini.
   - *Catatan dependensi*: Pembakaran watermark ke file MP4 baru akan diintegrasikan dengan lifecycle render versi pada milestone ekspor ulang (M3). Saat ini draft tersimpan aman di server dan dapat dipratinjau secara langsung di editor.

## Data, riwayat, dan penghentian

```text
data/
  models/                 cache model Whisper
  <id-pekerjaan>/
    source.<ext>          sumber YouTube atau source.mp4 untuk unggahan
    audio.wav             audio mono 16 kHz
    transcript.json       segmen dengan start, end, text
    job.json              status terakhir dan hasil
    clip-1.ass            subtitle
    clip-1.mp4            hasil video
```

Menu **Riwayat klip** berada di sidebar kiri. Klik menu untuk membuka daftar lebar di area utama (`/#history` atau `/global#history`). Di layar kecil, buka sidebar melalui **☰ Menu**. Pencarian, filter, tombol Buat klip baru, pagination dan hapus berada di halaman riwayat, bukan di sidebar. Memilih pekerjaan membuka hasilnya di bawah daftar riwayat. Kamu bisa meninjau dan mengunduh klip langsung dari sana. Panel ini membaca metadata pekerjaan dari server, terbaru di atas, dengan judul, tanggal, jumlah klip dan status. Daftar menampilkan 10 video per halaman. Gunakan **Sebelumnya/Berikutnya**, cari judul/link/nama sumber, atau filter **Semua/Diproses/Selesai/Gagal**. Angka judul menunjukkan total seluruh history; indikator bawah menunjukkan rentang hasil sesuai filter. Mengganti halaman/filter tidak menutup klip yang sedang dibuka atau membatalkan video aktif. Saat membuat video baru, pencarian/filter kembali ke semua dan halaman pertama. Klik entri untuk memutar/unduh hasil sebelumnya. Klik **Buat klip baru** untuk mereset form; hasil lama tetap tersimpan. Membuka riwayat saat video lain diproses tidak membatalkan proses itu. Halaman studio dibuka dengan form **Proyek baru** yang kosong. Jika pemrosesan berhasil dan kamu masih mengikuti pekerjaan itu, aplikasi menampilkan hasilnya di **Riwayat klip**. Riwayat tersimpan di disk dan tetap ada setelah refresh atau restart. Pekerjaan lama sebelum fitur history tetap muncul jika folder `job.json` masih tersedia; metadata yang belum tersimpan tidak dapat direkonstruksi sepenuhnya. Hasil di disk tidak otomatis dihapus. Tombol **Hapus** pada tiap history meminta konfirmasi lalu menghapus permanen folder pekerjaan: sumber, WAV, transkrip, metadata, subtitle dan semua MP4. Tindakan ini mengosongkan ruang disk dan tidak bisa dibatalkan; file yang sudah diunduh/disalin ke lokasi lain tetap ada. Cache `data/models/` tidak ikut dihapus. Tombol dinonaktifkan untuk pekerjaan aktif dan server juga menolaknya. Buka folder pekerjaan di Finder untuk mengambil hasil lama atau hapus subfolder pekerjaan yang sudah selesai untuk menghemat disk. Jangan hapus `data/models` jika ingin menghindari unduhan model ulang.

Launcher menjalankan server di latar belakang; menutup Terminal launcher atau tab tidak membatalkan pekerjaan selama server hidup. Gunakan `Berhenti.command` untuk berhenti setelah pekerjaan selesai. Restart/logout laptop menghentikan server; jalankan `Mulai.command` kembali. Menghentikan server menghentikan pekerjaan; proses tidak dilanjutkan otomatis. Status tersimpan dari proses terputus akan ditandai gagal saat diminta lagi setelah restart. Pekerjaan baru langsung dicatat sebelum worker dimulai.

## Privasi dan koneksi

Video dan audio diproses lokal; tidak diunggah ke layanan transkripsi. YouTube menerima request unduhan, Hugging Face menerima request model, npm/PyPI menerima request dependensi, dan browser memuat font Google Fonts. Semua artefak kerja disimpan tanpa enkripsi tambahan oleh aplikasi, mengikuti proteksi akun/filesystem laptop. Aplikasi tidak memakai cookie login browser atau menyimpan kredensial YouTube.


### Batas potongan mengikuti ucapan

Durasi 15/30/45/60 detik adalah target. Kandidat memakai segmen transkrip utuh dan mengutamakan awal/akhir kalimat atau jeda minimal 0,35 detik, dengan ruang napas hingga 0,15 detik. Akhir dapat melewati target hingga 20% (maksimal 6 detik) agar ucapan selesai. Bila tidak ada batas kalimat/jeda dalam rentang itu, dipakai akhir segmen terdekat; akurasi mengikuti timestamp transkripsi. Segmen terlalu panjang untuk rentang target dilewati, bukan dipotong di tengah. Berlaku untuk pekerjaan baru; hasil lama tidak diekspor ulang otomatis. Crop pada pekerjaan baru mengikuti perkiraan pembicara; lihat batasannya di bawah.


### Crop mengikuti perkiraan pembicara

OpenCV mendeteksi wajah pada sampel video sekitar 4 kali/detik. Gerakan area mulut dibandingkan area atas wajah dan tingkat audio digunakan sebagai perkiraan aktivitas bicara. Perpindahan menunggu aktivitas berkelanjutan; posisi kamera dihitung pada setiap frame dengan interpolasi, redaman serta batas kecepatan/akselerasi, bukan hanya saat deteksi wajah diperbarui. Bila tidak ada wajah, posisi terakhir ditahan; bila tidak pernah ada wajah, crop tengah digunakan. Catatan mode framing muncul di bawah hasil klip, termasuk fallback jika analisis gagal.

Ini heuristik visual dengan gerbang audio, bukan diarization atau model sinkronisasi bibir. Gerakan kepala, tertawa, wajah menyamping, shot berpindah, musik, dan pembicara bersamaan dapat membuat pilihan keliru. Tidak mengenali identitas atau memisahkan suara tiap orang. Selalu tinjau hasil; hasil lama tetap memakai framing sebelumnya. Analisis tambahan membuat proses lebih lama. Data analisis dan command crop disimpan di folder pekerjaan dan ikut terhapus lewat Hapus riwayat.


### Memilih gaya subtitle

Di form Studio klip maupun Studio Global, buka **Gaya subtitle**. Tersedia Klasik (default lama: putih tebal ber-outline hitam), Kuning tebal, Kotak gelap, dan Minimal. Preview langsung memperlihatkan gambaran gaya; ukuran preview bukan ukuran piksel ekspor. Semua preset memakai font Arial dan posisi bawah yang sama, dengan ukuran relatif terhadap resolusi hasil. Pilihan mengubah tampilan subtitle yang dibakar ke MP4, bukan model pengenalan suara, bahasa, waktu subtitle, atau caption posting.

Pilihan disimpan pada pekerjaan dan klip. Membuka history mengembalikan pilihannya di form. Hasil lama tetap menggunakan Klasik. Mengubah dropdown hanya memengaruhi pemrosesan baru; untuk mengganti gaya video yang sudah jadi, proses ulang sumbernya. **Buat klip baru** mengembalikan gaya default Klasik.


Caption lama yang belum dirangkum AI ditandai sebagai cuplikan transkrip. Gunakan **Buat caption AI lokal** untuk menghasilkan ringkasan pembahasan. Draft yang sudah diedit meminta konfirmasi sebelum diganti.


Konfirmasi Hapus history memakai dialog aplikasi: judul dan jumlah hasil klip ditampilkan sebelum tombol **Hapus permanen**. Fokus awal berada pada **Batal**; Escape, tombol tutup, Batal atau klik latar membatalkan tanpa menghapus. Selama permintaan hapus berjalan tombol baris dinonaktifkan; kegagalan ditampilkan dan tombol bisa digunakan kembali.


## Studio Anak (Usia 3–5 Tahun · Bahasa Indonesia)

Buka menu **Studio Anak** di sidebar atau navigasi ke `/kids`. Studio ini dirancang untuk kreator dewasa yang memproduksi konten edukatif anak usia 3–5 tahun berbahasa Indonesia.

### Katalog Ide Editorial
1. Telusuri katalog 10 ide awal berdasarkan riset (warna, hitung 1–5, bentuk, suara hewan, lagu & rutinitas, gerak/tepuk, cerita bergiliran, emosi dasar, gambar bentuk, dan besar/kecil).
2. Gunakan tombol filter kategori di bagian atas katalog untuk membatasi tampilan ide.
3. Setiap kartu ide memuat tujuan pembelajaran tunggal, outline alur video, kebutuhan aset/peraga, target durasi, dan label kelayakan workflow (misalnya lagu/gerak ditandai memerlukan pemilihan manual karena clipper berbasis transkrip ucapan).
4. Klik **Pakai ide ini ↗** pada kartu untuk langsung menyalin rancangan ide ke dalam form editor brief.

### Perencanaan & Manajemen Brief Lokal
1. **Lengkapi Form Brief**: Masukkan judul kerja (maks. 120 karakter), tujuan pembelajaran tunggal (maks. 300 karakter), outline alur (maks. 2000 karakter), dan catatan aset/peraga (maks. 2000 karakter).
2. **Simpan Brief**: Klik **Simpan brief** untuk menyimpan rancangan ke disk lokal (`data/kids-briefs/`). Sistem melacak nomor revisi secara otomatis dan melindungi dari konflik multi-tab (*optimistic concurrency control*).
3. **Ekspor Offline**:
   - **Salin TXT**: Menyalin draf brief dalam format teks terstruktur ke clipboard.
   - **Unduh TXT**: Mengunduh berkas `.txt` yang siap dibagikan atau dicetak.
   - **Unduh JSON**: Mengunduh berkas `.json` untuk cadangan data lokal.
4. **Buka Kembali Brief**: Panel sebelah kanan menampilkan daftar brief yang tersimpan. Klik **Buka di editor ↗** untuk memuat kembali rancangan yang pernah dibuat.


Saat menyimpan brief Studio Anak, form dan tombol pergantian brief terkunci hingga request selesai. Kegagalan simpan mempertahankan teks agar dapat dicoba ulang. Draft belum tersimpan memicu peringatan saat keluar editor/refresh; peringatan ini bukan autosave atau penyimpanan draft browser. Simpan brief sebelum menutup aplikasi.


## Studio Anak: dari brief ke kandidat klip

Simpan atau buka brief lalu klik **Gunakan video sendiri**. Form sumber menampilkan judul/tujuan brief; bahasa Indonesia dan audience lokal terkunci. Pilih narasi/percakapan yang jelas dan rekaman sendiri atau berizin. Durasi awal mengikuti brief. Perubahan brief di sesi lain memerlukan pemuatan ulang sebelum memproses; job menyimpan snapshot sehingga perubahan brief berikutnya tidak mengubah job lama. Lagu/gerak tanpa narasi belum didukung pemilihan otomatis.

Riwayat menampilkan **Anak · 3–5** dan hasil memakai label **Kandidat untuk ditinjau** beserta tujuan brief. Periksa sendiri narasi, gambar, subtitle, crop dan kesesuaian usia. Caption Indonesia dirangkum dari transkrip, bukan dari isi brief. AI tidak tersedia tidak membatalkan MP4; caption dapat ditulis dan disimpan manual.

## Ekspor watermark dan thumbnail dari klip

Di tiap kartu, edit caption atau simpan draft watermark. Pada **Tinjau & ekspor versi baru**, klik **Ekspor MP4 watermark** untuk membakar watermark tersimpan ke berkas MP4 baru. Audio serta subtitle yang sudah menyatu pada klip dipertahankan. Tombol Unduh MP4 awal tetap mengambil klip awal; unduh hasil watermark melalui **Unduh hasil** pada daftar ekspor.

Untuk gambar, pilih waktu frame dalam detik relatif terhadap klip dan rasio9:16 (1080×1920) atau16:9 (1280×720), lalu **Buat thumbnail PNG**. Gambar memakai frame klip sebenarnya, fit dengan bidang hitam bila rasio berbeda, dan watermark tersimpan bila aktif. Belum ada editor judul/template thumbnail atau trim/subtitle manual.

Satu pemrosesan media aktif pada satu waktu. Jangan menutup server saat ekspor. Ekspor yang terputus ditampilkan gagal; buat ekspor baru. Hasil ekspor menambah penggunaan disk dan ikut terhapus ketika riwayat tersebut dihapus. Tidak ada upload/ubah audience YouTube otomatis.

Membuka riwayat pekerjaan lain dari form sumber Studio Anak tidak mengubah pilihan video/bahasa brief yang sedang disiapkan. Prefill pengaturan hanya dilakukan untuk pekerjaan kids dari brief yang sama.


## Kualitas sumber dan crop halus

**Target sumber YouTube** terpisah dari **Resolusi hasil**. Pilih hingga1080p (default, lebih ringan),1440p, atau2160p/4K (lebih besar/lambat). Aplikasi mengunduh video dan audio terpisah lalu menggabungkannya bila tersedia. Target bukan jaminan resolusi tersedia; sumber gabungan melebihi2GB ditolak dan perlu target lebih rendah. Pilihan ini tidak mengubah file upload lokal.

Hasil baru menampilkan resolusi/FPS sumber aktual dan peringatan upscale jika pembesaran lebih dari5%. Contoh sumber640×360 yang diekspor1080×1920 tetap tidak mempunyai detail1080p asli. Untuk crop portrait dari sumber landscape, bahkan sumber1080p dapat memerlukan pembesaran. Hasil lama tidak diunduh/dirender ulang otomatis.

Crop baru memakai trajectory per-frame; analisis pembicara tetap heuristik4Hz. Encoding baru memakai Lanczos dan H.264fast/CRF18 untuk menjaga detail, dengan kemungkinan file lebih besar/waktu render lebih lama. Ekspor watermark mengikuti pengaturan kualitas ini. Sesudah memperbarui source, restart server ketika idle lalu refresh browser sebelum memulai pekerjaan baru.


### Jarak crop

**Lebih lebar · latar blur** adalah pilihan awal untuk pekerjaan baru dari form. Gambar utama memakai sekitar 80% tinggi kanvas sehingga pembicara terlihat lebih kecil dan lebih banyak bagian samping masuk pada video landscape. Latar mengisi kanvas 9:16; pelacakan tetap bekerja pada gambar utama. Pilih **Layar penuh · lebih dekat** untuk framing sebelumnya. Perubahan ini tidak merender ulang hasil lama.

Setiap kartu hasil menampilkan **Sumber video**. Sumber YouTube memiliki judul dan tombol **Buka video asli** yang membuka tab baru. Unggahan lokal menampilkan nama file. Hasil lama tanpa metadata sumber menampilkan keterangan bahwa sumber belum tersedia.
