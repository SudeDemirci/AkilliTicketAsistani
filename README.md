# Akıllı Ticket Asistanı

> NLP tabanlı kurum içi IT destek talebi analiz ve yönlendirme sistemi.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.5-orange)
![Docker](https://img.shields.io/badge/Docker-ready-blue)

---

##  Özellikler

- **AI Kategori Sınıflandırma** — TF-IDF + SVC ile 8 kategori, ~%90+ doğruluk
- **Çözüm Süresi Tahmini** — RandomForest Regressor (gün cinsinden)
- **Maliyet Tahmini** — RandomForest Regressor (TL cinsinden)
- **Departman Yönlendirme** — Kategoriye göre otomatik yönlendirme
- **Dosya Analizi** — PDF, TXT, LOG dosyalarından metin çıkarma
- **Sürekli Öğrenme** — Her analiz verisi kaydedilir, model güncellenebilir
- **MLOps Paneli** — Arka planda model yeniden eğitimi + canlı durum takibi
- **Premium UI** — Dark mode, glassmorphism, animasyonlu arayüz

---

##  Proje Yapısı

```
AkıllıTicketAsistanı/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI uygulama + endpoint'ler
│   │   ├── data_generator.py # Sentetik veri üretici
│   │   ├── model_trainer.py  # Model eğitim motoru
│   │   └── predictor.py     # Tahmin motoru (singleton)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Ana uygulama
│   ├── style.css            # Tasarım sistemi
│   └── app.js               # Uygulama mantığı
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## 🚀 Hızlı Başlangıç

### Yöntem 1: Yerel Çalıştırma (Önerilen)

Backend dizininde tek bir komutla hem API servisini hem de web arayüzünü başlatabilirsiniz:

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Tarayıcıdan doğrudan erişim:
- 🌐 **Web Arayüzü:** [http://localhost:8000](http://localhost:8000)
- 📚 **Swagger API Dokümantasyonu:** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Servis Sağlık Durumu:** [http://localhost:8000/saglik](http://localhost:8000/saglik)

---

### 🔑 Demo Giriş Hesapları

| Rol | Kullanıcı Adı | Şifre | Yetki ve İşlevler |
|---|---|---|---|
| **Çalışan** | `calisan` | `123456` | Destek talebi formu doldurma, dosya yükleme, geçmiş talepleri ve mesajlaşmaları takip etme |
| **IT Uzmanı** | `uzman` | `123456` | Tüm departman talepleri, P1-P4 ITIL aciliyet/etki skorları, SLA takibi, anlamsal emsal vaka analizi |

---

### Yöntem 2: Docker Compose ile Çalıştırma

Docker kurulu ortamlarda konteyner olarak ayağa kaldırmak için:

```bash
docker-compose up --build
```

- Web Arayüzü: [http://localhost:8000](http://localhost:8000) (veya Nginx proxy ile [http://localhost:3000](http://localhost:3000))
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

##  API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET  | `/saglik` | Servis sağlık kontrolü |
| GET  | `/istatistikler` | Model metrikleri + veri istatistikleri |
| POST | `/analiz-et` | Form + dosya ile ticket analizi |
| POST | `/analiz-et-json` | JSON body ile ticket analizi |
| POST | `/modeli-yeniden-egit` | Arka planda model yeniden eğitimi |
| GET  | `/egitim-durumu` | Eğitim durumu takibi |
| GET  | `/docs` | Swagger UI |

---

##  AI Model Detayları

| Model | Algoritma | Hedef |
|-------|-----------|-------|
| Kategori | TF-IDF (n-gram 1-2) + SVC (RBF) | 8 kategori sınıflandırma |
| Çözüm Süresi | TF-IDF + RandomForest Regressor | Gün cinsinden tahmin |
| Maliyet | TF-IDF + RandomForest Regressor | TL cinsinden tahmin |

**Kategori Listesi:**
- 💻 Yazılım Sorunu
- 🖥️ Donanım Arızası  
- 🌐 Ağ / Bağlantı
- 🔒 Güvenlik / Erişim
- 🗄️ Veritabanı
- 📧 E-posta / İletişim
- 💾 Yedekleme / Veri
- 🔑 Lisans / Abonelik

---

##  Teknoloji Stack

- **Backend:** Python 3.11, FastAPI, Uvicorn, Pydantic v2
- **AI/ML:** Scikit-learn, Pandas, NumPy, Joblib
- **Frontend:** Vanilla HTML/CSS/JS, Google Fonts (Inter)
- **DevOps:** Docker, Docker Compose, Nginx

---

##  Örnek API İsteği

```bash
curl -X POST http://localhost:8000/analiz-et \
  -F "gonderen_kisi=Ahmet Yılmaz" \
  -F "gonderen_birim=Muhasebe" \
  -F "oncelik=Yüksek" \
  -F "mesaj=SAP sistemi açılmıyor, hata mesajı veriyor"
```

**Örnek Yanıt:**
```json
{
  "kategori": "Yazılım Sorunu",
  "yonlendirilen_departman": "Yazılım Destek Ekibi",
  "cozum_suresi_gun": 2.3,
  "tahmini_maliyet_tl": 1850.0,
  "guven_skoru": 0.924,
  "alternatif_kategoriler": [
    {"kategori": "Yazılım Sorunu", "olasilik": 0.924},
    {"kategori": "Veritabanı",     "olasilik": 0.045},
    {"kategori": "Ağ / Bağlantı",  "olasilik": 0.018}
  ]
}
```
