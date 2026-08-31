"""
Tahmin Motoru
Yüklenmiş modeller üzerinden gerçek zamanlı tahmin yapar.
Stats tracker ile gerçek şirket verisi blended tahmine katılır.
"""

import os
import re
import json
import joblib
import numpy as np
from typing import Optional
from app.stats_tracker import blended_tahmin

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")


def metin_temizle(metin: str) -> str:
    metin = metin.lower().strip()
    metin = re.sub(r"[^\w\s]", " ", metin)
    metin = re.sub(r"\s+", " ", metin)
    return metin


def girti_birlestir(
    gonderen_birim: str,
    oncelik: str,
    mesaj: str,
    ek_icerik: Optional[str] = None,
) -> str:
    parcalar = [
        f"birim:{gonderen_birim}",
        f"oncelik:{oncelik}",
        mesaj,
    ]
    if ek_icerik:
        parcalar.append(ek_icerik[:2000])  # Dosya içeriği max 2000 karakter
    return metin_temizle(" ".join(parcalar))


class TahminMotoru:
    """Tüm AI modellerini yükler ve tahmin yapar."""

    def __init__(self):
        self.kategori_pipeline = None
        self.sure_bundle = None
        self.maliyet_bundle = None
        self.metrikler = {}
        self.embedding_model = None
        self._yukle()

    def _yukle(self):
        """Disk'ten modelleri yükle (varsa)."""
        kat_path = os.path.join(MODEL_DIR, "kategori_model.pkl")
        sure_path = os.path.join(MODEL_DIR, "sure_model.pkl")
        mal_path = os.path.join(MODEL_DIR, "maliyet_model.pkl")
        met_path = os.path.join(MODEL_DIR, "metrikler.json")

        self.sentetik_biletler = []

        if all(os.path.exists(p) for p in [kat_path, sure_path, mal_path]):
            self.kategori_pipeline = joblib.load(kat_path)
            self.sure_bundle = joblib.load(sure_path)
            self.maliyet_bundle = joblib.load(mal_path)
            if os.path.exists(met_path):
                with open(met_path, encoding="utf-8") as f:
                    self.metrikler = json.load(f)
            try:
                # We just check if it's importable, we will instantiate it lazily in emsal_bul
                import sentence_transformers
                self.has_sentence_transformers = True
            except Exception as e:
                self.has_sentence_transformers = False
                print(f"[UYARI] Embedding modeli yüklenemedi: {e}")
            return True
        return False

    def hazir_mi(self) -> bool:
        return self.kategori_pipeline is not None

    def tahmin_et(
        self,
        gonderen_kisi: str,
        gonderen_birim: str,
        oncelik: str,
        mesaj: str,
        ek_icerik: Optional[str] = None,
    ) -> dict:
        if not self.hazir_mi():
            raise RuntimeError("Modeller henüz yüklenmedi. Lütfen önce eğitin.")

        # Birleşik metin hazırla
        birlesik = girti_birlestir(gonderen_birim, oncelik, mesaj, ek_icerik)

        # Kategori tahmini
        # Önce yeni nesil LLM (Gemini) ile tahmin etmeyi deniyoruz.
        from app.llm_router import predict_category_with_llm
        llm_kategori = predict_category_with_llm(gonderen_birim, oncelik, mesaj)
        
        # Olasılıklar vs ML modelinden hesaplanmaya devam ediyor
        proba = self.kategori_pipeline.predict_proba([birlesik])[0]
        siniflar = self.kategori_pipeline.classes_
        
        if llm_kategori:
            kategori = llm_kategori
            guven_skoru = 0.99  # LLM kararlarına yüksek güven veriyoruz
        else:
            kategori = self.kategori_pipeline.predict([birlesik])[0]
            guven_skoru = float(max(proba))

        # Top-3 kategori (ML modeline göre alternatifler)
        top3_idx = np.argsort(proba)[::-1][:3]
        alternatif_kategoriler = [
            {"kategori": siniflar[i], "olasilik": round(float(proba[i]), 3)}
            for i in top3_idx
        ]

        # Çözüm süresi tahmini (model)
        X_sure = self.sure_bundle["tfidf"].transform([birlesik])
        sure_model = float(self.sure_bundle["model"].predict(X_sure)[0])
        sure_model = max(0.5, round(sure_model, 1))

        # Maliyet tahmini (model)
        X_mal = self.maliyet_bundle["tfidf"].transform([birlesik])
        maliyet_model = float(self.maliyet_bundle["model"].predict(X_mal)[0])
        maliyet_model = max(100, round(maliyet_model, 0))

        # Blended tahmin: model + gerçek şirket istatistikleri
        sure_tahmin, maliyet_tahmin, ogrenme_meta = blended_tahmin(
            kategori=kategori,
            model_sure=sure_model,
            model_maliyet=maliyet_model,
        )

        # Departman yönlendirme haritası (Dinamik JSON)
        routing_file = os.path.join(BASE_DIR, "department_routing.json")
        DEPARTMAN_HARITASI = {}
        try:
            if os.path.exists(routing_file):
                with open(routing_file, "r", encoding="utf-8") as f:
                    DEPARTMAN_HARITASI = json.load(f)
        except Exception:
            pass
            
        default_dept = DEPARTMAN_HARITASI.get("_default", "Genel IT Destek")
        yonlendir = DEPARTMAN_HARITASI.get(kategori, default_dept)

        return {
            "kategori": kategori,
            "yonlendirilen_departman": yonlendir,
            "cozum_suresi_gun": sure_tahmin,
            "tahmini_maliyet_tl": maliyet_tahmin,
            "guven_skoru": round(guven_skoru, 3),
            "alternatif_kategoriler": alternatif_kategoriler,
            "ogrenme_durumu": ogrenme_meta,
            "girdi": {
                "gonderen_kisi": gonderen_kisi,
                "gonderen_birim": gonderen_birim,
                "oncelik": oncelik,
                "mesaj": mesaj,
            },
        }

    def emsal_bul(self, hedef_bilet: dict, gecmis_biletler: list, limit: int = 15, min_sim: float = 0.60) -> Optional[dict]:
        """
        Geçmiş tamamlanmış biletler arasından anlamsal olarak en çok benzeyenleri bulur.
        Yüksek hız ve güvenilirlik için TF-IDF tabanlı arama kullanılır.
        Sadece kullanıcıların sisteme girdiği ve tamamladığı gerçek biletler aranır.
        """
        tum_gecmis = gecmis_biletler
        if not tum_gecmis:
            return None

        import os
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        def get_tam_metin(bilet: dict) -> str:
            metin = str(bilet.get("mesaj", ""))
            dosya_bilgisi = bilet.get("yuklenen_dosya")
            if dosya_bilgisi and isinstance(dosya_bilgisi, dict):
                url = dosya_bilgisi.get("url")
                dosya_adi = dosya_bilgisi.get("dosya_adi", "")
                if url and dosya_adi.lower().endswith((".txt", ".log", ".csv", ".json")):
                    filename = os.path.basename(url)
                    dosya_yolu = os.path.join(ROOT_DIR, "data", "uploads", filename)
                    if os.path.exists(dosya_yolu):
                        try:
                            with open(dosya_yolu, "r", encoding="utf-8", errors="ignore") as f:
                                ekin_icerigi = f.read()[:5000] # İlk 5000 karakteri analiz et
                                metin += " " + ekin_icerigi
                        except Exception:
                            pass
            return metin

        hedef_metin = metin_temizle(get_tam_metin(hedef_bilet))
        if not hedef_metin:
            return None

        from sklearn.metrics.pairwise import cosine_similarity
        
        adaylar = []
        aday_indexleri = []
        
        for i, b in enumerate(tum_gecmis):
            t_no = b.get("talep_no")
            if t_no == hedef_bilet.get("talep_no"):
                continue
            if b.get("durum") != "tamamlandi":
                continue
            metin = metin_temizle(get_tam_metin(b))
            if not metin:
                continue
            adaylar.append(metin)
            aday_indexleri.append(i)
            
        if not adaylar:
            return None
            
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Use the existing TF-IDF vectorizer if available, or create a quick local one
            if getattr(self, 'sure_bundle', None) and 'tfidf' in self.sure_bundle:
                tfidf = self.sure_bundle['tfidf']
                hedef_vec = tfidf.transform([hedef_metin])
                aday_vec = tfidf.transform(adaylar)
            else:
                tfidf = TfidfVectorizer(max_features=1000)
                tum_metinler = adaylar + [hedef_metin]
                tum_vec = tfidf.fit_transform(tum_metinler)
                aday_vec = tum_vec[:-1]
                hedef_vec = tum_vec[-1]
                
            skorlar = cosine_similarity(hedef_vec, aday_vec)[0]
        except Exception as e:
            print(f"[HATA] Semantic Search başarısız: {e}")
            return None
        
        # TF-IDF benzerlik skorları için eşiği 0.25'e düşürüyoruz. 
        # Çünkü TF-IDF skorları kelime bazlı olduğu için yoğun embeddinglere göre daha düşüktür.
        guncel_min_sim = 0.25
        
        top_indexler = []
        for j, skor in enumerate(skorlar):
            if skor >= guncel_min_sim:
                top_indexler.append((j, float(skor)))
                
        top_indexler.sort(key=lambda x: x[1], reverse=True)
        top_indexler = top_indexler[:limit]
        
        if not top_indexler:
            return None

        toplam_sure = 0.0
        toplam_maliyet = 0.0
        toplam_benzerlik = 0.0
        benzer_vakalar = []

        for k, (j, skor) in enumerate(top_indexler):
            bilet = tum_gecmis[aday_indexleri[j]]
            toplam_sure += float(bilet.get("gercek_sure_gun") or 0.0)
            toplam_maliyet += float(bilet.get("gercek_maliyet_tl") or 0.0)
            toplam_benzerlik += skor
            
            # En çok benzeyen ilk 3 vakayı listeye ekle
            if k < 3:
                benzer_vakalar.append({
                    "talep_no": bilet.get("talep_no"),
                    "mesaj": metin_temizle(bilet.get("mesaj", ""))[:80] + "...", # Kısa özet
                    "benzerlik": round(skor * 100, 1),
                    "sure": bilet.get("gercek_sure_gun"),
                    "maliyet": bilet.get("gercek_maliyet_tl")
                })

        adet = len(top_indexler)
        return {
            "adet": adet,
            "ortalama_sure_gun": round(toplam_sure / adet, 1),
            "ortalama_maliyet_tl": round(toplam_maliyet / adet, 0),
            "ortalama_benzerlik": round((toplam_benzerlik / adet) * 100, 1),
            "benzer_vakalar": benzer_vakalar
        }

    def yenile(self):
        """Modelleri diskten yeniden yükle."""
        return self._yukle()


# Global singleton
tahmin_motoru = TahminMotoru()
