import os
import urllib.parse
import numpy as np
import tempfile
import cv2
import psycopg2
from insightface.app import FaceAnalysis
from dotenv import load_dotenv

load_dotenv()

# DB connection
url = urllib.parse.urlparse(os.getenv("DATABASE_URL"))
DB = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode="disable"
)

# InsightFace model
face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))

THRESHOLD = 0.68
RATE_LIMIT = 5

def get_embedding(img_path):
    img = cv2.imread(img_path)
    faces = face_app.get(img)
    if not faces:
        raise ValueError("No face detected in the image")
    largest = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
    return largest.embedding.tolist()

def cosine_distance(a, b):
    a, b = np.array(a), np.array(b)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def make_thumbnail(img_path):
    from PIL import Image
    import io
    img = Image.open(img_path)
    img.thumbnail((200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def is_rate_limited(cur, chat_id):
    cur.execute("""
        SELECT COUNT(*) FROM upload_log
        WHERE chat_id = %s AND uploaded_at > now() - interval '1 hour'
    """, (chat_id,))
    return cur.fetchone()[0] >= RATE_LIMIT

def is_duplicate(cur, chat_id, embedding):
    cur.execute("SELECT embedding FROM submissions WHERE chat_id = %s", (chat_id,))
    for row in cur.fetchall():
        existing = [float(x) for x in str(row[0]).strip("[]").split(",")]
        if cosine_distance(embedding, existing) < THRESHOLD:
            return True
    return False

async def process_upload(file_bytes: bytes, filename: str, handle: str, chat_id: int):
    cur = DB.cursor()

    if is_rate_limited(cur, chat_id):
        return {"error": "rate_limited", "detail": "You can only upload 5 photos per hour."}

    suffix = os.path.splitext(filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        embedding = get_embedding(tmp_path)
        thumbnail = make_thumbnail(tmp_path)
    except Exception as e:
        return {"error": "no_face_detected", "detail": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if is_duplicate(cur, chat_id, embedding):
        return {"error": "duplicate", "detail": "You already submitted this person."}

    cur.execute("SELECT id, telegram_handle, chat_id, embedding FROM submissions")
    matches = []
    for db_id, db_handle, db_chat_id, db_embedding in cur.fetchall():
        if db_chat_id == chat_id:
            continue
        db_embedding = [float(x) for x in str(db_embedding).strip("[]").split(",")]
        dist = cosine_distance(embedding, db_embedding)
        if dist < THRESHOLD:
            matches.append({"id": db_id, "handle": db_handle, "chat_id": db_chat_id, "distance": round(dist, 4)})

    cur.execute(
        "INSERT INTO submissions (telegram_handle, chat_id, embedding, photo) VALUES (%s, %s, %s::vector, %s)",
        (handle, chat_id, str(embedding), psycopg2.Binary(thumbnail))
    )
    cur.execute("INSERT INTO upload_log (chat_id) VALUES (%s)", (chat_id,))
    DB.commit()

    return {"your_handle": handle, "matches_found": len(matches), "matches": matches}