import requests
import json
import time

API_BASE = "http://localhost:8000"

SCENARIOS = [
    {
        "gonderen_kisi": "Ahmet Yilmaz",
        "gonderen_birim": "Muhasebe",
        "oncelik": "Yüksek",
        "mesaj": "Sunucu odasında yangın çıktı, hiçbir sisteme erişilemiyor!",
        "expected_kategori": "Donanım Arızası",
        "expected_oncelik": "P1" # or P2 depending on mapping
    },
    {
        "gonderen_kisi": "Ayşe Kaya",
        "gonderen_birim": "İnsan Kaynakları",
        "oncelik": "Orta",
        "mesaj": "Yeni başlayan personel için VPN yetkisi tanımlar mısınız?",
        "expected_kategori": "Güvenlik / Erişim",
        "expected_oncelik": "P4" # Since VPN is routine, impact low, urgency low
    },
    {
        "gonderen_kisi": "Veli Demir",
        "gonderen_birim": "Satış",
        "oncelik": "Yüksek",
        "mesaj": "Sipariş veritabanı bağlantısı koptu, HikariPool hatası alıyoruz, acil müdahale lazım.",
        "expected_kategori": "Veritabanı",
        "expected_oncelik": "P1" # or P2
    },
    {
        "gonderen_kisi": "Fatma Şahin",
        "gonderen_birim": "Pazarlama",
        "oncelik": "Düşük",
        "mesaj": "Mobil uygulamanın ana menüsündeki renk çok soluk, daha yeşil bir ton olabilir mi?",
        "expected_kategori": "Tasarım / Estetik",
        "expected_oncelik": "P4"
    },
    {
        "gonderen_kisi": "Mehmet Can",
        "gonderen_birim": "Lojistik",
        "oncelik": "Orta",
        "mesaj": "Depo yazılımında yeni bir butona basınca donuyor, çok yavaş çalışıyor.",
        "expected_kategori": "Yazılım Sorunu",
        "expected_oncelik": "P2" # or P3
    }
]

print("=== AKILLI TICKET ASISTANI E2E TEST ===")
print("1. Login yapiliyor...")
login_res = requests.post(f"{API_BASE}/login", json={"kullanici_adi": "calisan", "sifre": "123456"})
if login_res.status_code != 200:
    print("HATA: Login basarisiz", login_res.text)
    exit(1)

token = login_res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login Basarili!")

results = []

for idx, sc in enumerate(SCENARIOS):
    print(f"--- TEST {idx+1}: {sc['expected_kategori']} ---")
    
    # Talep Oluştur
    res = requests.post(
        f"{API_BASE}/analiz-et-json",
        json={
            "gonderen_kisi": sc["gonderen_kisi"],
            "gonderen_birim": sc["gonderen_birim"],
            "oncelik": sc["oncelik"],
            "mesaj": sc["mesaj"],
            "talep_turu": "Diger",
            "kullanici_adi": "admin"
        },
        headers=headers
    )
    
    if res.status_code == 200:
        data = res.json()
        talep_no = data.get("talep_no")
        kategori = data.get("kategori")
        sure = data.get("cozum_suresi_gun")
        maliyet = data.get("tahmini_maliyet_tl")
        
        # AI Oncelik parsing
        ai_oncelik = data.get("ai_oncelik", {})
        oncelik_kodu = ai_oncelik.get("kod") if isinstance(ai_oncelik, dict) else "Unknown"
        
        print(f"  [OK] Bilet Oluşturuldu: {talep_no}")
        print(f"  Kategori: {kategori} (Beklenen: {sc['expected_kategori']})")
        print(f"  Öncelik: {oncelik_kodu} (Beklenen: {sc['expected_oncelik']})")
        print(f"  Tahmini Süre: {sure} gün")
        print(f"  Tahmini Maliyet: {maliyet} TL")
        
        # Mesajlaşma (Yorum) Testi
        yorum_res = requests.post(
            f"{API_BASE}/talep/{talep_no}/yorum",
            json={
                "talep_no": talep_no,
                "yazar_adi": "Test Bot",
                "yazar_rol": "Sistem",
                "mesaj": "Sistem test yorumu: Bu bilet basariyla olusturuldu."
            },
            headers=headers
        )
        
        if yorum_res.status_code == 200:
            print("  [OK] Mesaj / Yorum başarıyla eklendi.")
            chat_status = "Başarılı"
        else:
            print(f"  [HATA] Mesaj eklenemedi: {yorum_res.status_code} - {yorum_res.text}")
            chat_status = "Başarısız"
            
        results.append({
            "talep_no": talep_no,
            "mesaj": sc["mesaj"],
            "beklenen_kategori": sc["expected_kategori"],
            "gerceklesen_kategori": kategori,
            "beklenen_oncelik": sc["expected_oncelik"],
            "gerceklesen_oncelik": oncelik_kodu,
            "sure": sure,
            "maliyet": maliyet,
            "chat_status": chat_status
        })
        
    else:
        print(f"  [HATA] Bilet oluşturulamadı: {res.status_code} - {res.text}")

print("\n=== JSON SONUCLAR ===")
with open('test_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Sonuclar test_results.json'a kaydedildi.")
