import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from fastapi import FastAPI, UploadFile, File, Form
import psycopg2
import numpy as np
import tempfile

app = FastAPI()

DB = psycopg2.connect(
    dbname="faceapp",
    user="postgres",
    password="postgres",
    host="127.0.0.1"
)

THRESHOLD = 0.68

def get_embedding(img_path):
    from deepface import DeepFace  # import here, not at top
    result = DeepFace.represent(
        img_path=img_path,
        model_name="ArcFace",
        enforce_detection=True
    )
    return result[0]["embedding"]

def cosine_distance(a, b):
    a, b = np.array(a), np.array(b)
    return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@app.post("/upload")
async def upload(file: UploadFile = File(...), handle: str = Form(...)):
    # Save the uploaded image to a temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Extract embedding from the uploaded face
    try:
        embedding = get_embedding(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        return {"error": "no_face_detected", "detail": str(e)}

    # Search the database for similar embeddings
    cur = DB.cursor()
    cur.execute("SELECT id, telegram_handle, embedding FROM submissions")
    rows = cur.fetchall()

    matches = []
    for row in rows:
        db_id, db_handle, db_embedding = row
    # Convert string back to list of floats
    db_embedding = [float(x) for x in str(db_embedding).strip("[]").split(",")]
    dist = cosine_distance(embedding, db_embedding)
    if dist < THRESHOLD:
        matches.append({
            "id": db_id,
            "handle": db_handle,
            "distance": round(dist, 4)
        })
    # for row in rows:
    #     db_id, db_handle, db_embedding = row
    #     dist = cosine_distance(embedding, db_embedding)
    #     if dist < THRESHOLD:
    #         matches.append({
    #             "id": db_id,
    #             "handle": db_handle,
    #             "distance": round(dist, 4)
    #         })

    # Store the new submission
    cur.execute(
        "INSERT INTO submissions (telegram_handle, embedding) VALUES (%s, %s::vector)",
        (handle, str(embedding))
    )
    DB.commit()
    os.unlink(tmp_path)

    return {
        "your_handle": handle,
        "matches_found": len(matches),
        "matches": matches
    }