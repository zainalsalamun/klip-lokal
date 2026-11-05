# Studio Global — penonton berbahasa Inggris

Buka menu **Studio Global** atau `/global` setelah menjalankan server versi terbaru. Target versi ini adalah audiens global berbahasa Inggris. Audio asli dipertahankan; subtitle dan caption posting menggunakan bahasa Inggris. Tidak ada dubbing, voice cloning, atau jaminan distribusi ke negara tertentu.

## Cara penggunaan

1. Buka Studio Global.
2. Tinjau empat ide editorial: kebiasaan/produktivitas, teknologi praktis, cerita karier, dan budaya Indonesia.
3. Klik **Pakai fokus ini** untuk mengatur fokus kandidat dan contoh durasi. Tombol ini tidak mencari atau mengunduh video otomatis.
4. Masukkan URL YouTube atau unggah sumber yang relevan. **Cari referensi** membuka pencarian YouTube; pilih sumber sendiri.
5. Pilih **bahasa suara sumber** (bukan bahasa target), durasi, jumlah kandidat dan resolusi.
6. Proses video. Whisper menerjemahkan audio sumber menjadi segmen bahasa Inggris; segmen itu dipakai untuk subtitle, scoring dan caption.
7. Tinjau subtitle, nama orang/istilah, crop dan konteks. Edit caption posting, salin atau unduh TXT.

Riwayat lokal dan Global ditampilkan bersama. Pekerjaan Global diberi keterangan **English subtitles**. Membuka history lokal di Studio Global tidak menerjemahkan hasil lama secara otomatis; kirim sumber kembali melalui form Global untuk membuat pekerjaan baru. Mode form mengikuti halaman yang sedang dibuka.

## Cara pemrosesan

Request Global mengirim `audience=global_en` dan `topic`. `language` tetap kode bahasa sumber. faster-whisper menerima `task="translate"`, sedangkan Studio klip biasa memakai `task="transcribe"`. Terjemahan Whisper diarahkan ke bahasa Inggris. Audio hasil tetap berasal dari sumber melalui FFmpeg, tanpa sintesis suara.

Caption Global dirangkum AI lokal dari transkrip Inggris, target 6–12 kata, tanpa CTA/hashtag otomatis. Ini draft yang perlu ditinjau, bukan prediksi viralitas. Lihat [setup AI lokal](LOCAL_AI.md). Fokus konten menambahkan bobot keyword Inggris ke skor kandidat; fokus tidak menjamin sumber benar-benar membahas topik tersebut. Tidak ada pencarian semantik/gambar.

## Rekomendasi konten

Ide dan hook adalah usulan editorial yang disimpan di `global_content.py`, bukan hasil pemantauan tren real-time, data channel, atau rekomendasi video yang telah ditinjau. Hook bukan kutipan pembicara; gunakan hanya jika sesuai isi klip. Tidak ada pengambilan analytics atau pencarian video otomatis.

Alasan pemilihan topik merupakan penilaian editorial: konteks yang bisa dipahami tanpa mengenal tokoh lokal, demonstrasi praktis, cerita personal dan penjelasan budaya. Validasi tema menggunakan data channel dan kebutuhan penonton. Panduan sumber resmi:

- [YouTube: Explore trends / content gaps](https://support.google.com/youtube/answer/11962757?hl=en)
- [YouTube: translated titles and descriptions](https://support.google.com/youtube/answer/6289575?hl=en)
- [faster-whisper: transcribe/translate task](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)

Referensi diperiksa 4 November 2026. Ide tidak diberi angka peluang, volume pencarian atau janji performa karena data tersebut belum diintegrasikan.

## Batas kualitas

Whisper base lokal dapat keliru menerjemahkan slang, candaan, nama, istilah budaya atau ucapan tumpang tindih. Pemotongan kandidat juga dapat memotong kalimat. Subtitle memakai waktu segmen dan pembagian rata antarkelompok kata, bukan word alignment. Tidak ada editor subtitle di UI. Tinjau hasil sebelum memposting.

## Pembaruan server

Jika server versi lama masih memproses video, tunggu hingga selesai lalu restart. Halaman Global dan endpoint baru baru tersedia setelah Python server dimuat ulang. UI Global mengecek capability `global_en` sebelum submit untuk mencegah server lama mengabaikan mode dan mengekspor subtitle bahasa sumber secara diam-diam.

## Verifikasi

Tes regresi keseluruhan: 17 tes lolos. Tambahan pengujian nyata memakai cuplikan audio Indonesia dari video yang sudah tersedia: Whisper task translate menghasilkan segmen Inggris, subtitle ASS, caption Inggris dan MP4 480×854 dengan stream audio sumber. UI diverifikasi pada preview terpisah tanpa mengganggu worker utama; tombol ide teknologi mengubah fokus menjadi teknologi dan durasi 45 detik. Pengujian ini memverifikasi alur, bukan menjamin akurasi seluruh terjemahan atau performa konten.


Caption baru dirangkum oleh AI lokal dari pembahasan tiap klip, bukan potongan awal transkrip. Target 6–12 kata, maksimal 16 kata / 120 karakter, tanpa CTA/hashtag otomatis. Hasil lama dapat dirangkum lewat **Buat caption AI lokal**. Draft hasil edit meminta konfirmasi sebelum diganti. Lihat [AI lokal](LOCAL_AI.md).
