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

Hasil diurutkan menurut skor kandidat, bukan urutan waktu video. Setiap kartu menampilkan pemutar, waktu awal/akhir pada sumber, kutipan transkrip, dan **Unduh MP4**. Teks kutipan berasal dari segmen transkrip utuh yang dipilih untuk klip.

Tinjau isi, crop dan subtitle sebelum membagikan hasil. Resolusi bisa dipilih sebelum memproses: 480p lebih ringan, 720p default, 1080p lebih besar. Pilihan ini menentukan ukuran ekspor; tidak mengubah format unduhan sumber. 480×854 merupakan pembulatan dimensi vertikal agar sesuai encoder H.264. Kanvas ASS tetap 720×1280 dan FFmpeg menskalakan subtitle mengikuti ukuran keluaran. Crop memperkirakan pembicara dari deteksi wajah dan gerakan mulut saat audio aktif; bila wajah tidak terdeteksi atau pelacakan gagal, dipakai crop tengah. Video landscape akan kehilangan sisi kiri/kanan. Sumber resolusi rendah dapat terlihat buram setelah diperbesar. Subtitle menyatu dengan gambar dan tidak bisa dimatikan di pemutar; berkas ASS sumber tetap tersedia di folder pekerjaan.

Subtitle dikelompokkan sampai delapan kata. Durasi kelompok dibagi rata di dalam segmen ucapan yang beririsan dengan klip, sehingga ketepatan waktu dan kata tidak setara subtitle manual. Segmen yang terpotong batas klip masih menggunakan teks segmen utuh. Akurasi dapat menurun pada musik, suara tumpang tindih, aksen, dan audio bising.

## Caption posting

Setiap klip memiliki caption terpisah dari subtitle video. AI lokal membaca transkrip klip dan merangkum inti pembahasan menjadi satu kalimat singkat, target 6–12 kata, tanpa CTA/hashtag. Ini membutuhkan Ollama dan model Qwen3 1.7B; lihat [setup AI lokal](LOCAL_AI.md). Caption hasil lama dapat dirangkum lewat **Buat caption AI lokal** tanpa memproses ulang MP4. Bila transkrip kurang jelas atau AI tidak tersedia, aplikasi memberi alasan dan tetap menyediakan editor manual. Tinjau akurasi dan konteks sebelum memposting.

Edit teks pada **Caption posting**, klik **Salin caption**, atau **Unduh TXT**. TXT mengikuti teks hasil edit. Perubahan disimpan otomatis di localStorage browser untuk setiap klip; refresh di browser yang sama akan mempertahankan edit. Perubahan belum disinkronkan ke server atau browser lain. Jika storage browser dibersihkan, draft kembali ke teks awal. Bila akses clipboard ditolak, teks diseleksi dan dapat disalin dengan ⌘C/Ctrl+C.

Klip baru menyimpan caption awal pada metadata server. Klip lama juga mendapat draft saat dibuka dari history. Menghapus history melalui aplikasi membersihkan draft lokal untuk pekerjaan itu di browser yang digunakan.

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

Menu **Riwayat klip** berada di sidebar kiri. Klik menu untuk membuka daftar lebar di area utama (`/#history` atau `/global#history`). Di layar kecil, buka sidebar melalui **☰ Menu**. Pencarian, filter, tombol Buat klip baru, pagination dan hapus berada di halaman riwayat, bukan di sidebar. Memilih pekerjaan membuka hasilnya di studio. Panel ini membaca metadata pekerjaan dari server, terbaru di atas, dengan judul, tanggal, jumlah klip dan status. Daftar menampilkan 10 video per halaman. Gunakan **Sebelumnya/Berikutnya**, cari judul/link/nama sumber, atau filter **Semua/Diproses/Selesai/Gagal**. Angka judul menunjukkan total seluruh history; indikator bawah menunjukkan rentang hasil sesuai filter. Mengganti halaman/filter tidak menutup klip yang sedang dibuka atau membatalkan video aktif. Saat membuat video baru, pencarian/filter kembali ke semua dan halaman pertama. Klik entri untuk memutar/unduh hasil sebelumnya. Klik **Buat klip baru** untuk mereset form; hasil lama tetap tersimpan. Membuka riwayat saat video lain diproses tidak membatalkan proses itu. ID pilihan terakhir disimpan di localStorage; riwayatnya sendiri tersimpan di disk dan tetap ada setelah refresh/restart. Pekerjaan lama sebelum fitur history tetap muncul jika folder `job.json` masih tersedia; metadata yang belum tersimpan tidak dapat direkonstruksi sepenuhnya. Hasil di disk tidak otomatis dihapus. Tombol **Hapus** pada tiap history meminta konfirmasi lalu menghapus permanen folder pekerjaan: sumber, WAV, transkrip, metadata, subtitle dan semua MP4. Tindakan ini mengosongkan ruang disk dan tidak bisa dibatalkan; file yang sudah diunduh/disalin ke lokasi lain tetap ada. Cache `data/models/` tidak ikut dihapus. Tombol dinonaktifkan untuk pekerjaan aktif dan server juga menolaknya. Buka folder pekerjaan di Finder untuk mengambil hasil lama atau hapus subfolder pekerjaan yang sudah selesai untuk menghemat disk. Jangan hapus `data/models` jika ingin menghindari unduhan model ulang.

