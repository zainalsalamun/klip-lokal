# Caption AI lokal

Caption AI membaca **transkrip tiap klip**, bukan keseluruhan judul video. Model merangkum inti pembahasan menjadi satu kalimat, target 6–12 kata (batas validasi 16 kata / 120 karakter), tanpa CTA, hashtag atau klaim baru. Studio lokal menghasilkan bahasa Indonesia; Studio Global menghasilkan bahasa Inggris. Model tidak melihat gambar: pembahasan visual tanpa narasi tidak dapat dipahami lewat fitur ini.

## Instalasi

1. Pasang [Ollama resmi](https://ollama.com/download). Di macOS dengan Homebrew: `brew install ollama`.
2. Dari root source, jalankan `.venv/bin/python local_caption.py` (atau `npm run setup:ai` setelah environment Python tersedia).
3. Setup menjalankan server Ollama lokal bila diperlukan dan mengunduh `qwen3:1.7b` (sekitar 1,4 GB). Internet diperlukan untuk instalasi/unduhan pertama. Setelah model tersedia, inferensi bisa dilakukan tanpa internet.
4. Jalankan aplikasi seperti biasa (`npm run dev` atau launcher). Runtime Ollama akan dijalankan saat caption diperlukan; model tidak diunduh otomatis di tengah proses video.

Jika memasang Ollama untuk Windows/Linux, gunakan installer resmi. Launcher aplikasi saat ini berupa shell macOS/Linux; perintah Python dapat dijalankan langsung dari virtual environment di platform lain.

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

AI merangkum transkrip yang tersedia, bukan mendengarkan ulang audio. Kesalahan ASR dapat menghasilkan caption keliru. Prompt meminta model menolak transkrip yang tidak jelas/repetitif dan mengembalikan kutipan pendukung. Aplikasi memvalidasi kutipan benar-benar ada pada transkrip, panjang output, dan struktur respons. Pemeriksaan ini tidak membuktikan caption benar secara semantik; selalu tinjau sebelum posting. Model kecil dapat melewatkan konteks, humor, slang, atau negasi. Penolakan AI ditandai `needs_review`, bukan diganti caption hasil tebakan.

## Troubleshooting

- **Ollama belum terpasang:** pasang dari sumber resmi, kemudian jalankan setup.
- **Model belum tersedia:** `ollama pull qwen3:1.7b` atau jalankan ulang setup.
- **Runtime gagal dimulai:** lihat `data/ollama.log`, pastikan port 11434 tidak dipakai layanan lain.
- **Tidak merespons:** tunggu pemuatan model, periksa RAM, coba `ollama run qwen3:1.7b` di Terminal. Timeout aplikasi 180 detik per caption.
- **Transkrip kurang jelas:** tinjau subtitle dan suara; tulis caption manual. Mengulang model tidak memperbaiki transkrip sumber.

Sumber teknis: [Qwen3 di Ollama](https://ollama.com/library/qwen3), [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md).
