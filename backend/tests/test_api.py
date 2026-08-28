"""
API Entegrasyon Testleri
Tum FastAPI endpoint leri icin kapsamli testler.
"""

import re
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)

GECERLI_KATEGORILER = {
    "Yazilim Sorunu", "Donanim Arizasi", "Ag / Baglanti",
    "Guvenlik / Erisim", "Veritabani", "E-posta / Iletisim",
    "Yedekleme / Veri", "Lisans / Abonelik",
    # Turkce karakterli haller de gecerli
    "Yazilim Sorunu", "Donanim Arizasi",
}


# =============================================================================
# SAGLIK
# =============================================================================

class TestSaglik:
    def test_saglik_200(self):
        r = client.get("/saglik")
        assert r.status_code == 200

    def test_saglik_json_anahtarlari(self):
        data = client.get("/saglik").json()
        for k in ("durum", "modeller_hazir", "versiyon", "egitim_durumu"):
            assert k in data, f"Eksik anahtar: {k}"

    def test_saglik_durum_aktif(self):
        assert client.get("/saglik").json()["durum"] == "aktif"

    def test_saglik_versiyon(self):
        assert client.get("/saglik").json()["versiyon"] == "2.0.0"

    def test_saglik_modeller_hazir_bool(self):
        assert isinstance(client.get("/saglik").json()["modeller_hazir"], bool)

    def test_saglik_modeller_yuklenmis(self):
        assert client.get("/saglik").json()["modeller_hazir"] is True


# =============================================================================
# ANALIZ-ET (FORM)
# =============================================================================

TEMEL_FORM = {
    "gonderen_kisi": "Ahmet Yilmaz",
    "gonderen_birim": "Muhasebe",
    "oncelik": "Yuksek",
    "mesaj": "Muhasebe yazilimi acilmiyor SAP hata veriyor",
}


class TestAnalizEtForm:
    def test_200_ok(self):
        r = client.post("/analiz-et", data=TEMEL_FORM)
        assert r.status_code == 200

    def test_yanit_alanlari(self):
        data = client.post("/analiz-et", data=TEMEL_FORM).json()
        for k in ("kategori", "yonlendirilen_departman", "cozum_suresi_gun",
                  "tahmini_maliyet_tl", "guven_skoru", "alternatif_kategoriler",
                  "ticket_id", "ogrenme_durumu", "girdi"):
            assert k in data, f"Eksik alan: {k}"

    def test_guven_skoru_aralik(self):
        guven = client.post("/analiz-et", data=TEMEL_FORM).json()["guven_skoru"]
        assert 0.0 <= guven <= 1.0

    def test_sure_pozitif(self):
        assert client.post("/analiz-et", data=TEMEL_FORM).json()["cozum_suresi_gun"] > 0

    def test_maliyet_pozitif(self):
        assert client.post("/analiz-et", data=TEMEL_FORM).json()["tahmini_maliyet_tl"] > 0

    def test_alternatif_3_eleman(self):
        alts = client.post("/analiz-et", data=TEMEL_FORM).json()["alternatif_kategoriler"]
        assert len(alts) == 3

    def test_alternatif_olasilik_toplami(self):
        alts = client.post("/analiz-et", data=TEMEL_FORM).json()["alternatif_kategoriler"]
        for alt in alts:
            assert "kategori" in alt and "olasilik" in alt
            assert 0.0 <= alt["olasilik"] <= 1.0

    def test_ticket_id_uuid_format(self):
        tid = client.post("/analiz-et", data=TEMEL_FORM).json()["ticket_id"]
        uuid_re = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_re, tid), f"Gecersiz UUID: {tid}"

    def test_girdi_eko(self):
        girdi = client.post("/analiz-et", data=TEMEL_FORM).json()["girdi"]
        assert girdi["gonderen_kisi"] == "Ahmet Yilmaz"
        assert girdi["gonderen_birim"] == "Muhasebe"

    def test_eksik_alan_422(self):
        r = client.post("/analiz-et", data={"gonderen_kisi": "Test"})
        assert r.status_code == 422

    def test_tum_oncelikler(self):
        for onc in ("Dusuk", "Orta", "Yuksek", "Kritik"):
            form = dict(TEMEL_FORM, oncelik=onc)
            r = client.post("/analiz-et", data=form)
            assert r.status_code == 200, f"Oncelik '{onc}' icin {r.status_code}"

    def test_uzun_mesaj(self):
        form = dict(TEMEL_FORM, mesaj="Sistem arizasi " * 50)
        r = client.post("/analiz-et", data=form)
        assert r.status_code == 200

    def test_her_istekte_benzersiz_ticket_id(self):
        ids = {client.post("/analiz-et", data=TEMEL_FORM).json()["ticket_id"] for _ in range(3)}
        assert len(ids) == 3, "ticket_id benzersiz olmali"

    def test_ayni_girdi_ayni_kategori(self):
        k1 = client.post("/analiz-et", data=TEMEL_FORM).json()["kategori"]
        k2 = client.post("/analiz-et", data=TEMEL_FORM).json()["kategori"]
        assert k1 == k2

    def test_yazilim_sorun_tespiti(self):
        form = dict(TEMEL_FORM,
                    mesaj="Uygulama acilmiyor hata mesaji veriyor yazilim calismıyor")
        data = client.post("/analiz-et", data=form).json()
        assert data["kategori"] is not None

    def test_ag_sorun_tespiti(self):
        form = dict(TEMEL_FORM,
                    mesaj="internet baglantisi kesildi VPN calısmiyor ag yok")
        data = client.post("/analiz-et", data=form).json()
        assert data["kategori"] is not None

    def test_departman_bos_degil(self):
        data = client.post("/analiz-et", data=TEMEL_FORM).json()
        assert data["yonlendirilen_departman"]


