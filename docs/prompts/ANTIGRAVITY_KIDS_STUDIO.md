# Prompt Antigravity — Studio Anak 3–5 Indonesia

Status: handoff usulan, belum diimplementasikan. Target sudah dipilih pengguna: **3–5 tahun, Indonesia, bahasa Indonesia**. Buka repository Klip lokal dan jalankan satu tahap per tugas.

Acuan: [riset/ide](../KIDS_CONTENT_RESEARCH.md), [PRD Studio Anak](../prd/KLIP_KIDS_STUDIO.md).

## Prompt K1 — Menu, rekomendasi ide dan brief

```text
Tambahkan Studio Anak ke repository Klip lokal yang sedang dibuka, untuk kreator dewasa yang menyiapkan konten anak usia 3–5 tahun berbahasa Indonesia.

Baca AGENTS.md, SKILLS.md, docs/KIDS_CONTENT_RESEARCH.md, docs/prd/KLIP_KIDS_STUDIO.md dan docs/TESTING.md. Audit implementasi routing, template, JavaScript dan metadata saat ini; dokumentasi dapat tertinggal. Periksa git status dan pertahankan semua perubahan/untracked file yang sudah ada.

Kerjakan HANYA K1:
1. Menu Studio Anak di sidebar dan route /kids, dengan target 3–5 tahun / Indonesia yang jelas. Isi katalog/brief ada di area utama. Halaman lokal, Global dan menu history existing tetap bekerja.
2. Katalog minimal 10 ide asli berbahasa Indonesia dari riset: warna, hitung 1–5, bentuk, suara hewan, lagu orisinal merapikan mainan, gerak/tepuk, cerita bergiliran, emosi dasar, menggambar bentuk dan besar/kecil.
3. Setiap kartu mempunyai tujuan tunggal, outline pembukaan–kegiatan–penutup, kebutuhan aset, durasi usulan dan label kelayakan workflow. Lagu/gerak bukan janji automatic clipper mampu memilih lirik/ketukan/gerakan.
4. Filter kategori, detail ide dan tombol Pakai ide yang mengisi brief saja. Tidak mengunduh video referensi atau memulai render.
5. Brief lokal persisten: ID/revisi, judul, tujuan, outline, catatan aset dan target durasi. Validasi backend, write atomik, optimistic concurrency, state simpan/gagal/konflik dan pemulihan draft yang relevan.
6. Salin/ekspor brief TXT/JSON tanpa AI, internet atau worker media. Brief bukan hasil video.
7. Provenance editorial serta sumber/periode bila ada klaim angka. Jangan menyebut katalog sebagai trending live, paling ditonton anak Indonesia, atau menjamin viral.

K1 tidak menambahkan pipeline kids, model baru, pembuat lagu/animasi, dubbing, generative image, analytics, scraping, profil anak, akun/telemetry atau upload otomatis ke YouTube. Tidak meminta nama/sekolah/umur individual anak. Jangan mengubah pengaturan Made for Kids pada akun pengguna.

Periksa asumsi shared JavaScript: app.js saat ini memakai elemen form video di banyak tempat. Halaman baru tanpa form tersebut harus mempunyai entrypoint/guard yang benar, bukan menyembunyikan exception atau membuat form palsu. Pertahankan desain dan keyboard/responsif; jangan menambah framework UI/build pipeline baru.

Simpan brief di area data terpisah dari job dan pastikan scanner history tidak membacanya sebagai pekerjaan. Jangan menghapus/menggunakan history pengguna untuk pengujian. Jangan restart server yang memiliki pekerjaan aktif atau menjalankan server kedua pada data yang sama. Jangan commit, push, deploy atau mengubah konfigurasi global laptop.

Buat rencana singkat, lalu implementasikan dan verifikasi KD-01 sampai KD-05 serta KD-11/KD-12 yang relevan. Tambahkan regresi navigasi lokal/Global/history, console tanpa error null-form, validasi teks, simpan lintas refresh/restart, konflik dua tab dan ekspor offline. Pakai temporary directory/fixture, tanpa download model/video referensi pada unit test.

Update USAGE/API/DEVELOPMENT sesuai fitur yang benar-benar selesai. Laporkan hasil command, bukti browser desktop/sempit, acceptance criteria yang lolos dan batasnya. Jangan lanjut K2/K3 otomatis.
```

## Prompt K2 — Hubungkan brief ke clipper

```text
Lanjutkan K2 Studio Anak dari K1 yang sudah diverifikasi. Baca AGENTS.md dan docs/prd/KLIP_KIDS_STUDIO.md, audit API/metadata/worker aktual sebelum mengubahnya.

Target tetap 3–5 tahun, Indonesia, bahasa Indonesia. Implementasikan content_profile=kids secara terpisah dari audience existing. Kids MVP memakai audience=local dan language=id. Tolak kombinasi kids dengan Global/English secara jelas; jangan mengubah perilaku general lokal/Global.

Hubungkan brief tersimpan ke form sumber secara eksplisit, simpan snapshot pada job dan tampilkan badge history serta label “Kandidat untuk ditinjau”. Pertahankan audio asli. Tidak ada verifikasi kesesuaian usia/visual yang diklaim otomatis; memilih ide tidak membuktikan objek/pelajaran itu ada dalam sumber.

Video sumber dipersiapkan kreator dalam bahasa Indonesia. Caption wajib Indonesia, pendek dan berdasarkan pembahasan nyata, tanpa CTA komentar, data diri atau klaim hasil belajar. Sumber musik/tanpa ucapan jelas harus menunjukkan keterbatasan dan jalan manual/rencana yang tersedia, bukan sukses palsu. Kegagalan caption tidak menggagalkan MP4.

Gunakan editor/thumbnail/watermark hanya jika sudah benar-benar diimplementasikan. Jangan membangun PRD lain sekaligus, membuat kartun/lagu baru, mengunduh referensi populer, mengubah audience YouTube jarak jauh atau memasang model baru.

Jaga default general untuk job lama, API legacy, revisi dan semua batas AGENTS.md. Uji KD-06 sampai KD-10, regresi K1 dan sumber audio yang relevan memakai fixture milik tes. Bedakan mock dengan inspeksi media nyata. Perbarui dokumen dan laporkan batas, tanpa klaim aman untuk semua anak atau jaminan tayangan. Jangan lanjut analytics, bahasa Inggris/umur lain atau K3 otomatis.
```

## Catatan sumber

Referensi kebijakan/platform pada riset harus diperiksa kembali sebelum rilis. Label Studio Anak adalah metadata aplikasi, bukan sertifikasi konten atau jaminan masuk YouTube Kids. Prompt tidak menugaskan akun/cloud API atau pengumpulan data penonton anak.
