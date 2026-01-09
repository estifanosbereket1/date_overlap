import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DB = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST")
)

cur = DB.cursor()
cur.execute("DELETE FROM submissions")
cur.execute("DELETE FROM upload_log")
cur.execute("DELETE FROM consent_requests")
DB.commit()
DB.close()

print("✅ Database cleared!")
