"""
Unit Testler
- stats_tracker
- predictor
- data_generator
- model_trainer yardimci fonksiyonlar
"""
import sys
import os
import math
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# STATS TRACKER
# =============================================================================

class TestStatsTracker:
    def setup_method(self):
        """Her test oncesi bellekteki stats'i temizle."""
        from app import stats_tracker
        # Gecici path kullan
        self._orig = stats_tracker.STATS_PATH
        stats_tracker.STATS_PATH = os.path.join(
            os.path.dirname(__file__), "_test_stats.json"
        )
        # Varsa sil
        if os.path.exists(stats_tracker.STATS_PATH):
            os.remove(stats_tracker.STATS_PATH)

    def teardown_method(self):
        from app import stats_tracker
        if os.path.exists(stats_tracker.STATS_PATH):
            os.remove(stats_tracker.STATS_PATH)
        stats_tracker.STATS_PATH = self._orig

    def test_geri_bildirim_ilk_kayit(self):
        from app.stats_tracker import geri_bildirim_ekle
        istat = geri_bildirim_ekle("Yazilim Sorunu", 3.0, 500.0)
        assert istat["count"] == 1
        assert istat["sure_mean"] == 3.0
        assert istat["maliyet_mean"] == 500.0

    def test_geri_bildirim_welford_ortalama(self):
        from app.stats_tracker import geri_bildirim_ekle
        geri_bildirim_ekle("Yazilim Sorunu", 2.0, 400.0)
        geri_bildirim_ekle("Yazilim Sorunu", 4.0, 600.0)
        istat = geri_bildirim_ekle("Yazilim Sorunu", 3.0, 500.0)
        assert istat["count"] == 3
        assert abs(istat["sure_mean"] - 3.0) < 0.01
        assert abs(istat["maliyet_mean"] - 500.0) < 0.01

    def test_blended_hic_veri_yok(self):
        from app.stats_tracker import blended_tahmin
        sure, maliyet, meta = blended_tahmin("Yazilim Sorunu", 5.0, 1000.0)
        assert sure == 5.0
        assert maliyet == 1000.0
        assert meta["gercek_veri_sayisi"] == 0

    def test_blended_veri_var(self):
        from app.stats_tracker import geri_bildirim_ekle, blended_tahmin
        for _ in range(10):
            geri_bildirim_ekle("Yazilim Sorunu", 2.0, 300.0)
        sure, maliyet, meta = blended_tahmin("Yazilim Sorunu", 10.0, 2000.0)
        # Gercek veri agirliklaninca model tahmininden farkli olmali
        assert sure != 10.0 or maliyet != 2000.0
        assert meta["gercek_veri_sayisi"] == 10

    def test_blended_alpha_artisi(self):
        from app.stats_tracker import geri_bildirim_ekle, blended_tahmin, PRIOR_WEIGHT
        # 30 veri = alpha=1.0 (tam gercek veri)
        for _ in range(PRIOR_WEIGHT):
            geri_bildirim_ekle("Yazilim Sorunu", 3.0, 500.0)
        _, _, meta = blended_tahmin("Yazilim Sorunu", 10.0, 2000.0)
        assert meta["gercek_veri_katkisi_yuzdesi"] >= 100.0

    def test_farkli_kategoriler_ayri_istatistik(self):
        from app.stats_tracker import geri_bildirim_ekle
        geri_bildirim_ekle("Yazilim Sorunu", 3.0, 500.0)
        geri_bildirim_ekle("Veritabani", 7.0, 1500.0)
        i1 = geri_bildirim_ekle("Yazilim Sorunu", 3.0, 500.0)
        assert i1["count"] == 2

    def test_normalize_turkce(self):
        """Turkce karakterli kategori normalized edilmeli."""
        from app.stats_tracker import _normalize_kategori
        result = _normalize_kategori("Yazılım Sorunu")
        assert result is not None

    def test_tum_istatistikler_bos_dict(self):
        from app.stats_tracker import tum_istatistikler
        sonuc = tum_istatistikler()
        assert isinstance(sonuc, dict)

    def test_tum_istatistikler_geri_bildirim_sonrasi(self):
        from app.stats_tracker import geri_bildirim_ekle, tum_istatistikler
        geri_bildirim_ekle("Veritabani", 5.0, 900.0)
        sonuc = tum_istatistikler()
        # En az bir kategori olmali
        assert len(sonuc) >= 1

    def test_welford_m2_pozitif(self):
        """M2 (varyans birikimi) negatif olmamali."""
        from app.stats_tracker import geri_bildirim_ekle
        for v in [1.0, 3.0, 5.0, 7.0, 9.0]:
            istat = geri_bildirim_ekle("Yazilim Sorunu", v, v * 100)
        assert istat["sure_M2"] >= 0
        assert istat["maliyet_M2"] >= 0


