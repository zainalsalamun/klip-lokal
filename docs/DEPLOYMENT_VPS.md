# Deployment VPS pribadi Kelip Studio

Panduan ini menyiapkan satu pengguna admin pada Ubuntu 24.04 LTS x86_64 dengan systemd, Python 3.12, Gunicorn, Caddy dan Ollama. Target awal 2 vCPU, RAM 4 GB, SSD 40 GB. Model Whisper base, Qwen3 1.7B, pilihan resolusi dan kualitas sumber tetap tersedia. Stabilitas seluruh pipeline dalam RAM 4 GB perlu dibuktikan melalui uji pada VPS tujuan.

Gunicorn memakai satu worker karena reservasi video, lock AI dan cache aplikasi berada di dalam proses Python. Empat thread HTTP melayani upload, polling dan unduhan saat satu pekerjaan video berjalan di thread latar belakang. Caddy mengakhiri TLS dan melindungi seluruh halaman, API, berkas klip serta aset dengan satu akun HTTP Basic Auth. Gunicorn dan Ollama bind ke loopback. Referensi perilaku server tersedia di [Gunicorn](https://gunicorn.org/reference/settings/), [autentikasi Caddy](https://caddyserver.com/docs/caddyfile/directives/basic_auth) dan [HTTPS otomatis](https://caddyserver.com/docs/automatic-https).

~~~text
Browser → HTTPS 443 → Caddy + login → Gunicorn 127.0.0.1:8765
                                            ├─ yt-dlp / FFmpeg / Whisper
                                            ├─ /opt/kelip/data
                                            └─ Ollama 127.0.0.1:11434
~~~

## Berkas konfigurasi

| Berkas dalam deploy/ | Fungsi |
| --- | --- |
| install.sh | Environment Python, runtime Node dan service Kelip |
| requirements.txt | Dependensi aplikasi dan pin Gunicorn |
| gunicorn.conf.py | Satu worker, empat thread dan bind loopback |
| kelip.service | Pengguna service khusus dan pembatasan filesystem |
| kelip-workload.slice | Anggaran CPU/RAM gabungan aplikasi dan Ollama |
| ollama.conf | Ollama lokal dan satu model aktif |
| Caddyfile | Login, HTTPS, batas upload dan proteksi lintas situs |
| caddy.env.example | Contoh domain, username dan hash password |
| caddy.conf | Konfigurasi privat Caddy melalui systemd |
| check-idle.sh | Menolak maintenance ketika ada pekerjaan aktif |
| restart.sh | Restart Kelip setelah pemeriksaan idle |

## 1. Siapkan VPS dan DNS

Gunakan VPS khusus Kelip dengan Ubuntu 24.04 LTS x86_64 dan akses SSH melalui akun sudo. Arahkan record A subdomain, misalnya kelip.example.com, ke IPv4 VPS. Buat record AAAA hanya jika IPv6 VPS sudah berfungsi.

Buka inbound TCP 22 untuk SSH, TCP 80 untuk HTTP/validasi sertifikat, dan TCP 443 untuk HTTPS pada firewall penyedia VPS. Jika SSH memakai port khusus, izinkan port tersebut. Port 8765 dan 11434 tetap pada localhost. Caddy membutuhkan DNS yang sesuai serta akses port untuk memperoleh sertifikat. [Persyaratan HTTPS Caddy](https://caddyserver.com/docs/automatic-https)

Periksa kapasitas awal.

~~~bash
free -h
df -h /
swapon --show
~~~

Sediakan ruang untuk OS, environment Python, runtime Node, dua model AI, video sumber, WAV, ekspor dan file upload sementara. Pada disk 40 GB, pantau sisa disk setelah setiap beberapa proyek. Targetkan setidaknya 10 GB kosong sebelum video besar. Hapus proyek melalui menu Riwayat jika sudah selesai digunakan.

Jika VPS belum memiliki swap, tambahan 2 GB dapat menjadi penyangga lonjakan memori. Jalankan sekali pada filesystem yang mendukung swapfile, setelah memastikan /swapfile belum ada.

~~~bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudoedit /etc/fstab
~~~

Tambahkan baris berikut sekali ke /etc/fstab.

~~~text
/swapfile none swap sw 0 0
~~~

Swap memakai ruang SSD dan dapat memperlambat proses saat aktif. Ukur tekanan memori melalui uji penerimaan di bagian akhir.

## 2. Pasang paket sistem

~~~bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv npm curl ca-certificates gnupg
python3 --version
npm --version
~~~

Runtime Node 22 khusus downloader dipasang oleh installer di runtime/node_modules/node/bin/node.

Pasang Caddy dari repositori stable resminya.

~~~bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key -o /tmp/caddy-stable.key
sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg /tmp/caddy-stable.key
curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt -o /tmp/caddy-stable.list
sudo install -m 0644 /tmp/caddy-stable.list /etc/apt/sources.list.d/caddy-stable.list
sudo chmod 644 /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo apt-get update
sudo apt-get install -y caddy
caddy version
~~~

Konfigurasi memakai directive basic_auth pada Caddy 2.8+. Langkah instalasi mengikuti [paket stable Caddy](https://caddyserver.com/docs/install#debian-ubuntu-raspbian).

## 3. Pasang Ollama

Unduh installer resmi, tinjau, lalu jalankan pada VPS.

~~~bash
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
less /tmp/ollama-install.sh
sudo sh /tmp/ollama-install.sh
sudo systemctl enable --now ollama
ollama --version
~~~

Installer resmi menyiapkan runtime dan service Linux. [Instalasi Ollama Linux](https://docs.ollama.com/linux)

## 4. Pasang source Kelip

Ganti URL_REPOSITORY dengan repository yang berisi berkas deployment ini. Checkout rilis/commit yang sudah ditinjau dan catat hash untuk rollback. Path /opt/kelip digunakan oleh service serta installer dalam paket ini.

~~~bash
sudo git clone URL_REPOSITORY /opt/kelip
cd /opt/kelip
git rev-parse HEAD
sudo bash deploy/install.sh
~~~

Installer memerlukan root dan Linux x86_64. Installer membuat user kelip, environment Python, runtime Node dan service. Source hasil clone tetap dimiliki administrator. User aplikasi menulis data ke /opt/kelip/data, home ke /var/lib/kelip, dan cache ke /var/cache/kelip. Instalasi ulang memeriksa status pekerjaan sebelum menghentikan service atau mengubah environment.

Runtime Linux menggunakan deploy/install.sh. Launcher desktop npm run dev merupakan jalur macOS. Environment Python dan runtime Node dipasang ulang pada masing-masing mesin.

Installer menambahkan drop-in resource Ollama. Pada instalasi pertama, terapkan sebelum mengunduh model.

~~~bash
sudo systemctl restart ollama
curl --noproxy '*' -fsS http://127.0.0.1:11434/api/tags
ollama pull qwen3:1.7b
~~~

Ollama memakai loopback, satu request/model aktif, dan keep-alive nol. Model disimpan oleh service Ollama, biasanya di /usr/share/ollama/.ollama/models. Pastikan lokasi sebenarnya sebelum backup. Pengaturan service dijelaskan dalam [FAQ Ollama](https://docs.ollama.com/faq).

Unduh model Whisper terlebih dahulu agar pemrosesan pertama tidak menunggu unduhan.

~~~bash
sudo -u kelip env HOME=/var/lib/kelip HF_HUB_DISABLE_XET=1 /opt/kelip/.venv/bin/python -c 'from faster_whisper import WhisperModel; WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=2, download_root="/opt/kelip/data/models")'
~~~

Periksa server lokal.

~~~bash
sudo systemctl status kelip --no-pager
curl --noproxy '*' -fsS http://127.0.0.1:8765/api/health
~~~

## 5. Aktifkan HTTPS dan login pribadi

Buat hash password secara interaktif. Simpan password di password manager. Salin hasil hash lengkap untuk langkah berikutnya.

~~~bash
caddy hash-password
~~~

Buat konfigurasi privat. Perintah ini menyalin contoh hanya saat file belum ada.

~~~bash
sudo install -d -m 0750 -o root -g caddy /etc/kelip
sudo cp -n /opt/kelip/deploy/caddy.env.example /etc/kelip/caddy.env
sudo chown root:caddy /etc/kelip/caddy.env
sudo chmod 640 /etc/kelip/caddy.env
sudoedit /etc/kelip/caddy.env
~~~

Isi domain asli tanpa awalan https, username sederhana, dan hash password.

~~~text
KELIP_DOMAIN=kelip.example.com
KELIP_ADMIN_USER=admin
KELIP_ADMIN_HASH=HASIL_HASH_DARI_CADDY
~~~

Hash bcrypt mengandung tanda dolar. File ini dibaca systemd sebagai EnvironmentFile. Biarkan hash utuh dan hindari menjalankannya sebagai script shell.

Pada VPS khusus Kelip, pasang konfigurasi Caddy berikut. Jika server sudah memiliki situs lain, gabungkan site block Kelip ke Caddyfile aktif sebelum menerapkan.

~~~bash
sudo install -d /etc/systemd/system/caddy.service.d
sudo install -m 0644 /opt/kelip/deploy/caddy.conf /etc/systemd/system/caddy.service.d/kelip.conf
sudo cp -n /etc/caddy/Caddyfile /etc/caddy/Caddyfile.before-kelip
sudo install -m 0644 /opt/kelip/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemd-run --wait --pipe --collect -p EnvironmentFile=/etc/kelip/caddy.env /usr/bin/caddy validate --config /etc/caddy/Caddyfile
sudo systemctl restart caddy
sudo systemctl enable caddy
~~~

Buka https://kelip.example.com. Browser meminta username/password. Login melindungi halaman, API, sumber aset dan unduhan. Browser menyimpan sesi HTTP Basic Auth sesuai perilakunya. Pada perangkat bersama, gunakan jendela privat lalu tutup seluruh jendela privat setelah selesai.

Caddy menolak request POST/PUT/PATCH/DELETE dari Origin berbeda atau browser dengan Sec-Fetch-Site cross-site. CLI dengan autentikasi dapat bekerja tanpa header Origin. Backend dapat diakses langsung dari dalam VPS.

## 6. Verifikasi setelah instalasi

Tanpa login, endpoint publik harus menghasilkan 401.

~~~bash
curl -I https://kelip.example.com/
curl -I https://kelip.example.com/api/jobs
curl -I https://kelip.example.com/static/app.js
~~~

Dengan login, gunakan prompt password dari curl.

~~~bash
curl --user admin https://kelip.example.com/api/health
sudo ss -ltnp
~~~

Pastikan Gunicorn pada 127.0.0.1:8765 dan Ollama pada 127.0.0.1:11434. Caddy melayani port publik 80/443. Caddy admin API, bila aktif, tetap di loopback.

Jalankan video pendek milikmu pada 720p, lalu ekspor 1080p. Periksa subtitle, crop, caption bahasa Indonesia/Inggris, unduhan MP4, watermark dan PNG. Hentikan aplikasi ketika idle lalu mulai kembali untuk memastikan riwayat persisten. Gunakan fixture terpisah untuk simulasi kegagalan dan resume.

Pantau saat transkripsi, caption dan render.

~~~bash
watch -n 2 free -h
sudo systemd-cgtop
sudo systemctl show kelip-workload.slice -p MemoryCurrent -p MemoryPeak
sudo journalctl -u kelip -f
~~~

Anggaran gabungan aplikasi dan Ollama adalah CPU 180%, MemoryHigh 2800 MiB, MemoryMax 3200 MiB, dan swap maksimum 2 GiB jika tersedia. Caddy serta OS berada di luar slice. MemoryHigh menimbulkan reclaim/throttling. MemoryMax dapat mengakhiri proses ketika batas keras terlampaui. Pekerjaan yang terputus dapat dilanjutkan dari Riwayat. Uji seluruh pipeline pada VPS tetap diperlukan. [Resource control systemd](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)

Catat durasi/resolusi sumber, jumlah klip, pilihan crop, model, puncak RAM gabungan, penggunaan swap, waktu proses dan sisa disk. Uji render sintetis lokal yang sudah dilakukan belum mencakup seluruh pipeline Linux.

## 7. Update dan restart

Catat commit lama. Pastikan tidak ada pekerjaan aktif sebelum mengubah source.

~~~bash
cd /opt/kelip
git rev-parse HEAD
sudo bash deploy/check-idle.sh
sudo systemctl stop kelip
sudo git pull --ff-only
sudo bash deploy/install.sh
~~~

Jika update gagal setelah service dihentikan, periksa pesan instalasi. Source, metadata dan model tersedia untuk investigasi. Untuk rollback, checkout commit sebelumnya yang sudah dicatat saat service berhenti lalu jalankan kembali installer dari rilis tersebut. Simpan backup data sebelum update yang mengubah skema.

Restart biasa menggunakan pemeriksaan idle.

~~~bash
cd /opt/kelip
sudo bash deploy/restart.sh
~~~

Restart langsung lewat systemctl, reboot dan kehabisan memori dapat memutus pekerjaan. Resume bersifat manual setelah aplikasi kembali aktif. Restart Ollama dilakukan setelah inferensi selesai.

## 8. Backup dan pemulihan

Buat backup ketika aplikasi idle lalu service dihentikan agar metadata, aset dan ekspor konsisten. Ganti nama file contoh untuk setiap backup.

~~~bash
cd /opt/kelip
sudo bash deploy/check-idle.sh
sudo systemctl stop kelip
sudo install -d -m 0700 /var/backups/kelip
sudo tar -czf /var/backups/kelip/data-backup.tar.gz -C /opt/kelip data
sudo systemctl start kelip
~~~

Simpan salinan terenkripsi di luar VPS. Backup tersebut berisi video pribadi. Simpan konfigurasi /etc/kelip/caddy.env secara privat dan catat commit source. Model Ollama dapat diunduh ulang atau dicadangkan terpisah saat service Ollama idle. Pastikan ruang disk cukup sebelum membuat arsip yang menduplikasi video.

Untuk pemulihan, hentikan Kelip, pindahkan data lama ke direktori backup, ekstrak backup tepercaya ke /opt/kelip, lalu set pemilik kelip:kelip pada folder data dan mulai service. Pertahankan backup lama sampai hasil serta riwayat terverifikasi.

## 9. Troubleshooting

| Gejala | Pemeriksaan |
| --- | --- |
| 502 dari domain | systemctl status kelip dan health loopback |
| TLS belum terbit | Record A/AAAA, port 80/443 dan journalctl -u caddy |
| Login selalu ditolak | Username, hash utuh, environment dan restart Caddy |
| Upload 413 | Batas request 2 GiB mencakup overhead multipart |
| Video gagal ketika RAM tinggi | Log OOM kernel, MemoryPeak slice, swap dan resume |
| Caption AI unavailable | systemctl status ollama, model dan loopback API |
| Gagal sesudah reboot | Buka Riwayat lalu Lanjutkan proses |
| Downloader gagal | Log yt-dlp, runtime Node, akses sumber dan ruang disk |

Akses unduhan YouTube dari IP pusat data dapat berbeda dari laptop. Pesan autentikasi atau pembatasan penyedia perlu ditangani berdasarkan sumbernya. Alternatif sumber yang tersedia di aplikasi adalah unggahan file video.

## Status verifikasi

Konfigurasi disiapkan untuk deployment pribadi pada VPS khusus. Pengujian lokal memeriksa konfigurasi Gunicorn, reverse proxy/autentikasi Caddy, penolakan request lintas situs dan aplikasi dengan fixture terpisah. Installer apt, sandbox systemd, DNS, sertifikat publik dan kapasitas 4 GB harus divalidasi pada VPS Ubuntu tujuan.
