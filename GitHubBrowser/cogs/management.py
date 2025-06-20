import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Management(commands.Cog):
    """Server management and configuration commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_management_tables(self):
        """Create management tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS guild_settings (
                        guild_id BIGINT PRIMARY KEY,
                        prefix VARCHAR(10) DEFAULT '!',
                        welcome_channel BIGINT,
                        goodbye_channel BIGINT,
                        log_channel BIGINT,
                        auto_role BIGINT,
                        starboard_channel BIGINT,
                        starboard_threshold INTEGER DEFAULT 3,
                        maintenance_mode BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
        except Exception as e:
            logger.error(f"Database error creating management tables: {e}")
    
    @commands.hybrid_command(name="set_prefix")
    @commands.has_permissions(manage_guild=True)
    async def set_prefix(self, ctx, prefix: str):
        """Set a custom prefix for the server"""
        if len(prefix) > 10:
            await ctx.send("❌ Prefix must be 10 characters or less!")
            return
        
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, prefix)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET prefix = $2, updated_at = NOW()
                    """, ctx.guild.id, prefix)
            except Exception as e:
                logger.error(f"Database error setting prefix: {e}")
        
        embed = discord.Embed(
            title="✅ Prefix Updated",
            description=f"Server prefix changed to: `{prefix}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="welcome_channel")
    @commands.has_permissions(manage_guild=True)
    async def welcome_channel(self, ctx, channel: discord.TextChannel = None):
        """Set or remove welcome channel"""
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, welcome_channel)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET welcome_channel = $2, updated_at = NOW()
                    """, ctx.guild.id, channel.id if channel else None)
            except Exception as e:
                logger.error(f"Database error setting welcome channel: {e}")
        
        if channel:
            embed = discord.Embed(
                title="✅ Welcome Channel Set",
                description=f"Welcome messages will be sent to {channel.mention}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Welcome Channel Removed",
                description="Welcome messages have been disabled",
                color=discord.Color.orange()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="goodbye_channel")
    @commands.has_permissions(manage_guild=True)
    async def goodbye_channel(self, ctx, channel: discord.TextChannel = None):
        """Set or remove goodbye channel"""
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, goodbye_channel)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET goodbye_channel = $2, updated_at = NOW()
                    """, ctx.guild.id, channel.id if channel else None)
            except Exception as e:
                logger.error(f"Database error setting goodbye channel: {e}")
        
        if channel:
            embed = discord.Embed(
                title="✅ Goodbye Channel Set",
                description=f"Goodbye messages will be sent to {channel.mention}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Goodbye Channel Removed", 
                description="Goodbye messages have been disabled",
                color=discord.Color.orange()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="log_channel")
    @commands.has_permissions(manage_guild=True)
    async def log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set or remove log channel"""
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, log_channel)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET log_channel = $2, updated_at = NOW()
                    """, ctx.guild.id, channel.id if channel else None)
            except Exception as e:
                logger.error(f"Database error setting log channel: {e}")
        
        if channel:
            embed = discord.Embed(
                title="✅ Log Channel Set",
                description=f"Server logs will be sent to {channel.mention}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Log Channel Removed",
                description="Server logging has been disabled",
                color=discord.Color.orange()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="auto_role")
    @commands.has_permissions(manage_roles=True)
    async def auto_role(self, ctx, role: discord.Role = None):
        """Set or remove auto-role for new members"""
        if role and role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You cannot assign a role equal to or higher than your highest role!")
            return
        
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, auto_role)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET auto_role = $2, updated_at = NOW()
                    """, ctx.guild.id, role.id if role else None)
            except Exception as e:
                logger.error(f"Database error setting auto role: {e}")
        
        if role:
            embed = discord.Embed(
                title="✅ Auto Role Set",
                description=f"New members will automatically receive {role.mention}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Auto Role Removed",
                description="Auto role assignment has been disabled",
                color=discord.Color.orange()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx, *, reason: str = "Server lockdown initiated"):
        """Lock ALL channels in the server"""
        locked_channels = []
        
        for channel in ctx.guild.text_channels:
            try:
                overwrites = channel.overwrites_for(ctx.guild.default_role)
                if overwrites.send_messages is not False:
                    overwrites.send_messages = False
                    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=reason)
                    locked_channels.append(channel.name)
            except discord.Forbidden:
                continue
        
        embed = discord.Embed(
            title="🔒 Server Lockdown",
            description=f"Locked {len(locked_channels)} channels",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None, *, reason: str = "Channel unlocked"):
        """Unlock a specific channel or all channels"""
        if channel:
            # Unlock specific channel
            try:
                overwrites = channel.overwrites_for(ctx.guild.default_role)
                overwrites.send_messages = None
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=reason)
                
                embed = discord.Embed(
                    title="🔓 Channel Unlocked",
                    description=f"{channel.mention} has been unlocked",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                
                await ctx.send(embed=embed)
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to modify that channel!")
        else:
            # Unlock all channels
            unlocked_channels = []
            
            for text_channel in ctx.guild.text_channels:
                try:
                    overwrites = text_channel.overwrites_for(ctx.guild.default_role)
                    if overwrites.send_messages is False:
                        overwrites.send_messages = None
                        await text_channel.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=reason)
                        unlocked_channels.append(text_channel.name)
                except discord.Forbidden:
                    continue
            
            embed = discord.Embed(
                title="🔓 Server Unlocked",
                description=f"Unlocked {len(unlocked_channels)} channels",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="maintenance")
    @commands.has_permissions(administrator=True)
    async def maintenance(self, ctx, mode: str = None):
        """Set maintenance mode - use 'test' to enable test commands for all users"""
        if mode not in ['on', 'off', 'test']:
            await ctx.send("❌ Usage: `!maintenance [on/off/test]`")
            return
        
        maintenance_enabled = mode in ['on', 'test']
        test_mode = mode == 'test'
        
        if self.bot.db_pool:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO guild_settings (guild_id, maintenance_mode)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id)
                        DO UPDATE SET maintenance_mode = $2, updated_at = NOW()
                    """, ctx.guild.id, maintenance_enabled)
            except Exception as e:
                logger.error(f"Database error setting maintenance mode: {e}")
        
        # Set bot-wide maintenance flags
        if not hasattr(self.bot, 'maintenance_guilds'):
            self.bot.maintenance_guilds = set()
        if not hasattr(self.bot, 'test_mode_guilds'):
            self.bot.test_mode_guilds = set()
        
        if maintenance_enabled:
            self.bot.maintenance_guilds.add(ctx.guild.id)
        else:
            self.bot.maintenance_guilds.discard(ctx.guild.id)
        
        if test_mode:
            self.bot.test_mode_guilds.add(ctx.guild.id)
        else:
            self.bot.test_mode_guilds.discard(ctx.guild.id)
        
        if mode == 'on':
            embed = discord.Embed(
                title="🔧 Maintenance Mode Enabled",
                description="Bot is now in maintenance mode. Only administrators can use commands.",
                color=discord.Color.orange()
            )
        elif mode == 'test':
            embed = discord.Embed(
                title="🧪 Test Mode Enabled",
                description="Test commands are now available to all users. Maintenance mode is active.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="✅ Maintenance Mode Disabled",
                description="Bot is now operating normally.",
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="server_info")
    async def server_info(self, ctx):
        """Display server information"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name} Information",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(
            name="🏷️ Basic Info",
            value=f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                  f"**Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                  f"**ID:** {guild.id}",
            inline=True
        )
        
        # Member stats
        total_members = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total_members - bots
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total_members}\n"
                  f"**Humans:** {humans}\n"
                  f"**Bots:** {bots}",
            inline=True
        )
        
        # Channel stats
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="📁 Channels",
            value=f"**Text:** {text_channels}\n"
                  f"**Voice:** {voice_channels}\n"
                  f"**Categories:** {categories}",
            inline=True
        )
        
        # Role and emoji stats
        embed.add_field(
            name="🎭 Other",
            value=f"**Roles:** {len(guild.roles)}\n"
                  f"**Emojis:** {len(guild.emojis)}\n"
                  f"**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )
        
        # Features
        features = guild.features
        if features:
            feature_list = []
            feature_names = {
                'COMMUNITY': 'Community Server',
                'PARTNERED': 'Discord Partner',
                'VERIFIED': 'Verified',
                'VIP_REGIONS': 'VIP Voice Regions',
                'VANITY_URL': 'Vanity URL',
                'DISCOVERABLE': 'Server Discovery',
                'FEATURABLE': 'Featurable',
                'MORE_STICKERS': 'More Stickers',
                'ROLE_ICONS': 'Role Icons',
                'BANNER': 'Server Banner'
            }
            
            for feature in features[:5]:  # Show max 5 features
                feature_list.append(feature_names.get(feature, feature.replace('_', ' ').title()))
            
            embed.add_field(
                name="🌟 Features",
                value="\n".join(feature_list) if feature_list else "None",
                inline=True
            )
        
        # Verification level
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium", 
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="🔒 Security",
            value=f"**Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n"
                  f"**2FA Required:** {'Yes' if guild.mfa_level else 'No'}",
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    cog = Management(bot)
    await cog.create_management_tables()
    await bot.add_cog(cog)