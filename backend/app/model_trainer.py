"""
Model Eğitim Motoru
TF-IDF + SVC (kategori) + 2x RandomForestRegressor (süre + maliyet)
"""

import os
import sys
import json
import re
import joblib
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    mean_absolute_error,
    r2_score,
)

# Proje kökünden çalıştırılacak
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "tickets.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")


def metin_temizle(metin: str) -> str:
    """Temel metin temizleme: küçük harf, noktalama temizliği."""
    metin = metin.lower().strip()
    metin = re.sub(r"[^\w\s]", " ", metin)
    metin = re.sub(r"\s+", " ", metin)
    return metin


def girti_birlestir(row: pd.Series) -> str:
    """
    4 alanı tek bir zenginleştirilmiş metin olarak birleştirir.
    gonderen_kisi + gonderen_birim + oncelik + mesaj
    """
    parcalar = [
        f"birim:{row.get('gonderen_birim', '')}",
        f"oncelik:{row.get('oncelik', '')}",
        str(row.get("mesaj", "")),
    ]
    return metin_temizle(" ".join(parcalar))


def modelleri_egit(df: pd.DataFrame) -> dict:
    """Tüm modelleri eğitir ve performans metriklerini döndürür."""
    print("[INFO] Ozellik muhendisligi yapiliyor...")
    df["birlesik_metin"] = df.apply(girti_birlestir, axis=1)

    X = df["birlesik_metin"]
    y_kat = df["kategori"]
    y_sure = df["cozum_suresi_gun"]
    y_maliyet = df["maliyet_tl"]

    # Train/test split
    (
        X_train,
        X_test,
        y_kat_train,
        y_kat_test,
        y_sure_train,
        y_sure_test,
        y_mal_train,
        y_mal_test,
    ) = train_test_split(
        X,
        y_kat,
        y_sure,
        y_maliyet,
        test_size=0.2,
        random_state=42,
        stratify=y_kat,
    )

    # ── KATEGORİ MODELİ (TF-IDF + SVC) ──────────────────────────────
    print("[INFO] Kategori modeli (SVC) egitiliyor...")
    kategori_pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=10000,
                    sublinear_tf=True,
                ),
            ),
            ("svc", SVC(kernel="rbf", C=10, gamma="scale", probability=True)),
        ]
    )
    kategori_pipeline.fit(X_train, y_kat_train)
    kat_pred = kategori_pipeline.predict(X_test)
    kat_rapor = classification_report(y_kat_test, kat_pred, output_dict=True)
    print(f"[OK] Kategori dogrulugu: {kat_rapor['accuracy']:.2%}")

    # ── ÇÖZÜM SÜRESİ MODELİ ─────────────────────────────────────────
    print("[INFO] Cozum suresi modeli (RandomForest) egitiliyor...")
    tfidf_sure = TfidfVectorizer(
        ngram_range=(1, 2), max_features=5000, sublinear_tf=True
    )
    X_train_sure = tfidf_sure.fit_transform(X_train)
    X_test_sure = tfidf_sure.transform(X_test)

    sure_model = RandomForestRegressor(
        n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
    )
    sure_model.fit(X_train_sure, y_sure_train)
    sure_pred = sure_model.predict(X_test_sure)
    sure_mae = mean_absolute_error(y_sure_test, sure_pred)
    sure_r2 = r2_score(y_sure_test, sure_pred)
    print(f"[OK] Sure MAE: {sure_mae:.2f} gun, R2: {sure_r2:.3f}")

    # ── MALİYET MODELİ ───────────────────────────────────────────────
    print("[INFO] Maliyet modeli (RandomForest) egitiliyor...")
    tfidf_maliyet = TfidfVectorizer(
        ngram_range=(1, 2), max_features=5000, sublinear_tf=True
    )
    X_train_mal = tfidf_maliyet.fit_transform(X_train)
    X_test_mal = tfidf_maliyet.transform(X_test)

    maliyet_model = RandomForestRegressor(
        n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
    )
    maliyet_model.fit(X_train_mal, y_mal_train)
    mal_pred = maliyet_model.predict(X_test_mal)
    mal_mae = mean_absolute_error(y_mal_test, mal_pred)
    mal_r2 = r2_score(y_mal_test, mal_pred)
    print(f"[OK] Maliyet MAE: {mal_mae:.0f} TL, R2: {mal_r2:.3f}")

    # ── MODELLERİ KAYDET ─────────────────────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(kategori_pipeline, os.path.join(MODEL_DIR, "kategori_model.pkl"))
    joblib.dump(
        {"tfidf": tfidf_sure, "model": sure_model},
        os.path.join(MODEL_DIR, "sure_model.pkl"),
    )
    joblib.dump(
        {"tfidf": tfidf_maliyet, "model": maliyet_model},
        os.path.join(MODEL_DIR, "maliyet_model.pkl"),)

    # Metrik özetini kaydet
    metrikler = {
        "kategori_accuracy": round(kat_rapor["accuracy"], 4),
        "sure_mae": round(float(sure_mae), 2),
        "sure_r2": round(float(sure_r2), 4),
        "maliyet_mae": round(float(mal_mae), 0),
        "maliyet_r2": round(float(mal_r2), 4),
        "toplam_veri": len(df),
        "egitim_tarihi": pd.Timestamp.now().isoformat(),
    }
    with open(os.path.join(MODEL_DIR, "metrikler.json"), "w", encoding="utf-8") as f:
        json.dump(metrikler, f, ensure_ascii=False, indent=2)

    print("\n[OK] Tum modeller basariyla egitildi ve kaydedildi!")
    return metrikler


def ana():
    """Ana eğitim akışı."""
    from app.data_generator import veri_seti_olustur

    # Veri seti yoksa oluştur
    if not os.path.exists(DATA_PATH):
        print("[INFO] Veri seti bulunamadi, sentetik veri uretiliyor...")
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        df = veri_seti_olustur(2000)
        df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
        print(f"[OK] {len(df)} kayit olusturuldu: {DATA_PATH}")
    else:
        print(f"[INFO] Mevcut veri seti yukleniyor: {DATA_PATH}")
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    print(f"[INFO] Toplam veri: {len(df)} satir")
    return modelleri_egit(df)


if __name__ == "__main__":
    sys.path.insert(0, BASE_DIR)
    ana()
