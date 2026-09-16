"""
Eski biletleri LLM ile yeniden siniflandiran batch script.
Sadece llm_etki/llm_aciliyet NULL olan (ITIL oncesi) biletleri gunceller.
"""
import sys, os, json, time
sys.path.insert(0, '/app')

from app.ticket_db import _get_connection, _lock
from app.llm_router import predict_with_llm

def reklasifiye_et():
    conn = _get_connection()
    c = conn.cursor()
    
    # llm_etki NULL olan eski biletleri getir (bekliyor durumundakiler)
    c.execute("""
        SELECT talep_no, gonderen_birim, oncelik, mesaj, kategori 
        FROM talepler 
        WHERE (llm_etki IS NULL OR llm_aciliyet IS NULL)
        AND durum = 'bekliyor'
        ORDER BY talep_no ASC
    """)
    eski_biletler = c.fetchall()
    conn.close()
    
    print(f"[BATCH] {len(eski_biletler)} eski bilet yeniden siniflandirilacak...", flush=True)
    
    for bilet in eski_biletler:
        talep_no = bilet['talep_no']
        mesaj = bilet['mesaj'] or ''
        birim = bilet['gonderen_birim'] or ''
        oncelik = bilet['oncelik'] or 'Orta'
        eski_kategori = bilet['kategori'] or ''
        
        print(f"[BATCH] Analiz ediliyor: {talep_no} | {mesaj[:50]}", flush=True)
        
        try:
            sonuc = predict_with_llm(birim, oncelik, mesaj)
            
            yeni_kategori = sonuc.get('kategori') or eski_kategori
            llm_etki     = sonuc.get('etki')
            llm_aciliyet = sonuc.get('aciliyet')
            
            if not llm_etki or not llm_aciliyet:
                print(f"  [UYARI] LLM eksik deger donurdu, atlanıyor.", flush=True)
                time.sleep(1)
                continue
            
            # DB guncelle
            conn2 = _get_connection()
            c2 = conn2.cursor()
            c2.execute("""
                UPDATE talepler 
                SET kategori = ?, llm_etki = ?, llm_aciliyet = ?
                WHERE talep_no = ?
            """, (yeni_kategori, llm_etki, llm_aciliyet, talep_no))
            conn2.commit()
            conn2.close()
            
            print(f"  [OK] {talep_no}: {eski_kategori} -> {yeni_kategori} | Etki:{llm_etki} Acil:{llm_aciliyet}", flush=True)
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"  [HATA] {talep_no}: {e}", flush=True)
            time.sleep(2)
    
    print("[BATCH] Tamamlandi!", flush=True)

if __name__ == '__main__':
    reklasifiye_et()
