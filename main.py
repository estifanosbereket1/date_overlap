import os
import urllib.parse
from fastapi import FastAPI, UploadFile, File, Form, Request
import psycopg2
import numpy as np
import tempfile
from dotenv import load_dotenv
import cv2
from insightface.app import FaceAnalysis
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

load_dotenv()

# Load InsightFace model once at startup — not on every request
face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_app.prepare(ctx_id=0, det_size=(640, 640))


app = FastAPI()

# DB = psycopg2.connect(
#     dbname=os.getenv("DB_NAME"),
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASSWORD"),
#     host=os.getenv("DB_HOST")
# )

url = urllib.parse.urlparse(os.getenv("DATABASE_URL"))
DB = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode="disable" 
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
telegram_app = Application.builder().token(BOT_TOKEN).build()

THRESHOLD = 0.68
RATE_LIMIT = 5  # max uploads per hour per user

import bot as bot_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")
telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", bot_handlers.start))
telegram_app.add_handler(MessageHandler(filters.PHOTO, bot_handlers.handle_photo))
telegram_app.add_handler(CallbackQueryHandler(bot_handlers.handle_consent, pattern="^consent_"))
telegram_app.add_handler(CommandHandler("mysubmissions", bot_handlers.my_submissions))
telegram_app.add_handler(CallbackQueryHandler(bot_handlers.handle_delete, pattern="^delete_"))

@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    await telegram_app.bot.set_webhook(f"{webhook_url}/webhook")

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

#def get_embedding(img_path):
    
 #   result = DeepFace.represent(
#      img_path=img_path,
 #       model_name="ArcFace",
 #       enforce_detection=True
 #   )
  #  return result[0]["embedding"]

def get_embedding(img_path):
    img = cv2.imread(img_path)
    faces = face_app.get(img)
    if not faces:
        raise ValueError("No face detected in the image")
    # Return embedding of the largest detected face
    largest = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
    return largest.embedding.tolist()
    
def cosine_distance(a, b):
    a, b = np.array(a), np.array(b)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def make_thumbnail(img_path):
    from PIL import Image
    import io
    img = Image.open(img_path)
    img.thumbnail((200, 200))  # resize to max 200x200 pixels
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()  # returns raw bytes

def is_rate_limited(cur, chat_id):
    # Count uploads by this user in the last hour
    cur.execute("""
        SELECT COUNT(*) FROM upload_log
        WHERE chat_id = %s
        AND uploaded_at > now() - interval '1 hour'
    """, (chat_id,))
    count = cur.fetchone()[0]
    return count >= RATE_LIMIT

def is_duplicate(cur, chat_id, embedding):
    # Check if this user already submitted this same face
    cur.execute("""
        SELECT embedding FROM submissions
        WHERE chat_id = %s
    """, (chat_id,))
    rows = cur.fetchall()
    for row in rows:
        existing = [float(x) for x in str(row[0]).strip("[]").split(",")]
        dist = cosine_distance(embedding, existing)
        if dist < THRESHOLD:
            return True
    return False





@app.post("/upload")
async def upload(file: UploadFile = File(...), handle: str = Form(...), chat_id: int = Form(...)):
    cur = DB.cursor()

    # --- Rate limiting ---
    if is_rate_limited(cur, chat_id):
        return {"error": "rate_limited", "detail": "You can only upload 5 photos per hour."}

    # Save uploaded image to temp file
# Save uploaded image to temp file
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Extract embedding AND thumbnail before deleting the file
    try:
        embedding = get_embedding(tmp_path)
        thumbnail = make_thumbnail(tmp_path)  # make thumbnail while file still exists
    except Exception as e:
        return {"error": "no_face_detected", "detail": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)  # delete AFTER both operations are done

    # --- Duplicate submission guard ---
    if is_duplicate(cur, chat_id, embedding):
        return {"error": "duplicate", "detail": "You already submitted this person."}

    # --- Find matches ---
    cur.execute("SELECT id, telegram_handle, chat_id, embedding FROM submissions")
    rows = cur.fetchall()

    matches = []
    for row in rows:
        db_id, db_handle, db_chat_id, db_embedding = row
        if db_chat_id == chat_id:
            continue
        db_embedding = [float(x) for x in str(db_embedding).strip("[]").split(",")]
        dist = cosine_distance(embedding, db_embedding)
        if dist < THRESHOLD:
            matches.append({
                "id": db_id,
                "handle": db_handle,
                "chat_id": db_chat_id,
                "distance": round(dist, 4)
            })

    # --- Store submission and log the upload ---
    cur.execute(
        "INSERT INTO submissions (telegram_handle, chat_id, embedding, photo) VALUES (%s, %s, %s::vector, %s)",
        (handle, chat_id, str(embedding), psycopg2.Binary(thumbnail))
    )
    cur.execute(
        "INSERT INTO upload_log (chat_id) VALUES (%s)",
        (chat_id,)
    )
    DB.commit()

    return {
        "your_handle": handle,
        "matches_found": len(matches),
        "matches": matches
    }
