# Review hasil M1 — persistensi caption

**Pembaruan review kedua:** tiga temuan awal di bawah sudah diperbaiki pada checkout terbaru saat pemeriksaan ulang. Suite Python 51 tes dan ketiga tes JS terkait lolos. Reproduksi write/replace gagal serta regenerasi manual stabil juga berhasil. Masih ada temuan P2 pada tombol Simpan saat request berjalan; lihat bagian terakhir. Bagian temuan awal dipertahankan sebagai riwayat review, bukan klaim bahwa bug tersebut masih ada.

Tanggal: 5 November 2026. Scope: meninjau laporan M1 dari Antigravity terhadap checkout saat review. **Tidak ada perubahan implementasi aplikasi pada review ini.** Temuan berikut adalah snapshot; reproduksi ulang sebelum memperbaiki karena source dapat berubah.

## Kesimpulan

Fitur utama M1 sudah hadir dan suite Python **48 tes lolos** saat dijalankan ulang. Namun tiga masalah di bawah berhasil direproduksi dengan fixture sementara/logic UI terisolasi. Rekomendasi: perbaiki dan perluas tes M1 sebelum lanjut M2. Klaim “lengkap dan terverifikasi” perlu dibatasi sampai skenario kegagalan serta regenerasi eksplisit ini lolos.

## P1 — Memori berubah walaupun penyimpanan disk gagal

Lokasi saat review: `app.py`, `update_caption()`, sekitar baris 474–489; pola serupa juga perlu diperiksa pada commit AI.

Handler memodifikasi objek `current`, memasukkannya ke `jobs`, lalu memanggil `save_job()`. Jika write gagal, handler mengembalikan 500 tetapi tidak mengembalikan state memori/revisi. Bila `current` berasal dari cache resident, modifikasi juga langsung memengaruhi referensi sebelumnya.

Reproduksi dengan job resident, caption “Versi tersimpan”, revisi 1; patch `save_job()` agar melempar OSError:

```text
PATCH caption baru dengan expected_revision=1 → 500
GET sesudah gagal → caption baru, revision=2
job.json pada disk → caption lama, revision=1
retry expected_revision=1 → 409
```

Dampak: server dapat menampilkan data yang belum tersimpan sebagai versi terkini, menciptakan konflik palsu dan menghilangkan perubahan saat restart. Tes disk failure saat ini hanya memeriksa HTTP/message, belum kesetaraan memori/disk dan keberhasilan retry.

Arah perbaikan: copy-on-write terhadap snapshot, persist secara atomik sebelum memublikasikan objek baru ke cache; jangan hanya mengganti variabel lokal yang masih berbagi referensi nested. Commit AI/manual harus memakai prinsip konsisten. Uji kegagalan write/replace ketika job resident maupun disk-only; GET/revisi/cache/file tetap lama dan retry revision lama berhasil setelah kegagalan dipulihkan.

## P1 — Caption manual tidak pernah bisa diganti AI meski pengguna mengonfirmasi

Lokasi saat review: `app.py`, `_handle_generate_caption()`, sekitar baris 554.

Kondisi konflik memakai `revision berubah OR caption_source == manual`. Artinya caption yang sudah manual sebelum request dimulai selalu ditolak, bukan hanya edit yang terjadi ketika AI berjalan. UI justru menawarkan “Ganti teks & buat AI”.

Reproduksi dengan caption_source=manual, revisi 2, tanpa edit bersamaan, dan summarize mock berhasil:

```text
POST regenerasi AI → 409
pesan menyatakan caption diedit saat AI berjalan, padahal tidak ada edit baru
```

Dampak: alur regenerasi yang sudah dikonfirmasi tidak dapat digunakan setelah pengguna menyimpan caption manual.

Arah perbaikan: bedakan persetujuan penggantian eksplisit dengan deteksi race. Gunakan expected revision/kontrak konfirmasi yang jelas dari UI jika diperlukan. Jangan menghapus perlindungan late-AI; edit baru yang masuk selama inferensi tetap harus menang. Tambahkan tes manual stabil + konfirmasi boleh sukses, manual berubah selama AI tetap 409, serta pesan konflik sesuai kejadian sebenarnya. Pertahankan kompatibilitas endpoint legacy yang memang diperlukan.

## P1 — Perlindungan draft hilang saat saving/error/conflict

Lokasi saat review: `static/app.js`, `updateStatus()`, baris 156 dan handler Simpan.

`has-unsaved` ditentukan hanya oleh `state === 'modified'`. Memanggil status saving, error atau conflict menghapus flag meski teks editor masih berbeda dari caption server. `hasUnsavedCaptionEdits()` dan proteksi navigasi memakai flag tersebut.

