import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Geçerli Kategoriler Listesi
GECERLI_KATEGORILER = [
    "Yazılım Sorunu",
    "Donanım Arızası",
    "Ağ / Bağlantı",
    "Güvenlik / Erişim",
    "Veritabanı",
    "E-posta / İletişim",
    "Yedekleme / Veri",
    "Lisans / Abonelik",
    "Mobil Uygulama Geliştirme",
    "Tasarım / Estetik"
]

def predict_with_llm(gonderen_birim: str, oncelik: str, mesaj: str, ek_icerik: Optional[str] = None) -> dict:
    """
    Talebi Gemini ile analiz edip Kategori + Etki + Aciliyet döner.
    ITIL Impact/Urgency Matrix için gerekli 3 değeri tek promptta alırız.
    Hata olursa {} döner → fallback devreye girer.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {}
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Sen bir kurumsal IT Hizmet Yönetimi (ITSM) uzmanısın.
Aşağıdaki IT destek talebini analiz et ve tam olarak 3 satır yaz:

Satır 1 - KATEGORİ: Talebin IT kategorisi (listeden seç)
Satır 2 - ETKİ: Kaç kişiyi/birimi etkiliyor? (Yüksek / Orta / Düşük)
Satır 3 - ACİLİYET: Ne kadar acil? (Yüksek / Orta / Düşük)

ETKİ KURALLARI (kaç kişi/süreç etkileniyor?):
- Yüksek: Tüm şirket/birim durdu, üretim/müşteri etkilendi, veri kaybı riski var
          ÖRNEK: Sunucu çöktü, internet kesildi, veritabanı erişilemiyor
- Orta:   Birden fazla kişi etkilendi ama iş tamamen durmadı
          ÖRNEK: Departman yazılımı hatalı çalışıyor, mail geliyor ama yavaş
- Düşük:  Sadece 1 kişi etkilendi, bireysel/rutin talep
          ÖRNEK: Şifre sıfırlama, klasör izni, donanım isteği, lisans yenileme

ACİLİYET KURALLARI (IT yöneticisi bakışıyla — kullanıcının "acil" hissi DEĞİL!):
- Yüksek: Şu an çözülmezse iş DURUR, şirket zarar görür. SLA < 4 saat
          ÖRNEK: Sunucu çöktü, veritabanı erişilemiyor, internet kesildi
- Orta:   Bu hafta içinde çözülmeli, gecikirse iş yavaşlar. SLA < 24 saat  
          ÖRNEK: Yazılım hatası, e-posta sorunu, backup hatası
- Düşük:  Standart prosedürle çözülür, iş devam eder. SLA < 5 gün
          ÖRNEK: Şifre sıfırlama (kullanıcı başka yollarla çalışabilir),
                 lisans yenileme, yeni ekipman talebi, klasör izni

KATEGORİ LİSTESİ:
{chr(10).join(['- ' + k for k in GECERLI_KATEGORILER])}

KATEGORİ KURALLARI:
- UI/UX değişikliği, renk, tasarım → Tasarım / Estetik
- database, SQL, connection refused, HikariPool → Veritabanı
- Uygulama içine özellik ekleme → Yazılım Sorunu
- Şifre sıfırlama, klasör izni, VPN erişimi → Güvenlik / Erişim

Gönderen Birim: {gonderen_birim}
Kullanıcının Belirttiği Öncelik: {oncelik}
Talep Mesajı: {mesaj}"""

        if ek_icerik:
            prompt += f"\nEk Dosya İçeriği:\n{ek_icerik[:1000]}"
            
        prompt += "\n\nYANIT (sadece 3 satır):"
        print(f"--- LLM PROMPT ---\n{prompt}\n------------------", flush=True)
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        raw = response.text.strip()
        print(f"[LLM YANITI] Gemini: {raw}", flush=True)
        
        def normalize(s):
            """Türkçe karakterleri ASCII'ye çevir, küçük harf yap."""
            return (s.lower()
                .replace("ü", "u").replace("ö", "o").replace("ç", "c")
                .replace("ş", "s").replace("ğ", "g").replace("ı", "i")
                .replace("İ", "i").replace("Ü", "u").replace("Ö", "o")
                .replace("Ç", "c").replace("Ş", "s").replace("Ğ", "g"))

        def deger_bul(text):
            """Bir satırdan Yüksek/Orta/Düşük değerini çıkar."""
            n = normalize(text)
            if "yuksek" in n: return "Yüksek"
            if "orta"   in n: return "Orta"
            if "dusuk"  in n: return "Düşük"
            return None

        # Yanıtı parse et - hem etiket bazlı hem pozisyonel
        result = {}
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        
        for line in lines:
            n = normalize(line)
            # Kategori
            for vc in GECERLI_KATEGORILER:
                if normalize(vc) in n:
                    result["kategori"] = vc
                    break
            # Etki satırı (etiket bazlı)
            if "etki" in n and "acil" not in n:
                val = deger_bul(line)
                if val:
                    result["etki"] = val
            # Aciliyet satırı (etiket bazlı)
            if "acil" in n:
                val = deger_bul(line)
                if val:
                    result["aciliyet"] = val

        # Etiket bulunamadıysa pozisyonel parse (satır 2 = etki, satır 3 = aciliyet)
        if "etki" not in result or "aciliyet" not in result:
            non_cat_lines = [l for l in lines if not any(normalize(vc) in normalize(l) for vc in GECERLI_KATEGORILER)]
            if len(non_cat_lines) >= 2 and "etki" not in result:
                val = deger_bul(non_cat_lines[0])
                if val: result["etki"] = val
            if len(non_cat_lines) >= 2 and "aciliyet" not in result:
                val = deger_bul(non_cat_lines[1] if len(non_cat_lines) > 1 else non_cat_lines[0])
                if val: result["aciliyet"] = val

        print(f"[LLM PARSE] Sonuç: {result}", flush=True)
        return result
    except Exception as e:
        print(f"[LLM HATA] Gemini API hatası: {e}")
        # SMART LOCAL FALLBACK: API kotası dolduğunda eski ML modelinin saçmalamaması için
        m = mesaj.lower()
        if "şifre" in m or "sifre" in m or "vpn" in m:
            return {"kategori": "Güvenlik / Erişim", "etki": "Düşük", "aciliyet": "Düşük"}
        if "ağ bağlantısı" in m or "internet" in m or "ag baglantisi" in m:
            return {"kategori": "Ağ / Bağlantı", "etki": "Yüksek", "aciliyet": "Yüksek"}
        if "renk" in m or "yeşil" in m or "sarı" in m or "tasarım" in m or "buton" in m:
            return {"kategori": "Tasarım / Estetik", "etki": "Düşük", "aciliyet": "Düşük"}
        if "sunucu" in m or "çöktü" in m or "coktu" in m:
            return {"kategori": "Donanım Arızası", "etki": "Yüksek", "aciliyet": "Yüksek"}
        if "veritaban" in m or "database" in m or "sql" in m:
            return {"kategori": "Veritabanı", "etki": "Yüksek", "aciliyet": "Yüksek"}
        if "ekle" in m or "istiyorum" in m or "özellik" in m or "ozellik" in m:
            return {"kategori": "Yazılım Sorunu", "etki": "Düşük", "aciliyet": "Düşük"}
        if "yavaş" in m or "yavas" in m:
            return {"kategori": "Yazılım Sorunu", "etki": "Orta", "aciliyet": "Orta"}
        return {}


# Geriye dönük uyumluluk için eski fonksiyonu wrapper olarak tut
def predict_category_with_llm(gonderen_birim: str, oncelik: str, mesaj: str, ek_icerik: Optional[str] = None) -> str:
    result = predict_with_llm(gonderen_birim, oncelik, mesaj, ek_icerik)
    return result.get("kategori", None)

import time
_embedding_cooldown_until = 0

def get_embedding(text: str) -> list[float]:
    """
    Verilen metin için Gemini text-embedding-004 modelini kullanarak vektör döner.
    Hata olursa boş liste döner.
    """
    global _embedding_cooldown_until
    if time.time() < _embedding_cooldown_until:
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not text:
        return []
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model='gemini-embedding-2',
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"[EMBEDDING HATA] {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            _embedding_cooldown_until = time.time() + 60
        return []
