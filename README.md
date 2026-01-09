# DateOverlap 🔍

A privacy-first Telegram bot that helps women identify if they are dating the same person. Users submit a photo of someone they are dating, and the system uses facial recognition to find other women who submitted the same face. If a match is found, both women are asked for consent before any information is shared.

---

## How It Works

1. A woman sends a photo to the bot
2. The system extracts a facial embedding (a 512-number mathematical fingerprint of the face)
3. The embedding is compared against all stored embeddings in the database
4. If a match is found, both women are asked: _"Do you want to share your username with her?"_
5. Only if **both** say YES are usernames exchanged
6. If either says NO, both are told the other preferred to stay anonymous

---

## Features

- 🤖 **Face matching** — powered by ArcFace, one of the most accurate face recognition models
- 🔒 **Mutual consent** — usernames are never shared without both women agreeing
- 💾 **Persistent state** — consent requests survive bot restarts
- 🚫 **Duplicate guard** — the same face can't be submitted twice by the same user
- ⏱️ **Rate limiting** — max 5 uploads per hour per user
- 👥 **Multiple matches** — handles 3+ women submitting the same person
- 🗑️ **Photo deletion** — women can delete their submissions at any time via /mysubmissions
- 🐳 **Dockerized** — runs as three containers with a single command

---

## Tech Stack

| Layer            | Technology              |
| ---------------- | ----------------------- |
| Face recognition | DeepFace + ArcFace      |
| Backend API      | FastAPI                 |
| Database         | PostgreSQL + pgvector   |
| Telegram bot     | python-telegram-bot     |
| Containerization | Docker + docker-compose |

---

## Project Structure

- dateoverlap/
- ├── main.py # FastAPI backend — handles uploads, matching, rate limiting
- ├── bot.py # Telegram bot — handles user interaction and consent flow
- ├── cleardb.py # Terminal utility to wipe the database
- ├── init.sql # Database schema — runs automatically on first Docker start
- ├── Dockerfile # Container definition for api and bot services
- ├── docker-compose.yml # Orchestrates db, api, and bot containers
- ├── requirements.txt # Python dependencies
- └── .env # Environment variables (never commit this)

---

## Getting Started

### Prerequisites

- Docker and docker-compose installed
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### 1. Clone the repo

```bash
git clone https://github.com/yourname/dateoverlap.git
cd dateoverlap
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

### 3. Run

```bash
docker-compose up --build
```

That's it. All three services start automatically.

---

## Bot Commands

| Command          | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `/start`         | Introduction and usage guide                         |
| `/mysubmissions` | View all your submitted photos with option to delete |

---

## Development (without Docker)

### 1. Set up virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE faceapp;
\c faceapp
CREATE EXTENSION vector;
```

Then run the contents of `init.sql` manually.
BOT_TOKEN=your_telegram_bot_token
API_URL=http://api:8000
DB_NAME=faceapp
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=db

### 3. Update .env for local development

API_URL=http://127.0.0.1:8000
DB_HOST=127.0.0.1

### 4. Run both services

```bash
# Terminal 1
uvicorn main:app

# Terminal 2
python bot.py
```

### Clear the database

```bash
python cleardb.py
```

---

## How Face Matching Works

Rather than comparing photos directly, the system works with **facial embeddings**:

1. When a photo is uploaded, DeepFace runs the ArcFace model on it and produces a list of 512 floats — a mathematical representation of that face
2. This embedding is stored in PostgreSQL using the pgvector extension
3. When a new photo is uploaded, its embedding is compared against all stored ones using **cosine distance**
4. If the distance between two embeddings is below 0.68 (the ArcFace threshold), they are considered the same person

This means the actual photos are never compared — only their mathematical fingerprints. The thumbnail stored in the database is only used to show women their own submissions in `/mysubmissions`.

---

## Privacy

- Raw photos are deleted immediately after embedding extraction
- Only a small thumbnail is stored, used solely for the `/mysubmissions` command
- Facial embeddings cannot be reverse-engineered back into photos
- Usernames are never shared without explicit consent from both parties
- Women can delete their submissions at any time

---

## License

MIT
