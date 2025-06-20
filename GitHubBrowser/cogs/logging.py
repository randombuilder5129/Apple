import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import asyncpg
from datetime import datetime, timezone
import pytz
import json
import logging

class Logging(commands.Cog):
    """Comprehensive tracking and logging system for all server activity"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
    async def cog_load(self):
        """Initialize logging tables when cog loads"""
        if self.bot.db_pool:
            await self.create_logging_tables()
        else:
            self.logger.warning("Logging cog loaded without database - limited functionality")
        
    async def create_logging_tables(self):
        """Create comprehensive logging tables in database"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Message logs table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS message_logs (
                        id SERIAL PRIMARY KEY,
                        message_id BIGINT UNIQUE,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        user_id BIGINT,
                        username TEXT,
                        content TEXT,
                        attachments TEXT,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        message_type TEXT DEFAULT 'message',
                        edited BOOLEAN DEFAULT FALSE,
                        deleted BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # Command usage logs table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS command_usage_logs (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT,
                        channel_id BIGINT,
                        user_id BIGINT,
                        username TEXT,
                        command_name TEXT,
                        command_args TEXT,
                        command_type TEXT DEFAULT 'text',
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        timestamp TIMESTAMPTZ DEFAULT NOW()
                    )
                ''')
                
                # Activity logs table for general events
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        username TEXT,
                        activity_type TEXT,
                        description TEXT,
                        metadata JSONB,
                        timestamp TIMESTAMPTZ DEFAULT NOW()
                    )
                ''')
                
                # Channel logs settings table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS log_settings (
                        guild_id BIGINT PRIMARY KEY,
                        log_channel_id BIGINT,
                        log_messages BOOLEAN DEFAULT TRUE,
                        log_commands BOOLEAN DEFAULT TRUE,
                        log_joins_leaves BOOLEAN DEFAULT TRUE,
                        log_edits_deletes BOOLEAN DEFAULT TRUE,
                        log_voice_activity BOOLEAN DEFAULT TRUE,
                        log_role_changes BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                ''')
                
                self.logger.info("Logging tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to create logging tables: {e}")
    
    async def get_log_channel(self, guild_id: int):
        """Get the designated log channel for a guild"""
        if not self.bot.db_pool:
            return None
        try:
            async with self.bot.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT log_channel_id FROM log_settings WHERE guild_id = $1",
                    guild_id
                )
                if result:
                    channel = self.bot.get_channel(result['log_channel_id'])
                    return channel
                return None
        except Exception as e:
            self.logger.error(f"Failed to get log channel: {e}")
            return None
    
    async def get_log_settings(self, guild_id: int):
        """Get logging settings for a guild"""
        if not self.bot.db_pool:
            return None
        try:
            async with self.bot.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM log_settings WHERE guild_id = $1",
                    guild_id
                )
                if result:
                    return dict(result)
                return {
                    'log_messages': True,
                    'log_commands': True,
                    'log_joins_leaves': True,
                    'log_edits_deletes': True,
                    'log_voice_activity': True,
                    'log_role_changes': True
                }
        except Exception as e:
            self.logger.error(f"Failed to get log settings: {e}")
            return {}
    
    async def log_to_database(self, table: str, data: dict):
        """Log data to specified database table"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                if table == 'message_logs':
                    await conn.execute('''
                        INSERT INTO message_logs (message_id, guild_id, channel_id, user_id, username, content, attachments, message_type)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (message_id) DO NOTHING
                    ''', data['message_id'], data['guild_id'], data['channel_id'], 
                         data['user_id'], data['username'], data['content'], 
                         data['attachments'], data['message_type'])
                
                elif table == 'command_usage_logs':
                    await conn.execute('''
                        INSERT INTO command_usage_logs (guild_id, channel_id, user_id, username, command_name, command_args, command_type, success, error_message)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', data['guild_id'], data['channel_id'], data['user_id'], 
                         data['username'], data['command_name'], data['command_args'],
                         data['command_type'], data['success'], data['error_message'])
                
                elif table == 'activity_logs':
                    await conn.execute('''
                        INSERT INTO activity_logs (guild_id, user_id, username, activity_type, description, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''', data['guild_id'], data['user_id'], data['username'],
                         data['activity_type'], data['description'], json.dumps(data['metadata']))
                         
        except Exception as e:
            self.logger.error(f"Failed to log to database: {e}")
    
    async def create_log_embed(self, title: str, description: str, color: int, fields=None):
        """Create a standardized log embed"""
        est = pytz.timezone('US/Eastern')
        timestamp = datetime.now(est)
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=timestamp
        )
        
        if fields is not None:
            for field in fields:
                embed.add_field(
                    name=field.get('name', 'Field'),
                    value=field.get('value', 'No value'),
                    inline=field.get('inline', True)
                )
        
        embed.set_footer(text="Apple Bot Logging System")
        return embed
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Log all messages sent in the server"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        settings = await self.get_log_settings(message.guild.id)
        if not settings or not settings.get('log_messages', True):
            return
        
        # Log to database
        attachments_data = []
        if message.attachments:
            attachments_data = [{'filename': att.filename, 'url': att.url} for att in message.attachments]
        
        await self.log_to_database('message_logs', {
            'message_id': message.id,
            'guild_id': message.guild.id,
            'channel_id': message.channel.id,
            'user_id': message.author.id,
            'username': str(message.author),
            'content': message.content[:2000],  # Truncate if too long
            'attachments': json.dumps(attachments_data),
            'message_type': 'message'
        })
        
        # Send to log channel
        log_channel = await self.get_log_channel(message.guild.id)
        if log_channel:
            embed = await self.create_log_embed(
                "📝 Message Sent",
                f"Message sent in {message.channel.mention}",
                0x3498db,
                [
                    {'name': 'User', 'value': f"{message.author.mention} ({message.author})", 'inline': True},
                    {'name': 'Channel', 'value': message.channel.mention, 'inline': True},
                    {'name': 'Content', 'value': message.content[:1000] if message.content else "*No text content*", 'inline': False}
                ]
            )
            
            if message.attachments:
                attach_list = '\n'.join([f"[{att.filename}]({att.url})" for att in message.attachments])
                embed.add_field(name="Attachments", value=attach_list[:1000], inline=False)
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass  # Silently fail if log channel is not accessible
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log message edits"""
        if before.author.bot or not before.guild:
            return
        
        settings = await self.get_log_settings(before.guild.id)
        if not settings or not settings.get('log_edits_deletes', True):
            return
        
        # Update database
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE message_logs SET edited = TRUE WHERE message_id = $1",
                    before.id
                )
        except Exception as e:
            self.logger.error(f"Failed to update message edit in database: {e}")
        
        # Send to log channel
        log_channel = await self.get_log_channel(before.guild.id)
        if log_channel:
            embed = await self.create_log_embed(
                "✏️ Message Edited",
                f"Message edited in {before.channel.mention}",
                0xf39c12,
                [
                    {'name': 'User', 'value': f"{before.author.mention} ({before.author})", 'inline': True},
                    {'name': 'Channel', 'value': before.channel.mention, 'inline': True},
                    {'name': 'Before', 'value': before.content[:1000] if before.content else "*No content*", 'inline': False},
                    {'name': 'After', 'value': after.content[:1000] if after.content else "*No content*", 'inline': False}
                ]
            )
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log message deletions"""
        if message.author.bot or not message.guild:
            return
        
        settings = await self.get_log_settings(message.guild.id)
        if not settings or not settings.get('log_edits_deletes', True):
            return
        
        # Update database
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE message_logs SET deleted = TRUE WHERE message_id = $1",
                    message.id
                )
        except Exception as e:
            self.logger.error(f"Failed to update message deletion in database: {e}")
        
        # Send to log channel
        log_channel = await self.get_log_channel(message.guild.id)
        if log_channel:
            embed = await self.create_log_embed(
                "🗑️ Message Deleted",
                f"Message deleted from {message.channel.mention}",
                0xe74c3c,
                [
                    {'name': 'User', 'value': f"{message.author.mention} ({message.author})", 'inline': True},
                    {'name': 'Channel', 'value': message.channel.mention, 'inline': True},
                    {'name': 'Content', 'value': message.content[:1000] if message.content else "*No content*", 'inline': False}
                ]
            )
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Log command usage"""
        if not ctx.guild:
            return
        
        settings = await self.get_log_settings(ctx.guild.id)
        if not settings or not settings.get('log_commands', True):
            return
        
        # Log to database
        await self.log_to_database('command_usage_logs', {
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'user_id': ctx.author.id,
            'username': str(ctx.author),
            'command_name': ctx.command.name if ctx.command else 'unknown',
            'command_args': ' '.join(ctx.args[2:]) if len(ctx.args) > 2 else '',  # Skip self and ctx
            'command_type': 'text',
            'success': True,
            'error_message': None
        })
        
        # Send to log channel
        log_channel = await self.get_log_channel(ctx.guild.id)
        if log_channel:
            embed = await self.create_log_embed(
                "⚡ Command Used",
                f"Command executed in {ctx.channel.mention}",
                0x9b59b6,
                [
                    {'name': 'User', 'value': f"{ctx.author.mention} ({ctx.author})", 'inline': True},
                    {'name': 'Channel', 'value': ctx.channel.mention, 'inline': True},
                    {'name': 'Command', 'value': f"`{ctx.prefix}{ctx.invoked_with}`", 'inline': True},
                    {'name': 'Arguments', 'value': ' '.join(ctx.args[2:])[:500] if len(ctx.args) > 2 else "*No arguments*", 'inline': False}
                ]
            )
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Log command errors"""
        if not ctx.guild:
            return
        
        settings = await self.get_log_settings(ctx.guild.id)
        if not settings or not settings.get('log_commands', True):
            return
        
        # Log to database
        await self.log_to_database('command_usage_logs', {
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'user_id': ctx.author.id,
            'username': str(ctx.author),
            'command_name': ctx.command.name if ctx.command else 'unknown',
            'command_args': ' '.join(ctx.args[2:]) if len(ctx.args) > 2 else '',
            'command_type': 'text',
            'success': False,
            'error_message': str(error)[:500]
        })
        
        # Send to log channel for significant errors
        if not isinstance(error, (commands.CommandNotFound, commands.MissingRequiredArgument)):
            log_channel = await self.get_log_channel(ctx.guild.id)
            if log_channel:
                embed = await self.create_log_embed(
                    "❌ Command Error",
                    f"Command failed in {ctx.channel.mention}",
                    0xe74c3c,
                    [
                        {'name': 'User', 'value': f"{ctx.author.mention} ({ctx.author})", 'inline': True},
                        {'name': 'Channel', 'value': ctx.channel.mention, 'inline': True},
                        {'name': 'Command', 'value': f"`{ctx.prefix}{ctx.invoked_with}`", 'inline': True},
                        {'name': 'Error', 'value': str(error)[:1000], 'inline': False}
                    ]
                )
                
                try:
                    await log_channel.send(embed=embed)
                except discord.HTTPException:
                    pass
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log member joins"""
        settings = await self.get_log_settings(member.guild.id)
        if not settings or not settings.get('log_joins_leaves', True):
            return
        
        # Log to database
        await self.log_to_database('activity_logs', {
            'guild_id': member.guild.id,
            'user_id': member.id,
            'username': str(member),
            'activity_type': 'member_join',
            'description': f"{member} joined the server",
            'metadata': {
                'account_created': member.created_at.isoformat(),
                'member_count': member.guild.member_count
            }
        })
        
        # Send to log channel
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            embed = await self.create_log_embed(
                "👋 Member Joined",
                f"{member.mention} joined the server",
                0x2ecc71,
                [
                    {'name': 'User', 'value': f"{member.mention} ({member})", 'inline': True},
                    {'name': 'Account Created', 'value': discord.utils.format_dt(member.created_at, 'R'), 'inline': True},
                    {'name': 'Member Count', 'value': str(member.guild.member_count), 'inline': True}
                ]
            )
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log member leaves"""
        settings = await self.get_log_settings(member.guild.id)
        if not settings or not settings.get('log_joins_leaves', True):
            return
        
        # Log to database
        await self.log_to_database('activity_logs', {
            'guild_id': member.guild.id,
            'user_id': member.id,
            'username': str(member),
            'activity_type': 'member_leave',
            'description': f"{member} left the server",
            'metadata': {
                'member_count': member.guild.member_count,
                'roles': [role.name for role in member.roles if role.name != "@everyone"]
            }
        })
        
        # Send to log channel
        log_channel = await self.get_log_channel(member.guild.id)
        if log_channel:
            roles_list = ', '.join([role.name for role in member.roles if role.name != "@everyone"])
            embed = await self.create_log_embed(
                "👋 Member Left",
                f"{member} left the server",
                0xe67e22,
                [
                    {'name': 'User', 'value': f"{member} (ID: {member.id})", 'inline': True},
                    {'name': 'Member Count', 'value': str(member.guild.member_count), 'inline': True},
                    {'name': 'Roles', 'value': roles_list[:1000] if roles_list else "No roles", 'inline': False}
                ]
            )
            
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException:
                pass
    
    @commands.group(name="logconfig", aliases=["logcfg"])
    @commands.has_permissions(manage_guild=True)
    async def logging_commands(self, ctx):
        """Configure server logging settings"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🔍 Logging System",
                description="Configure comprehensive server logging",
                color=0x3498db
            )
            embed.add_field(
                name="Available Commands",
                value="`!logconfig channel <#channel>` - Set log channel\n"
                      "`!logconfig settings` - View current settings\n"
                      "`!logconfig toggle <setting>` - Toggle logging features\n"
                      "`!logconfig stats` - View logging statistics",
                inline=False
            )
            await ctx.send(embed=embed)
    
    @logging_commands.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set the log channel for this server"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO log_settings (guild_id, log_channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET log_channel_id = $2, updated_at = NOW()
                ''', ctx.guild.id, channel.id)
            
            embed = discord.Embed(
                title="✅ Log Channel Set",
                description=f"Log channel has been set to {channel.mention}",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to set log channel: {e}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
    
    @logging_commands.command(name="settings")
    @commands.has_permissions(manage_guild=True)
    async def view_settings(self, ctx):
        """View current logging settings"""
        settings = await self.get_log_settings(ctx.guild.id)
        log_channel = await self.get_log_channel(ctx.guild.id)
        
        embed = discord.Embed(
            title="🔍 Current Logging Settings",
            color=0x3498db
        )
        
        embed.add_field(
            name="Log Channel",
            value=log_channel.mention if log_channel else "Not set",
            inline=False
        )
        
        status_emojis = {True: "✅", False: "❌"}
        if settings:
            embed.add_field(
                name="Logging Features",
                value=f"{status_emojis[settings.get('log_messages', True)]} Messages\n"
                      f"{status_emojis[settings.get('log_commands', True)]} Commands\n"
                      f"{status_emojis[settings.get('log_joins_leaves', True)]} Joins/Leaves\n"
                      f"{status_emojis[settings.get('log_edits_deletes', True)]} Edits/Deletes\n"
                      f"{status_emojis[settings.get('log_voice_activity', True)]} Voice Activity\n"
                      f"{status_emojis[settings.get('log_role_changes', True)]} Role Changes",
                inline=False
            )
        else:
            embed.add_field(
                name="Logging Features",
                value="❌ Database unavailable - cannot show settings",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @logging_commands.command(name="toggle")
    @commands.has_permissions(manage_guild=True)
    async def toggle_setting(self, ctx, setting: str):
        """Toggle logging features on/off"""
        valid_settings = {
            'messages': 'log_messages',
            'commands': 'log_commands', 
            'joins': 'log_joins_leaves',
            'edits': 'log_edits_deletes',
            'voice': 'log_voice_activity',
            'roles': 'log_role_changes'
        }
        
        if setting.lower() not in valid_settings:
            embed = discord.Embed(
                title="❌ Invalid Setting",
                description=f"Valid options: {', '.join(valid_settings.keys())}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        db_column = valid_settings[setting.lower()]
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get current setting
                current = await conn.fetchval(
                    f"SELECT {db_column} FROM log_settings WHERE guild_id = $1",
                    ctx.guild.id
                )
                
                # Toggle the setting
                new_value = not (current if current is not None else True)
                
                # Update or insert setting
                await conn.execute(f'''
                    INSERT INTO log_settings (guild_id, {db_column})
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET {db_column} = $2, updated_at = NOW()
                ''', ctx.guild.id, new_value)
                
                status = "enabled" if new_value else "disabled"
                embed = discord.Embed(
                    title="✅ Setting Updated",
                    description=f"**{setting.title()} logging** has been **{status}**",
                    color=0x2ecc71 if new_value else 0xe67e22
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to toggle setting: {e}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
    
    @logging_commands.command(name="stats")
    @commands.has_permissions(manage_guild=True)
    async def logging_stats(self, ctx):
        """View logging statistics"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get message stats
                message_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM message_logs WHERE guild_id = $1",
                    ctx.guild.id
                )
                
                # Get command stats
                command_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM command_usage_logs WHERE guild_id = $1",
                    ctx.guild.id
                )
                
                # Get activity stats
                activity_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM activity_logs WHERE guild_id = $1",
                    ctx.guild.id
                )
                
                # Get recent stats (last 24 hours)
                recent_messages = await conn.fetchval(
                    "SELECT COUNT(*) FROM message_logs WHERE guild_id = $1 AND timestamp > NOW() - INTERVAL '24 hours'",
                    ctx.guild.id
                )
                
                recent_commands = await conn.fetchval(
                    "SELECT COUNT(*) FROM command_usage_logs WHERE guild_id = $1 AND timestamp > NOW() - INTERVAL '24 hours'",
                    ctx.guild.id
                )
                
            embed = discord.Embed(
                title="📊 Logging Statistics",
                color=0x3498db
            )
            
            embed.add_field(
                name="Total Logged Events",
                value=f"📝 **{message_count:,}** Messages\n"
                      f"⚡ **{command_count:,}** Commands\n"
                      f"📋 **{activity_count:,}** Activities",
                inline=True
            )
            
            embed.add_field(
                name="Last 24 Hours",
                value=f"📝 **{recent_messages:,}** Messages\n"
                      f"⚡ **{recent_commands:,}** Commands",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to get statistics: {e}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
    
    @app_commands.command(name="logging", description="Configure server logging settings")
    @app_commands.describe(
        action="Action to perform",
        channel="Log channel (for setup)",
        setting="Setting to toggle (for toggle action)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Setup Channel", value="setup"),
            app_commands.Choice(name="View Settings", value="settings"),
            app_commands.Choice(name="Toggle Feature", value="toggle"),
            app_commands.Choice(name="View Statistics", value="stats")
        ],
        setting=[
            app_commands.Choice(name="Messages", value="messages"),
            app_commands.Choice(name="Commands", value="commands"),
            app_commands.Choice(name="Member Joins/Leaves", value="joins"),
            app_commands.Choice(name="Message Edits/Deletes", value="edits"),
            app_commands.Choice(name="Voice Activity", value="voice"),
            app_commands.Choice(name="Role Changes", value="roles")
        ]
    )
    async def slash_logging(
        self, 
        interaction: discord.Interaction, 
        action: app_commands.Choice[str],
        channel: discord.TextChannel = None,
        setting: app_commands.Choice[str] = None
    ):
        """Slash command interface for logging configuration"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions to use this command.", ephemeral=True)
            return
        
        if action.value == "setup":
            if not channel:
                await interaction.response.send_message("Please specify a channel for logging setup.", ephemeral=True)
                return
            
            if not self.bot.db_pool:
                await interaction.response.send_message("Database unavailable - logging setup disabled.", ephemeral=True)
                return
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO log_settings (guild_id, log_channel_id)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id) 
                        DO UPDATE SET log_channel_id = $2, updated_at = NOW()
                    ''', interaction.guild.id, channel.id)
                
                embed = discord.Embed(
                    title="✅ Log Channel Set",
                    description=f"Log channel has been set to {channel.mention}",
                    color=0x2ecc71
                )
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Failed to set log channel: {e}",
                    color=0xe74c3c
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action.value == "settings":
            settings = await self.get_log_settings(interaction.guild.id)
            log_channel = await self.get_log_channel(interaction.guild.id)
            
            embed = discord.Embed(
                title="🔍 Current Logging Settings",
                color=0x3498db
            )
            
            embed.add_field(
                name="Log Channel",
                value=log_channel.mention if log_channel else "Not set",
                inline=False
            )
            
            status_emojis = {True: "✅", False: "❌"}
            if settings:
                embed.add_field(
                    name="Logging Features",
                    value=f"{status_emojis[settings.get('log_messages', True)]} Messages\n"
                          f"{status_emojis[settings.get('log_commands', True)]} Commands\n"
                          f"{status_emojis[settings.get('log_joins_leaves', True)]} Joins/Leaves\n"
                          f"{status_emojis[settings.get('log_edits_deletes', True)]} Edits/Deletes\n"
                          f"{status_emojis[settings.get('log_voice_activity', True)]} Voice Activity\n"
                          f"{status_emojis[settings.get('log_role_changes', True)]} Role Changes",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Logging Features",
                    value="❌ Database unavailable - settings not accessible",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        
        elif action.value == "toggle":
            if not setting:
                await interaction.response.send_message("Please specify a setting to toggle.", ephemeral=True)
                return
            
            valid_settings = {
                'messages': 'log_messages',
                'commands': 'log_commands', 
                'joins': 'log_joins_leaves',
                'edits': 'log_edits_deletes',
                'voice': 'log_voice_activity',
                'roles': 'log_role_changes'
            }
            
            db_column = valid_settings[setting.value]
            
            if not self.bot.db_pool:
                await interaction.response.send_message("Database unavailable - logging settings disabled.", ephemeral=True)
                return
            
            try:
                async with self.bot.db_pool.acquire() as conn:
                    # Get current setting
                    current = await conn.fetchval(
                        f"SELECT {db_column} FROM log_settings WHERE guild_id = $1",
                        interaction.guild.id
                    )
                    
                    # Toggle the setting
                    new_value = not (current if current is not None else True)
                    
                    # Update or insert setting
                    await conn.execute(f'''
                        INSERT INTO log_settings (guild_id, {db_column})
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id) 
                        DO UPDATE SET {db_column} = $2, updated_at = NOW()
                    ''', interaction.guild.id, new_value)
                    
                    status = "enabled" if new_value else "disabled"
                    embed = discord.Embed(
                        title="✅ Setting Updated",
                        description=f"**{setting.name} logging** has been **{status}**",
                        color=0x2ecc71 if new_value else 0xe67e22
                    )
                    await interaction.response.send_message(embed=embed)
                    
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Failed to toggle setting: {e}",
                    color=0xe74c3c
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action.value == "stats":
            if not self.bot.db_pool:
                await interaction.response.send_message("Database unavailable - logging statistics disabled.", ephemeral=True)
                return
            try:
                async with self.bot.db_pool.acquire() as conn:
                    # Get message stats
                    message_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM message_logs WHERE guild_id = $1",
                        interaction.guild.id
                    )
                    
                    # Get command stats
                    command_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM command_usage_logs WHERE guild_id = $1",
                        interaction.guild.id
                    )
                    
                    # Get activity stats
                    activity_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM activity_logs WHERE guild_id = $1",
                        interaction.guild.id
                    )
                    
                    # Get recent stats (last 24 hours)
                    recent_messages = await conn.fetchval(
                        "SELECT COUNT(*) FROM message_logs WHERE guild_id = $1 AND timestamp > NOW() - INTERVAL '24 hours'",
                        interaction.guild.id
                    )
                    
                    recent_commands = await conn.fetchval(
                        "SELECT COUNT(*) FROM command_usage_logs WHERE guild_id = $1 AND timestamp > NOW() - INTERVAL '24 hours'",
                        interaction.guild.id
                    )
                    
                embed = discord.Embed(
                    title="📊 Logging Statistics",
                    color=0x3498db
                )
                
                embed.add_field(
                    name="Total Logged Events",
                    value=f"📝 **{message_count:,}** Messages\n"
                          f"⚡ **{command_count:,}** Commands\n"
                          f"📋 **{activity_count:,}** Activities",
                    inline=True
                )
                
                embed.add_field(
                    name="Last 24 Hours",
                    value=f"📝 **{recent_messages:,}** Messages\n"
                          f"⚡ **{recent_commands:,}** Commands",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Failed to get statistics: {e}",
                    color=0xe74c3c
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Logging(bot))