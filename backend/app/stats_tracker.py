"""
Yığılımlı İstatistik Takipçisi
Her onaylanan ticket sonrası kategori başına ortalama süre ve maliyet
Welford online algoritması ile güncellenir.
Veriler disk'te kalıcı olarak saklanır (volume bağlı).
"""

import os
import json
import math
import threading
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_PATH = os.path.join(BASE_DIR, "data", "category_stats.json")

# Başlangıç sentetik prior ağırlığı
PRIOR_WEIGHT = 30

_lock = threading.Lock()

# Kategori normalizasyonu: Türkçe/ASCII farklı yazımlar → canonical ASCII anahtar
# Bu sayede JSON'daki kayıtlar her zaman aynı anahtarla eşleşir.
_CANONICAL = {
    "yazilim sorunu":     "Yazilim Sorunu",
    "donanim arizasi":    "Donanim Arizasi",
    "ag / baglanti":      "Ag / Baglanti",
    "guvenlik / erisim":  "Guvenlik / Erisim",
    "veritabani":         "Veritabani",
    "e-posta / iletisim": "E-posta / Iletisim",
    "yedekleme / veri":   "Yedekleme / Veri",
    "lisans / abonelik":  "Lisans / Abonelik",
}

def _normalize_kategori(kategori: str) -> str:
    """Her türlü yazımı (Türkçe/ASCII) canonical ASCII anahtara çevirir."""
    anahtar = (kategori.lower()
               .replace("ı", "i").replace("i̇", "i")
               .replace("ö", "o").replace("ü", "u")
               .replace("ş", "s").replace("ğ", "g")
               .replace("ç", "c").replace("â", "a")
               .replace("î", "i").replace("û", "u"))
    return _CANONICAL.get(anahtar, kategori)



def _bos_istat() -> dict:
    """Boş kategori istatistiği."""
    return {
        "count": 0,           # Gerçek ticket sayısı
        "sure_mean": None,    # Gerçek ortalama süre (gün)
        "sure_M2": 0.0,       # Welford için varyans birikimi
        "maliyet_mean": None, # Gerçek ortalama maliyet (TL)
        "maliyet_M2": 0.0,
    }


def _yukle() -> dict:
    """İstatistikleri diskten yükle."""
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _kaydet(stats: dict):
    """İstatistikleri diske yaz."""
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def _welford_guncelle(istat: dict, sure: float, maliyet: float) -> dict:
    """
    Welford online algoritması ile ortalama ve M2 (varyans birikimi) güncelle.
    Tüm tarihi veriyi saklamadan O(1) bellek ile çalışır.
    """
    istat["count"] += 1
    n = istat["count"]

    # Süre güncellemesi
    if istat["sure_mean"] is None:
        istat["sure_mean"] = sure
    else:
        delta = sure - istat["sure_mean"]
        istat["sure_mean"] += delta / n
        delta2 = sure - istat["sure_mean"]
        istat["sure_M2"] += delta * delta2

    # Maliyet güncellemesi
    if istat["maliyet_mean"] is None:
        istat["maliyet_mean"] = maliyet
    else:
        delta = maliyet - istat["maliyet_mean"]
        istat["maliyet_mean"] += delta / n
        delta2 = maliyet - istat["maliyet_mean"]
        istat["maliyet_M2"] += delta * delta2

    return istat


def geri_bildirim_ekle(kategori: str, gercek_sure: float, gercek_maliyet: float) -> dict:
    """
    Yeni gerçek veri ekle ve istatistikleri güncelle.
    Thread-safe.
    """
    kategori = _normalize_kategori(kategori)
    with _lock:
        stats = _yukle()
        if kategori not in stats:
            stats[kategori] = _bos_istat()
        stats[kategori] = _welford_guncelle(stats[kategori], gercek_sure, gercek_maliyet)
        _kaydet(stats)
        return stats[kategori]


def blended_tahmin(
    kategori: str,
    model_sure: float,
    model_maliyet: float,
) -> tuple[float, float, dict]:
    """
    Model tahmini ile gerçek istatistikleri Bayes ağırlıklı karıştır.
    """
    kategori = _normalize_kategori(kategori)
    stats = _yukle()
    istat = stats.get(kategori)

    meta = {
        "gercek_veri_sayisi": 0,
        "gercek_veri_katkisi_yuzdesi": 0,
        "gercek_ortalama_sure": None,
        "gercek_ortalama_maliyet": None,
    }

    if not istat or istat["count"] == 0:
        # Hiç gerçek veri yok, sadece model tahmini
        return round(model_sure, 1), round(model_maliyet, 0), meta

    count = istat["count"]
    alpha = min(1.0, count / PRIOR_WEIGHT)

    gercek_sure = istat["sure_mean"]
    gercek_maliyet = istat["maliyet_mean"]

    blended_sure = (1 - alpha) * model_sure + alpha * gercek_sure
    blended_maliyet = (1 - alpha) * model_maliyet + alpha * gercek_maliyet

    # Standart sapma (Welford'dan)
    sure_std = math.sqrt(istat["sure_M2"] / count) if count > 1 else 0
    mal_std = math.sqrt(istat["maliyet_M2"] / count) if count > 1 else 0

    meta = {
        "gercek_veri_sayisi": count,
        "gercek_veri_katkisi_yuzdesi": round(alpha * 100, 1),
        "gercek_ortalama_sure": round(gercek_sure, 1),
        "gercek_ortalama_maliyet": round(gercek_maliyet, 0),
        "gercek_sure_std": round(sure_std, 2),
        "gercek_maliyet_std": round(mal_std, 0),
        "prior_weight": PRIOR_WEIGHT,
    }

    return round(blended_sure, 1), round(blended_maliyet, 0), meta


def tum_istatistikler() -> dict:
    """Tüm kategori istatistiklerini özet olarak döndür."""
    stats = _yukle()
    ozet = {}
    for kat, istat in stats.items():
        count = istat["count"]
        ozet[kat] = {
            "gercek_ticket_sayisi": count,
            "gercek_ortalama_sure_gun": round(istat["sure_mean"], 1) if istat["sure_mean"] else None,
            "gercek_ortalama_maliyet_tl": round(istat["maliyet_mean"], 0) if istat["maliyet_mean"] else None,
            "model_katkisi_yuzdesi": round((1 - min(1.0, count / PRIOR_WEIGHT)) * 100, 1),
            "gercek_veri_katkisi_yuzdesi": round(min(1.0, count / PRIOR_WEIGHT) * 100, 1),
        }
    return ozet
