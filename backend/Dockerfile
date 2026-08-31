# Akıllı Ticket Asistanı — Backend
FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
# Uygulama dosyaları
COPY . .

# Model ve veri dizinleri
RUN mkdir -p models data

# İlk eğitim (build sırasında)
RUN python -c "import sys, os; sys.path.insert(0, '/app'); \
from app.data_generator import veri_seti_olustur; \
import pandas as pd; \
os.makedirs('data', exist_ok=True); \
df = veri_seti_olustur(2000); \
df.to_csv('data/tickets.csv', index=False, encoding='utf-8-sig'); \
print('Veri olusturuldu: {} satir'.format(len(df)))"

RUN python -c "import sys, os; sys.path.insert(0, '/app'); \
import pandas as pd; \
from app.model_trainer import modelleri_egit; \
df = pd.read_csv('data/tickets.csv', encoding='utf-8-sig'); \
modelleri_egit(df); \
print('Modeller egitildi!')"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
