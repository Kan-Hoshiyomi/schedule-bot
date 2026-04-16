import discord
from discord import app_commands
import aiosqlite
import calendar
from datetime import datetime
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

TOKEN = 'YOUR_BOT_TOKEN_HERE'
GUILD_ID = None

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ====================== DB ======================
async def init_db():
    async with aiosqlite.connect("schedules.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                date TEXT,
                title TEXT,
                description TEXT,
                creator_id INTEGER,
                participants TEXT DEFAULT ''
            )
        """)
        await db.commit()

# ====================== 月間カレンダー画像 ======================
def generate_calendar_image(year: int, month: int, day_events: dict):
    img_width = 900
    img_height = 650
    img = Image.new('RGB', (img_width, img_height), color='#1e1e1e')
    draw = ImageDraw.Draw(img)
    
    try:
        font_path = "C:/Windows/Fonts/msgothic.ttc"
        title_font = ImageFont.truetype(font_path, 42)
        day_font = ImageFont.truetype(font_path, 28)
        event_font = ImageFont.truetype(font_path, 16)
    except:
        title_font = day_font = event_font = ImageFont.load_default()

    title = f"{year}年 {month:02d}月 スケジュール"
    draw.text((img_width//2 - 200, 20), title, fill="#ffffff", font=title_font)

    weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    cell_width = img_width // 7
    for i, wd in enumerate(weekdays):
        color = "#ff5555" if i == 0 else "#ffffff"
        draw.text((i * cell_width + 40, 80), wd, fill=color, font=day_font)

    cal = calendar.monthcalendar(year, month)
    y_offset = 130
    for week in cal:
        for i, day in enumerate(week):
            if day == 0: continue
            x = i * cell_width + 20
            y = y_offset
            events_today = day_events.get(day, [])
            has_event = len(events_today) > 0
            box_color = "#334433" if has_event else "#2a2a2a"
            draw.rectangle([x, y, x + cell_width - 20, y + 80], fill=box_color, outline="#555555")
            
            day_color = "#ffdd55" if has_event else "#ffffff"
            draw.text((x + 15, y + 10), str(day), fill=day_color, font=day_font)
            
            if events_today:
                count = len(events_today)
                draw.text((x + 15, y + 45), f"{count}件", fill="#aaffaa", font=event_font)
                total_part = sum(c for _, _, c in events_today)
                if total_part > 0:
                    draw.text((x + cell_width - 80, y + 12), f"👥{total_part}", fill="#ffcc77", font=event_font)
        y_offset += 90

    image_binary = BytesIO()
    img.save(image_binary, 'PNG')
    image_binary.seek(0)
    return image_binary

# ====================== 1日詳細画像（0:00〜24:00に変更） ======================
def generate_day_detail_image(year: int, month: int, day: int, events: list):
    img_width = 900
    img_height = 1400                     # 高さを大きくして24時間分を表示
    img = Image.new('RGB', (img_width, img_height), color='#1e1e1e')
    draw = ImageDraw.Draw(img)
    
    try:
        font_path = "C:/Windows/Fonts/msgothic.ttc"
        title_font = ImageFont.truetype(font_path, 42)
        time_font = ImageFont.truetype(font_path, 24)
        event_font = ImageFont.truetype(font_path, 18)
    except:
        title_font = time_font = event_font = ImageFont.load_default()

    title = f"{year}年 {month:02d}月 {day:02d}日 の詳細スケジュール"
    draw.text((50, 30), title, fill="#ffffff", font=title_font)

    # 時間軸（0:00 〜 24:00）
    for h in range(0, 25):                    # 0時から24時まで
        y = 120 + h * 50                      # 1時間あたり50px（見やすい間隔）
        time_str = f"{h:02d}:00"
        draw.text((50, y - 10), time_str, fill="#aaaaaa", font=time_font)
        draw.line((150, y + 10, 850, y + 10), fill="#444444", width=2)   # 横線

    # 予定を表示（現在は簡易的に上から順番に。後で時間ソートも追加可能）
    y_offset = 180
    for eid, title, desc, parts in events:
        draw.text((180, y_offset), f"• {title}", fill="#aaffaa", font=event_font)
        if desc:
            draw.text((200, y_offset + 28), desc[:90] + ("..." if len(desc) > 90 else ""), fill="#cccccc", font=event_font)
        y_offset += 70   # 予定間の間隔

    if not events:
        draw.text((180, 250), "この日の予定はありません", fill="#888888", font=event_font)

    image_binary = BytesIO()
    img.save(image_binary, 'PNG')
    image_binary.seek(0)
    return image_binary

# ====================== 以降のコードは前回と同じ（メニュー、ビュー、モーダルなど） ======================
# （省略せずに全て含めたい場合は前回のメッセージからコピーして、generate_day_detail_imageだけ上記の新しい関数に置き換えてください）

# 注意：以下の部分は変更なしでOKです
# - ScheduleMenuView
# - CalendarControlView
# - DaySelectModal
# - DayDetailView
# - AddModal
# - get_events_by_day
# - setup_schedule コマンド
# - on_ready

# ====================== ヘルパー関数（get_events_by_day） ======================
async def get_events_by_day(guild_id: int, year: int, month: int):
    start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{last_day}"
    async with aiosqlite.connect("schedules.db") as db:
        async with db.execute(
            "SELECT id, date, title, participants FROM events WHERE guild_id=? AND date BETWEEN ? AND ?",
            (guild_id, start, end)
        ) as cursor:
            rows = await cursor.fetchall()
    day_events = defaultdict(list)
    for eid, date, title, parts in rows:
        d = int(date[-2:])
        count = len([x for x in parts.split(',') if x]) if parts else 0
        day_events[d].append((eid, title, count))
    return day_events

# ====================== セットアップ ======================
@tree.command(name="setup_schedule", description="スケジュールメニューを設置（1回だけ実行）")
async def setup_schedule(interaction: discord.Interaction):
    view = ScheduleMenuView()
    await interaction.response.send_message("📅 **スケジュール管理メニュー**\n下のボタンで全て操作できます！", view=view)
    await interaction.followup.send("✅ メニュー設置完了。以降はボタンのみで操作してください。", ephemeral=True)

@bot.event
async def on_ready():
    await init_db()
    bot.add_view(ScheduleMenuView())
    await tree.sync(guild=discord.Object(id=GUILD_ID) if GUILD_ID else None)
    print(f"✅ {bot.user} 起動完了！ 0:00〜24:00 の時間軸に変更済み")

bot.run(TOKEN)
