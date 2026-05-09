import os
import requests
import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import io
import urllib.parse

from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO)


API_URL = os.getenv("API_URL")

# DB is shared from main.py to avoid two connections
from main import DB



def make_match_key(id_a, id_b):
    return f"match_{min(id_a, id_b)}_{max(id_a, id_b)}"

def consent_buttons():
    keyboard = [[
        InlineKeyboardButton("✅ YES", callback_data="consent_yes"),
        InlineKeyboardButton("❌ NO", callback_data="consent_no")
    ]]
    return InlineKeyboardMarkup(keyboard)

def red_flag_score(match_count):
    flags = "🚩" * min(match_count, 5)
    if match_count == 1:
        roast = "Busy boy."
    elif match_count == 2:
        roast = "This man is running a side hustle."
    elif match_count == 3:
        roast = "He's basically a local celebrity."
    elif match_count == 4:
        roast = "This man is running a franchise 🏢"
    else:
        roast = "Sir this is a Wendy's 😭"
    return f"{flags} Red Flag Score: {match_count}\n{roast}"

async def dramatic_reveal(status_msg):
    import asyncio
    await status_msg.edit_text("Checking... 🔍")
    await asyncio.sleep(1)
    await status_msg.edit_text("Hmm... 👀")
    await asyncio.sleep(1)
    await status_msg.edit_text("Oh. OH. 😳")
    await asyncio.sleep(1)

# --- DB helpers ---

def save_consent_request(match_key, user_a_id, user_a_handle, user_b_id, user_b_handle):
    cur = DB.cursor()
    # Avoid duplicate consent requests for the same match
    cur.execute("SELECT id FROM consent_requests WHERE match_key = %s", (match_key,))
    if cur.fetchone():
        return
    cur.execute("""
        INSERT INTO consent_requests
            (match_key, user_a_chat_id, user_a_handle, user_b_chat_id, user_b_handle)
        VALUES (%s, %s, %s, %s, %s)
    """, (match_key, user_a_id, user_a_handle, user_b_id, user_b_handle))
    DB.commit()

def get_consent_request(chat_id):
    cur = DB.cursor()
    cur.execute("""
        SELECT match_key,
               user_a_chat_id, user_a_handle, user_a_consent,
               user_b_chat_id, user_b_handle, user_b_consent
        FROM consent_requests
        WHERE (user_a_chat_id = %s OR user_b_chat_id = %s)
        AND user_a_consent IS NULL OR user_b_consent IS NULL
        ORDER BY created_at DESC
        LIMIT 1
    """, (chat_id, chat_id))
    return cur.fetchone()

def record_consent(match_key, chat_id, consent):
    cur = DB.cursor()
    # Figure out if this user is user_a or user_b and update accordingly
    cur.execute("SELECT user_a_chat_id FROM consent_requests WHERE match_key = %s", (match_key,))
    row = cur.fetchone()
    if not row:
        return None
    if row[0] == chat_id:
        cur.execute("""
            UPDATE consent_requests SET user_a_consent = %s WHERE match_key = %s
        """, (consent, match_key))
    else:
        cur.execute("""
            UPDATE consent_requests SET user_b_consent = %s WHERE match_key = %s
        """, (consent, match_key))
    DB.commit()
    # Return the full updated row
    cur.execute("""
        SELECT user_a_chat_id, user_a_handle, user_a_consent,
               user_b_chat_id, user_b_handle, user_b_consent
        FROM consent_requests WHERE match_key = %s
    """, (match_key,))
    return cur.fetchone()

def delete_consent_request(match_key):
    cur = DB.cursor()
    cur.execute("DELETE FROM consent_requests WHERE match_key = %s", (match_key,))
    DB.commit()

