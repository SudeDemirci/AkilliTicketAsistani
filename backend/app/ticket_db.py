"""
Ticket Veritabanı (SQLite tabanlı)
Her talep TKT-0001 formatında numaralanır.
Durum: bekliyor / tamamlandi
"""

import os
import json
import sqlite3
import threading
from datetime import datetime
from typing import Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DB_PATH = os.path.join(BASE_DIR, "data", "tickets_db.json")
SQLITE_DB_PATH = os.path.join(BASE_DIR, "data", "tickets.db")

_lock = threading.Lock()

def _get_connection():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_connection()
    c = conn.cursor()
    # Talepler Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS talepler (
            talep_no TEXT PRIMARY KEY,
            gonderen_kisi TEXT,
            gonderen_birim TEXT,
            oncelik TEXT,
            mesaj TEXT,
            kategori TEXT,
            talep_turu TEXT,
            cozum_suresi_gun REAL,
            maliyet_tl REAL,
            durum TEXT,
            created_at TEXT,
            tamamlandi_at TEXT,
            gercek_sure_gun REAL,
            gercek_maliyet_tl REAL,
            ai_oncelik TEXT,
            yuklenen_dosya TEXT,
            kullanici_adi TEXT
        )
    ''')
    
    # Kullanıcılar Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            kullanici_adi TEXT PRIMARY KEY,
            sifre TEXT,
            ad_soyad TEXT,
            rol TEXT,
            birim TEXT
        )
    ''')
    
    # Yorumlar Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS yorumlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            talep_no TEXT,
            yazar_adi TEXT,
            yazar_rol TEXT,
            mesaj TEXT,
            created_at TEXT
        )
    ''')

    # Default kullanıcıları oluştur
    c.execute("SELECT COUNT(*) FROM kullanicilar")
    if c.fetchone()[0] == 0:
        c.executemany('''
            INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, rol, birim)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ("calisan", "1234", "Ahmet Çalışan", "calisan", "Muhasebe"),
            ("uzman", "1234", "Mehmet Uzman", "uzman", "IT")
        ])

    conn.commit()
    conn.close()

