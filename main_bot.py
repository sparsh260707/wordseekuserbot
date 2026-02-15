import asyncio
import os
from pyrogram import Client, filters
from config import Config
import wordseek
from dotenv import load_dotenv

load_dotenv()

app = Client("wordseek_host", bot_token=Config.BOT_TOKEN)

# Global state
solver_client = None

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply(
        "🤖 **WordSeek Solver Host**\n\n"
        "/login - Login userbot (phone → code)\n"
        "/start_solver - Start solving\n"
        "/stop - Stop solver"
    )

@app.on_message(filters.command("login") & filters.private & filters.user(Config.AUTHORIZED_USERS))
async def login_cmd(client, message):
    global solver_client
    
    await message.reply("📱 **Send your PHONE NUMBER** (with country code, like +1234567890)")
    
    @app.on_message(filters.private & filters.text & ~filters.command(["start", "login"]))
    async def phone_handler(c, m):
        if m.from_user.id not in Config.AUTHORIZED_USERS:
            return
            
        phone = m.text.strip()
        try:
            await message.reply(f"✅ **Code sent to** `{phone}`\n**Reply with SMS CODE**:")
            
            @app.on_message(filters.private & filters.text)
            async def code_handler(cc, msg):
                if msg.from_user.id not in Config.AUTHORIZED_USERS:
                    return
                    
                code = msg.text.strip()
                await wordseek.start_solver(Config.API_ID, Config.API_HASH)
                
                # Sign in with session
                await solver_client.send_code_request(phone)
                await solver_client.sign_in(phone, code)
                
                await msg.reply("✅ **LOGIN SUCCESS!** Session saved!\n\n🔄 Restart VPS → **NO LOGIN NEEDED**\n\n📢 Send `/start_solver`")
                print("✅ Session created!")
                
                # Stop listening
                app.remove_handler(phone_handler)
                app.remove_handler(code_handler)
            
        except Exception as e:
            await m.reply(f"❌ **Error**: {e}")

@app.on_message(filters.command("start_solver") & filters.private & filters.user(Config.AUTHORIZED_USERS))
async def start_solver_cmd(client, message):
    global solver_client
    
    try:
        await wordseek.start_solver(Config.API_ID, Config.API_HASH)
        await message.reply("🚀 **Solver STARTED!**\n\n👉 Go to @WordSeekBot → `/new@WordSeekBot`")
        print("✅ Solver running!")
    except Exception as e:
        await message.reply(f"❌ **Error**: {e}")

@app.on_message(filters.command("stop") & filters.private & filters.user(Config.AUTHORIZED_USERS))
async def stop_cmd(client, message):
    import wordseek
    await wordseek.stop_solver()
    await message.reply("⏹️ **Solver STOPPED**")

print("🤖 **HostBot running** - Send /start")
app.run()
