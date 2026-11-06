# Peta dokumentasi

Mulai dari [README utama](../README.md) untuk instalasi cepat dan penggunaan aplikasi.

## Pengguna dan operator lokal

| Dokumen | Kapan dibaca |
| --- | --- |
| [NEW_MACHINE](NEW_MACHINE.md) | Memasang dari checkout bersih pada komputer pengguna lain |
| [SETUP](SETUP.md) | Memasang dependensi, menjalankan foreground/launcher, memperbarui instalasi |
| [USAGE](USAGE.md) | Membuat klip, mengatur hasil, membuka dan menghapus history |
| [GLOBAL](GLOBAL.md) | Subtitle/caption Inggris dengan audio asli dan ide editorial |
| [LOCAL_AI](LOCAL_AI.md) | Memasang Ollama/model caption, privasi dan batas akurasi |
| [TROUBLESHOOTING](TROUBLESHOOTING.md) | Server, port, unduhan, model dan ekspor bermasalah |

## Developer dan agent

| Dokumen | Kapan dibaca |
| --- | --- |
| [SKILLS](../SKILLS.md) | Memilih alur kerja, modul dan verifikasi untuk tugas pengembangan |
| [AGENTS](../AGENTS.md) | Sebelum coding agent mengubah repository |
| [CONTRIBUTING](../CONTRIBUTING.md) | Alur kontribusi, konvensi dan penyerahan perubahan |
| [DEVELOPMENT](DEVELOPMENT.md) | Peta source dan titik implementasi fitur |
| [ARCHITECTURE](ARCHITECTURE.md) | Pipeline, penyimpanan dan konkurensi |
| [API](API.md) | Parameter/response endpoint dan kompatibilitas |
| [TESTING](TESTING.md) | Memilih dan menjalankan pemeriksaan yang tepat |
| [DECISIONS](DECISIONS.md) | Alasan desain dan konsekuensi perubahan |
| [Analisis produk](PRODUCT_REVIEW.md) | Prioritas tambahan berdasarkan batas aplikasi saat ini |
| [Review M1](reviews/M1_REVIEW.md) | Temuan reproduksi, batas verifikasi dan prompt perbaikan persistensi caption |
| [PRD editor](prd/KLIP_REVIEW_EDITOR.md) | Scope, milestone dan acceptance criteria usulan P0 |
| [Riset konten anak](KIDS_CONTENT_RESEARCH.md) | Ide editorial usia 3–5 Indonesia dan sumber popularitas/kebijakan |
| [PRD Studio Anak](prd/KLIP_KIDS_STUDIO.md) | Menu, katalog, brief dan integrasi yang masih diusulkan |
| [Prompt Studio Anak](prompts/ANTIGRAVITY_KIDS_STUDIO.md) | Handoff K1 dan K2 untuk Antigravity |
| [PRD watermark](prd/KLIP_WATERMARK.md) | Teks/logo, posisi, transparansi dan integrasi ekspor yang diusulkan |
| [Prompt watermark](prompts/ANTIGRAVITY_WATERMARK.md) | Handoff watermark sesuai fondasi renderer yang tersedia |
| [PRD thumbnail](prd/KLIP_THUMBNAIL.md) | Frame video, judul, template dan ekspor cover yang masih diusulkan |
| [Prompt thumbnail](prompts/ANTIGRAVITY_THUMBNAIL.md) | Handoff implementasi MVP thumbnail/cover |
| [Prompt Antigravity](prompts/ANTIGRAVITY_REVIEW_EDITOR.md) | Instruksi implementasi terpisah M1/M2/M3 |
| [ROADMAP](ROADMAP.md) | Usulan pengembangan; bukan daftar fitur yang sudah tersedia |

## Menjaga dokumentasi

Perubahan UI/input memperbarui USAGE; endpoint memperbarui API; dependensi/launcher memperbarui SETUP; perilaku pipeline memperbarui ARCHITECTURE; prompt/runtime caption memperbarui LOCAL_AI. Catat bukti pemeriksaan di PR, bukan klaim bahwa semua platform/video telah diuji.

Gunakan tautan relatif antarberkas. Jangan memasukkan path laptop pribadi atau isi data pengguna. Jika menambah dokumen, daftarkan di halaman ini agar mudah ditemukan.

Catatan implementasi terbaru: [Studio Anak K2/K3 dan batas ekspor](reviews/KIDS_K2_K3_IMPLEMENTATION.md).

Bukti pengujian live: [Smoke test Studio Anak K2/K3](reviews/KIDS_K2_K3_SMOKE_TEST.md).

Identitas produk dan arah lokal: [Kelip Studio](BRANDING.md).

Analisis media: [Crop bertangga dan kualitas HD](reviews/CROP_QUALITY_ANALYSIS.md).
