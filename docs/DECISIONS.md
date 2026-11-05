# Keputusan arsitektur

Dokumen ini mencatat desain yang ada beserta tradeoff-nya. Bukan persetujuan otomatis untuk mengubah arsitektur.

## Lokal dan satu pengguna

Flask berjalan pada loopback dan media diproses di laptop. Tujuannya penggunaan pribadi tanpa akun/cloud inference. Konsekuensinya: laptop harus aktif dan sumber daya terbatas. Hosting publik membutuhkan desain autentikasi, otorisasi berkas, isolasi worker dan penyimpanan yang berbeda; jangan hanya mengganti bind host.

## Satu worker video dalam proses server

Thread worker, state pekerjaan dan model berada dalam proses Flask. Ini menyederhanakan instalasi. Konsekuensinya: tidak ada antrean durable atau resume jika proses mati. Debug reloader/multi-process dapat menggandakan state dan tidak boleh diaktifkan tanpa redesign.

## Metadata JSON per pekerjaan

`data/<id>/job.json` disimpan secara atomik dan dibaca kembali untuk history. Daftar dipaginasi dengan cache ringkasan terbatas. Ini mudah diperiksa dan dihapus per pekerjaan, tetapi pencarian masih memindai direktori; bukan database dengan skalabilitas tak terbatas. Perubahan skema harus memiliki default untuk record lama.

## Subtitle ASS dan audio asli

ASS dibakar melalui FFmpeg dengan kanvas referensi 720×1280. Preset klasik mempertahankan tampilan default. Ketepatan waktu mengikuti segmen Whisper, bukan alignment setiap kata. Mode Global memakai terjemahan transkrip untuk subtitle, sementara stream audio tetap berasal dari sumber.

## Crop pembicara berupa heuristik

Deteksi wajah, gerakan area mulut dan level audio memperkirakan posisi pembicara. Smoothing mengurangi perpindahan mendadak; fallback tengah tersedia. Ini tidak mengenali identitas pembicara dan belum memakai model active-speaker yang terverifikasi.

## Caption semantik lewat Ollama lokal

Qwen3 1.7B merangkum transkrip klip lewat endpoint loopback. Model dipasang terpisah dari Whisper, tanpa cloud fallback, dan dilepas dari RAM setelah request. Pemeriksaan pengulangan, struktur, panjang, pembuka dan kutipan membantu menyaring keluaran; tidak membuktikan kebenaran semantik. AI gagal tidak boleh menggagalkan ekspor MP4.

## UI tanpa framework tambahan

Jinja, JavaScript biasa dan CSS melayani kedua studio. Select asli tetap menjadi sumber FormData, walaupun tampilannya memakai combobox kustom. Menu history berada di sidebar; isi history memakai area utama. Draft manual disimpan di browser, caption AI di metadata server.

## Mengubah keputusan

Jelaskan masalah, alternatif, dampak data/history, privasi, kebutuhan sumber daya dan strategi verifikasi pada PR. Perbarui dokumen ini serta API/SETUP/ARCHITECTURE yang relevan setelah perubahan benar-benar diterapkan. Jangan menulis rencana sebagai fitur tersedia.