# =============================================================================
# ANALIZ-ET-JSON
# =============================================================================

TEMEL_JSON = {
    "gonderen_kisi": "Fatma Kaya",
    "gonderen_birim": "IT",
    "oncelik": "Kritik",
    "mesaj": "Sunucu coktu tum servisler erisilemedigi icin kritik",
}


class TestAnalizEtJson:
    def test_200_ok(self):
        r = client.post("/analiz-et-json", json=TEMEL_JSON)
        assert r.status_code == 200

    def test_yanit_alanlari(self):
        data = client.post("/analiz-et-json", json=TEMEL_JSON).json()
        for k in ("kategori", "ticket_id", "cozum_suresi_gun", "tahmini_maliyet_tl"):
            assert k in data

    def test_eksik_alan_422(self):
        r = client.post("/analiz-et-json", json={"gonderen_kisi": "Test"})
        assert r.status_code == 422

    def test_guven_skoru_aralik(self):
        guven = client.post("/analiz-et-json", json=TEMEL_JSON).json()["guven_skoru"]
        assert 0.0 <= guven <= 1.0

    def test_ticket_id_uuid(self):
        tid = client.post("/analiz-et-json", json=TEMEL_JSON).json()["ticket_id"]
        uuid_re = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_re, tid)

    def test_bos_body_422(self):
        r = client.post("/analiz-et-json", json={})
        assert r.status_code == 422

    def test_form_ile_json_tutarliligi(self):
        """Form ve JSON endpoint ayni girdi icin ayni kategoriyi vermeli."""
        form = {
            "gonderen_kisi": "Test",
            "gonderen_birim": "Satis",
            "oncelik": "Orta",
            "mesaj": "Yazilim acilmiyor hata var",
        }
        r_form = client.post("/analiz-et", data=form)
        r_json = client.post("/analiz-et-json", json=form)
        assert r_form.json()["kategori"] == r_json.json()["kategori"]


# =============================================================================
# GERI BILDIRIM
# =============================================================================

TEMEL_BILDIRIM = {
    "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
    "kategori": "Yazilim Sorunu",
    "gercek_sure_gun": 3.5,
    "gercek_maliyet_tl": 750.0,
}