# --- Handlers ---

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Welcome to DateOverlap.\n\n"
        "Here's what you can do:\n\n"
        "📸 Send a photo — check if other women know the same guy\n"
        "📋 /mysubmissions — view and delete your submitted photos\n\n"
        "All matches are private. Usernames are only shared if both women agree. 🔒"
    )

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    handle = f"@{user.username}" if user.username else str(user.id)

    status_msg = await update.message.reply_text("Got it! Checking the database...")

    # Download photo
    photo = await update.message.photo[-1].get_file()
    img_path = f"/tmp/{user.id}.jpg"
    await photo.download_to_drive(img_path)

    # Send to backend
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/upload",
                files={"file": ("photo.jpg", f, "image/jpeg")},
                data={"handle": handle, "chat_id": user.id},
                timeout=60
            )
        result = resp.json()
    except Exception as e:
        print(f"Error uploading photo: {e}")
        await status_msg.edit_text("Something went wrong. Please try again.")
        return
    finally:
        if os.path.exists(img_path):
            os.unlink(img_path)

    # Error handling
    if "error" in result:
        error = result["error"]
        if error == "rate_limited":
            await status_msg.edit_text(
                "⚠️ You've uploaded too many photos this hour.\n"
                "Please wait a bit before trying again."
            )
        elif error == "duplicate":
            await status_msg.edit_text(
                "You already submitted this person before.\n"
                "We'll notify you if someone else submits the same face."
            )
        else:
            await status_msg.edit_text(
                "I couldn't detect a face in that photo.\n"
                "Please send a clear front-facing photo."
            )
        return

    matches = result.get("matches", [])

    if not matches:
            await status_msg.edit_text(
                "No matches found yet. You're the first to submit this person.\n"
                "I'll notify you if someone else submits the same face."
            )
            return

    # Dramatic reveal
    await dramatic_reveal(status_msg)

    match_count = len(matches)
    score_text = red_flag_score(match_count)

    for match in matches:
        if not match.get("chat_id"):
            continue

        matched_chat_id = match["chat_id"]
        matched_handle = match["handle"]
        match_key = make_match_key(user.id, matched_chat_id)

        save_consent_request(match_key, user.id, handle, matched_chat_id, matched_handle)

        # Ask current user with red flag score
        await status_msg.edit_text(
            f"🚨 MATCH FOUND 🚨\n\n"
            f"{score_text}\n\n"
            f"Another woman has submitted the same guy.\n"
            f"Do you want to share your username with her so you can connect?",
            reply_markup=consent_buttons()
        )

        # Notify matched user with score too
        try:
            await ctx.bot.send_message(
                chat_id=matched_chat_id,
                text=(
                    f"🚨 MATCH FOUND 🚨\n\n"
                    f"{score_text}\n\n"
                    f"Someone else just submitted the same guy you did!\n"
                    f"Do you want to share your username with her so you can connect?"
                ),
                reply_markup=consent_buttons()
            )
        except Exception as e:
            logging.warning(f"Could not notify {matched_handle}: {e}")

async def handle_consent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chose_yes = query.data == "consent_yes"

    # Load consent request from DB
    row = get_consent_request(user.id)
    if not row:
        await query.edit_message_text("This request has already been resolved.")
        return

    match_key = row[0]
    chosen_text = "✅ YES" if chose_yes else "❌ NO"
    await query.edit_message_text(
        f"You chose {chosen_text}. Waiting for the other woman's response..."
    )

    # Record this user's consent in DB
    updated = record_consent(match_key, user.id, chose_yes)
    if not updated:
        return

    user_a_chat_id, user_a_handle, user_a_consent, \
    user_b_chat_id, user_b_handle, user_b_consent = updated

    # Check if both have answered
    if user_a_consent is None or user_b_consent is None:
        return

    # Both answered — resolve
    both_consented = user_a_consent and user_b_consent

    if both_consented:
        await ctx.bot.send_message(
            chat_id=user_a_chat_id,
            text=f"✅ You both agreed to connect!\n\nShe is: {user_b_handle}\n\nYou two should start a support group. 💅"
        )
        await ctx.bot.send_message(
            chat_id=user_b_chat_id,
            text=f"✅ You both agreed to connect!\n\nShe is: {user_a_handle}\n\nYou two should start a support group. 💅"
        )
    else:
        await ctx.bot.send_message(
            chat_id=user_a_chat_id,
            text="She said no. Respect. Some things are better kept private. 🤫\nNo information was shared."
        )
        await ctx.bot.send_message(
            chat_id=user_b_chat_id,
            text="She said no. Respect. Some things are better kept private. 🤫\nNo information was shared."
        )

    delete_consent_request(match_key)

async def my_submissions(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cur = DB.cursor()
    cur.execute("""
        SELECT id, uploaded_at, photo FROM submissions
        WHERE chat_id = %s
        ORDER BY uploaded_at DESC
    """, (user.id,))
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text(
            "You haven't submitted anyone yet.\n"
            "Send me a photo to get started!"
        )
        return

    await update.message.reply_text(
        f"You have {len(rows)} submission(s). "
        f"Tap 🗑️ Delete under any photo to remove it."
    )

    for row in rows:
        sub_id, uploaded_at, photo_bytes = row
        date_str = uploaded_at.strftime("%b %d, %Y")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🗑️ Delete this submission",
                callback_data=f"delete_{sub_id}"
            )
        ]])
        # Send the thumbnail photo with a delete button
        await update.message.reply_photo(
            photo=io.BytesIO(bytes(photo_bytes)),
            caption=f"Submitted on {date_str}",
            reply_markup=keyboard
        )

async def handle_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    sub_id = int(query.data.split("_")[1])

    cur = DB.cursor()

    # Make sure this submission belongs to this user
    cur.execute("""
        SELECT id FROM submissions
        WHERE id = %s AND chat_id = %s
    """, (sub_id, user.id))
    row = cur.fetchone()

    if not row:
        await query.edit_message_caption(
            caption="❌ Submission not found or already deleted."
        )
        return

    # Delete it
    cur.execute("DELETE FROM submissions WHERE id = %s", (sub_id,))
    DB.commit()

    await query.edit_message_caption(
        caption="✅ Submission deleted. Good riddance. You deserve better. 👏"
    )

def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_consent, pattern="^consent_"))
    app.add_handler(CommandHandler("mysubmissions", my_submissions))
    app.add_handler(CallbackQueryHandler(handle_delete, pattern="^delete_"))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()