def _migrate_from_json():
    if not os.path.exists(JSON_DB_PATH):
        return

    conn = _get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM talepler")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    try:
        with open(JSON_DB_PATH, encoding="utf-8") as f:
            data = json.load(f)
            
        talepler = data.get("talepler", {})
        for talep_no, t in talepler.items():
            c.execute('''
                INSERT INTO talepler (
                    talep_no, gonderen_kisi, gonderen_birim, oncelik, mesaj, 
                    kategori, talep_turu, cozum_suresi_gun, maliyet_tl, durum, 
                    created_at, tamamlandi_at, gercek_sure_gun, gercek_maliyet_tl, 
                    ai_oncelik, yuklenen_dosya, kullanici_adi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                t.get("talep_no"),
                t.get("gonderen_kisi"),
                t.get("gonderen_birim"),
                t.get("oncelik"),
                t.get("mesaj"),
                t.get("kategori"),
                t.get("talep_turu"),
                t.get("cozum_suresi_gun"),
                t.get("maliyet_tl") or t.get("tahmini_maliyet_tl"),
                t.get("durum", "bekliyor"),
                t.get("created_at"),
                t.get("tamamlandi_at"),
                t.get("gercek_sure_gun"),
                t.get("gercek_maliyet_tl"),
                json.dumps(t.get("ai_oncelik")) if t.get("ai_oncelik") else None,
                json.dumps(t.get("yuklenen_dosya")) if t.get("yuklenen_dosya") else None,
                "calisan"
            ))
        conn.commit()
        print("[MIGRATION] Mevcut biletler basariyla SQLite veritabanina aktarildi!")
    except Exception as e:
        print(f"[MIGRATION HATA] {e}")
    finally:
        conn.close()

# Initialize DB and run migration on import
with _lock:
    _init_db()
    _migrate_from_json()


def _row_to_dict(row):
    d = dict(row)
    if d.get("ai_oncelik"):
        d["ai_oncelik"] = json.loads(d["ai_oncelik"])
    if d.get("yuklenen_dosya"):
        d["yuklenen_dosya"] = json.loads(d["yuklenen_dosya"])
    if "maliyet_tl" in d and "tahmini_maliyet_tl" not in d:
        d["tahmini_maliyet_tl"] = d["maliyet_tl"]
    return d

def kullanici_dogrula(kullanici_adi: str, sifre: str) -> Optional[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?", (kullanici_adi, sifre))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

def kullanici_getir(kullanici_adi: str) -> Optional[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

def talep_no_olustur(no: int) -> str:
    return f"TKT-{no:04d}"

def ticket_kaydet(ticket_data: dict) -> str:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        
        c.execute("SELECT talep_no FROM talepler ORDER BY talep_no DESC LIMIT 1")
        row = c.fetchone()
        if row:
            last_no = int(row["talep_no"].split("-")[1])
            son_no = last_no + 1
        else:
            son_no = 1
            
        talep_no = talep_no_olustur(son_no)
        created_at = datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO talepler (
                talep_no, gonderen_kisi, gonderen_birim, oncelik, mesaj, 
                kategori, talep_turu, cozum_suresi_gun, maliyet_tl, durum, 
                created_at, ai_oncelik, yuklenen_dosya, kullanici_adi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            talep_no,
            ticket_data.get("gonderen_kisi"),
            ticket_data.get("gonderen_birim"),
            ticket_data.get("oncelik"),
            ticket_data.get("mesaj"),
            ticket_data.get("kategori"),
            ticket_data.get("talep_turu"),
            ticket_data.get("cozum_suresi_gun"),
            ticket_data.get("tahmini_maliyet_tl", ticket_data.get("maliyet_tl")),
            "bekliyor",
            created_at,
            json.dumps(ticket_data.get("ai_oncelik")) if ticket_data.get("ai_oncelik") else None,
            json.dumps(ticket_data.get("yuklenen_dosya")) if ticket_data.get("yuklenen_dosya") else None,
            ticket_data.get("kullanici_adi")
        ))
        conn.commit()
        conn.close()
        return talep_no

def ticket_listele(kullanici_adi: Optional[str] = None, durum: Optional[str] = None) -> List[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        
        query = "SELECT t.*, (SELECT created_at FROM yorumlar y WHERE y.talep_no = t.talep_no ORDER BY id DESC LIMIT 1) as son_yorum_tarihi, (SELECT yazar_rol FROM yorumlar y WHERE y.talep_no = t.talep_no ORDER BY id DESC LIMIT 1) as son_yorum_yapan_rol FROM talepler t WHERE 1=1"
        params = []
        if kullanici_adi:
            query += " AND t.kullanici_adi = ?"
            params.append(kullanici_adi)
        if durum:
            query += " AND t.durum = ?"
            params.append(durum)
            
        query += " ORDER BY t.talep_no DESC"
        
        c.execute(query, params)
        columns = [column[0] for column in c.description]
        rows = c.fetchall()
        conn.close()
        
        result = []
        for r in rows:
            d = dict(zip(columns, r))
            if d.get("ai_oncelik"): d["ai_oncelik"] = json.loads(d["ai_oncelik"])
            if d.get("yuklenen_dosya"): d["yuklenen_dosya"] = json.loads(d["yuklenen_dosya"])
            if "maliyet_tl" in d and "tahmini_maliyet_tl" not in d: d["tahmini_maliyet_tl"] = d["maliyet_tl"]
            result.append(d)
        return result

def ticket_getir(talep_no: str) -> Optional[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM talepler WHERE talep_no = ?", (talep_no,))
        row = c.fetchone()
        conn.close()
        if row:
            return _row_to_dict(row)
        return None

def ticket_tamamla(talep_no: str, gercek_sure: float, gercek_maliyet: float) -> Optional[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM talepler WHERE talep_no = ?", (talep_no,))
        if not c.fetchone():
            conn.close()
            return None
            
        tamamlandi_at = datetime.now().isoformat()
        c.execute('''
            UPDATE talepler 
            SET durum = 'tamamlandi', tamamlandi_at = ?, gercek_sure_gun = ?, gercek_maliyet_tl = ?
            WHERE talep_no = ?
        ''', (tamamlandi_at, gercek_sure, gercek_maliyet, talep_no))
        conn.commit()
        
        c.execute("SELECT * FROM talepler WHERE talep_no = ?", (talep_no,))
        row = c.fetchone()
        conn.close()
        return _row_to_dict(row)

def yorum_ekle(talep_no: str, yazar_adi: str, yazar_rol: str, mesaj: str) -> dict:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        created_at = datetime.now().isoformat()
        c.execute('''
            INSERT INTO yorumlar (talep_no, yazar_adi, yazar_rol, mesaj, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (talep_no, yazar_adi, yazar_rol, mesaj, created_at))
        yorum_id = c.lastrowid
        conn.commit()
        
        c.execute("SELECT * FROM yorumlar WHERE id = ?", (yorum_id,))
        row = c.fetchone()
        conn.close()
        return dict(row)

def yorumlari_getir(talep_no: str) -> List[dict]:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM yorumlar WHERE talep_no = ? ORDER BY created_at ASC", (talep_no,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def ticket_sil(talep_no: str) -> bool:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM talepler WHERE talep_no = ?", (talep_no,))
        if not c.fetchone():
            conn.close()
            return False
            
        c.execute("DELETE FROM talepler WHERE talep_no = ?", (talep_no,))
        c.execute("DELETE FROM yorumlar WHERE talep_no = ?", (talep_no,))
        conn.commit()
        conn.close()
        return True

def istatistikler() -> dict:
    with _lock:
        conn = _get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM talepler")
        toplam = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM talepler WHERE durum = 'bekliyor'")
        bekliyor = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM talepler WHERE durum = 'tamamlandi'")
        tamamlandi = c.fetchone()[0]
        
        conn.close()
        return {
            "toplam": toplam,
            "bekliyor": bekliyor,
            "tamamlandi": tamamlandi,
        }

EMBEDDINGS_CACHE_PATH = os.path.join(BASE_DIR, "data", "embeddings_cache.json")

def get_cached_embedding(talep_no: str) -> Optional[list]:
    with _lock:
        if not os.path.exists(EMBEDDINGS_CACHE_PATH):
            return None
        try:
            with open(EMBEDDINGS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            return cache.get(talep_no)
        except Exception:
            return None

def save_cached_embedding(talep_no: str, vector: list):
    with _lock:
        cache = {}
        if os.path.exists(EMBEDDINGS_CACHE_PATH):
            try:
                with open(EMBEDDINGS_CACHE_PATH, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception:
                pass
        cache[talep_no] = vector
        try:
            with open(EMBEDDINGS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        except Exception:
            pass
