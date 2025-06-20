import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    """Comprehensive moderation system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_moderation_tables(self):
        """Create moderation tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS moderation (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        moderator_id BIGINT NOT NULL,
                        action VARCHAR(20) NOT NULL,
                        reason TEXT,
                        duration INTERVAL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS muted_users (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        muted_until TIMESTAMP,
                        muted_by BIGINT NOT NULL,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(guild_id, user_id)
                    )
                """)
        except Exception as e:
            logger.error(f"Database error in moderation: {e}")
    
    async def log_moderation(self, guild_id, user_id, moderator_id, action, reason, duration=None):
        """Log moderation action"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO moderation (guild_id, user_id, moderator_id, action, reason, duration)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, guild_id, user_id, moderator_id, action, reason, duration)
        except Exception as e:
            logger.error(f"Database error logging moderation: {e}")
    
    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot ban someone with equal or higher role!")
            return
        
        try:
            await member.ban(reason=f"Banned by {ctx.author}: {reason}")
            await self.log_moderation(ctx.guild.id, member.id, ctx.author.id, "ban", reason)
            
            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"**{member}** has been banned",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this member!")
        except Exception as e:
            await ctx.send(f"❌ Error banning member: {e}")
    
    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban_user(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        """Unban a user from the server"""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}: {reason}")
            await self.log_moderation(ctx.guild.id, user_id, ctx.author.id, "unban", reason)
            
            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user}** has been unbanned",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.NotFound:
            await ctx.send("❌ User not found or not banned!")
        except Exception as e:
            await ctx.send(f"❌ Error unbanning user: {e}")
    
    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot kick someone with equal or higher role!")
            return
        
        try:
            await member.kick(reason=f"Kicked by {ctx.author}: {reason}")
            await self.log_moderation(ctx.guild.id, member.id, ctx.author.id, "kick", reason)
            
            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member}** has been kicked",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this member!")
        except Exception as e:
            await ctx.send(f"❌ Error kicking member: {e}")
    
    @commands.hybrid_command(name="mute")
    @commands.has_permissions(manage_messages=True)
    async def mute_user(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided"):
        """Mute a member (timeout)"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot mute someone with equal or higher role!")
            return
        
        # Parse duration
        if duration:
            try:
                duration_seconds = self.parse_duration(duration)
                if duration_seconds > 2419200:  # 28 days max
                    await ctx.send("❌ Maximum mute duration is 28 days!")
                    return
                mute_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
            except ValueError:
                await ctx.send("❌ Invalid duration format! Use: 1h, 30m, 2d")
                return
        else:
            mute_until = datetime.utcnow() + timedelta(hours=1)  # Default 1 hour
        
        try:
            await member.timeout(mute_until, reason=f"Muted by {ctx.author}: {reason}")
            await self.log_moderation(ctx.guild.id, member.id, ctx.author.id, "mute", reason, mute_until - datetime.utcnow())
            
            if self.bot.db_pool:
                try:
                    async with self.bot.db_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO muted_users (guild_id, user_id, muted_until, muted_by, reason)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                                muted_until = $3, muted_by = $4, reason = $5
                        """, ctx.guild.id, member.id, mute_until, ctx.author.id, reason)
                except Exception as e:
                    logger.error(f"Database error storing mute: {e}")
            
            embed = discord.Embed(
                title="🔇 Member Muted",
                description=f"**{member}** has been muted",
                color=discord.Color.dark_gray()
            )
            embed.add_field(name="Duration", value=f"<t:{int(mute_until.timestamp())}:R>", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to mute this member!")
        except Exception as e:
            await ctx.send(f"❌ Error muting member: {e}")
    
    @commands.hybrid_command(name="unmute")
    @commands.has_permissions(manage_messages=True)
    async def unmute_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a member"""
        try:
            await member.timeout(None, reason=f"Unmuted by {ctx.author}: {reason}")
            await self.log_moderation(ctx.guild.id, member.id, ctx.author.id, "unmute", reason)
            
            if self.bot.db_pool:
                try:
                    async with self.bot.db_pool.acquire() as conn:
                        await conn.execute(
                            "DELETE FROM muted_users WHERE guild_id = $1 AND user_id = $2",
                            ctx.guild.id, member.id
                        )
                except Exception as e:
                    logger.error(f"Database error removing mute: {e}")
            
            embed = discord.Embed(
                title="🔊 Member Unmuted",
                description=f"**{member}** has been unmuted",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error unmuting member: {e}")
    
    @commands.hybrid_command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        await self.log_moderation(ctx.guild.id, member.id, ctx.author.id, "warn", reason)
        
        # Get warning count
        warning_count = 1
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    warning_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM moderation WHERE guild_id = $1 AND user_id = $2 AND action = 'warn'",
                        ctx.guild.id, member.id
                    )
            except Exception as e:
                logger.error(f"Database error getting warning count: {e}")
        
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"**{member}** has been warned",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
        # DM the user
        try:
            dm_embed = discord.Embed(
                title=f"Warning in {ctx.guild.name}",
                description=f"You have been warned by {ctx.author}",
                color=discord.Color.yellow()
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
            
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # User has DMs disabled
    
    @commands.hybrid_command(name="warnings")
    async def view_warnings(self, ctx, member: discord.Member = None):
        """View warnings for a member"""
        if not member:
            member = ctx.author
        
        if not self.bot.db_pool:
            await ctx.send("❌ Database unavailable!")
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                warnings = await conn.fetch("""
                    SELECT reason, created_at, moderator_id 
                    FROM moderation 
                    WHERE guild_id = $1 AND user_id = $2 AND action = 'warn'
                    ORDER BY created_at DESC
                    LIMIT 10
                """, ctx.guild.id, member.id)
            
            if not warnings:
                await ctx.send(f"✅ **{member}** has no warnings!")
                return
            
            embed = discord.Embed(
                title=f"⚠️ Warnings for {member}",
                description=f"Total warnings: {len(warnings)}",
                color=discord.Color.yellow()
            )
            
            for i, warning in enumerate(warnings[:5], 1):
                moderator = self.bot.get_user(warning['moderator_id'])
                mod_name = moderator.mention if moderator else f"<@{warning['moderator_id']}>"
                
                embed.add_field(
                    name=f"Warning {i}",
                    value=f"**Reason:** {warning['reason']}\n**By:** {mod_name}\n**Date:** <t:{int(warning['created_at'].timestamp())}:R>",
                    inline=False
                )
            
            if len(warnings) > 5:
                embed.set_footer(text=f"Showing 5 of {len(warnings)} warnings")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Database error getting warnings: {e}")
            await ctx.send("❌ Error retrieving warnings!")
    
    @commands.hybrid_command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: int = 10):
        """Clear messages from the channel"""
        if amount < 1 or amount > 100:
            await ctx.send("❌ Amount must be between 1 and 100!")
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
            
            embed = discord.Embed(
                title="🗑️ Messages Cleared",
                description=f"Deleted {len(deleted) - 1} messages",
                color=discord.Color.blue()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            # Send and auto-delete confirmation
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages!")
        except Exception as e:
            await ctx.send(f"❌ Error clearing messages: {e}")
    
    def parse_duration(self, duration_str):
        """Parse duration string into seconds"""
        import re
        
        duration_str = duration_str.lower()
        
        patterns = {
            r'(\d+)s': 1,
            r'(\d+)m': 60,
            r'(\d+)h': 3600,
            r'(\d+)d': 86400
        }
        
        total_seconds = 0
        
        for pattern, multiplier in patterns.items():
            match = re.search(pattern, duration_str)
            if match:
                total_seconds += int(match.group(1)) * multiplier
        
        if total_seconds == 0:
            raise ValueError("Invalid duration format")
        
        return total_seconds

async def setup(bot):
    cog = Moderation(bot)
    await cog.create_moderation_tables()
    await bot.add_cog(cog)
