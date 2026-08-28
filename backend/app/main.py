"""
FastAPI Ana Uygulama
Akillli Ticket Asistani Mikroservisi - v3.0
"""

import os
import sys
import json
import uuid
import asyncio
import io
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.predictor import tahmin_motoru
from app.data_generator import veri_seti_olustur
from app.stats_tracker import geri_bildirim_ekle, tum_istatistikler
from app.ticket_db import (
    ticket_kaydet, ticket_listele, ticket_getir,
    ticket_tamamla, istatistikler as db_istatistikler,
    kullanici_dogrula, kullanici_getir, yorum_ekle, yorumlari_getir
)
from app.priority_scorer import oncelik_hesapla

DATA_PATH = os.path.join(BASE_DIR, "data", "tickets.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

egitim_durumu = {"calisiyor": False, "son_mesaj": "Hazir"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not tahmin_motoru.hazir_mi():
        print("[UYARI] Modeller bulunamadi, ilk egitim baslatiliyor...")
        await asyncio.to_thread(_egitim_yap)
    else:
        print("[OK] Modeller yuklendi, servis hazir.")
    yield


app = FastAPI(
    title="Akillli Ticket Asistani API",
    description="NLP tabanli kurum ici destek talebi analiz mikroservisi",
    version="3.0.0",
    lifespan=lifespan,
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── MODELLER ───────────────────────────────────────────────────────────────────
class LoginGirdi(BaseModel):
    kullanici_adi: str
    sifre: str

class YorumGirdi(BaseModel):
    talep_no: str
    yazar_adi: str
    yazar_rol: str
    mesaj: str

class TicketGirdi(BaseModel):
    gonderen_kisi:  str = Field(..., examples=["Ahmet Yilmaz"])
    gonderen_birim: str = Field(..., examples=["Muhasebe"])
    oncelik:        str = Field(..., examples=["Yuksek"])
    mesaj:          str = Field(..., examples=["Muhasebe yazilimi acilmiyor"])
    talep_turu:     str = Field("Diger", examples=["Bug / Hata"])
    kullanici_adi:  Optional[str] = None


class EgitimYanit(BaseModel):
    basarili: bool
    mesaj:    str
    metrikler: Optional[dict] = None


class GeriBildirimGirdi(BaseModel):
    ticket_id:         str
    kategori:          str
    gercek_sure_gun:   float = Field(..., gt=0)
    gercek_maliyet_tl: float = Field(..., gt=0)
    notlar:            Optional[str] = None


class TamamlaGirdi(BaseModel):
    talep_no:          str = Field(..., examples=["TKT-0001"])
    gercek_sure_gun:   float = Field(..., gt=0, description="Gercekte kac gunde cozuldu")
    gercek_maliyet_tl: float = Field(..., gt=0, description="Gercek maliyet (TL)")


# ── YARDIMCI ─────────────────────────────────────────────────────────────────
def _egitim_yap() -> dict:
    import pandas as pd
    from app.model_trainer import modelleri_egit

    egitim_durumu["calisiyor"] = True
    egitim_durumu["son_mesaj"] = "Egitim baslatildi..."
    try:
        if not os.path.exists(DATA_PATH):
            egitim_durumu["son_mesaj"] = "Sentetik veri uretiliyor..."
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
            df = veri_seti_olustur(2000)
            df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
        else:
            df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

        egitim_durumu["son_mesaj"] = "Modeller egitiliyor..."
        metrikler = modelleri_egit(df)
        tahmin_motoru.yenile()
        egitim_durumu["son_mesaj"] = "Egitim tamamlandi"
        return metrikler
    except Exception as e:
        egitim_durumu["son_mesaj"] = f"Hata: {str(e)}"
        raise
    finally:
        egitim_durumu["calisiyor"] = False


async def _dosya_oku(icerik: bytes, dosya_adi: str) -> str:
    dosya_adi = dosya_adi.lower()
    if dosya_adi.endswith(".pdf"):
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(icerik))
            return " ".join(p.extract_text() or "" for p in reader.pages)[:2000]
        except Exception:
            return ""
    elif dosya_adi.endswith((".txt", ".log", ".csv")):
        try:
            return icerik.decode("utf-8", errors="ignore")[:2000]
        except Exception:
            return ""
    return ""


def _sonuca_oncelik_ekle(sonuc: dict, talep_turu: str, created_at: str = None) -> dict:
    """Analiz sonucuna AI oncelik skoru ekler."""
    oncelik = oncelik_hesapla(
        kategori=sonuc["kategori"],
        talep_turu=talep_turu,
        tahmini_sure_gun=sonuc["cozum_suresi_gun"],
        tahmini_maliyet_tl=sonuc["tahmini_maliyet_tl"],
        created_at=created_at,
    )
    sonuc["ai_oncelik"] = oncelik
    sonuc["talep_turu"] = talep_turu
    return sonuc


def _yeni_veri_kaydet(gonderen_kisi, gonderen_birim, oncelik, mesaj, sonuc):
    import pandas as pd
    try:
        yeni = {
            "gonderen_kisi":  gonderen_kisi,
            "gonderen_birim": gonderen_birim,
            "oncelik":        oncelik,
            "mesaj":          mesaj,
            "kategori":       sonuc["kategori"],
            "cozum_suresi_gun": sonuc["cozum_suresi_gun"],
            "maliyet_tl":     sonuc["tahmini_maliyet_tl"],
        }
        if os.path.exists(DATA_PATH):
            df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
            df = pd.concat([df, pd.DataFrame([yeni])], ignore_index=True)
        else:
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
            df = pd.DataFrame([yeni])
        df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"[UYARI] Veri kaydedilemedi: {e}")


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/saglik", tags=["Sistem"])
async def saglik_kontrolu():
    return {
        "durum": "aktif",
        "modeller_hazir": tahmin_motoru.hazir_mi(),
        "egitim_durumu": egitim_durumu,
        "versiyon": "3.0.0",
    }


@app.get("/istatistikler", tags=["Istatistik"])
async def istatistikler():
    import pandas as pd
    met_path = os.path.join(MODEL_DIR, "metrikler.json")
    if not os.path.exists(met_path):
        raise HTTPException(status_code=404, detail="Modeller henuz egitilmedi.")
    with open(met_path, encoding="utf-8") as f:
        metrikler = json.load(f)
    veri_istat = {}
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
        veri_istat = {
            "toplam_kayit":     len(df),
            "kategori_dagilimi": df["kategori"].value_counts().to_dict(),
            "oncelik_dagilimi":  df["oncelik"].value_counts().to_dict(),
            "ortalama_sure":     round(df["cozum_suresi_gun"].mean(), 2),
            "ortalama_maliyet":  round(df["maliyet_tl"].mean(), 2),
        }
    return {
        "model_metrikleri":    metrikler,
        "veri_istatistikleri": veri_istat,
        "ogrenme_istatistikleri": tum_istatistikler(),
        "ticket_db": db_istatistikler(),
    }


@app.post("/login", tags=["Auth"])
def login(girdi: LoginGirdi):
    print(f"--- LOGIN START: {girdi.kullanici_adi} ---", flush=True)
    import time; t0=time.time()
    user = kullanici_dogrula(girdi.kullanici_adi, girdi.sifre)
    print(f"--- LOGIN DB TOOK: {time.time()-t0}s ---", flush=True)
    if not user:
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı veya şifre")
    print(f"--- LOGIN SUCCESS ---", flush=True)
    return {"token": girdi.kullanici_adi, "user": user} # Simüle edilmiş token

@app.get("/kullanici/{kullanici_adi}", tags=["Auth"])
async def get_kullanici(kullanici_adi: str):
    user = kullanici_getir(kullanici_adi)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user

@app.post("/talep/{talep_no}/yorum", tags=["İletişim"])
async def yorum_gonder(talep_no: str, girdi: YorumGirdi):
    talep = ticket_getir(talep_no)
    if not talep:
        raise HTTPException(status_code=404, detail="Talep bulunamadı")
    yorum = yorum_ekle(talep_no, girdi.yazar_adi, girdi.yazar_rol, girdi.mesaj)
    print(f"[E-POSTA SİMÜLASYONU] '{girdi.yazar_adi}' adlı kullanıcı '{talep_no}' numaralı bilete yorum yaptı. İlgili taraflara mail gönderildi.")
    return yorum

@app.get("/talep/{talep_no}/yorum", tags=["İletişim"])
async def yorum_liste(talep_no: str):
    return yorumlari_getir(talep_no)

@app.post("/analiz-et", tags=["Analiz"])
async def ticket_analiz(
    gonderen_kisi:  str = Form(...),
    gonderen_birim: str = Form(...),
    oncelik:        str = Form(...),
    mesaj:          str = Form(...),
    talep_turu:     str = Form("Diger"),
    kullanici_adi:  Optional[str] = Form(None),
    dosya: Optional[UploadFile] = File(None),
):
    if not tahmin_motoru.hazir_mi():
        raise HTTPException(status_code=503, detail="Modeller hazir degil.")

    ek_icerik = None
    dosya_bilgisi = None
    if dosya and dosya.filename:
        icerik = await dosya.read()
        ek_icerik = await _dosya_oku(icerik, dosya.filename)
        dosya_id = str(uuid.uuid4())[:8]
        hedef_ad = f"{dosya_id}_{dosya.filename}"
        hedef_yol = os.path.join(UPLOAD_DIR, hedef_ad)
        
        with open(hedef_yol, "wb") as f:
            f.write(icerik)
            
        dosya_bilgisi = {
            "dosya_adi": dosya.filename,
            "url": f"/uploads/{hedef_ad}",
            "icerik_uzunlugu": len(ek_icerik) if ek_icerik else 0
        }

    sonuc = tahmin_motoru.tahmin_et(
        gonderen_kisi=gonderen_kisi,
        gonderen_birim=gonderen_birim,
        oncelik=oncelik,
        mesaj=mesaj,
        ek_icerik=ek_icerik,
    )

    if dosya_bilgisi:
        sonuc["yuklenen_dosya"] = dosya_bilgisi

    sonuc["ticket_id"] = str(uuid.uuid4())

    from datetime import datetime as _dt
    created_at = _dt.now().isoformat()
    _sonuca_oncelik_ekle(sonuc, talep_turu, created_at)

    talep_no = ticket_kaydet({
        "ticket_id":           sonuc["ticket_id"],
        "gonderen_kisi":       gonderen_kisi,
        "gonderen_birim":      gonderen_birim,
        "oncelik_girdi":       oncelik,
        "talep_turu":          talep_turu,
        "mesaj":               mesaj,
        "kategori":            sonuc["kategori"],
        "yonlendirilen_departman": sonuc["yonlendirilen_departman"],
        "cozum_suresi_gun":    sonuc["cozum_suresi_gun"],
        "tahmini_maliyet_tl":  sonuc["tahmini_maliyet_tl"],
        "guven_skoru":         sonuc["guven_skoru"],
        "ai_oncelik":          sonuc["ai_oncelik"],
        "yuklenen_dosya":      dosya_bilgisi,
        "kullanici_adi":       kullanici_adi,
    })
    sonuc["talep_no"] = talep_no
    
    print(f"[E-POSTA SİMÜLASYONU] '{gonderen_kisi}' tarafından '{talep_no}' numaralı bilet başarıyla açıldı. 'it_destek@albaraka.local' adresine mail gönderildi.")

    _yeni_veri_kaydet(gonderen_kisi, gonderen_birim, oncelik, mesaj, sonuc)

    return sonuc


@app.post("/analiz-et-json", tags=["Analiz"])
def ticket_analiz_json(girdi: TicketGirdi):
    if not tahmin_motoru.hazir_mi():
        raise HTTPException(status_code=503, detail="Modeller hazir degil.")

    sonuc = tahmin_motoru.tahmin_et(
        gonderen_kisi=girdi.gonderen_kisi,
        gonderen_birim=girdi.gonderen_birim,
        oncelik=girdi.oncelik,
        mesaj=girdi.mesaj,
    )
    sonuc["ticket_id"] = str(uuid.uuid4())
    from datetime import datetime as _dt
    created_at = _dt.now().isoformat()
    _sonuca_oncelik_ekle(sonuc, girdi.talep_turu, created_at)

    talep_no = ticket_kaydet({
        "ticket_id":           sonuc["ticket_id"],
        "gonderen_kisi":       girdi.gonderen_kisi,
        "gonderen_birim":      girdi.gonderen_birim,
        "oncelik_girdi":       girdi.oncelik,
        "talep_turu":          girdi.talep_turu,
        "mesaj":               girdi.mesaj,
        "kategori":            sonuc["kategori"],
        "yonlendirilen_departman": sonuc["yonlendirilen_departman"],
        "cozum_suresi_gun":    sonuc["cozum_suresi_gun"],
        "tahmini_maliyet_tl":  sonuc["tahmini_maliyet_tl"],
        "guven_skoru":         sonuc["guven_skoru"],
        "ai_oncelik":          sonuc["ai_oncelik"],
    })
    sonuc["talep_no"] = talep_no
    return sonuc


@app.get("/talepler", tags=["Biletler"])
def talepler_listele(durum: Optional[str] = None, kullanici_adi: Optional[str] = None):
    """
    Tum talepleri AI oncelik skoruna gore sirali dondurur.
    durum: 'bekliyor' | 'tamamlandi' | None (hepsi)
    kullanici_adi: filtrelemek icin opsiyonel.
    """
    talepler = ticket_listele(kullanici_adi, durum)

    # created_at ile bekleme bonusu guncel hale getirilsin
    # ve aktif biletler icin NLP tabanli emsal analizi hesaplansin
    gecmis_biletler = [t for t in talepler if t.get("durum") == "tamamlandi"]

    for t in talepler:
        guncel = oncelik_hesapla(
            kategori=t.get("kategori", ""),
            talep_turu=t.get("talep_turu", "Diger"),
            tahmini_sure_gun=t.get("cozum_suresi_gun", 5),
            tahmini_maliyet_tl=t.get("tahmini_maliyet_tl", 500),
            created_at=t.get("created_at"),
        )
        t["ai_oncelik"] = guncel

        # NLP Emsal Analizi sadece bekleyen/aktif biletler için hesaplansın
        if t.get("durum") != "tamamlandi" and tahmin_motoru.hazir_mi():
            emsal_sonuc = tahmin_motoru.emsal_bul(
                hedef_bilet=t,
                gecmis_biletler=gecmis_biletler,
                limit=15,
                min_sim=0.65
            )
            t["emsal_analizi"] = emsal_sonuc

    # Oncelik koduna gore sirala: P1 > P2 > P3 > P4, esit skor ise sure
    oncelik_siralama = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    talepler.sort(key=lambda t: (
        oncelik_siralama.get(t["ai_oncelik"]["kod"], 4),
        -t["ai_oncelik"]["skor"],
        t.get("created_at", ""),
    ))

    # Ozet istatistik
    ozet = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "toplam": len(talepler)}
    for t in talepler:
        kod = t["ai_oncelik"]["kod"]
        if kod in ozet:
            ozet[kod] += 1

    return {"talepler": talepler, "ozet": ozet}


