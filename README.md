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
