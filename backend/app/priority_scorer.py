"""
ITIL v4 Etki / Aciliyet Matrisi Tabanli Oncelik Skorlama Motoru
----------------------------------------------------------------
Yeni mimari:
  - LLM'den gelen Etki (Impact) ve Aciliyet (Urgency) degerleri
    standart ITIL 3x3 matrisinde kesistirilir → P1/P2/P3/P4 belirlenir.
  - LLM cevap veremezse (API hatasi vb.) kural tabanli fallback devreye girer.
  - Bu mimari sayesinde "sinif basinа kural yazma" sorununa son verilir;
    yeni hicbir kural eklenmeden binlerce farkli senaryo dogru siniflandirilir.
"""

from datetime import datetime

# ── ITIL 3x3 Etki / Aciliyet Matrisi ──────────────────────────────────────────
# Satir: Etki (Impact)   | Sutun: Aciliyet (Urgency)
#        Yüksek  Orta   Düşük
ITIL_MATRIX = {
    "Yüksek": {"Yüksek": "P1", "Orta": "P1", "Düşük": "P2"},
    "Orta":   {"Yüksek": "P1", "Orta": "P2", "Düşük": "P3"},
    "Düşük":  {"Yüksek": "P2", "Orta": "P3", "Düşük": "P4"},
}

ONCELIK_META = {
    "P1": {"etiket": "Kritik",  "ikon": "🔴", "skor": 95},
    "P2": {"etiket": "Yüksek",  "ikon": "🟠", "skor": 70},
    "P3": {"etiket": "Orta",    "ikon": "🟡", "skor": 40},
    "P4": {"etiket": "Düşük",   "ikon": "⚪", "skor": 10},
}

# ── FALLBACK: Kural Tabanli Sistem (LLM yoksa devreye girer) ──────────────────
# Kategori → varsayilan Etki/Aciliyet tahmini
KATEGORI_FALLBACK = {
    "Güvenlik / Erişim":  ("Yüksek", "Yüksek"),  # Siber tehdit varsayimi
    "Veritabanı":          ("Yüksek", "Yüksek"),
    "Ağ / Bağlantı":       ("Yüksek", "Yüksek"),
    "Yazılım Sorunu":      ("Orta",   "Orta"),
    "Donanım Arızası":     ("Orta",   "Orta"),
    "E-posta / İletişim":  ("Orta",   "Orta"),
    "Yedekleme / Veri":    ("Yüksek", "Orta"),
    "Lisans / Abonelik":   ("Düşük",  "Orta"),
    "Mobil Uygulama Geliştirme": ("Düşük", "Düşük"),
    "Tasarım / Estetik":   ("Düşük",  "Düşük"),
}

GECERLI_DEGERLER = {"Yüksek", "Orta", "Düşük"}


def oncelik_hesapla(
    kategori: str,
    talep_turu: str,
    tahmini_sure_gun: float,
    tahmini_maliyet_tl: float,
    created_at: str = None,
    llm_etki: str = None,
    llm_aciliyet: str = None,
) -> dict:
    """
    ITIL Etki/Aciliyet Matrisi ile oncelik belirler.
    
    1. LLM'den Etki ve Aciliyet geldiyse → dogrudan matrise sok.
    2. LLM yoksa → kategori bazli fallback tahmin kullan.
    3. Bekleme bonusu: uzun sure bekleyen biletler bir seviye yukar cikabilir.
    """
    kaynak = "itil_matrix"

    # Etki / Aciliyet belirleme
    if llm_etki in GECERLI_DEGERLER and llm_aciliyet in GECERLI_DEGERLER:
        etki = llm_etki
        aciliyet = llm_aciliyet
        kaynak = "llm"
    else:
        # Fallback: kategori bazli varsayim
        fallback = KATEGORI_FALLBACK.get(kategori, ("Orta", "Orta"))
        etki, aciliyet = fallback
        kaynak = "fallback"

    # ITIL matrisinden oncelik kodu al
    oncelik_kod = ITIL_MATRIX.get(etki, {}).get(aciliyet, "P3")

    # Bekleme bonusu: 3+ gun bekleyen P3/P4 biletler bir seviye yukari ciksin
    bekle_gun = 0.0
    if created_at:
        try:
            olusturulma = datetime.fromisoformat(created_at)
            bekle_gun = (datetime.now() - olusturulma).total_seconds() / 86400
        except Exception:
            pass

    if bekle_gun >= 3:
        yukaridan = {"P4": "P3", "P3": "P2"}
        if oncelik_kod in yukaridan:
            oncelik_kod = yukaridan[oncelik_kod]

    meta = ONCELIK_META[oncelik_kod]

    aciklama_parcalar = []
    if etki == "Yüksek":
        aciklama_parcalar.append("yüksek iş etkisi")
    if aciliyet == "Yüksek":
        aciklama_parcalar.append("yüksek aciliyet")
    if bekle_gun >= 3:
        aciklama_parcalar.append(f"{bekle_gun:.0f} gündür bekliyor")
    if kaynak == "fallback":
        aciklama_parcalar.append("otomat. kategori tahmini")

    return {
        "kod":     oncelik_kod,
        "etiket":  meta["etiket"],
        "ikon":    meta["ikon"],
        "skor":    meta["skor"],
        "aciklama": ", ".join(aciklama_parcalar) if aciklama_parcalar else "standart öncelik",
        "detay": {
            "etki":      etki,
            "aciliyet":  aciliyet,
            "kaynak":    kaynak,
            "bekleme_gun": round(bekle_gun, 1),
        },
    }
