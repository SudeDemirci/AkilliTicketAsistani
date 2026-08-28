"""
Yapay Zeka Tabanli Oncelik Skorlama Motoru
ITIL v4 prensiplerine dayali cok faktörlü önceliklendirme.

Faktörler:
  1. IT Kategori aciliyeti  (Güvenlik > DB > Donanim > Yazilim ...)
  2. Talep turu agirlik     (Bug > Erisim > Donanim > Ozellik ...)
  3. Tahmini cözüm süresi  (kisa sure = daha acil)
  4. Maliyet etkisi
  5. Bekleme süresi bonus   (eskiyen talepler +puan alir)
"""

from datetime import datetime

# Kategori bazlı aciliyet (ITSM best-practice)
KATEGORI_AGIRLIK = {
    "Güvenlik / Erişim":  10,
    "Veritabanı":          9,
    "Donanım Arızası":     8,
    "Ağ / Bağlantı":       7,
    "Yazılım Sorunu":      6,
    "E-posta / İletişim":  5,
    "Yedekleme / Veri":    4,
    "Lisans / Abonelik":   3,
    "Tasarım / Estetik":   1,
}

# Talep türü ağırlıkları
TALEP_TURU_AGIRLIK = {
    "Bug / Hata":           1.6,
    "Erişim Sorunu":        1.5,
    "Donanım Arızası":      1.4,
    "İletişim Sorunu":      1.2,
    "Veri / Yedekleme":     1.1,
    "Lisans Sorunu":        1.0,
    "Özellik İsteği":       0.7,
    "Diğer":                1.0,
}

ONCELIK_SEVIYELERI = [
    ("P1", "Kritik", "🔴", 31),
    ("P2", "Yüksek", "🟠", 24),
    ("P3", "Orta",   "🟡", 14),
    ("P4", "Düşük",  "⚪",  0),
]


def oncelik_hesapla(
    kategori: str,
    talep_turu: str,
    tahmini_sure_gun: float,
    tahmini_maliyet_tl: float,
    created_at: str = None,
) -> dict:
    """
    Cok faktorlu oncelik skoru hesapla.
    Sonuc: {kod, etiket, ikon, skor, aciklama, detay}
    """
    # 1) Kategori agirlik puani (maks ~20)
    cat_w = KATEGORI_AGIRLIK.get(kategori, 5)
    kat_puan = cat_w * 2.0

    # 2) Talep türü puanı (maks ~9.6)
    type_w = TALEP_TURU_AGIRLIK.get(talep_turu, 1.0)
    tur_puan = type_w * 6.0

    # 3) Çözüm süresi tersi: kisa sure = yüksek öncelik
    #    1 gun → 10 puan, 2 gun → 5, 5 gun → 2, 10+ gun → 1
    sure_puan = min(10.0, 10.0 / max(0.5, float(tahmini_sure_gun)))

    # 4) Maliyet etkisi (0-4 puan)
    if tahmini_maliyet_tl >= 10000:
        maliyet_puan = 4
    elif tahmini_maliyet_tl >= 5000:
        maliyet_puan = 3
    elif tahmini_maliyet_tl >= 2000:
        maliyet_puan = 2
    elif tahmini_maliyet_tl >= 500:
        maliyet_puan = 1
    else:
        maliyet_puan = 0

    # 5) Bekleme bonusu (maks +5)
    bekle_puan = 0.0
    if created_at:
        try:
            olusturulma = datetime.fromisoformat(created_at)
            bekleme_gun = (datetime.now() - olusturulma).total_seconds() / 86400
            bekle_puan = min(5.0, bekleme_gun * 0.3)
        except Exception:
            pass

    skor = kat_puan + tur_puan + sure_puan + maliyet_puan + bekle_puan

    # Etiket belirle
    oncelik_kod, oncelik_etiket, oncelik_ikon = "P4", "Düşük", "⚪"
    for kod, etiket, ikon, esik in ONCELIK_SEVIYELERI:
        if skor >= esik:
            oncelik_kod, oncelik_etiket, oncelik_ikon = kod, etiket, ikon
            break

    if kategori == "Tasarım / Estetik":
        oncelik_kod, oncelik_etiket, oncelik_ikon = "P4", "Düşük", "⚪"

    # Açıklama mesajı
    parcalar = []
    if cat_w >= 9:
        parcalar.append("kritik IT kategorisi")
    if type_w >= 1.4:
        parcalar.append("acil talep türü")
    if tahmini_sure_gun <= 2:
        parcalar.append(f"{tahmini_sure_gun:.1f} günlük kısa çözüm")
    if bekle_puan >= 2:
        parcalar.append("uzun süredir bekliyor")

    return {
        "kod": oncelik_kod,
        "etiket": oncelik_etiket,
        "ikon": oncelik_ikon,
        "skor": round(skor, 2),
        "aciklama": ", ".join(parcalar) if parcalar else "standart öncelik",
        "detay": {
            "kategori_puani":    round(kat_puan, 1),
            "talep_turu_puani":  round(tur_puan, 1),
            "sure_puani":        round(sure_puan, 1),
            "maliyet_puani":     maliyet_puan,
            "bekleme_puani":     round(bekle_puan, 1),
        },
    }
