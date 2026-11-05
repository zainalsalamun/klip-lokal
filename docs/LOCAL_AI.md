# Caption AI lokal

Caption AI membaca **transkrip tiap klip**, bukan keseluruhan judul video. Model merangkum inti pembahasan menjadi satu kalimat, target 6–12 kata (batas validasi 16 kata / 120 karakter), tanpa CTA, hashtag atau klaim baru. Caption Studio lokal wajib bahasa Indonesia; Studio Global menghasilkan bahasa Inggris. Model tidak melihat gambar: pembahasan visual tanpa narasi tidak dapat dipahami lewat fitur ini.

## Instalasi

Pengguna baru mengikuti [NEW_MACHINE](NEW_MACHINE.md). Pada macOS:

1. Pasang Python 3.11–3.13, npm dan [Ollama resmi](https://ollama.com/download/mac). Homebrew: `brew install python@3.13 node ollama` jika Homebrew sudah tersedia.
2. Clone repository dan buka root source. Jalankan `npm run setup:ai`; bootstrap dasar dijalankan otomatis sehingga `.venv` tidak perlu dibuat manual dahulu.
3. Setup menjalankan server Ollama lokal bila diperlukan, memeriksa model, dan mengunduh `qwen3:1.7b` hanya jika belum ada. Progress dicetak di Terminal. Model yang sudah siap dipakai kembali, termasuk jika CLI tidak ditemukan tetapi endpoint Ollama sudah berjalan.
4. Jalankan `npm run doctor`, lalu `npm run dev` atau launcher macOS.

Internet diperlukan untuk instalasi/unduhan pertama. Setelah model tersedia, inferensi dapat dilakukan tanpa internet. Model caption tidak diunduh otomatis di tengah proses video. Script tidak memasang Ollama atau paket sistem secara diam-diam; runtime yang belum tersedia menampilkan petunjuk instalasi. Jika unduhan terputus, ulangi `npm run setup:ai`.

Qwen3 1.7B dipilih sebagai default ringan yang diuji pada RAM 8 GB, bukan konfigurasi khusus pemilik laptop. Model sama bisa dipakai pengguna lain; kecepatan dan kecukupan RAM harus diperiksa pada mesin masing-masing. `npm run doctor` melaporkan RAM/disk/runtime. Belum ada pemilihan model otomatis berdasarkan hardware.

Ollama juga tersedia untuk Windows/Linux, tetapi aplikasi Klip lengkap belum didukung end-to-end di kedua OS tersebut. Jangan menganggap launcher macOS dapat langsung dipakai di sana.

## Pemakaian

- Klip baru: setelah ekspor, aplikasi membuat caption AI secara berurutan. Video tetap selesai jika AI belum tersedia atau transkrip tidak jelas; kolom caption dibiarkan kosong dan alasan ditampilkan.
- Hasil lama: klik **Buat caption AI lokal** pada klip yang dipilih. Video dan subtitle tidak dirender ulang. Endpoint menyimpan hasil di metadata history.
- Edit manual tetap tersedia. Mengganti draft yang telah diedit meminta konfirmasi. Salin/Unduh TXT menggunakan isi textarea saat ini.
- Untuk menjaga RAM, caption manual dari history ditolak selama video masih diproses. Hanya satu inferensi caption berjalan pada satu waktu.
- Model dilepas dari RAM setelah setiap permintaan (`keep_alive: 0`); permintaan berikutnya memuatnya lagi. Pada RAM 8 GB proses dapat memerlukan waktu lebih lama, terutama saat aplikasi lain memakai banyak memori.

## Privasi dan penyimpanan

Inferensi memakai `http://127.0.0.1:11434` yang ditetapkan di kode, melewati proxy lingkungan. Tidak ada API key atau fallback cloud. Runtime yang dimulai aplikasi memakai bind loopback dan `OLLAMA_NO_CLOUD=1`. Jika Ollama sudah berjalan, aplikasi menggunakan server lokal tersebut tanpa mengubah pengaturannya. Transkrip dikirim hanya ke endpoint loopback, sebagai data JSON di prompt.

Model berada di penyimpanan Ollama (default `~/.ollama/models`), terpisah dari `data/` aplikasi. Hapus history menghapus video/metadata klip, bukan model. `ollama rm qwen3:1.7b` menghapus model jika tidak lagi diperlukan; caption AI tidak akan tersedia sampai model diunduh lagi. Log runtime yang dimulai aplikasi: `data/ollama.log`. Server Ollama tidak didaftarkan sebagai login item oleh aplikasi. Untuk menghentikannya setelah selesai: `ollama stop qwen3:1.7b` melepas model dari RAM; proses server tetap dapat berjalan lokal.

## Batas akurasi

AI merangkum transkrip yang tersedia, bukan mendengarkan ulang audio. Kesalahan ASR dapat menghasilkan caption keliru. Pemeriksaan awal menolak pola pengulangan parah (trigram atau kata dominan). Prompt juga meminta model menolak transkrip yang tidak jelas/repetitif dan memilih indeks kalimat pendukung. Aplikasi mengambil kutipan persis dari kalimat sumber; model tidak perlu menyalin ulang ejaan transkrip. Aplikasi memvalidasi kutipan benar-benar ada pada transkrip, minimal tiga kata dan berbagi kata topik dengan caption, panjang output, dan struktur respons. Pemeriksaan ini tidak membuktikan caption benar secara semantik; selalu tinjau sebelum posting. Model kecil dapat melewatkan konteks, humor, slang, atau negasi. Penolakan AI ditandai `needs_review`, bukan diganti caption hasil tebakan.

## Troubleshooting

- **Ollama belum terpasang:** pasang dari sumber resmi, kemudian jalankan setup.
- **Model belum tersedia:** `ollama pull qwen3:1.7b` atau jalankan ulang setup.
- **Runtime gagal dimulai:** lihat `data/ollama.log`, pastikan port 11434 tidak dipakai layanan lain.
- **Tidak merespons:** tunggu pemuatan model, periksa RAM, coba `ollama run qwen3:1.7b` di Terminal. Timeout 180 detik per permintaan model; perbaikan bahasa bisa menambah satu permintaan. Mode penalaran diaktifkan hanya saat memperbaiki bahasa yang salah, sehingga retry bisa lebih lama.
- **Transkrip kurang jelas:** tinjau subtitle dan suara; tulis caption manual. Mengulang model tidak memperbaiki transkrip sumber.

Sumber teknis: [Qwen3 di Ollama](https://ollama.com/library/qwen3), [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md).


Uji model nyata pada laptop ini menghasilkan ringkasan topik untuk contoh kebiasaan olahraga dan keamanan email berbahasa Inggris. Contoh dana darurat menghasilkan caption relevan, tetapi ditolak validasi akhir karena kutipan pendukungnya kurang sesuai. Contoh transkrip kacau/repetitif ditolak oleh pemeriksaan awal. Ini contoh terbatas, bukan benchmark akurasi seluruh video.


Bahasa caption ditetapkan dari mode studio, bukan tebakan model: `local → id`, `global_en → en`. Keluaran diperiksa memakai deteksi bahasa lokal; jika salah/tidak cukup jelas, AI diminta memperbaiki sekali. Jika tetap gagal, hasil ditolak tanpa menimpa caption sebelumnya. Deteksi teks pendek dapat menolak keluaran yang sebenarnya layak; editor manual tetap tersedia. Evidence mempertahankan bahasa transkrip, sehingga pada sumber berbeda bahasa tidak dipaksakan berbagi ejaan kata dengan caption terjemahan.
