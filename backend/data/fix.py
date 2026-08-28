import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "tickets.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("UPDATE talepler SET kategori='Yazılım Sorunu' WHERE talep_no='TKT-0025'")
conn.commit()
conn.close()
print("Fixed!")
