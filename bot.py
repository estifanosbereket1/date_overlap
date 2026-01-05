import os
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8678218747:AAGIXLf-B9KfLA6pTvB8HZMO5LaHtjk7Yrs"
API_URL = "http://127.0.0.1:8000"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a clear photo of the guy's face.\n"
        "I'll check if any other woman has submitted the same person."
    )

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    handle = f"@{user.username}" if user.username else str(user.id)

    await update.message.reply_text("Got it! Checking the database...")

    # Download the photo from Telegram
    photo = await update.message.photo[-1].get_file()
    img_path = f"/tmp/{user.id}.jpg"
    await photo.download_to_drive(img_path)

    # Send to our FastAPI backend
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/upload",
                files={"file": ("photo.jpg", f, "image/jpeg")},
                data={"handle": handle},
                timeout=60
            )
        result = resp.json()
    except Exception as e:
        await update.message.reply_text("Something went wrong. Please try again.")
        return
    finally:
        os.unlink(img_path)

    # Handle no face detected
    if "error" in result:
        await update.message.reply_text(
            "I couldn't detect a face in that photo.\n"
            "Please send a clear front-facing photo."
        )
        return

    matches = result.get("matches", [])

    if not matches:
        await update.message.reply_text(
            "No matches found yet. You're the first to submit this person.\n"
            "I'll notify you if someone else submits the same face."
        )
    else:
        handles = [m["handle"] for m in matches]
        names = ", ".join(handles)
        await update.message.reply_text(
            f"Match found! {len(matches)} other woman submitted the same guy.\n"
            f"Notifying them now..."
        )
        # Notify all matched users
        for match in matches:
            try:
                matched_handle = match["handle"]
                await ctx.bot.send_message(
                    chat_id=matched_handle.replace("@", ""),
                    text=(
                        f"Someone else just submitted the same guy you did!\n"
                        f"You may want to connect with them."
                    )
                )
            except Exception as e:
                logging.warning(f"Could not notify {matched_handle}: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()