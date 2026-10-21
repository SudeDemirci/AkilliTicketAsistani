import requests
import json
import time

API_URL = "http://localhost:8000"

def run_tests():
    print("1. Sisteme 'calisan' hesabi ile giris yapiliyor...")
    res = requests.post(f"{API_URL}/login", json={"kullanici_adi": "calisan", "sifre": "1234"})
    if res.status_code != 200:
        print("Login basarisiz!", res.text)
        return
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Giris basarili, JWT alindi.\n")

    test_tickets = [
        {
            "gonderen_kisi": "Ahmet Calisan",
            "gonderen_birim": "Muhasebe",
            "oncelik": "Orta",
            "mesaj": "Muhasebe yazilimina giris yapamiyorum, 'Database connection refused' diye kirmizi bir hata veriyor. Acil bakabilir misiniz?",
            "talep_turu": "Hata / Bug"
        },
        {
            "gonderen_kisi": "Ayse Yilmaz",
            "gonderen_birim": "IK",
            "oncelik": "Orta",
            "mesaj": "Yeni ise baslayan personellerimiz icin 3 adet yeni laptop alinmasi gerekiyor. Ozellikleri ekte belirttim.",
            "talep_turu": "Donanim"
        },
        {
            "gonderen_kisi": "Mehmet Demir",
            "gonderen_birim": "Satis",
            "oncelik": "Dusuk",
            "mesaj": "Ortak ag uzerindeki Satis_Raporlari_2026 klasorune erisim iznimin verilmesini talep ediyorum.",
            "talep_turu": "Erisim Sorunu"
        }
    ]

    for i, t in enumerate(test_tickets):
        print(f"--- TEST {i+1}: {t['talep_turu']} ---")
        print(f"Mesaj: {t['mesaj']}")
        print("API'ye gonderiliyor...")
        
        # We must use 'data' for Form fields in requests
        res = requests.post(f"{API_URL}/analiz-et", data=t, headers=headers)
        if res.status_code == 200:
            sonuc = res.json()
            print(f">>> Talep No: {sonuc.get('talep_no')}")
            print(f">>> Kategori: {sonuc['kategori']}")
            print(f">>> Atanan Departman: {sonuc.get('yonlendirilen_departman', 'Yok')}")
            print(f">>> AI Oncelik: {sonuc['ai_oncelik']['kod']} ({sonuc['ai_oncelik']['etiket']})")
        else:
            print("HATA:", res.status_code, res.text)
        print("\n")
        time.sleep(1)

if __name__ == '__main__':
    run_tests()
