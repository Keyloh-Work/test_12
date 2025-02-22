import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @app_commands.command(name="addpointauto", description="毎日00:00時に自動付与されるポイントを調整します")
    @app_commands.default_permissions(administrator=True)
    async def addpointauto(self, interaction: discord.Interaction, pointnumber: int):
        if pointnumber < 0:
            await interaction.response.send_message("0以上の値を指定してください。", ephemeral=True)
            return
        old_value = self.bot.daily_auto_points
        self.bot.daily_auto_points = pointnumber
        await interaction.response.send_message(
            f"毎日00:00時に自動付与されるポイントを {old_value} から {pointnumber} に変更しました。\n"
            f"次に迎える00:00から {pointnumber} ポイントが付与されます。",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