@app.get("/talep/{talep_no}", tags=["Talepler"])
async def talep_getir(talep_no: str):
    t = ticket_getir(talep_no)
    if not t:
        raise HTTPException(status_code=404, detail=f"{talep_no} bulunamadi.")
    return t


@app.post("/talep-tamamla", tags=["Talepler"])
async def talep_tamamla_endpoint(girdi: TamamlaGirdi):
    """
    Talep tamamlandi olarak isaretlenir.
    Gercek sure ve maliyet yigilimli ogrenmede kullanilir.
    """
    t = ticket_getir(girdi.talep_no)
    if not t:
        raise HTTPException(status_code=404, detail=f"{girdi.talep_no} bulunamadi.")
    if t["durum"] == "tamamlandi":
        raise HTTPException(status_code=400, detail="Talep zaten tamamlandi.")

    # Yigilimli ogrenmeye ekle
    istat = geri_bildirim_ekle(
        kategori=t["kategori"],
        gercek_sure=girdi.gercek_sure_gun,
        gercek_maliyet=girdi.gercek_maliyet_tl,
    )

    # DB guncelle
    guncellenmis = ticket_tamamla(
        talep_no=girdi.talep_no,
        gercek_sure=girdi.gercek_sure_gun,
        gercek_maliyet=girdi.gercek_maliyet_tl,
    )

    from app.stats_tracker import PRIOR_WEIGHT
    count = istat["count"]
    alpha = min(1.0, count / PRIOR_WEIGHT)

    return {
        "basarili": True,
        "talep_no": girdi.talep_no,
        "kategori": t["kategori"],
        "gercek_sure_gun": girdi.gercek_sure_gun,
        "gercek_maliyet_tl": girdi.gercek_maliyet_tl,
        "ogrenme": {
            "toplam_gercek_ticket": count,
            "gercek_veri_katkisi": round(alpha * 100, 1),
            "model_katkisi": round((1 - alpha) * 100, 1),
        },
        "mesaj": (
            f"'{t['kategori']}' kategorisi guncellendi. "
            f"{count} gercek veriden %{round(alpha * 100, 1)} oraninda ogreniliyor."
        ),
    }


