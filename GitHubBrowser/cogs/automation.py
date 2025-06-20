import discord
from discord.ext import commands
import logging
import asyncio

logger = logging.getLogger(__name__)

class Automation(commands.Cog):
    """Core automation functionality"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_automation_tables(self):
        """Create automation tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS automation_data (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
        except Exception as e:
            logger.error(f"Database error in automation: {e}")

async def setup(bot):
    await bot.add_cog(Automation(bot))
