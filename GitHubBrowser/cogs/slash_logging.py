import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import asyncpg
from datetime import datetime, timezone
import pytz
import json
import logging

class SlashLogging(commands.Cog):
    """Slash command logging integration for the comprehensive tracking system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
    async def log_slash_command(self, interaction: discord.Interaction, success: bool = True, error_message: str = None):
        """Log slash command usage to the database and log channel"""
        if not interaction.guild or not self.bot.db_pool:
            return
            
        # Get logging settings
        try:
            async with self.bot.db_pool.acquire() as conn:
                settings = await conn.fetchrow(
                    "SELECT * FROM log_settings WHERE guild_id = $1",
                    interaction.guild.id
                )
                
                if not settings or not settings.get('log_commands', True):
                    return
                
                # Log to database
                await conn.execute('''
                    INSERT INTO command_usage_logs (guild_id, channel_id, user_id, username, command_name, command_args, command_type, success, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', interaction.guild.id, interaction.channel.id, interaction.user.id, 
                     str(interaction.user), interaction.command.name if interaction.command else 'unknown',
                     str(interaction.data.get('options', [])), 'slash', success, error_message)
                
                # Get log channel
                log_channel_id = settings.get('log_channel_id')
                if log_channel_id:
                    log_channel = self.bot.get_channel(log_channel_id)
                    if log_channel:
                        await self.send_slash_log_embed(log_channel, interaction, success, error_message)
                        
        except Exception as e:
            self.logger.error(f"Failed to log slash command: {e}")
    
    async def send_slash_log_embed(self, log_channel, interaction: discord.Interaction, success: bool, error_message: str = None):
        """Send slash command log embed to log channel"""
        est = pytz.timezone('US/Eastern')
        timestamp = datetime.now(est)
        
        if success:
            title = "⚡ Slash Command Used"
            color = 0x9b59b6
        else:
            title = "❌ Slash Command Error"
            color = 0xe74c3c
        
        embed = discord.Embed(
            title=title,
            description=f"Slash command executed in {interaction.channel.mention}",
            color=color,
            timestamp=timestamp
        )
        
        embed.add_field(
            name='User', 
            value=f"{interaction.user.mention} ({interaction.user})", 
            inline=True
        )
        embed.add_field(
            name='Channel', 
            value=interaction.channel.mention, 
            inline=True
        )
        embed.add_field(
            name='Command', 
            value=f"`/{interaction.command.name}`" if interaction.command else "`/unknown`", 
            inline=True
        )
        
        # Add command options if available
        if hasattr(interaction, 'data') and interaction.data and 'options' in interaction.data:
            options_str = self.format_slash_options(interaction.data['options'])
            embed.add_field(
                name='Options', 
                value=options_str[:1000], 
                inline=False
            )
        
        if error_message:
            embed.add_field(
                name='Error', 
                value=error_message[:1000], 
                inline=False
            )
        
        embed.set_footer(text="Apple Bot Logging System")
        
        try:
            await log_channel.send(embed=embed)
        except discord.HTTPException:
            pass
    
    def format_slash_options(self, options):
        """Format slash command options for display"""
        formatted = []
        for option in options:
            name = option.get('name', 'unknown')
            value = option.get('value', 'No value')
            formatted.append(f"{name}: {value}")
        return "\n".join(formatted) if formatted else "No options"

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Log all slash command interactions"""
        if interaction.type == discord.InteractionType.application_command:
            # Log successful slash command
            await self.log_slash_command(interaction, success=True)

async def setup(bot):
    await bot.add_cog(SlashLogging(bot))