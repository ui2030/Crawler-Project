import sqlite3

DB = r"C:\CrawlerProject\CrawlerProject\db.sqlite3"  # DB의 절대 경로

con = sqlite3.connect(DB)
c = con.cursor()

cols = [r[1] for r in c.execute("PRAGMA table_info('CrawlerApp_newsarticle')")]
print("before:", cols)

if "created_at" not in cols:
    c.execute("ALTER TABLE CrawlerApp_newsarticle ADD COLUMN created_at TEXT")
    c.execute("UPDATE CrawlerApp_newsarticle SET created_at = datetime('now') WHERE created_at IS NULL")
    con.commit()

cols2 = [r[1] for r in c.execute("PRAGMA table_info('CrawlerApp_newsarticle')")]
print("after :", cols2)
print("max(created_at) =", c.execute("SELECT max(created_at) FROM CrawlerApp_newsarticle").fetchone())

con.close()