Reproduksi logic `updateStatus()` di Node VM dengan classList stub:

```text
modified → has-unsaved=true
saving   → has-unsaved=false
error    → has-unsaved=false
modified → has-unsaved=true
conflict → has-unsaved=false
```

Dampak: setelah gagal simpan/konflik, teks masih terlihat tetapi pengguna dapat berpindah video atau menutup halaman tanpa perlindungan draft yang dijanjikan M1.

Arah perbaikan: dirty state harus terpisah dari status request dan didasarkan pada teks dibanding snapshot yang benar-benar tersimpan. Jangan membersihkannya sampai server mengonfirmasi sukses atau pengguna eksplisit membuang/memuat versi server. Verifikasi pula tombol Simpan kembali tersedia setelah request Simpan/AI gagal jika draft masih berbeda.

## Batas verifikasi review

- Python: `unittest discover -s tests -q` dijalankan ulang dan melaporkan 48 tes lolos.
- Kasus disk gagal dan manual→AI direproduksi lewat Flask test client, temporary directory, dan mock model; tidak mengubah history pengguna atau menjalankan inferensi model.
- Dirty state direproduksi dari fungsi asli melalui Node VM/stub; ini bukan bukti uji navigasi browser.
- Klaim persistensi lintas browser dan seluruh state UI dalam laporan awal belum dapat dianggap terbukti hanya dari hasil unit test. Perbaikan perlu bukti browser untuk jalur tersebut.

## Prompt tindak lanjut untuk Antigravity

```text
Tinjau dan perbaiki M1 Klip lokal sebelum melanjutkan M2.

Baca AGENTS.md, SKILLS.md, docs/reviews/M1_REVIEW.md dan docs/prd/KLIP_REVIEW_EDITOR.md. Periksa source aktual dan status Git; review ini snapshot, jadi reproduksi ulang setiap temuan terlebih dahulu. Pertahankan semua perubahan pengguna/untracked file. Jangan reset, commit/push/deploy, memakai data pengguna sebagai fixture, atau menghentikan job aktif.

Scope hanya tiga perbaikan M1:
1. Write caption yang gagal tidak mengubah jobs/cache/revisi. Gunakan copy-on-write/transactional commit yang konsisten untuk manual dan AI. Jangan bocorkan referensi nested yang sudah berubah sebelum disk sukses.
2. Regenerasi AI setelah persetujuan pengguna terhadap caption manual yang stabil harus dapat sukses. Revisi yang berubah selama inferensi tetap konflik dan tidak tertimpa. Bedakan izin mengganti dari race; jangan sekadar menghapus semua guard manual.
3. Dirty state UI terpisah dari saving/error/conflict. Draft tetap terlindungi sampai benar-benar tersimpan atau dibuang eksplisit. Pulihkan tombol Simpan setelah kegagalan jika masih ada perubahan.

Tambahkan regresi berikut sebelum menganggap M1 selesai:
- Job resident dan disk-only: write/replace gagal → GET, disk, cache dan revision tetap lama; retry dengan expected_revision lama berhasil setelah storage pulih.
- Manual stabil + konfirmasi regenerasi → sukses; edit manual lebih baru saat AI berjalan → 409 dan edit baru tetap ada.
- Draft berubah lalu save gagal/konflik → dirty tetap aktif, teks tidak hilang, tombol dapat dipakai kembali, openJob/new-job/close-page tetap melindungi draft.
- AI gagal pada draft belum tersimpan tidak membuat tombol Simpan terkunci permanen.

Jalankan suite Python/JS terkait dan verifikasi UI desktop/sempit, termasuk dua tab serta navigasi setelah gagal/conflict. Jangan menganggap VM/mock membuktikan perilaku browser. Perbarui dokumentasi dan catat bukti command/hasil serta keterbatasan. Hentikan pekerjaan setelah M1 ini diperbaiki; jangan mulai M2 otomatis.
```


## Review kedua — perbaikan tiga temuan awal

Pemeriksaan ulang laporan perbaikan Antigravity pada 5 November 2026:

- Atomic replace gagal: HTTP 500, objek resident tetap sama, GET masih caption lama/revisi 1, retry expected_revision=1 berhasil 200 setelah storage pulih.
- Caption manual stabil: regenerasi AI dengan expected_revision=2 berhasil 200/revisi 3. Tes late-AI tetap lolos.
- Dirty state: tes JS mempertahankan flag saat saving/error/conflict/AI failure; teks tidak dibuang ketika request gagal.
- Suite Python: 51 tes lolos. `test_api_errors.cjs`, `test_delete_dialog.cjs` dan `test_ui_dirty_state.cjs` lolos saat dijalankan ulang.

