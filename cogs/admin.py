import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging
from db import get_points, set_points, DB_PATH

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addpointuser", description="指定ユーザーにポイントを付与(上限10)")
    @app_commands.default_permissions(administrator=True)
    async def addpointuser(self, interaction: discord.Interaction, member: discord.Member, pointnumber: int):
        old_points = get_points(member.id)
        new_points = old_points + pointnumber
        if new_points > 10:
            new_points = 10
        set_points(member.id, new_points)
        await interaction.response.send_message(f"{member.mention} に {pointnumber}ポイント付与しました。({old_points} -> {new_points})", ephemeral=True)

    @app_commands.command(name="addpointall", description="全てのユーザーに指定ポイントを付与(上限10)")
    @app_commands.default_permissions(administrator=True)
    async def addpointall(self, interaction: discord.Interaction, pointnumber: int):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, points FROM user_points")
        rows = cursor.fetchall()
        count = 0
        for user_id, pt in rows:
            new_pt = pt + pointnumber
            if new_pt > 10:
                new_pt = 10
            if new_pt > pt:
                count += 1
            cursor.execute("UPDATE user_points SET points=? WHERE user_id=?", (new_pt, user_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            f"全てのユーザーに {pointnumber}ポイント付与しました。(上限10まで)\n"
            f"ポイントが増えたユーザー数: {count}",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
