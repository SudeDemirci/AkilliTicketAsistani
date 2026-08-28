"""
Sentetik IT Destek Talebi Veri Seti Üretici
Eğitim için gerçekçi Türkçe/İngilizce karışık veriler üretir.
"""

import pandas as pd
import numpy as np
import random

random.seed(42)
np.random.seed(42)

KATEGORILER = [
    "Yazılım Sorunu",
    "Donanım Arızası",
    "Ağ / Bağlantı",
    "Güvenlik / Erişim",
    "Veritabanı",
    "E-posta / İletişim",
    "Yedekleme / Veri",
    "Lisans / Abonelik",
]

DEPARTMANLAR = [
    "İnsan Kaynakları",
    "Muhasebe",
    "Satış",
    "Mühendislik",
    "Pazarlama",
    "Operasyon",
    "Hukuk",
    "Ar-Ge",
]

ONCELIKLER = ["Düşük", "Orta", "Yüksek", "Kritik"]

MESAJLAR = {
    "Yazılım Sorunu": [
        "Uygulama açılmıyor, hata mesajı veriyor",
        "Excel dosyaları bozuk açılıyor",
        "SAP modülü çöküyor sürekli",
        "Teams uygulaması login olmuyor",
        "Chrome tarayıcı yavaş çalışıyor",
        "ERP sistemi hata veriyor",
        "Yazıcı sürücüsü kurulmuyor",
        "Güncellemeden sonra program açılmıyor",
        "Office 365 aktivasyon sorunu",
        "Python script çalıştırılamıyor",
        "VPN istemcisi bağlanamıyor",
        "Yazılım kurulum izni reddedildi",
        "Uygulama açılışta çöküyor",
        "Dahili portalda hata oluşuyor",
        "Uygulama içinde veritabanı bağlantı zaman aşımı",
        "Program yüklenemiyor, kurulum başarısız",
        "Lisans doğrulama hatası alıyorum",
        "Uygulama güncelleme sonrası çalışmıyor",
        "Muhasebe yazılımı açılmıyor",
        "CRM sistemi donuyor",
        "Otomatik rapor oluşturulmuyor",
        "Yazılım uyumluluk sorunu var",
        "Arka plan servisi durdu",
        "API bağlantısı hata veriyor",
        "Web uygulaması sayfası açılmıyor",
    ],
    "Donanım Arızası": [
        "Bilgisayar açılmıyor",
        "Ekran görüntü vermiyor",
        "Klavye tuşları çalışmıyor",
        "Mouse donuyor",
        "Laptop bataryası şarj olmuyor",
        "Yazıcı kağıt sıkışıyor",
        "USB portları tanımıyor",
        "Fan sesi çok yüksek",
        "RAM yetersiz, sistem yavaş",
        "SSD disk doldu",
        "Monitör titriyor ve görüntü bozuluyor",
        "Klavye algılanmıyor",
        "Laptop aşırı ısınıyor",
        "Harici hard disk tanınmıyor",
        "Yazıcı kartuşu bitti",
        "Bilgisayar aniden kapanıyor",
        "Güç kaynağı bozuldu",
        "Ekran kartı arızalı",
        "Hoparlör ses vermiyor",
        "Kamera çalışmıyor",
        "Dokunmatik ekran çalışmıyor",
        "Masaüstü bilgisayar kasası arızalı",
        "CD/DVD sürücüsü tanınmıyor",
        "Ağ kartı bağlantı sorunu",
        "Sabit disk sesli çalışıyor",
    ],
    "Ağ / Bağlantı": [
        "İnternet bağlantısı yok",
        "VPN üzerinden sisteme girilemiyor",
        "Wi-Fi sinyali çok zayıf",
        "Dosya sunucusuna erişilemiyor",
        "Ağ yavaş, sayfa açılmıyor",
        "IP adresi çakışması",
        "DNS sorunu, siteler açılmıyor",
        "Proxy ayarları sorunlu",
        "Uzak masaüstü bağlanamıyor",
        "Ağ sürücüsü bağlanamıyor",
        "Sunucuya bağlantı kurulamıyor",
        "Güvenlik duvarı uygulamayı engelliyor",
        "Ağ kablosu bağlı değil",
        "İnternet hızı çok yavaş",
        "VPN kimlik doğrulama başarısız",
        "Kablosuz ağ görünmüyor",
        "Switch arızalı, bağlantı yok",
        "Sunucu ping alamıyor",
        "İç ağda paket kaybı var",
        "Ağ geçidi erişilemiyor",
        "Uzak masaüstü bağlantısı kopuyor",
        "İnternet bağlantısı aralıklı kesiliyor",
        "Ağ paylaşımı çalışmıyor",
        "Bant genişliği yetersiz",
        "Router yeniden başlatılması gerekiyor",
    ],
    "Güvenlik / Erişim": [
        "Şifremi unuttum, sıfırlama gerekiyor",
        "Hesabım kilitlendi",
        "Yeni sisteme erişim yetkisi gerekiyor",
        "İki adımlı doğrulama kodu gelmiyor",
        "Kimlik avı e-posta şüphesi",
        "Yetkisiz erişim denemesi fark ettim",
        "Dosya paylaşım izni gerekiyor",
        "Aktif Dizin hesabı devre dışı",
        "SSL sertifikası hatası",
        "Antivirüs uyarısı veriyor",
        "Hesap kilitlendi, giriş yapamıyorum",
        "Yönetici yetkisine ihtiyacım var",
        "Şüpheli giriş denemesi tespit edildi",
        "Şifre sıfırlama gerekiyor",
        "Paylaşılan klasöre erişim reddedildi",
        "İki faktörlü doğrulama çalışmıyor",
        "Kullanıcı hesabı oluşturulmalı",
        "Yetkisiz program çalıştırılmış",
        "Güvenlik sertifikası süresi dolmuş",
        "Sistem erişim yetkisi kaldırılmalı",
        "Fidye yazılımı şüphesi var",
        "Parola politikası değişikliği gerekiyor",
        "Kullanıcı rolü güncellenmelidir",
        "Erişim logu incelenmeli",
        "Hesap parolası süresi doldu",
    ],
    "Veritabanı": [
        "Veritabanı bağlantısı kopuyor",
        "Sorgu çok yavaş çalışıyor",
        "Tablo erişim yetkisi yok",
        "Yedekleme görevi başarısız",
        "Disk alanı doldu",
        "SQL hata mesajı alıyorum",
        "Replikasyon durdu",
        "Kilitlenme oluşuyor",
        "Dizin bozuk",
        "Saklı yordam çalışmıyor",
        "Veritabanı bağlantı havuzu tükendi",
        "Sorgu çalışması zaman aşımına uğradı",
        "Veri bozulması tespit edildi",
        "Gece yedeği başarısız oldu",
        "Tekrar eden anahtar eklenemiyor",
        "Veritabanı yedekleme planı hata veriyor",
        "Tablo kilitleme sorunu yaşanıyor",
        "Sorgu optimizasyonu gerekiyor",
        "Veritabanı boyutu çok büyüdü",
        "Log dosyası disk alanını doldurdu",
        "Veri tabanı şeması değişikliği gerekiyor",
        "Yabancı anahtar kısıtı hatası",
        "Dizin yeniden oluşturulmalı",
        "Veritabanı kullanıcı yetkisi eklenmeli",
        "Otomatik bakım görevi çalışmıyor",
    ],
    "E-posta / İletişim": [
        "E-posta gönderilemiyor",
        "Gelen kutusu dolu",
        "Spam filtresi meşru mailleri engelliyor",
        "Outlook açılmıyor",
        "Takvim senkronizasyonu çalışmıyor",
        "Teams toplantı bağlantısı çalışmıyor",
        "E-posta eki açılmıyor",
        "Ortak posta kutusu erişimi yok",
        "İmza şablonu bozuldu",
        "Otomatik yanıt ayarlanamıyor",
        "E-posta ekiyle dosya gönderilemiyor",
        "E-posta teslim edilemedi hatası",
        "Teams toplantısında ses çalışmıyor",
        "Takvim davetiyesi alınamıyor",
        "E-posta hesabı senkronize olmuyor",
        "Outlook profili bozuldu",
        "Dağıtım listesi çalışmıyor",
        "E-posta otomatik iletme ayarı sorunu",
        "Teams video görüntüsü gelmiyor",
        "Konferans araması bağlanamıyor",
        "E-posta arşivi açılmıyor",
        "Posta kutusu kotası dolmak üzere",
        "Spam klasörü aşırı doldu",
        "Exchange sunucusu bağlantı hatası",
        "E-posta kuralları çalışmıyor",
    ],
    "Yedekleme / Veri": [
        "Yanlışlıkla dosya silindi",
        "Yedekleme başarısız oldu",
        "Eski versiyona geri dönmek istiyorum",
        "Bulut senkronizasyonu durdu",
        "OneDrive kotası doldu",
        "Kritik veri kayboldu",
        "Arşiv dosyasına erişilemiyor",
        "Yedek dosya bozuk",
        "Kurtarma planı test edilmeli",
        "Veri transferi tamamlanamadı",
        "Önemli dosyaları yanlışlıkla sildim",
        "Yedekleme görevi başarısız oldu",
        "Önceki versiyona geri dönmem gerekiyor",
        "Bulut senkronizasyonu çalışmıyor",
        "Veri taşıma sorunu yaşıyorum",
        "SharePoint dosyası kayboldu",
        "Yedekleme zamanlaması bozuldu",
        "Felaket kurtarma testi yapılmalı",
        "Veri kurtarma işlemi başlatılmalı",
        "Yedekleme sunucusu doldu",
        "Artımlı yedekleme çalışmıyor",
        "Depolama alanı yetersiz",
        "Sürüm geçmişi görüntülenemiyor",
        "Otomatik yedekleme durdu",
        "Bulut depolama kotası aşıldı",
    ],
    "Lisans / Abonelik": [
        "Yazılım lisansı süresi dolmuş",
        "Yeni kullanıcı için lisans gerekiyor",
        "Adobe lisansı açılmıyor",
        "Office 365 abonelik hatası",
        "Antivirus lisansı dolmak üzere",
        "Autocad lisansı sorunlu",
        "Lisans aktivasyon kodu çalışmıyor",
        "Lisans sayısı yetersiz",
        "SaaS abonelik yenilenmeli",
        "Deneme süresi bitti, satın alınmalı",
        "Yazılım lisansı sona erdi",
        "Ekip için ek lisans gerekiyor",
        "Lisans anahtarı kabul edilmiyor",
        "Abonelik yenilenmesi gerekiyor",
        "Lisans sunucusu yanıt vermiyor",
        "Ödeme sonrası lisans aktif olmuyor",
        "Lisans transferi yapılmalı",
        "Kurumsal lisans sözleşmesi güncellenmeli",
        "Kullanılmayan lisanslar iade edilmeli",
        "Lisans kullanım raporu hazırlanmalı",
        "Abonelik faturası ödenmedi",
        "Yazılım abonelik planı değiştirilmeli",
        "Çoklu lisans yönetimi sorunu",
        "Lisans uyumluluk denetimi gerekiyor",
        "Otomatik abonelik yenileme başarısız",
    ],
}