Bukti ini berasal dari Flask test client/temp directory, mock model serta DOM stub. Tidak ada perubahan source aplikasi atau history pengguna dari review ini. Pengujian lintas tab/browser secara nyata belum dilakukan oleh reviewer.

### P2 — Tombol Simpan kembali aktif saat request masih pending

Lokasi: `static/app.js`, `syncDirtyState()` dan handler klik Simpan.

Handler menetapkan saveBtn.disabled=true, tetapi langsung memanggil updateStatus('saving'). Fungsi itu memanggil syncDirtyState(), yang menetapkan disabled hanya dari !isDirty(). Draft memang masih dirty, sehingga disabled menjadi false ketika request belum selesai.

Reproduksi memakai captionEditor asli dan API Promise yang sengaja belum di-resolve:

```text
status = Menyimpan caption ke server…
textarea.disabled = true
has-unsaved = true
saveBtn.disabled = false
```

Dirty state sudah benar, tetapi status request/busy belum dipisahkan dari aturan enabled tombol. Klik berulang bisa membuat request paralel dengan revisi sama, menimbulkan konflik palsu atau status yang membingungkan. Expected behavior: dirty tetap true, tombol Simpan tetap disabled sampai request selesai, lalu enabled kembali jika gagal dan teks masih berbeda.

### Prompt tindak lanjut kecil

```text
Perbaiki sisa P2 M1 pada docs/reviews/M1_REVIEW.md tanpa mengubah perbaikan tiga temuan awal yang sudah lolos.

Baca AGENTS.md dan source aktual. Reproduksi saveBtn.disabled=false ketika request Simpan masih pending. Pisahkan dirty state (teks vs snapshot server) dari busy state (request Simpan/AI masih berjalan). Aturan tombol Simpan perlu mempertimbangkan keduanya: disabled ketika busy atau tidak dirty. Jangan menghapus has-unsaved hanya karena request sedang berjalan.

Gunakan finally untuk melepas busy dan menyinkronkan tombol sesudah sukses/error/conflict/AI failure. Tambahkan regresi dengan deferred Promise: selama pending tombol Simpan disabled dan dirty true; setelah error tombol enabled dan draft tetap ada; setelah sukses tombol disabled dan dirty false. Pastikan klik berulang tidak memulai request simpan ganda.

Jalankan regresi existing dan verifikasi browser desktop/sempit, termasuk dua tab dan navigasi setelah gagal/conflict. Tulis bukti mana yang mock dan mana yang browser nyata. Jangan mengklaim M1 terverifikasi penuh hanya dari DOM stub. Jangan memulai M2, mengubah data pengguna, commit/push/deploy atau menghentikan pekerjaan aktif dalam tugas ini.
```


## Review ketiga — busy state dan batas bukti browser

Pemeriksaan ulang 5 November 2026 atas laporan perbaikan P2:

- Source kini memisahkan isBusy dari isDirty; Simpan dinonaktifkan ketika busy atau draft bersih. Handler Simpan menolak request ganda, dan finally mengembalikan kontrol setelah sukses/gagal.
- Regresi deferred Promise membuktikan Simpan tetap disabled selama pending, klik berulang tidak menambah panggilan API, draft tetap dirty setelah gagal, dan dirty bersih setelah sukses. P2 sebelumnya tertutup dalam cakupan source dan tes ini.
- Reviewer menjalankan ulang 51 tes Python non-browser dan tiga tes Node (API errors, delete dialog, UI dirty state); semuanya lolos. Tes browser tidak dijalankan ulang oleh reviewer.

### Batas klaim pengujian

Berkas test_browser_caption.py menjalankan Chrome nyata, tetapi hanya memasukkan potongan captionEditor dan CSS ke halaman fixture. API diganti fungsi JavaScript tiruan. Kasus bernama two_tabs memakai satu editor pada satu halaman, lalu mengubah objek serverJob; bukan dua tab nyata atau backend Flask. hasUnsavedCaptionEdits juga didefinisikan ulang di fixture, dan tes tidak menjalankan handler beforeunload/openJob/new-job aplikasi. Tes layar sempit memeriksa sebagian bounding rect, belum mengassert seluruh tombol/wrapping atau mengambil bukti visual.

Hasil ini berguna untuk perilaku DOM komponen, tetapi klaim M1 terverifikasi penuh perlu dipersempit. Tidak ada temuan bug runtime baru pada perbaikan busy state dalam review ini. Sisa validasi integrasi: dua tab nyata terhadap Flask dengan data sementara, draft konflik, tindakan Pakai versi server, dan navigasi nyata setelah gagal/konflik; periksa pula seluruh kontrol di layar sempit. Jangan memakai atau menghapus history pengguna. Tidak perlu membuka kembali perbaikan P2 atau mulai M2 otomatis.
