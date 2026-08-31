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

def predict_category_with_llm(gonderen_birim: str, oncelik: str, mesaj: str, ek_icerik: Optional[str] = None) -> str:
    """
    Talebi Gemini 2.5 Flash ile analiz edip en doğru kategoriyi döner.
    API key yoksa veya hata olursa None döner.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Sen bir kurumsal IT Bilet (Ticket) Yönlendirme Uzmanısın.
Görev: Gelen talebin bağlamını anlayarak aşağıdaki kategorilerden en uygun olana atamak.
SADECE kategorinin adını yaz, başka hiçbir kelime, noktalama veya açıklama ekleme.

  Dikkat: Eğer metinde bir uygulamanın (mobil, web vb) içine bir özellik (örneğin e-posta butonu, yeni ekran) eklenmesi isteniyorsa, bu "E-posta / İletişim" DEĞİL, doğrudan "Mobil Uygulama Geliştirme" veya "Yazılım Sorunu"dur. Bağlamı insan gibi analiz et.
  Ek Kural 1: "Uygulamanın rengi değişsin", "arayüz", "tasarım", "buton rengi" gibi UI/UX estetik değişiklikleri kesinlikle "Tasarım / Estetik" olarak sınıflandırılmalıdır.
  Ek Kural 2: Eğer Ek (Dosya) İçeriğinde veya mesajda veritabanı hataları ("HikariPool", "Connection refused", "SQL", "veritabanı", "database") varsa, bu KESİNLİKLE "Veritabanı" olarak sınıflandırılmalıdır. Sadece "Yazılım Sorunu" deyip geçme.

Geçerli Kategoriler:
{chr(10).join(['- ' + k for k in GECERLI_KATEGORILER])}

Gönderen Birim: {gonderen_birim}
Öncelik: {oncelik}
Talep Mesajı: {mesaj}"""
        if ek_icerik:
            prompt += f"\nEk (Dosya) İçeriği:\n{ek_icerik[:1000]}"
            
        prompt += "\nKategori:"
        print(f"--- LLM PROMPT ---\n{prompt}\n------------------", flush=True)
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        cat = response.text.strip()
        print(f"[LLM YANITI] Gemini'nin cevabı: {cat}", flush=True)
        
        # Sonucu temizle ve listeden doğrula
        for vc in GECERLI_KATEGORILER:
            if vc.lower() in cat.lower():
                print(f"[LLM EŞLEŞME] Eşleşen Kategori: {vc}", flush=True)
                return vc
                
        print("[LLM UYARI] Hiçbir geçerli kategori bulunamadı, fallback çalışacak.", flush=True)
        return None
    except Exception as e:
        print(f"[LLM HATA] Gemini API hatası: {e}")
        return None

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