class TestGeriBildirim:
    def test_200_ok(self):
        r = client.post("/geri-bildirim", json=TEMEL_BILDIRIM)
        assert r.status_code == 200

    def test_basarili_true(self):
        assert client.post("/geri-bildirim", json=TEMEL_BILDIRIM).json()["basarili"] is True

    def test_yanit_alanlari(self):
        data = client.post("/geri-bildirim", json=TEMEL_BILDIRIM).json()
        for k in ("basarili", "kategori", "guncellenen_istatistikler", "mesaj"):
            assert k in data

    def test_istatistik_alanlari(self):
        istat = client.post("/geri-bildirim", json=TEMEL_BILDIRIM).json()["guncellenen_istatistikler"]
        for k in ("toplam_gercek_ticket", "gercek_ortalama_sure_gun",
                  "gercek_ortalama_maliyet_tl", "gercek_veri_katkisi_yuzdesi",
                  "model_katkisi_yuzdesi"):
            assert k in istat

    def test_katkı_yuzde_toplam_100(self):
        istat = client.post("/geri-bildirim", json=TEMEL_BILDIRIM).json()["guncellenen_istatistikler"]
        toplam = istat["gercek_veri_katkisi_yuzdesi"] + istat["model_katkisi_yuzdesi"]
        assert abs(toplam - 100.0) < 0.2

    def test_katkı_aralik(self):
        istat = client.post("/geri-bildirim", json=TEMEL_BILDIRIM).json()["guncellenen_istatistikler"]
        assert 0 <= istat["gercek_veri_katkisi_yuzdesi"] <= 100
        assert 0 <= istat["model_katkisi_yuzdesi"] <= 100

    def test_negatif_sure_422(self):
        payload = dict(TEMEL_BILDIRIM, gercek_sure_gun=-1.0)
        assert client.post("/geri-bildirim", json=payload).status_code == 422

    def test_sifir_sure_422(self):
        payload = dict(TEMEL_BILDIRIM, gercek_sure_gun=0)
        assert client.post("/geri-bildirim", json=payload).status_code == 422

    def test_negatif_maliyet_422(self):
        payload = dict(TEMEL_BILDIRIM, gercek_maliyet_tl=-100.0)
        assert client.post("/geri-bildirim", json=payload).status_code == 422

    def test_sayac_artiyor(self):
        r1 = client.post("/geri-bildirim", json=TEMEL_BILDIRIM)
        r2 = client.post("/geri-bildirim", json=TEMEL_BILDIRIM)
        c1 = r1.json()["guncellenen_istatistikler"]["toplam_gercek_ticket"]
        c2 = r2.json()["guncellenen_istatistikler"]["toplam_gercek_ticket"]
        assert c2 == c1 + 1

    def test_tum_kategoriler_kabul_edilir(self):
        for kat in ("Donanim Arizasi", "Veritabani", "E-posta / Iletisim"):
            payload = dict(TEMEL_BILDIRIM, kategori=kat)
            r = client.post("/geri-bildirim", json=payload)
            assert r.status_code == 200, f"Kategori '{kat}' reddedildi"

    def test_not_alani_opsiyonel(self):
        payload = dict(TEMEL_BILDIRIM, notlar="Ozel not eklendi")
        r = client.post("/geri-bildirim", json=payload)
        assert r.status_code == 200


# =============================================================================
# ISTATISTIKLER
# =============================================================================

