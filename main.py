import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import wordseek
from config import Config

app = Client("wordseek-host", bot_token=Config.BOT_TOKEN)
HOSTS = set()

@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply(
        "🤖 **WordSeek Host**\n\n"
        "/host - Start solving\n"
        "/cancel - Stop\n"
        "/status - Check status"
    )

@app.on_message(filters.command("host"))
async def host(client: Client, message: Message):
    global HOSTS
    user_id = message.from_user.id
    
    if user_id not in Config.AUTHORIZED_HOSTS:
        return await message.reply("❌ Unauthorized")
    
    HOSTS.add(user_id)
    await wordseek.start_solver()
    
    await message.reply(
        f"🎯 **HOSTING ACTIVE** ({len(HOSTS)} hosts)\n\n"
        "✅ Send `/new@WordSeekBot` in target chat!\n"
        f"📁 Locked to: `{wordseek.CHAT_ID or 'First /new'}`"
    )

@app.on_message(filters.command("cancel"))
async def cancel(client: Client, message: Message):
    global HOSTS
    user_id = message.from_user.id
    
    if user_id in HOSTS:
        HOSTS.remove(user_id)
    
    if not HOSTS:
        await wordseek.stop_solver()
    
    await message.reply("🛑 Hosting stopped")

@app.on_message(filters.command("status"))
async def status(client: Client, message: Message):
    status = "🟢 ACTIVE" if HOSTS else "🔴 INACTIVE"
    await message.reply(f"**Status**: {status}\n**Hosts**: {len(HOSTS)}")

async def main():
    print("🤖 Starting host bot...")
    await app.start()
    print("✅ Bot ready! Send /host")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
