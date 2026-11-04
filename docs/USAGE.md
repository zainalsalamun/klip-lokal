# Panduan pengguna

## Memilih sumber

Tempel URL `youtube.com`, `www.youtube.com`, `m.youtube.com`, atau `youtu.be`, dengan protokol HTTP/HTTPS. Aplikasi mengunduh satu video, bukan playlist. Video privat, dibatasi login/usia/wilayah, dihapus, dan siaran langsung belum menjadi alur yang didukung khusus; gunakan file lokal jika tersedia.

Alternatifnya, klik **Pilih file video**. MP4, MOV dan MKV adalah contoh format yang dapat dibaca FFmpeg, bukan jaminan seluruh codec dalam format itu didukung. Input lokal disimpan sebagai `source.mp4`; aplikasi tidak melakukan konversi container sebelum decoding, dan FFmpeg mendeteksi isi file. Video harus memiliki suara yang dapat ditranskripsi.

Memilih file mengosongkan URL; mengisi URL mengosongkan pilihan file. Pada request API yang berisi keduanya, URL didahulukan. Batas request multipart keseluruhan adalah 2 GiB (2 × 1024³ byte), sehingga file yang mendekati batas dapat ditolak karena overhead request.

## Pilihan

| Pilihan | Nilai | Makna |
| --- | --- | --- |
| Durasi | 15, 30, 45, 60 detik | Durasi maksimum setiap kandidat |
| Jumlah | 1, 3, 5 | Jumlah maksimum klip tanpa tumpang tindih |
| Bahasa | Otomatis, Indonesia, English | Bahasa ucapan untuk Whisper; bukan terjemahan |

Pilih bahasa secara eksplisit jika deteksi otomatis keliru. Video panjang memakai lebih banyak waktu CPU dan disk. Progres menunjukkan tahap pekerjaan, bukan estimasi waktu atau persentase frame yang telah selesai. Persentase dapat lama bertahan pada tahap transkripsi.

## Meninjau hasil

Hasil diurutkan menurut skor kandidat, bukan urutan waktu video. Setiap kartu menampilkan pemutar, waktu awal/akhir pada sumber, kutipan transkrip, dan **Unduh MP4**. Teks kutipan berasal dari segmen transkrip dan dapat mencakup kata di luar batas akhir klip apabila segmen melewati batas durasi.

Tinjau isi, crop dan subtitle sebelum membagikan hasil. Crop tengah tidak mengikuti pembicara. Video landscape akan kehilangan sisi kiri/kanan. Sumber resolusi rendah dapat terlihat buram setelah diperbesar. Subtitle menyatu dengan gambar dan tidak bisa dimatikan di pemutar; berkas ASS sumber tetap tersedia di folder pekerjaan.

Subtitle dikelompokkan sampai delapan kata. Durasi kelompok dibagi rata di dalam segmen ucapan yang beririsan dengan klip, sehingga ketepatan waktu dan kata tidak setara subtitle manual. Segmen yang terpotong batas klip masih menggunakan teks segmen utuh. Akurasi dapat menurun pada musik, suara tumpang tindih, aksen, dan audio bising.

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

ID pekerjaan aktif disimpan di localStorage browser agar status dapat dibuka lagi setelah refresh. Tidak ada halaman daftar riwayat. Hasil di disk tidak otomatis dihapus. Buka folder pekerjaan di Finder untuk mengambil hasil lama atau hapus subfolder pekerjaan yang sudah selesai untuk menghemat disk. Jangan hapus `data/models` jika ingin menghindari unduhan model ulang.

Launcher menjalankan server di latar belakang; menutup Terminal launcher atau tab tidak membatalkan pekerjaan selama server hidup. Gunakan `Berhenti.command` untuk berhenti setelah pekerjaan selesai. Restart/logout laptop menghentikan server; jalankan `Mulai.command` kembali. Menghentikan server menghentikan pekerjaan; proses tidak dilanjutkan otomatis. Status tersimpan dari proses terputus akan ditandai gagal saat diminta lagi setelah restart. Pekerjaan bisa tidak tercatat bila server dihentikan sebelum status pertama ditulis.

## Privasi dan koneksi

Video dan audio diproses lokal; tidak diunggah ke layanan transkripsi. YouTube menerima request unduhan, Hugging Face menerima request model, npm/PyPI menerima request dependensi, dan browser memuat font Google Fonts. Semua artefak kerja disimpan tanpa enkripsi tambahan oleh aplikasi, mengikuti proteksi akun/filesystem laptop. Aplikasi tidak memakai cookie login browser atau menyimpan kredensial YouTube.