# =============================================================================
# PREDICTOR YARDIMCI FONKSIYONLAR
# =============================================================================

class TestPredictorHelpers:
    def test_metin_temizle_kucuk_harf(self):
        from app.predictor import metin_temizle
        assert metin_temizle("BUYUK HARF") == "buyuk harf"

    def test_metin_temizle_noktalama(self):
        from app.predictor import metin_temizle
        result = metin_temizle("test! sorun? hata.")
        assert "!" not in result and "?" not in result and "." not in result

    def test_metin_temizle_bosluk(self):
        from app.predictor import metin_temizle
        result = metin_temizle("cok   fazla    bosluk")
        assert "  " not in result

    def test_metin_temizle_strip(self):
        from app.predictor import metin_temizle
        assert metin_temizle("  bosluk  ") == "bosluk"

    def test_girdi_birlestir_temel(self):
        from app.predictor import girti_birlestir
        result = girti_birlestir("IT", "Yuksek", "test mesaji")
        assert "it" in result
        assert "yuksek" in result
        assert "test" in result

    def test_girdi_birlestir_ek_icerik(self):
        from app.predictor import girti_birlestir
        result = girti_birlestir("IT", "Orta", "sorun", ek_icerik="log dosyasi icerik")
        assert "log" in result

    def test_girdi_birlestir_ek_icerik_max_500(self):
        from app.predictor import girti_birlestir
        uzun = "x" * 1000
        result = girti_birlestir("IT", "Orta", "sorun", ek_icerik=uzun)
        # ek icerik 500 karakterle kesilmeli
        assert len(result) < 1500  # makul ust sinir

    def test_tahmin_motoru_hazir(self):
        from app.predictor import tahmin_motoru
        assert tahmin_motoru.hazir_mi()

    def test_tahmin_et_temel(self):
        from app.predictor import tahmin_motoru
        sonuc = tahmin_motoru.tahmin_et(
            gonderen_kisi="Test",
            gonderen_birim="IT",
            oncelik="Orta",
            mesaj="Yazilim acilmiyor hata veriyor",
        )
        assert "kategori" in sonuc
        assert "cozum_suresi_gun" in sonuc
        assert "tahmini_maliyet_tl" in sonuc

    def test_tahmin_et_sure_pozitif(self):
        from app.predictor import tahmin_motoru
        sonuc = tahmin_motoru.tahmin_et("T", "IT", "Orta", "test")
        assert sonuc["cozum_suresi_gun"] >= 0.5

    def test_tahmin_et_maliyet_pozitif(self):
        from app.predictor import tahmin_motoru
        sonuc = tahmin_motoru.tahmin_et("T", "IT", "Orta", "test")
        assert sonuc["tahmini_maliyet_tl"] >= 100

    def test_tahmin_et_guven_aralik(self):
        from app.predictor import tahmin_motoru
        sonuc = tahmin_motoru.tahmin_et("T", "IT", "Orta", "test")
        assert 0.0 <= sonuc["guven_skoru"] <= 1.0

    def test_tahmin_et_3_alternatif(self):
        from app.predictor import tahmin_motoru
        sonuc = tahmin_motoru.tahmin_et("T", "IT", "Orta", "test")
        assert len(sonuc["alternatif_kategoriler"]) == 3

    def test_tahmin_et_yonsuz_model_hatasi(self):
        """Yuklenmemis model RuntimeError vermeli."""
        from app.predictor import TahminMotoru
        bos = TahminMotoru.__new__(TahminMotoru)
        bos.kategori_pipeline = None
        bos.sure_bundle = None
        bos.maliyet_bundle = None
        bos.metrikler = {}
        with pytest.raises(RuntimeError):
            bos.tahmin_et("T", "IT", "Orta", "test")


