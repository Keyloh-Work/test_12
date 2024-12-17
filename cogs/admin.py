import discord
from discord.ext import commands
from discord import app_commands
import csv
import chardet
import logging

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 新規追加：指定ユーザーにポイント付与(上限10)
    @app_commands.command(name="addpointuser", description="指定ユーザーにポイントを付与(上限10)")
    @app_commands.default_permissions(administrator=True)
    async def addpointuser(self, interaction: discord.Interaction, member: discord.Member, pointnumber: int):
        self.bot.ensure_user_points(member.id)
        old_points = self.bot.user_points[member.id]
        new_points = min(10, old_points + pointnumber)
        self.bot.user_points[member.id] = new_points
        await interaction.response.send_message(
            f"{member.mention} に {pointnumber}ポイント付与しました。({old_points} -> {new_points})",
            ephemeral=True
        )

    # 新規追加：全ユーザーにポイント付与(上限10)
    @app_commands.command(name="addpointall", description="全ユーザーに指定ポイントを付与(上限10)")
    @app_commands.default_permissions(administrator=True)
    async def addpointall(self, interaction: discord.Interaction, pointnumber: int):
        count = 0
        for user_id, points in self.bot.user_points.items():
            old_points = points
            new_points = min(10, points + pointnumber)
            self.bot.user_points[user_id] = new_points
            if new_points > old_points:
                count += 1

        await interaction.response.send_message(
            f"全てのユーザーに {pointnumber}ポイント付与しました。(上限10まで)\n"
            f"ポイントが増えたユーザー数: {count}",
            ephemeral=True
        )

    # 旧コマンド(gachareset/gacharesetall)削除済み
    # setresetdateコマンドも要件にないので削除済み

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
