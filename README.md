# Akıllı IT Destek Sistemi (Ticket Asistanı)

> NLP ve LLM tabanlı kurumsal IT destek talebi analiz, önceliklendirme ve otomatik yönlendirme platformu.

[![Canlı Demo](https://img.shields.io/badge/Canlı%20Demo-Render-brightgreen?style=for-the-badge&logo=render)](https://akilliticketasistani.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.5-orange?style=for-the-badge&logo=scikit-learn)](https://scikit-learn.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

 **Canlı Uygulama:** [https://akilliticketasistani.onrender.com](https://akilliticketasistani.onrender.com)  
 **Canlı Swagger API Dokümantasyonu:** [https://akilliticketasistani.onrender.com/docs](https://akilliticketasistani.onrender.com/docs)  
 **Canlı Sağlık Kontrolü:** [https://akilliticketasistani.onrender.com/saglik](https://akilliticketasistani.onrender.com/saglik)

---

##  Demo Giriş Hesapları

Projeyi canlı ortamda veya yerelde hemen test etmek için hazır hesaplar:

| Rol | Kullanıcı Adı | Şifre | Yetki ve İşlevler |
|---|---|---|---|
| **Çalışan** | `calisan` | `123456` | Destek talebi oluşturma, dosya yükleme, geçmiş talepleri görme ve mesajlaşma |
| **IT Uzmanı** | `uzman` | `123456` | Tüm departman talepleri, P1-P4 ITIL öncelikleri, SLA takibi, emsal vaka analizi ve bilet tamamlama |

---

##  Temel Özellikler

- **AI Kategori Sınıflandırma:** TF-IDF + SVC (RBF Çekirdeği) ve Google Gemini LLM desteğiyle 8 kategori sınıflandırması (~%90+ doğruluk).
- **ITIL v4 Öncelik Matrisi (P1 - P4):** Etki (Impact) ve Aciliyet (Urgency) parametrelerine göre otomatik öncelik belirleme.
- **Çözüm Süresi ve Maliyet Tahmini:** RandomForest Regressor modelleriyle tahmini gün ve TL maliyeti öngörüsü.
- **Departman Yönlendirme:** Kategori ve talep içeriğine göre ilgili IT uzman ekibine otomatik atama.
- **Anlamsal Emsal Vaka Analizi:** Benzer geçmiş kayıtları tarayarak daha önceki ortalama çözüm süresi ve maliyet referanslarını sunma.
- **SLA Takibi:** Talepler için dinamik geri sayım ve SLA ihlali durum bildirimi.
- **Canlı Yazışma & Mesajlaşma (Thread):** Çalışan ve IT uzmanı arasında bilet bazlı etkileşim ve durum logları.
- **Dosya Analizi:** PDF, TXT, LOG gibi ekli dosyalardan metin çıkarma ve hata analizi.
- **Sürekli Öğrenme (MLOps):** Uzman tarafından tamamlanan biletlerin gerçek verileriyle modellerin dinamik öğrenmesi ve arka planda yeniden eğitimi.
- **Bulut ve Docker Entegrasyonu:** Render.com için `render.yaml` ve Docker Compose yapılandırması.

---

##  Hızlı Başlangıç

### Seçenek 1: Canlı Demoyu Deneyin (Kurulumsuz)
Herhangi bir kurulum yapmadan doğrudan tarayıcınızdan inceleyebilirsiniz:  
 **[https://akilliticketasistani.onrender.com](https://akilliticketasistani.onrender.com)**

---

### Seçenek 2: Yerel Geliştirme (Local)

Backend servisi FastAPI ile frontend statik dosyalarını da doğrudan sunar:

```bash
# 1. Projeyi klonlayın
git clone https://github.com/SudeDemirci/AkilliTicketAsistani.git
cd AkilliTicketAsistani/backend

# 2. Sanal ortam oluşturup aktif edin
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Sunucuyu başlatın
uvicorn app.main:app --reload --port 8000
```

Tarayıcınızdan:
* **Arayüz:** [http://localhost:8000](http://localhost:8000)
* **Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Seçenek 3: Docker Compose ile Çalıştırma

```bash
docker-compose up --build
```
* **Arayüz:** [http://localhost:8000](http://localhost:8000) (veya Nginx proxy ile [http://localhost:3000](http://localhost:3000))

---

### Seçenek 4: Render.com ile Buluta Dağıtım

Proje kök dizinindeki `render.yaml` sayesinde Render üzerinde 1 tıkla yayına alınabilir:
1. [dashboard.render.com](https://dashboard.render.com) adresine gidin.
2. **New > Web Service** seçin ve GitHub deponuzu bağlayın.
3. **Runtime:** `Python 3`
4. **Build Command:** `pip install -r backend/requirements.txt`
5. **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. **Deploy** butonuna basın.

---

##  Proje Yapısı

```
AkıllıTicketAsistanı/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI ana uygulama, statik sunucu ve endpoint'ler
│   │   ├── auth.py              # JWT kimlik doğrulama & şifreleme
│   │   ├── ticket_db.py         # SQLite veritabanı motoru
│   │   ├── priority_scorer.py   # ITIL öncelik puanlama algoritması
│   │   ├── llm_router.py        # Gemini LLM analiz yönlendiricisi
│   │   ├── predictor.py         # ML tahmin motoru (kategori, süre, maliyet)
│   │   ├── model_trainer.py     # TF-IDF + SVC ve RF model eğitim motoru
│   │   ├── data_generator.py    # Sentetik veri üretici
│   │   └── stats_tracker.py     # Sürekli öğrenme ve geri bildirim takipçisi
│   ├── data/
│   │   ├── tickets.db           # SQLite veritabanı (114+ talep)
│   │   └── tickets_db.json      # Veritabanı başlangıç tohum verisi
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Tek sayfa kurumsal destek uygulaması (SPA)
│   ├── style.css                # Tasarım sistemi
│   └── app.js                   # Dinamik UI mantığı, filtreleme ve API istemcisi
├── docker-compose.yml           # Konteyner orkestrasyonu
├── nginx.conf                   # Nginx ters vekil sunucu yapılandırması
├── render.yaml                  # Render bulut dağıtım konfigürasyonu
├── .python-version              # Python sürüm kilidi (3.11.9)
└── README.md
```

---

##  API Endpoint'leri

| Method | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/saglik` | Servis sağlık kontrolü ve model durumu |
| `POST` | `/login` | JWT tabanlı kullanıcı girişi (`calisan` / `uzman`) |
| `POST` | `/analiz-et` | Form ve ekli dosya ile AI destek talebi analizi |
| `GET` | `/talepler` | Talepleri listeleme (departman ve durum filtreli) |
| `POST` | `/talep-tamamla` | Talebi gerçek süre/maliyetle kapatma (sürekli öğrenme) |
| `POST` | `/talep/{talep_no}/yorum` | Talep altına mesaj/yorum ekleme |
| `GET` | `/talep/{talep_no}/yorum` | Talep geçmiş yazışmalarını getirme |
| `GET` | `/istatistikler` | Model metrikleri ve bilet istatistikleri |
| `POST` | `/modeli-yeniden-egit` | Arka planda modeli yeniden eğitme |
| `GET` | `/docs` | Etkileşimli Swagger UI |

---

##  AI Model Detayları

| Görev | Algoritma / Yöntem | Amaç |
|---|---|---|
| **Kategori Sınıflandırma** | TF-IDF (n-gram 1-2) + SVC (RBF) & Gemini LLM | 8 IT kategorisi sınıflandırma |
| **Çözüm Süresi Tahmini** | TF-IDF + RandomForest Regressor | Gün cinsinden süre tahmini |
| **Maliyet Tahmini** | TF-IDF + RandomForest Regressor | TL cinsinden maliyet tahmini |
| **Öncelik Skorlaması** | Kural Tabanlı ITIL v4 Matrisi | P1 Kritik, P2 Yüksek, P3 Orta, P4 Düşük |

**Kategori Kapsamı:**
-  Yazılım Sorunu
-  Donanım Arızası
-  Ağ / Bağlantı
-  Güvenlik / Erişim
-  Veritabanı
-  E-posta / İletişim
-  Yedekleme / Veri
-  Lisans / Abonelik

---

##  Teknoloji Yığını

- **Backend:** Python 3.11, FastAPI, Uvicorn, Pydantic v2, PyJWT, Passlib (bcrypt), SQLite
- **Yapay Zeka / ML:** Scikit-learn, Pandas, NumPy, Joblib, Google GenAI (Gemini)
- **Frontend:** Vanilla HTML5, Modern CSS (Glassmorphism, Dark UI, Responsive), Vanilla JavaScript ES6+
- **DevOps & Bulut:** Render.com, Docker, Docker Compose, Nginx
