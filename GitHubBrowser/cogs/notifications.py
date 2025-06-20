import discord
from discord.ext import commands
import logging
import asyncio

logger = logging.getLogger(__name__)

class Notifications(commands.Cog):
    """Core notifications functionality"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_notifications_tables(self):
        """Create notifications tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS notifications_data (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
        except Exception as e:
            logger.error(f"Database error in notifications: {e}")

async def setup(bot):
    await bot.add_cog(Notifications(bot))