SURE_ARALIK = {
    "Yazılım Sorunu": (0.5, 5),
    "Donanım Arızası": (1, 10),
    "Ağ / Bağlantı": (0.5, 3),
    "Güvenlik / Erişim": (0.5, 4),
    "Veritabanı": (1, 7),
    "E-posta / İletişim": (0.5, 3),
    "Yedekleme / Veri": (1, 5),
    "Lisans / Abonelik": (0.5, 3),
}

MALIYET_ARALIK = {
    "Yazılım Sorunu": (200, 3000),
    "Donanım Arızası": (500, 15000),
    "Ağ / Bağlantı": (300, 5000),
    "Güvenlik / Erişim": (400, 8000),
    "Veritabanı": (800, 12000),
    "E-posta / İletişim": (150, 2000),
    "Yedekleme / Veri": (500, 10000),
    "Lisans / Abonelik": (200, 25000),
}

ONCELIK_CARPANI = {
    "Düşük": 0.7,
    "Orta": 1.0,
    "Yüksek": 1.4,
    "Kritik": 2.0,
}


def veri_seti_olustur(n: int = 2000, seed: int = None) -> pd.DataFrame:
    """n adet sentetik destek talebi üretir.
    
    Args:
        n: Üretilecek kayıt sayısı
        seed: Rastgelelik için seed (testlerde tekrarlanabilirlik için kullanın)
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    kayitlar = []

    for _ in range(n):
        kategori = random.choice(KATEGORILER)
        departman = random.choice(DEPARTMANLAR)
        oncelik = random.choice(ONCELIKLER)
        gonderen = f"Kullanıcı_{random.randint(100, 999)}"
        mesaj = random.choice(MESAJLAR[kategori])

        sure_min, sure_max = SURE_ARALIK[kategori]
        maliyet_min, maliyet_max = MALIYET_ARALIK[kategori]
        carpan = ONCELIK_CARPANI[oncelik]

        # Gerçekçilik için gürültü ekle
        sure = round(
            np.clip(
                random.uniform(sure_min, sure_max) * carpan
                + np.random.normal(0, 0.3),
                0.5,
                30,
            ),
            1,
        )

        maliyet = round(
            np.clip(
                random.uniform(maliyet_min, maliyet_max) * carpan
                + np.random.normal(0, 200),
                100,
                50000,
            ),
            0,
        )

        kayitlar.append(
            {
                "gonderen_kisi": gonderen,
                "gonderen_birim": departman,
                "oncelik": oncelik,
                "mesaj": mesaj,
                "kategori": kategori,
                "cozum_suresi_gun": sure,
                "maliyet_tl": maliyet,
            }
        )

    return pd.DataFrame(kayitlar)


if __name__ == "__main__":
    df = veri_seti_olustur(2000)
    df.to_csv("data/tickets.csv", index=False, encoding="utf-8-sig")
    print(f"✅ {len(df)} adet ticket verisi oluşturuldu.")
    print(df.head())
    print(df["kategori"].value_counts())
