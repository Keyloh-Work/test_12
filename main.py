import os
import logging
import discord
from discord.ext import commands
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from db import init_db, add_daily_points, load_gacha_data

load_dotenv()  # .envから環境変数読み込み

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()  # コンテナ上でのログは標準出力へ
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)
JST = pytz.timezone('Asia/Tokyo')
scheduler = AsyncIOScheduler(timezone=JST)

@scheduler.scheduled_job('cron', hour=0, minute=0)
def scheduled_add_points():
    add_daily_points()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}!')
    init_db()
    # gacha_data.csvをDBへロード（初回起動時のみ必要、既存データある場合はスキップ）
    load_gacha_data('data/gacha_data.csv')
    scheduler.start()
    # on_ready後ならapplication_id取得済みのはず
    await bot.tree.sync()
    logger.info("Commands synced.")

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

async def main():
    await bot.load_extension("cogs.gacha")
    await bot.load_extension("cogs.admin")
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
