import os
import logging
import discord
from discord.ext import commands
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

JST = pytz.timezone('Asia/Tokyo')
scheduler = AsyncIOScheduler(timezone=JST)

# ユーザーデータ管理
bot.user_points = {}  # {user_id: int} ポイント制に変更
bot.user_cards = {}   # {user_id: [card_no, ...]}
bot.gacha_data_path = 'data/gacha_data.csv'

# クールダウン廃止（要件にないためそのまま維持するかは自由）
# 今回特にクールダウン削除要求はないので、残してもいいがユーザーには記載なし。
# 要件に言及がないので消しても良いが、ここでは残すことにします。
bot.last_gacha_usage = {}
COOLDOWN = 10.0

def add_daily_points():
    # 毎日00:00に全員に1ポイント付与、ただし最大10まで
    for user_id, points in bot.user_points.items():
        if points < 10:
            bot.user_points[user_id] = min(10, points + 1)
    logger.info("Daily points added to all users.")

# 00:00に毎日実行
scheduler.add_job(add_daily_points, 'cron', hour=0, minute=0)
scheduler.start()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}!')
    await bot.load_extension("cogs.gacha")
    await bot.load_extension("cogs.admin")
    await bot.tree.sync()
    logger.info("Commands synced.")

# 初期ポイント付与
def ensure_user_points(user_id):
    if user_id not in bot.user_points:
        bot.user_points[user_id] = 10  # 初期10ポイント所持

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

bot.ensure_user_points = ensure_user_points  # 他のCogからも呼べるようにする
bot.run(TOKEN)