@app.post("/geri-bildirim", tags=["Surekli Ogrenme"])
async def geri_bildirim_al(girdi: GeriBildirimGirdi):
    istat = geri_bildirim_ekle(
        kategori=girdi.kategori,
        gercek_sure=girdi.gercek_sure_gun,
        gercek_maliyet=girdi.gercek_maliyet_tl,
    )
    from app.stats_tracker import PRIOR_WEIGHT
    count = istat["count"]
    alpha = min(1.0, count / PRIOR_WEIGHT)
    return {
        "basarili": True,
        "ticket_id": girdi.ticket_id,
        "kategori": girdi.kategori,
        "guncellenen_istatistikler": {
            "toplam_gercek_ticket":    count,
            "gercek_ortalama_sure_gun":    round(istat["sure_mean"], 1) if istat["sure_mean"] else None,
            "gercek_ortalama_maliyet_tl":  round(istat["maliyet_mean"], 0) if istat["maliyet_mean"] else None,
            "gercek_veri_katkisi_yuzdesi": round(alpha * 100, 1),
            "model_katkisi_yuzdesi":       round((1 - alpha) * 100, 1),
        },
        "mesaj": (
            f"Tesekkurler! '{girdi.kategori}' icin {count} gercek veri var. "
            f"Tahminlerin %{round(alpha * 100, 1)} gercek veriye dayanıyor."
        ),
    }


@app.get("/ogrenme-istatistikleri", tags=["Surekli Ogrenme"])
async def ogrenme_istatistikleri():
    return {"aciklama": "Kategori basina gercek veri birikimi.", "kategoriler": tum_istatistikler()}


@app.post("/modeli-yeniden-egit", tags=["MLOps"], response_model=EgitimYanit)
async def modeli_yeniden_egit(background_tasks: BackgroundTasks):
    if egitim_durumu["calisiyor"]:
        return EgitimYanit(basarili=False, mesaj="Egitim zaten devam ediyor.")
    background_tasks.add_task(_egitim_yap_arka_plan)
    return EgitimYanit(basarili=True, mesaj="Egitim arka planda basladi. /saglik ile takip edin.")


@app.get("/egitim-durumu", tags=["MLOps"])
async def egitim_durumu_kontrol():
    return egitim_durumu


def _egitim_yap_arka_plan():
    try:
        _egitim_yap()
    except Exception as e:
        print(f"[HATA] Egitim hatasi: {e}")