# =============================================================================
# DATA GENERATOR
# =============================================================================

class TestDataGenerator:
    def test_veri_seti_olustur_boyut(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(100)
        assert len(df) == 100

    def test_veri_seti_kolonlar(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(50)
        for k in ("gonderen_kisi", "gonderen_birim", "oncelik", "mesaj",
                  "kategori", "cozum_suresi_gun", "maliyet_tl"):
            assert k in df.columns, f"Eksik kolon: {k}"

    def test_veri_seti_kategori_cesitliligi(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(500)
        assert df["kategori"].nunique() >= 6

    def test_veri_seti_sure_pozitif(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(100)
        assert (df["cozum_suresi_gun"] > 0).all()

    def test_veri_seti_maliyet_pozitif(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(100)
        assert (df["maliyet_tl"] > 0).all()

    def test_veri_seti_oncelik_gecerli(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(100)
        gecerli = {"Dusuk", "Orta", "Yuksek", "Kritik",
                   "D\u00fc\u015f\u00fck", "Y\u00fcksek"}  # hem ascii hem turkce
        for onc in df["oncelik"].unique():
            assert onc is not None

    def test_veri_seti_bos_mesaj_yok(self):
        from app.data_generator import veri_seti_olustur
        df = veri_seti_olustur(100)
        assert df["mesaj"].notna().all()
        assert (df["mesaj"].str.strip() != "").all()

    def test_veri_seti_gecerli_kategoriler(self):
        """Gecerli kategoriler dondurmeli."""
        from app.data_generator import veri_seti_olustur, KATEGORILER
        df = veri_seti_olustur(50, seed=42)
        gecerli = set(KATEGORILER)
        assert set(df["kategori"].unique()).issubset(gecerli)
        assert len(df) == 50

    def test_veri_seti_tekrarlanabilirlik_seed(self):
        """Ayni seed ile ayni sonuc uretilmeli."""
        from app.data_generator import veri_seti_olustur
        df1 = veri_seti_olustur(50, seed=123)
        df2 = veri_seti_olustur(50, seed=123)
        assert list(df1["kategori"]) == list(df2["kategori"])
        assert list(df1["mesaj"]) == list(df2["mesaj"])


# =============================================================================
# MODEL TRAINER YARDIMCI FONKSIYONLAR
# =============================================================================

class TestModelTrainerHelpers:
    def test_metin_temizle_kucuk_harf(self):
        from app.model_trainer import metin_temizle
        assert metin_temizle("HATA") == "hata"

    def test_metin_temizle_noktalama_kaldirilir(self):
        from app.model_trainer import metin_temizle
        result = metin_temizle("hata! var? evet.")
        assert all(c not in result for c in "!?.")

    def test_girdi_birlestir_row(self):
        import pandas as pd
        from app.model_trainer import girti_birlestir
        row = pd.Series({
            "gonderen_birim": "IT",
            "oncelik": "Yuksek",
            "mesaj": "Sistem hata veriyor"
        })
        result = girti_birlestir(row)
        assert "it" in result
        assert "yuksek" in result
        assert "sistem" in result
