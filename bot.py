# import os
# import requests
# import logging
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# from dotenv import load_dotenv
# load_dotenv()
# logging.basicConfig(level=logging.INFO)



# pending_consents = {}
# consent_pairs = {}

# def make_match_key(id_a, id_b):
#     return f"match_{min(id_a, id_b)}_{max(id_a, id_b)}"

# def consent_buttons():
#     keyboard = [
#         [
#             InlineKeyboardButton("✅ YES", callback_data="consent_yes"),
#             InlineKeyboardButton("❌ NO", callback_data="consent_no")
#         ]
#     ]
#     return InlineKeyboardMarkup(keyboard)

# async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text(
#         "Hi! Send me a clear photo of the guy's face.\n"
#         "I'll check if any other woman has submitted the same person."
#     )

# async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     handle = f"@{user.username}" if user.username else str(user.id)

#     status_msg = await update.message.reply_text("Got it! Checking the database...")

#     # Download photo
#     photo = await update.message.photo[-1].get_file()
#     img_path = f"/tmp/{user.id}.jpg"
#     await photo.download_to_drive(img_path)

#     # Send to backend
#     try:
#         with open(img_path, "rb") as f:
#             resp = requests.post(
#                 f"{os.getenv("API_URL")}/upload",
#                 files={"file": ("photo.jpg", f, "image/jpeg")},
#                 data={"handle": handle, "chat_id": user.id},
#                 timeout=60
#             )
#         result = resp.json()
#     except Exception as e:
#         await status_msg.edit_text("Something went wrong. Please try again.")
#         return
#     finally:
#         os.unlink(img_path)

#     if "error" in result:
#             error = result["error"]
#             if error == "rate_limited":
#                 await status_msg.edit_text(
#                     "⚠️ You've uploaded too many photos this hour.\n"
#                     "Please wait a bit before trying again."
#                 )
#             elif error == "duplicate":
#                 await status_msg.edit_text(
#                     "You already submitted this person before.\n"
#                     "We'll notify you if someone else submits the same face."
#                 )
#             else:
#                 await status_msg.edit_text(
#                     "I couldn't detect a face in that photo.\n"
#                     "Please send a clear front-facing photo."
#                 )
#             return
#     matches = result.get("matches", [])

#     if not matches:
#         await status_msg.edit_text(
#             "No matches found yet. You're the first to submit this person.\n"
#             "I'll notify you if someone else submits the same face."
#         )
#         return

#     for match in matches:
#         if not match.get("chat_id"):
#             continue

#         matched_chat_id = match["chat_id"]
#         matched_handle = match["handle"]
#         match_key = make_match_key(user.id, matched_chat_id)

#         consent_pairs[match_key] = {
#             user.id: None,
#             matched_chat_id: None
#         }

#         pending_consents[user.id] = {
#             "my_handle": handle,
#             "matched_chat_id": matched_chat_id,
#             "matched_handle": matched_handle,
#             "match_key": match_key
#         }

#         pending_consents[matched_chat_id] = {
#             "my_handle": matched_handle,
#             "matched_chat_id": user.id,
#             "matched_handle": handle,
#             "match_key": match_key
#         }

#         # Ask current user
#         await status_msg.edit_text(
#             "Match found! Another woman has submitted the same guy.\n\n"
#             "Do you want to share your username with her so you can connect?",
#             reply_markup=consent_buttons()
#         )

#         # Notify and ask matched user
#         try:
#             await ctx.bot.send_message(
#                 chat_id=matched_chat_id,
#                 text=(
#                     "Someone else just submitted the same guy you did!\n\n"
#                     "Do you want to share your username with her so you can connect?"
#                 ),
#                 reply_markup=consent_buttons()
#             )
#         except Exception as e:
#             logging.warning(f"Could not notify {matched_handle}: {e}")

# async def handle_consent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()  # dismisses the loading spinner on the button

#     user = query.from_user
#     chose_yes = query.data == "consent_yes"

