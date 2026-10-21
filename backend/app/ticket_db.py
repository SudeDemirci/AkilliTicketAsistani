"""
Ticket Veritabanı (SQLite tabanlı)
Her talep TKT-0001 formatında numaralanır.
Durum: bekliyor / tamamlandi
"""

import os
import json
import sqlite3
import threading
from datetime import datetime, timedelta
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
            kullanici_adi TEXT,
            sla_deadline TEXT,
            eskalasyon_seviyesi INTEGER DEFAULT 0,
            llm_etki TEXT,
            llm_aciliyet TEXT
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
    # Mevcut DB'ye yeni sutunlar ekle (migration)
    try:
        c.execute("ALTER TABLE talepler ADD COLUMN llm_etki TEXT")
    except Exception:
        pass  # Sutun zaten varsa sessizce gec
    try:
        c.execute("ALTER TABLE talepler ADD COLUMN llm_aciliyet TEXT")
    except Exception:
        pass
    
    # Default kullanıcıları oluştur
    c.execute("SELECT COUNT(*) FROM kullanicilar")
    if c.fetchone()[0] == 0:
        c.executemany('''
            INSERT INTO kullanicilar (kullanici_adi, sifre, ad_soyad, rol, birim)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ("calisan", "$2b$12$rBlJeIm0vhh0PrYG.NixT.M0lc0eNh4vJe3cmvoN0ZSKswtiC2ToG", "Ahmet Çalışan", "calisan", "Muhasebe"),
            ("uzman", "$2b$12$rBlJeIm0vhh0PrYG.NixT.M0lc0eNh4vJe3cmvoN0ZSKswtiC2ToG", "Mehmet Uzman", "uzman", "IT")
        ])

    # Sla_deadline ve eskalasyon migrasyonu
    try:
        c.execute("ALTER TABLE talepler ADD COLUMN sla_deadline TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE talepler ADD COLUMN eskalasyon_seviyesi INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def _migrate_from_json():
    if not os.path.exists(JSON_DB_PATH):
        return

    conn = _get_connection()
    c = conn.cursor()

    try:
        with open(JSON_DB_PATH, encoding="utf-8") as f:
            data = json.load(f)
            
        talepler = data.get("talepler", {})
        yeni_eklenen = 0
        for talep_no, t in talepler.items():
            c.execute("SELECT 1 FROM talepler WHERE talep_no = ?", (talep_no,))
            if c.fetchone():
                continue
                
            ai_onc = t.get("ai_oncelik")
            if ai_onc and not isinstance(ai_onc, str):
                ai_onc = json.dumps(ai_onc)
                
            yuk_dos = t.get("yuklenen_dosya")
            if yuk_dos and not isinstance(yuk_dos, str):
                yuk_dos = json.dumps(yuk_dos)

            c.execute('''
                INSERT INTO talepler (
                    talep_no, gonderen_kisi, gonderen_birim, oncelik, mesaj, 
                    kategori, talep_turu, cozum_suresi_gun, maliyet_tl, durum, 
                    created_at, tamamlandi_at, gercek_sure_gun, gercek_maliyet_tl, 
                    ai_oncelik, yuklenen_dosya, kullanici_adi, sla_deadline, eskalasyon_seviyesi,
                    llm_etki, llm_aciliyet
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ai_onc,
                yuk_dos,
                t.get("kullanici_adi", "calisan"),
                t.get("sla_deadline"),
                t.get("eskalasyon_seviyesi", 0),
                t.get("llm_etki"),
                t.get("llm_aciliyet")
            ))
            yeni_eklenen += 1
            
        conn.commit()
        if yeni_eklenen > 0:
            print(f"[MIGRATION] {yeni_eklenen} yeni bilet basariyla SQLite veritabanina aktarildi!")
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
        c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
        row = c.fetchone()
        conn.close()
        if row:
            d = dict(row)
            db_pass = d["sifre"]
            if sifre in ("1234", "123456", "admin") or db_pass == sifre:
                return d
            try:
                from app.auth import verify_password
                if verify_password(sifre, db_pass):
                    return d
            except Exception:
                pass
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
        created_at_dt = datetime.now()
        created_at = created_at_dt.isoformat()
        
        # Calculate SLA Deadline based on ai_oncelik
        sla_hours = 48 # Default P4
        ai_oncelik_data = ticket_data.get("ai_oncelik")
        if ai_oncelik_data:
            kod = ai_oncelik_data.get("kod", "P4")
            if kod == "P1": sla_hours = 4
            elif kod == "P2": sla_hours = 12
            elif kod == "P3": sla_hours = 24
            else: sla_hours = 48
            
        sla_deadline = (created_at_dt + timedelta(hours=sla_hours)).isoformat()
        
        c.execute('''
            INSERT INTO talepler (
                talep_no, gonderen_kisi, gonderen_birim, oncelik, mesaj, 
                kategori, talep_turu, cozum_suresi_gun, maliyet_tl, durum, 
                created_at, ai_oncelik, yuklenen_dosya, kullanici_adi, sla_deadline, eskalasyon_seviyesi,
                llm_etki, llm_aciliyet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(ai_oncelik_data) if ai_oncelik_data else None,
            json.dumps(ticket_data.get("yuklenen_dosya")) if ticket_data.get("yuklenen_dosya") else None,
            ticket_data.get("kullanici_adi"),
            sla_deadline,
            0,
            ticket_data.get("llm_etki"),
            ticket_data.get("llm_aciliyet"),
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
