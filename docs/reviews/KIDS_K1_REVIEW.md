# Review Studio Anak K1

Pemeriksaan 5 November2026: cakupan katalog/editor brief sesuai K1, tanpa memulai K2/K3. Reviewer menjalankan test_kids_studio.py:11 tes lolos. Browser tidak dijalankan ulang. Source aplikasi dan data pengguna tidak diubah.

## P1 — Teks brief dipasang sebagai HTML tersimpan

Di loadSavedBriefs static/app.js, item.innerHTML menginterpolasi b.title dan b.learning_goal langsung. Validasi backend mengizinkan teks biasa termasuk tag; contoh title `<img src=x onerror=alert(1)>` diterima validator. Saat daftar dimuat, browser akan memperlakukan teks tersebut sebagai markup, termasuk atribut event. Ini jalur stored XSS pada origin aplikasi lokal, bukan sekadar tampilan judul yang salah. Tidak ada payload dieksekusi terhadap data pengguna dalam review ini.

Gunakan createElement/textContent untuk seluruh nilai brief. Jangan menghapus karakter sah dari judul sebagai pengganti perbaikan sink HTML. Regresi harus menyimpan/memuat tag dan memastikan tampil literal tanpa elemen/event aktif.

## P2 — Respons simpan lama menghapus dirty state edit baru

saveBrief hanya menonaktifkan tombol Simpan. Input, Pakai ide, Brief baru dan Buka brief lain tetap bisa dipakai. Payload diambil sebelum await; setelah respons, handler selalu mengganti currentBriefId/serverRevision lalu markSaved. Jika pengguna mengubah teks selama request, teks terbaru tidak terkirim tetapi dianggap tersimpan. Jika pengguna berpindah ke brief lain saat pending, respons lama bahkan memasang identitas brief sebelumnya ke form lain.

Gunakan busy lock untuk seluruh operasi yang mengganti konteks/form, atau snapshot+generation token serta perbandingan draft saat respons. Tambahkan deferred Promise: edit ketika pending tidak boleh dianggap tersimpan; pergantian konteks tidak boleh menerima respons lama.

## P2 — Draft brief tidak terlindungi saat keluar halaman

isDirty hanya closure initKidsStudio. Handler beforeunload existing hanya memeriksa caption/watermark has-unsaved. Tidak ada integrasi brief untuk refresh/tutup tab/tautan studio/sidebar. Draft bisa hilang tanpa peringatan meski peralihan ide dan brief internal sudah memakai confirm. Integrasikan proteksi navigasi dan uji cancel menjaga teks; jangan mengklaim draft browser persisten jika hanya ada warning.

## P2 — Validasi invalid belum sesuai KD-04

Validator category invalid menjadi warna, target_duration30.9 dipotong menjadi30, language=en dan age_band9_12 diam-diam diganti. Endpoint PATCH juga menerima expected_revision=true karena bool adalah int Python. Reproduksi validator lokal mengonfirmasi semua normalisasi tersebut. PRD meminta tipe/enum invalid ditolak; nilai yang absen dapat memakai default, nilai eksplisit salah harus400. Tambahkan ukuran request brief yang sesuai kebutuhan tanpa mengubah batas upload video global.

## Batas laporan acceptance

K1 tidak membuktikan KD-10 snapshot job sesudah brief berubah; itu memerlukan K2. Pemisahan folder membuktikan isolasi storage saja. Status K1 perlu dibedakan dari KD-07/08/09/10 yang menunggu integrasi video.

## Prompt perbaikan untuk Antigravity

```text
Baca AGENTS.md, SKILLS.md, PRD Studio Anak dan docs/reviews/KIDS_K1_REVIEW.md. Reproduksi source terbaru. Perbaiki hanya K1: hilangkan interpolasi teks brief ke innerHTML, lindungi state/form dari respons simpan lama, integrasikan dirty brief ke navigasi keluar, dan tolak tipe/enum/revisi invalid secara ketat. Pertahankan teks Unicode dan karakter literal, OCC serta penyimpanan atomik. Tambahkan regresi API dan deferred Promise serta browser memakai fixture sementara untuk teks markup literal, input saat pending, switch context, refresh/sidebar cancel, konflik409 dan validasi bool/float/enums. Jangan memakai history atau brief pengguna sebagai fixture. Selaraskan laporan acceptance K1; jangan mulai K2/K3/M2/M3, commit/push/deploy atau menghentikan job aktif. Laporkan mana tes mock/browser fixture/live.
```


## Perbaikan langsung dan verifikasi

Empat temuan di atas diperbaiki pada source: kartu brief dibangun dengan textContent; form dan pergantian konteks dikunci selama request Simpan; dirty brief ikut proteksi beforeunload dan tautan studio; validasi tipe/enum/revisi diperketat. Payload POST/PATCH brief dibatasi32KiB per request, tanpa mengubah batas upload video. Input teks literal/Unicode tetap disimpan utuh.

Verifikasi:82 tes Python non-browser lolos (termasuk13 tes Studio Anak), tiga suite Node existing lolos. Regresi baru tests/kids_ui_regression.js dijalankan melalui halaman fixture template/JS asli di in-app browser pada desktop dan iframe375px:15 assertion lolos, tanpa exception JS; tidak ada markup aktif dari title/goal; busy lock, retry setelah error, dan proteksi navigasi bersih/kotor berhasil. Halaman375px mempunyai scrollWidth=clientWidth=375. Browser memakai API fixture, bukan Flask live; beforeunload diperiksa sebagai event cancelable, bukan dialog tutup-tab OS. Tidak ada inferensi model/worker video atau perubahan data pengguna. Tes Chrome headless existing tidak dijalankan ulang; regresi yang sama telah ditambahkan pada harness browser existing agar dapat dijalankan developer.

Scope tetap K1. KD-07/08/09/10 yang memerlukan snapshot/pipeline video masih menunggu K2.