#     if user.id not in pending_consents:
#         await query.edit_message_text("This request has already been resolved.")
#         return

#     consent_data = pending_consents[user.id]
#     match_key = consent_data["match_key"]
#     matched_chat_id = consent_data["matched_chat_id"]
#     matched_handle = consent_data["matched_handle"]
#     my_handle = consent_data["my_handle"]

#     # Record consent
#     consent_pairs[match_key][user.id] = chose_yes
#     del pending_consents[user.id]

#     # Update button message to show their choice
#     chosen_text = "✅ YES" if chose_yes else "❌ NO"
#     await query.edit_message_text(
#         f"You chose {chosen_text}. Waiting for the other woman's response..."
#     )

#     # Check if both answered
#     pair = consent_pairs[match_key]
#     if None in pair.values():
#         return  # other person hasn't answered yet

#     # Both answered — resolve
#     both_consented = all(pair.values())

#     if both_consented:
#         await ctx.bot.send_message(
#             chat_id=user.id,
#             text=f"✅ You both agreed to connect!\n\nShe is: {matched_handle}"
#         )
#         await ctx.bot.send_message(
#             chat_id=matched_chat_id,
#             text=f"✅ You both agreed to connect!\n\nShe is: {my_handle}"
#         )
#     else:
#         await ctx.bot.send_message(
#             chat_id=user.id,
#             text="The other woman preferred to stay anonymous.\nNo information was shared."
#         )
#         await ctx.bot.send_message(
#             chat_id=matched_chat_id,
#             text="The other woman preferred to stay anonymous.\nNo information was shared."
#         )

#     del consent_pairs[match_key]

# def main():
#     app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
#     app.add_handler(CallbackQueryHandler(handle_consent, pattern="^consent_"))
#     print("Bot is running...")
#     app.run_polling()

# if __name__ == "__main__":
#     main()


import os
import requests
import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO)

API_URL = os.getenv("API_URL")

# --- Database connection ---
DB = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST")
)

def make_match_key(id_a, id_b):
    return f"match_{min(id_a, id_b)}_{max(id_a, id_b)}"

def consent_buttons():
    keyboard = [[
        InlineKeyboardButton("✅ YES", callback_data="consent_yes"),
        InlineKeyboardButton("❌ NO", callback_data="consent_no")
    ]]
    return InlineKeyboardMarkup(keyboard)

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
        "Hi! Send me a clear photo of the guy's face.\n"
        "I'll check if any other woman has submitted the same person."
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

    # Handle multiple matches
    for match in matches:
        if not match.get("chat_id"):
            continue

        matched_chat_id = match["chat_id"]
        matched_handle = match["handle"]
        match_key = make_match_key(user.id, matched_chat_id)

        # Save consent request to DB instead of memory
        save_consent_request(match_key, user.id, handle, matched_chat_id, matched_handle)

        # Ask current user
        await status_msg.edit_text(
            "Match found! Another woman has submitted the same guy.\n\n"
            "Do you want to share your username with her so you can connect?",
            reply_markup=consent_buttons()
        )

        # Notify matched user
        try:
            await ctx.bot.send_message(
                chat_id=matched_chat_id,
                text=(
                    "Someone else just submitted the same guy you did!\n\n"
                    "Do you want to share your username with her so you can connect?"
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
            text=f"✅ You both agreed to connect!\n\nShe is: {user_b_handle}"
        )
        await ctx.bot.send_message(
            chat_id=user_b_chat_id,
            text=f"✅ You both agreed to connect!\n\nShe is: {user_a_handle}"
        )
    else:
        await ctx.bot.send_message(
            chat_id=user_a_chat_id,
            text="The other woman preferred to stay anonymous.\nNo information was shared."
        )
        await ctx.bot.send_message(
            chat_id=user_b_chat_id,
            text="The other woman preferred to stay anonymous.\nNo information was shared."
        )

    delete_consent_request(match_key)

def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_consent, pattern="^consent_"))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()