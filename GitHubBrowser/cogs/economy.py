import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    """Core economy functionality"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_economy_tables(self):
        """Create economy tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS economy (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        balance BIGINT DEFAULT 1000,
                        last_daily TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(guild_id, user_id)
                    )
                """)
        except Exception as e:
            logger.error(f"Database error in economy: {e}")
    
    @commands.hybrid_command(name="balance")
    async def is_economy_enabled(self, guild_id):
        """Check if economy is enabled for this guild"""
        if not self.bot.db_pool:
            return True  # Default enabled if no database
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT economy_enabled FROM guild_settings 
                    WHERE guild_id = $1
                """, guild_id)
                
                if not row:
                    # Auto-enable economy for new guilds
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, economy_enabled)
                        VALUES ($1, TRUE)
                        ON CONFLICT (guild_id) DO UPDATE SET
                            economy_enabled = TRUE
                    """, guild_id)
                    return True
                
                return row["economy_enabled"] if row["economy_enabled"] is not None else True
        except Exception:
            return True  # Default enabled on error
    
    async def check_balance(self, ctx, member: discord.Member = None):
        """Check your or someone else's balance"""
        
        # Check if economy is enabled
        if not await self.is_economy_enabled(ctx.guild.id):
            embed = discord.Embed(
                title="💰 Economy Disabled",
                description="The economy system is currently disabled in this server.\n\nAdministrators can enable it using `!settings`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        if not member:
            member = ctx.author
        
        if not self.bot.db_pool:
            await ctx.send("❌ Economy system unavailable!")
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                balance = await conn.fetchval(
                    "SELECT balance FROM economy WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, member.id
                )
                
                if balance is None:
                    balance = 1000  # Starting balance
                    await conn.execute(
                        "INSERT INTO economy (guild_id, user_id, balance) VALUES ($1, $2, $3)",
                        ctx.guild.id, member.id, balance
                    )
                
                embed = discord.Embed(
                    title=f"💰 {member.display_name}'s Balance",
                    description=f"**{balance:,}** coins",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error checking balance: {e}")
            await ctx.send("❌ Error checking balance!")
    
    @commands.hybrid_command(name="daily")
    async def daily_reward(self, ctx):
        """Claim your daily reward"""
        
        # Check if economy is enabled
        if not await self.is_economy_enabled(ctx.guild.id):
            embed = discord.Embed(
                title="💰 Economy Disabled",
                description="The economy system is currently disabled in this server.\n\nAdministrators can enable it using `!settings`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        if not self.bot.db_pool:
            await ctx.send("❌ Economy system unavailable!")
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Check last daily claim
                last_daily = await conn.fetchval(
                    "SELECT last_daily FROM economy WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, ctx.author.id
                )
                
                now = datetime.utcnow()
                if last_daily and (now - last_daily).total_seconds() < 86400:  # 24 hours
                    next_daily = last_daily + timedelta(days=1)
                    await ctx.send(f"❌ You already claimed your daily reward! Next claim: <t:{int(next_daily.timestamp())}:R>")
                    return
                
                # Give daily reward
                reward = 500
                await conn.execute("""
                    INSERT INTO economy (guild_id, user_id, balance, last_daily)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE SET 
                        balance = economy.balance + $3,
                        last_daily = $4
                """, ctx.guild.id, ctx.author.id, reward, now)
                
                embed = discord.Embed(
                    title="🎁 Daily Reward",
                    description=f"You received **{reward:,}** coins!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error with daily reward: {e}")
            await ctx.send("❌ Error claiming daily reward!")
    
    @commands.hybrid_command(name="pay")
    async def pay_user(self, ctx, member: discord.Member, amount: int):
        """Pay another user coins"""
        
        # Check if economy is enabled
        if not await self.is_economy_enabled(ctx.guild.id):
            embed = discord.Embed(
                title="💰 Economy Disabled",
                description="The economy system is currently disabled in this server.\n\nAdministrators can enable it using `!settings`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        if member == ctx.author:
            await ctx.send("❌ You cannot pay yourself!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        if not self.bot.db_pool:
            await ctx.send("❌ Economy system unavailable!")
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Check sender balance
                sender_balance = await conn.fetchval(
                    "SELECT balance FROM economy WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, ctx.author.id
                )
                
                if not sender_balance or sender_balance < amount:
                    await ctx.send("❌ Insufficient balance!")
                    return
                
                # Transfer money
                await conn.execute(
                    "UPDATE economy SET balance = balance - $3 WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, ctx.author.id, amount
                )
                
                await conn.execute("""
                    INSERT INTO economy (guild_id, user_id, balance)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE SET balance = economy.balance + $3
                """, ctx.guild.id, member.id, amount)
                
                embed = discord.Embed(
                    title="💸 Payment Sent",
                    description=f"You paid **{amount:,}** coins to {member.mention}",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error with payment: {e}")
            await ctx.send("❌ Error processing payment!")

async def setup(bot):
    await bot.add_cog(Economy(bot))
