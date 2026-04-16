import discord
import os
import asyncio
from aiohttp import web

# ====================== TOKEN取得 ======================
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("❌ TOKEN が設定されていません！ RenderのEnvironment Variablesで 'TOKEN' を確認してください。")
    raise ValueError("Missing TOKEN")

# ====================== Render用 Health Check ======================
async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("🌐 Render用 Health Check Server がポート10000で起動しました")

# ====================== シンプルなBOT ======================
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} が正常に起動しました！")
    print(f"   サーバー数: {len(bot.guilds)}")
    asyncio.create_task(start_web_server())   # Render対策

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content == "!ping":
        await message.channel.send("Pong! BOTは正常に動作しています。")

bot.run(TOKEN)
