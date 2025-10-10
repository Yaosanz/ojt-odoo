# 🧩 OJT Batch Management

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-purple.svg)](https://www.odoo.com)

Modul Odoo untuk mengelola program On-the-Job Training (OJT) secara komprehensif. Sistem ini dirancang untuk memudahkan perusahaan dalam mengorganisir, memonitor, dan mendokumentasikan program pelatihan kerja.

## ✨ Fitur Utama

- 🗂️ **Batch Management** - Kelola jadwal, mentor, dan status batch OJT
- 👨‍🎓 **Participant Management** - Tracking peserta dan progres pelatihan
- 🪪 **Certificate Generation** - Cetak sertifikat otomatis dengan template profesional
- 🌐 **Portal Integration** - Portal khusus peserta untuk melihat status dan unduh sertifikat
- 📧 **Email Notification** - Notifikasi otomatis saat sertifikat diterbitkan

## 📋 Prasyarat

- Docker Desktop
- Git Bash
- VScode

## 🚀 Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/Yaosanz/ojt-odoo.git
cd ojt-odoo
```

### 2. Jalankan Docker Compose

```bash
docker-compose up -d
```

Perintah ini akan menjalankan:
- **Odoo** pada `http://localhost:8069`
- **PostgreSQL** pada port `5432`

### 3. Akses Odoo

Buka browser dan akses:
```
http://localhost:8069
```

### 4. Instal Modul

#### Via UI:
1. Aktifkan Developer Mode dengan menambahkan `?debug=1` di URL
   ```
   http://localhost:8069/web?debug=1
   ```
2. Buka menu **Apps**
3. Klik **Update Apps List**
4. Cari **"OJT Batch Management"**
5. Klik **Install**

#### Via Command Line:
```bash
# Update daftar modul
docker exec -it odoo odoo -d <nama_database> -u base

# Install modul
docker exec -it odoo odoo -d <nama_database> -i ojt_batch_management
```

## 📁 Struktur Modul

```
ojt_batch_management/
│
├── __init__.py
├── __manifest__.py
│
├── models/                      # Model data
│   ├── __init__.py
│   ├── ojt_batch.py            # Model batch OJT
│   ├── ojt_participant.py      # Model peserta
│   └── ojt_certificate.py      # Model sertifikat
│
├── controllers/                 # Controllers
│   ├── __init__.py
│   └── portal_controller.py    # Portal peserta
│
├── views/                       # XML Views
│   ├── menus.xml
│   ├── ojt_batch_views.xml
│   ├── ojt_participant_views.xml
│   ├── ojt_certificate_views.xml
│   └── portal/
│       └── ojt_portal_templates.xml
│
├── report/                      # Report templates
│   ├── report_certificate_template.xml
│   └── report_actions.xml
│
├── data/                        # Data awal
│   ├── ojt_sequence.xml
│   └── email_template_certificate.xml
│
├── security/                    # Access rights
│   └── ir.model.access.csv
│
└── static/
    └── description/
        └── icon.png
```

## 🔧 Development

### Update Modul

Setelah mengubah kode, jalankan:

```bash
docker exec -it odoo odoo -d <nama_database> -u ojt_batch_management
```

### Melihat Log

```bash
docker logs -f odoo
```

### Restart Container

```bash
docker-compose restart
```

## 🐛 Troubleshooting

### Error: FileNotFoundError

Jika muncul error file tidak ditemukan:

```bash
# Periksa keberadaan file
ls ojt_batch_management/views/portal/

# Buat folder jika belum ada
mkdir -p ojt_batch_management/views/portal
touch ojt_batch_management/views/portal/ojt_portal_templates.xml
```

Atau hapus referensi file di `__manifest__.py` jika tidak diperlukan.

### Module Tidak Muncul di Apps List

```bash
# Update apps list
docker exec -it odoo odoo -d <nama_database> -u base

# Restart Odoo
docker-compose restart odoo
```

### Permission Denied

```bash
# Set permission untuk folder
chmod -R 755 ojt_batch_management/
```

## 📖 Penggunaan

### 1. Membuat Batch OJT
- Buka menu **OJT → Batches**
- Klik **Create**
- Isi informasi batch (nama, tanggal mulai/selesai, mentor)

### 2. Menambah Peserta
- Buka menu **OJT → Participants**
- Klik **Create**
- Pilih batch dan isi data peserta

### 3. Generate Sertifikat
- Buka detail peserta
- Klik tombol **Generate Certificate**
- Sertifikat otomatis dibuat dan email terkirim

### 4. Portal Peserta
Peserta dapat mengakses portal di:
```
http://localhost:8069/my/ojt
```

## 🤝 Kontribusi

Kontribusi sangat diterima! Silakan:

1. Fork repository ini
2. Buat branch fitur (`git checkout -b feature/AmazingFeature`)
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

## 📄 Lisensi

Modul ini dilisensikan di bawah [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html), sesuai dengan standar Odoo Community.

## 👨‍💻 Author

**Yaosan**
- GitHub: [@Yaosanz](https://github.com/Yaosanz)

## 🙏 Acknowledgments

- [Odoo Community](https://www.odoo.com/page/community)
- [Odoo Documentation](https://www.odoo.com/documentation)

---

⭐ Jika modul ini berguna, jangan lupa beri star pada repository!
```

README ini sudah mengikuti best practices GitHub dengan:
- ✅ Badge untuk lisensi dan versi
- ✅ Emoji untuk visual appeal
- ✅ Struktur yang jelas dan terorganisir
- ✅ Bagian instalasi yang detail
- ✅ Troubleshooting guide
- ✅ Kontribusi guidelines
- ✅ Dokumentasi lengkap
- ✅ Formatting markdown yang konsisten