Launcher menjalankan server di latar belakang; menutup Terminal launcher atau tab tidak membatalkan pekerjaan selama server hidup. Gunakan `Berhenti.command` untuk berhenti setelah pekerjaan selesai. Restart/logout laptop menghentikan server; jalankan `Mulai.command` kembali. Menghentikan server menghentikan pekerjaan; proses tidak dilanjutkan otomatis. Status tersimpan dari proses terputus akan ditandai gagal saat diminta lagi setelah restart. Pekerjaan baru langsung dicatat sebelum worker dimulai.

## Privasi dan koneksi

Video dan audio diproses lokal; tidak diunggah ke layanan transkripsi. YouTube menerima request unduhan, Hugging Face menerima request model, npm/PyPI menerima request dependensi, dan browser memuat font Google Fonts. Semua artefak kerja disimpan tanpa enkripsi tambahan oleh aplikasi, mengikuti proteksi akun/filesystem laptop. Aplikasi tidak memakai cookie login browser atau menyimpan kredensial YouTube.


### Batas potongan mengikuti ucapan

Durasi 15/30/45/60 detik adalah target. Kandidat memakai segmen transkrip utuh dan mengutamakan awal/akhir kalimat atau jeda minimal 0,35 detik, dengan ruang napas hingga 0,15 detik. Akhir dapat melewati target hingga 20% (maksimal 6 detik) agar ucapan selesai. Bila tidak ada batas kalimat/jeda dalam rentang itu, dipakai akhir segmen terdekat; akurasi mengikuti timestamp transkripsi. Segmen terlalu panjang untuk rentang target dilewati, bukan dipotong di tengah. Berlaku untuk pekerjaan baru; hasil lama tidak diekspor ulang otomatis. Crop pada pekerjaan baru mengikuti perkiraan pembicara; lihat batasannya di bawah.


### Crop mengikuti perkiraan pembicara

OpenCV mendeteksi wajah pada sampel video sekitar 4 kali/detik. Gerakan area mulut dibandingkan area atas wajah dan tingkat audio digunakan sebagai perkiraan aktivitas bicara. Perpindahan menunggu aktivitas yang berkelanjutan dan kamera bergerak bertahap agar tidak meloncat pada tiap frame. Bila tidak ada wajah, posisi terakhir ditahan; bila tidak pernah ada wajah, crop tengah digunakan. Catatan mode framing muncul di bawah hasil klip, termasuk fallback jika analisis gagal.

Ini heuristik visual dengan gerbang audio, bukan diarization atau model sinkronisasi bibir. Gerakan kepala, tertawa, wajah menyamping, shot berpindah, musik, dan pembicara bersamaan dapat membuat pilihan keliru. Tidak mengenali identitas atau memisahkan suara tiap orang. Selalu tinjau hasil; hasil lama tetap memakai framing sebelumnya. Analisis tambahan membuat proses lebih lama. Data analisis dan command crop disimpan di folder pekerjaan dan ikut terhapus lewat Hapus riwayat.


### Memilih gaya subtitle

Di form Studio klip maupun Studio Global, buka **Gaya subtitle**. Tersedia Klasik (default lama: putih tebal ber-outline hitam), Kuning tebal, Kotak gelap, dan Minimal. Preview langsung memperlihatkan gambaran gaya; ukuran preview bukan ukuran piksel ekspor. Semua preset memakai font Arial dan posisi bawah yang sama, dengan ukuran relatif terhadap resolusi hasil. Pilihan mengubah tampilan subtitle yang dibakar ke MP4, bukan model pengenalan suara, bahasa, waktu subtitle, atau caption posting.

Pilihan disimpan pada pekerjaan dan klip. Membuka history mengembalikan pilihannya di form. Hasil lama tetap menggunakan Klasik. Mengubah dropdown hanya memengaruhi pemrosesan baru; untuk mengganti gaya video yang sudah jadi, proses ulang sumbernya. **Buat klip baru** mengembalikan gaya default Klasik.


Caption lama yang belum dirangkum AI ditandai sebagai cuplikan transkrip. Gunakan **Buat caption AI lokal** untuk menghasilkan ringkasan pembahasan. Draft yang sudah diedit meminta konfirmasi sebelum diganti.
