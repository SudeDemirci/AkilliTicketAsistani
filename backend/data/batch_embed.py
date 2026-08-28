
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.ticket_db import ticket_listele, get_cached_embedding, save_cached_embedding
from app.llm_router import get_embedding
from app.predictor import metin_temizle
import time

def run():
    print('Starting batch embedding...')
    tickets = ticket_listele(None, None)
    to_embed = []
    
    for t in tickets:
        metin = metin_temizle(t.get('mesaj', ''))
        t_no = t.get('talep_no')
        if not metin or not t_no:
            continue
            
        if get_cached_embedding(t_no) is None:
            to_embed.append((t_no, metin))
            
    print(f'Need to embed {len(to_embed)} tickets.')
    
    for t_no, metin in to_embed:
        time.sleep(4.1) # Max 15 RPM = 4 seconds per request
        print(f'Embedding {t_no}...')
        vec = get_embedding(metin)
        if vec:
            save_cached_embedding(t_no, vec)
            print(f'Saved {t_no}.')
        else:
            print(f'Failed {t_no}.')

if __name__ == '__main__':
    run()

