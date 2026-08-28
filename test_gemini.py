import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GECERLI_KATEGORILER = [
    "Yazılım Sorunu",
    "Donanım Arızası",
    "Ağ / Bağlantı",
    "Güvenlik / Erişim",
    "Veritabanı",
    "E-posta / İletişim",
    "Yedekleme / Veri",
    "Lisans / Abonelik",
    "Mobil Uygulama Geliştirme"
]

prompt = f"""Sen bir kurumsal IT Bilet (Ticket) Yönlendirme Uzmanısın.
Görev: Gelen talebin bağlamını anlayarak aşağıdaki kategorilerden en uygun olana atamak.
SADECE kategorinin adını yaz, başka hiçbir kelime, noktalama veya açıklama ekleme.

Dikkat: Eğer metinde bir uygulamanın (mobil, web vb) içine bir özellik (örneğin e-posta butonu, yeni ekran) eklenmesi isteniyorsa, bu "E-posta / İletişim" DEĞİL, doğrudan "Mobil Uygulama Geliştirme" veya "Yazılım Sorunu"dur. Bağlamı insan gibi analiz et.

Geçerli Kategoriler:
{chr(10).join(['- ' + k for k in GECERLI_KATEGORILER])}

Gönderen Birim: Muhasebe
Öncelik: Orta
Talep Mesajı: mobil uygulamanın ana ekranına bir e posta girişi barı eklenmesini istiyorum
Kategori:"""

response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents=prompt,
)
print("GEMINI YANITI: ", response.text)