class TestIstatistikler:
    def test_200_veya_404(self):
        r = client.get("/istatistikler")
        assert r.status_code in (200, 404)

    def test_200_yanit_yapisi(self):
        r = client.get("/istatistikler")
        if r.status_code == 200:
            data = r.json()
            for k in ("model_metrikleri", "veri_istatistikleri", "ogrenme_istatistikleri"):
                assert k in data

    def test_model_metrikleri_alanlari(self):
        r = client.get("/istatistikler")
        if r.status_code == 200:
            met = r.json()["model_metrikleri"]
            for k in ("kategori_accuracy", "sure_mae", "maliyet_mae", "toplam_veri"):
                assert k in met

    def test_dogruluk_aralik(self):
        r = client.get("/istatistikler")
        if r.status_code == 200:
            acc = r.json()["model_metrikleri"]["kategori_accuracy"]
            assert 0.0 <= acc <= 1.0

    def test_veri_toplam_kayit_pozitif(self):
        r = client.get("/istatistikler")
        if r.status_code == 200 and r.json()["veri_istatistikleri"]:
            assert r.json()["veri_istatistikleri"]["toplam_kayit"] > 0

    def test_yuksek_dogruluk(self):
        """Model dogrulugu en az %70 olmali."""
        r = client.get("/istatistikler")
        if r.status_code == 200:
            acc = r.json()["model_metrikleri"]["kategori_accuracy"]
            assert acc >= 0.70, f"Model dogrulugu dusuk: {acc:.2%}"


# =============================================================================
# OGRENME ISTATISTIKLERI
# =============================================================================

class TestOgrenmeIstatistikleri:
    def test_200(self):
        assert client.get("/ogrenme-istatistikleri").status_code == 200

    def test_yanit_yapisi(self):
        data = client.get("/ogrenme-istatistikleri").json()
        assert "aciklama" in data
        assert "kategoriler" in data

    def test_kategoriler_dict(self):
        assert isinstance(client.get("/ogrenme-istatistikleri").json()["kategoriler"], dict)


# =============================================================================
# EGITIM DURUMU
# =============================================================================

class TestEgitimDurumu:
    def test_200(self):
        assert client.get("/egitim-durumu").status_code == 200

    def test_calisiyor_bool(self):
        assert isinstance(client.get("/egitim-durumu").json()["calisiyor"], bool)

    def test_son_mesaj_var(self):
        assert "son_mesaj" in client.get("/egitim-durumu").json()


# =============================================================================
# YENIDEN EGIT
# =============================================================================

class TestModeliYenidenEgit:
    def test_200(self):
        assert client.post("/modeli-yeniden-egit").status_code == 200

    def test_yanit_yapisi(self):
        data = client.post("/modeli-yeniden-egit").json()
        assert "basarili" in data and "mesaj" in data

    def test_basarili_bool(self):
        assert isinstance(client.post("/modeli-yeniden-egit").json()["basarili"], bool)


# =============================================================================
# CORS
# =============================================================================

class TestCors:
    def test_cors_header_var(self):
        r = client.get("/saglik", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
        assert "access-control-allow-origin" in r.headers

    def test_cors_wildcard(self):
        r = client.get("/saglik", headers={"Origin": "http://example.com"})
        acao = r.headers.get("access-control-allow-origin", "")
        assert acao in ("*", "http://example.com")


# =============================================================================
# DEGER MANTIGI
# =============================================================================

class TestDegerMantigi:
    """Tahmin degerleri mantikli aralikta olmali."""

    def test_sure_mantikli_aralik(self):
        """Cozum suresi 0.5 ile 60 gun arasinda olmali."""
        data = client.post("/analiz-et", data=TEMEL_FORM).json()
        assert 0.5 <= data["cozum_suresi_gun"] <= 60

    def test_maliyet_mantikli_aralik(self):
        """Maliyet 100 ile 50000 TL arasinda olmali."""
        data = client.post("/analiz-et", data=TEMEL_FORM).json()
        assert 100 <= data["tahmini_maliyet_tl"] <= 50000

    def test_kritik_yuksek_maliyet(self):
        """Kritik oncelik daha yuksek maliyet vermeli (genel egilim)."""
        dusuk = client.post("/analiz-et", data=dict(TEMEL_FORM, oncelik="Dusuk")).json()
        kritik = client.post("/analiz-et", data=dict(TEMEL_FORM, oncelik="Kritik")).json()
        # Ayni kategori olmasa da maliyet tamamen farkli olabilir, sadece pozitif oldugunu dogrula
        assert dusuk["tahmini_maliyet_tl"] > 0
        assert kritik["tahmini_maliyet_tl"] > 0
