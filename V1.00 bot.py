
import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json
import datetime
import pytz
import os
import random
import re

intents = discord.Intents.all()

def get_prefix(bot, message):
    if message.guild:
        return get_guild_prefix(message.guild.id)
    return "!"

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

scheduler = AsyncIOScheduler()

# Multi-server support - store settings per guild
guild_settings = {}
settings_file = "guild_settings.json"
warnings_file = "warnings.json"

def get_user_key(guild_id, user_id):
    """Generate consistent user key for multi-server data"""
    return f"{guild_id}_{user_id}"
locked_channels_file = "locked_channels.json"
xp_file = "xp_data.json"
tokens_file = "tokens.json"
reaction_roles_file = "reaction_roles.json"

# Bot start time for uptime tracking
bot_start_time = datetime.datetime.now()

# XP System tracking
xp_cooldown = {}  # User cooldown for XP earning
XP_COOLDOWN_SECONDS = 60  # 1 minute cooldown between XP gains

# Level roles that should be auto-created
LEVEL_ROLES = {5: "Level 5", 10: "Level 10", 20: "Level 20", 50: "Level 50", 
               100: "Level 100", 125: "Level 125", 150: "Level 150", 175: "Level 175", 
               200: "Level 200", 500: "Level 500", 1000: "Level 1000"}

# DM tracking for spam detection
dm_tracker = {}
DM_SPAM_THRESHOLD = 10  # messages per minute
DM_TIME_WINDOW = 60  # seconds

# Anti-raid tracking
join_tracker = {}
RAID_THRESHOLD = 5  # users joining
RAID_TIME_WINDOW = 10  # seconds

# Account age verification
MIN_ACCOUNT_AGE_DAYS = 3

# Mention spam detection
mention_tracker = {}
MENTION_SPAM_THRESHOLD = 5  # mentions per message or short time
MENTION_TIME_WINDOW = 30  # seconds

# Load/save functions for multi-server support
def load_guild_settings():
    global guild_settings
    try:
        with open(settings_file, 'r') as f:
            guild_settings = json.load(f)
    except FileNotFoundError:
        guild_settings = {}

def save_guild_settings():
    with open(settings_file, 'w') as f:
        json.dump(guild_settings, f, indent=2)

def get_log_channel_id(guild_id):
    return guild_settings.get(str(guild_id), {}).get("log_channel_id")

def set_log_channel_id(guild_id, channel_id):
    if str(guild_id) not in guild_settings:
        guild_settings[str(guild_id)] = {}
    guild_settings[str(guild_id)]["log_channel_id"] = channel_id
    save_guild_settings()

# Warning system functions
def load_warnings():
    try:
        with open(warnings_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warnings(warnings_data):
    with open(warnings_file, 'w') as f:
        json.dump(warnings_data, f, indent=2)

def load_locked_channels():
    try:
        with open(locked_channels_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_locked_channels(locked_data):
    with open(locked_channels_file, 'w') as f:
        json.dump(locked_data, f, indent=2)

def load_xp_data():
    try:
        with open(xp_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_xp_data(xp_data):
    with open(xp_file, 'w') as f:
        json.dump(xp_data, f, indent=2)

def load_tokens():
    try:
        with open(tokens_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_tokens(tokens_data):
    with open(tokens_file, 'w') as f:
        json.dump(tokens_data, f, indent=2)

def load_reaction_roles():
    try:
        with open(reaction_roles_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_reaction_roles(reaction_data):
    with open(reaction_roles_file, 'w') as f:
        json.dump(reaction_data, f, indent=2)

def get_guild_prefix(guild_id):
    return guild_settings.get(str(guild_id), {}).get("prefix", "!")

def set_guild_prefix(guild_id, prefix):
    if str(guild_id) not in guild_settings:
        guild_settings[str(guild_id)] = {}
    guild_settings[str(guild_id)]["prefix"] = prefix
    save_guild_settings()

def get_greeting_channel_id(guild_id):
    return guild_settings.get(str(guild_id), {}).get("greeting_channel_id")

def set_greeting_channel_id(guild_id, channel_id):
    if str(guild_id) not in guild_settings:
        guild_settings[str(guild_id)] = {}
    guild_settings[str(guild_id)]["greeting_channel_id"] = channel_id
    save_guild_settings()

def calculate_level(xp):
    # Simple level calculation: level = sqrt(xp / 100)
    import math
    return int(math.sqrt(xp / 100))

def get_xp_for_level(level):
    return level * level * 100

async def ensure_level_roles(guild):
    """Create level roles if they don't exist"""
    for level, role_name in LEVEL_ROLES.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                await guild.create_role(name=role_name, color=discord.Color.blue(), reason="Auto-created level role")
            except Exception as e:
                print(f"Failed to create role {role_name}: {e}")

async def assign_level_roles(member, new_level):
    """Assign appropriate level roles to a member"""
    guild = member.guild
    await ensure_level_roles(guild)

    # Remove old level roles and add new ones
    for level, role_name in LEVEL_ROLES.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            if level <= new_level and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Reached level {new_level}")
                except Exception as e:
                    print(f"Failed to add role {role_name}: {e}")

def parse_time_duration(duration_str):
    """Parse duration string like '1h30m' into total minutes"""
    total_minutes = 0

    # Extract hours
    hours_match = re.search(r'(\d+)h', duration_str.lower())
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60

    # Extract minutes
    minutes_match = re.search(r'(\d+)m', duration_str.lower())
    if minutes_match:
        total_minutes += int(minutes_match.group(1))

    # Extract seconds
    seconds_match = re.search(r'(\d+)s', duration_str.lower())
    if seconds_match:
        total_minutes += int(seconds_match.group(1)) / 60

    return total_minutes

def cleanup_expired_warnings():
    warnings_data = load_warnings()
    current_time = datetime.datetime.now()

    for user_id in list(warnings_data.keys()):
        user_warnings = warnings_data[user_id]
        # Remove warnings older than 2 weeks
        user_warnings = [w for w in user_warnings if 
                        (current_time - datetime.datetime.fromisoformat(w['timestamp'])).days < 14]

        if user_warnings:
            warnings_data[user_id] = user_warnings
        else:
            del warnings_data[user_id]

    save_warnings(warnings_data)
    return warnings_data

async def timeout_user(guild, user, duration_hours, reason):
    """Timeout a user for specified hours"""
    try:
        member = guild.get_member(user.id)
        if member:
            timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=duration_hours)
            await member.edit(timed_out_until=timeout_until, reason=reason)
            return True
    except Exception as e:
        print(f"Error timing out user: {e}")
    return False

@bot.event
async def on_ready():
    global bot_start_time
    bot_start_time = datetime.datetime.now()
    print(f'Logged in as {bot.user}')
    try:
        scheduler.start()
    except Exception as e:
        print(f"Scheduler already running: {e}")
    load_guild_settings()

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    current_time = datetime.datetime.now()

    # Anti-raid detection
    if guild_id not in join_tracker:
        join_tracker[guild_id] = []

    join_tracker[guild_id].append(current_time)

    # Remove joins older than time window
    join_tracker[guild_id] = [timestamp for timestamp in join_tracker[guild_id] 
                             if (current_time - timestamp).seconds < RAID_TIME_WINDOW]

    # Check for raid
    if len(join_tracker[guild_id]) >= RAID_THRESHOLD:
        # Lock the server by removing send message permissions for @everyone
        try:
            for channel in member.guild.text_channels:
                overwrite = channel.overwrites_for(member.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(member.guild.default_role, overwrite=overwrite)

            # Log raid detection
            log_channel_id = get_log_channel_id(guild_id)
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    raid_embed = discord.Embed(
                        title="🚨 RAID DETECTED - SERVER LOCKED",
                        color=0xff0000,
                        timestamp=datetime.datetime.now()
                    )
                    raid_embed.add_field(name="Joins in 10 seconds", value=str(len(join_tracker[guild_id])), inline=True)
                    raid_embed.add_field(name="Action", value="All channels locked automatically", inline=True)
                    raid_embed.add_field(name="Latest joiner", value=f"{member.mention} ({member})", inline=True)
                    await log_channel.send(embed=raid_embed, content="@here")
        except Exception as e:
            print(f"Error locking server during raid: {e}")

    # Account age verification
    account_age = current_time - member.created_at.replace(tzinfo=None)
    if account_age.days < MIN_ACCOUNT_AGE_DAYS:
        try:
            timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
            await member.edit(timed_out_until=timeout_until, reason=f"Account too new: {account_age.days} days old")

            # Log account age timeout
            log_channel_id = get_log_channel_id(guild_id)
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    age_embed = discord.Embed(
                        title="👶 New Account Auto-Timeout",
                        color=0xffa500,
                        timestamp=datetime.datetime.now()
                    )
                    age_embed.add_field(name="User", value=f"{member.mention} ({member})", inline=True)
                    age_embed.add_field(name="Account Age", value=f"{account_age.days} days", inline=True)
                    age_embed.add_field(name="Action", value="12 hour timeout", inline=True)
                    await log_channel.send(embed=age_embed)
        except Exception as e:
            print(f"Error timing out new account: {e}")

    # Welcome message
    greeting_channel_id = get_greeting_channel_id(member.guild.id)
    if greeting_channel_id:
        greeting_channel = bot.get_channel(greeting_channel_id)
        if greeting_channel:
            account_age = (datetime.datetime.now() - member.created_at.replace(tzinfo=None)).days
            welcome_embed = discord.Embed(
                title="👋 Welcome!",
                description=f"Welcome to the server, {member.mention}!",
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            welcome_embed.add_field(name="Username", value=str(member), inline=True)
            welcome_embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
            welcome_embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await greeting_channel.send(embed=welcome_embed)

@bot.event
async def on_member_remove(member):
    # Leave message
    greeting_channel_id = get_greeting_channel_id(member.guild.id)
    if greeting_channel_id:
        greeting_channel = bot.get_channel(greeting_channel_id)
        if greeting_channel:
            leave_embed = discord.Embed(
                title="👋 Goodbye!",
                description=f"{member} has left the server.",
                color=0xff0000,
                timestamp=datetime.datetime.now()
            )
            leave_embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            await greeting_channel.send(embed=leave_embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    # Handle reaction roles
    reaction_roles_data = load_reaction_roles()
    message_id = str(reaction.message.id)

    if message_id in reaction_roles_data:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles_data[message_id]:
            role_id = reaction_roles_data[message_id][emoji_str]
            role = discord.utils.get(reaction.message.guild.roles, id=role_id)
            if role:
                try:
                    await user.add_roles(role, reason="Reaction role assignment")
                except Exception as e:
                    print(f"Failed to assign reaction role: {e}")

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return

    # Handle reaction roles removal
    reaction_roles_data = load_reaction_roles()
    message_id = str(reaction.message.id)

    if message_id in reaction_roles_data:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles_data[message_id]:
            role_id = reaction_roles_data[message_id][emoji_str]
            role = discord.utils.get(reaction.message.guild.roles, id=role_id)
            if role:
                try:
                    await user.remove_roles(role, reason="Reaction role removal")
                except Exception as e:
                    print(f"Failed to remove reaction role: {e}")

@bot.command()
async def logset(ctx, channel: discord.TextChannel):
    set_log_channel_id(ctx.guild.id, channel.id)
    await ctx.send(f"Logging channel set to {channel.mention}.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)  # allow commands to run
    if message.author.bot:
        return

    # Invite link auto-deletion (skip if user has manage messages or admin)
    if not isinstance(message.channel, discord.DMChannel):
        if not (message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator):
            # Check for Discord invite links
            if any(invite in message.content.lower() for invite in ['discord.gg/', 'discord.com/invite/', 'discordapp.com/invite/']):
                try:
                    await message.delete()
                    # Send warning to user
                    warning_msg = await message.channel.send(f"{message.author.mention}, invite links are not allowed!")
                    await asyncio.sleep(5)
                    await warning_msg.delete()

                    # Log deletion
                    log_channel_id = get_log_channel_id(message.guild.id)
                    if log_channel_id:
                        log_channel = bot.get_channel(log_channel_id)
                        if log_channel:
                            invite_embed = discord.Embed(
                                title="🔗 Invite Link Deleted",
                                color=0xff6600,
                                timestamp=datetime.datetime.now()
                            )
                            invite_embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                            invite_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                            invite_embed.add_field(name="Message", value=message.content[:500], inline=False)
                            await log_channel.send(embed=invite_embed)
                except Exception as e:
                    print(f"Error deleting invite: {e}")

        # Excessive mention detection
        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count >= MENTION_SPAM_THRESHOLD:
            try:
                # Timeout user for mention spam
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                await message.author.edit(timed_out_until=timeout_until, reason="Excessive mentions")

                # Delete the message
                await message.delete()

                # Log mention spam
                log_channel_id = get_log_channel_id(message.guild.id)
                if log_channel_id:
                    log_channel = bot.get_channel(log_channel_id)
                    if log_channel:
                        mention_embed = discord.Embed(
                            title="🔇 Mention Spam - User Timed Out",
                            color=0xff0000,
                            timestamp=datetime.datetime.now()
                        )
                        mention_embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                        mention_embed.add_field(name="Mentions", value=f"{mention_count} mentions", inline=True)
                        mention_embed.add_field(name="Action", value="1 hour timeout", inline=True)
                        await log_channel.send(embed=mention_embed)
            except Exception as e:
                print(f"Error handling mention spam: {e}")

    # DM spam detection with timeout capability
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        current_time = datetime.datetime.now()

        if user_id not in dm_tracker:
            dm_tracker[user_id] = []

        # Add current message timestamp
        dm_tracker[user_id].append(current_time)

        # Remove messages older than time window
        dm_tracker[user_id] = [timestamp for timestamp in dm_tracker[user_id] 
                              if (current_time - timestamp).seconds < DM_TIME_WINDOW]

        # Check if spam threshold exceeded
        if len(dm_tracker[user_id]) >= DM_SPAM_THRESHOLD:
            # Try to timeout user in all mutual guilds
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    timeout_success = await timeout_user(guild, message.author, 1, "Suspicious DM activity detected")

                    # Log to that guild's log channel
                    log_channel_id = get_log_channel_id(guild.id)
                    if log_channel_id:
                        log_channel = bot.get_channel(log_channel_id)
                        if log_channel:
                            alert_embed = discord.Embed(
                                title="🚨 Suspicious DM Activity - User Timed Out",
                                color=0xff0000,
                                timestamp=datetime.datetime.now()
                            )
                            alert_embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                            alert_embed.add_field(name="Messages sent", value=f"{len(dm_tracker[user_id])} messages in {DM_TIME_WINDOW} seconds", inline=True)
                            alert_embed.add_field(name="Action", value="User timed out for 1 hour" if timeout_success else "Failed to timeout user", inline=True)
                            await log_channel.send(embed=alert_embed)

            # Reset tracker for this user
            dm_tracker[user_id] = []

    # XP System (only for guild messages, not DMs)
    if not isinstance(message.channel, discord.DMChannel) and not message.author.bot:
        user_key = get_user_key(message.guild.id, message.author.id)
        current_time = datetime.datetime.now()

        # Check cooldown
        if user_key not in xp_cooldown or (current_time - xp_cooldown[user_key]).seconds >= XP_COOLDOWN_SECONDS:
            xp_data = load_xp_data()

            if user_key not in xp_data:
                xp_data[user_key] = 0

            # Award 15-25 XP per message
            xp_gain = random.randint(15, 25)
            old_level = calculate_level(xp_data[user_key])
            xp_data[user_key] += xp_gain
            new_level = calculate_level(xp_data[user_key])

            save_xp_data(xp_data)
            xp_cooldown[user_key] = current_time

            # Check for level up
            if new_level > old_level:
                await assign_level_roles(message.author, new_level)
                level_embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"{message.author.mention} has reached level {new_level}!",
                    color=0xffd700
                )
                level_embed.add_field(name="Total XP", value=f"{xp_data[user_key]:,}", inline=True)
                level_embed.add_field(name="Next Level", value=f"{get_xp_for_level(new_level + 1):,} XP", inline=True)
                await message.channel.send(embed=level_embed)

@bot.command()
async def warn(ctx):
    # Check if user has permission (administrator or manage messages)
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages):
        await ctx.send("You don't have permission to warn users.")
        return

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        await ctx.send("Which user would you like to warn? (mention them or provide their username)")
        user_msg = await bot.wait_for('message', check=check, timeout=60)

        # Try to get user from mention or username
        target_user = None
        if user_msg.mentions:
            target_user = user_msg.mentions[0]
        else:
            # Try to find by username
            target_user = discord.utils.get(ctx.guild.members, name=user_msg.content)
            if not target_user:
                target_user = discord.utils.get(ctx.guild.members, display_name=user_msg.content)

        if not target_user:
            await ctx.send("User not found. Please mention them or use their exact username.")
            return

        await ctx.send("What is the reason for this warning?")
        reason_msg = await bot.wait_for('message', check=check, timeout=60)
        reason = reason_msg.content

        # Add warning to database
        warnings_data = load_warnings()
        user_key = get_user_key(ctx.guild.id, target_user.id)

        if user_key not in warnings_data:
            warnings_data[user_key] = []

        warning_entry = {
            "warned_by": str(ctx.author.id),
            "warned_by_name": str(ctx.author),
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat(),
            "guild_id": str(ctx.guild.id)
        }

        warnings_data[user_key].append(warning_entry)
        save_warnings(warnings_data)

        warning_count = len(warnings_data[user_key])

        # Auto-timeout after 3 warnings
        if warning_count >= 3:
            timeout_success = await timeout_user(ctx.guild, target_user, 12, f"Automatic timeout: 3+ warnings reached")
            await ctx.send(f"⚠️ {target_user.mention} has been warned for: {reason}\n🚫 **AUTOMATIC TIMEOUT**: User has reached 3 warnings and has been timed out for 12 hours.")
        else:
            await ctx.send(f"⚠️ {target_user.mention} has been warned for: {reason}\nWarning {warning_count}/3")

        # Log to log channel
        log_channel_id = get_log_channel_id(ctx.guild.id)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="⚠️ User Warning Issued",
                    color=0xffaa00,
                    timestamp=datetime.datetime.now()
                )
                log_embed.add_field(name="Warned User", value=f"{target_user.mention} ({target_user})", inline=True)
                log_embed.add_field(name="Warned by", value=f"{ctx.author.mention} ({ctx.author})", inline=True)
                log_embed.add_field(name="Reason", value=reason, inline=False)
                log_embed.add_field(name="Total Warnings", value=f"{warning_count}/3", inline=True)
                if warning_count >= 3:
                    log_embed.add_field(name="Auto Action", value="User timed out for 12 hours", inline=True)
                await log_channel.send(embed=log_embed)

    except asyncio.TimeoutError:
        await ctx.send("Warning cancelled - no response received.")

@bot.command()
async def warnings(ctx):
    # Clean up expired warnings first
    warnings_data = cleanup_expired_warnings()

    # Filter warnings for current guild
    guild_warnings = {k: v for k, v in warnings_data.items() if k.startswith(f"{ctx.guild.id}_")}

    if not guild_warnings:
        await ctx.send("No active warnings found in this server.")
        return

    # Create leaderboard
    user_warning_counts = []
    for user_key, user_warnings in guild_warnings.items():
        try:
            parts = user_key.split('_')
            if len(parts) >= 2:
                user_id = int(parts[1])
                user = bot.get_user(user_id)
                if user:
                    user_warning_counts.append((user, len(user_warnings)))
        except (ValueError, IndexError):
            continue

    # Sort by warning count (descending)
    user_warning_counts.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="⚠️ Warnings Leaderboard",
        description="Users with active warnings in this server (last 2 weeks)",
        color=0xffaa00,
        timestamp=datetime.datetime.now()
    )

    leaderboard_text = ""
    for i, (user, count) in enumerate(user_warning_counts[:10]):  # Top 10
        leaderboard_text += f"{i+1}. {user.mention} - {count}/3 warning{'s' if count != 1 else ''}\n"

    if leaderboard_text:
        embed.add_field(name="Top Users", value=leaderboard_text, inline=False)
    else:
        embed.add_field(name="No Warnings", value="No active warnings found.", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def lock(ctx):
    # Check if user has permission
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_channels):
        await ctx.send("You don't have permission to lock channels.")
        return

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        await ctx.send("How long should this channel be locked? (e.g., '30m', '2h', '1d')")
        duration_msg = await bot.wait_for('message', check=check, timeout=60)
        duration_str = duration_msg.content.strip().lower()

        # Parse duration
        duration_minutes = 0
        if duration_str.endswith('m'):
            duration_minutes = int(duration_str[:-1])
        elif duration_str.endswith('h'):
            duration_minutes = int(duration_str[:-1]) * 60
        elif duration_str.endswith('d'):
            duration_minutes = int(duration_str[:-1]) * 60 * 24
        else:
            await ctx.send("Invalid duration format. Use 'm' for minutes, 'h' for hours, 'd' for days.")
            return

        # Lock the channel
        channel = ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        # Store lock info
        locked_data = load_locked_channels()
        unlock_time = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
        locked_data[str(channel.id)] = {
            "unlock_time": unlock_time.isoformat(),
            "locked_by": str(ctx.author.id),
            "guild_id": str(ctx.guild.id)
        }
        save_locked_channels(locked_data)

        # Schedule unlock
        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(
                unlock_channel(channel.id), bot.loop
            ),
            'date',
            run_date=unlock_time
        )

        await ctx.send(f"🔒 Channel locked for {duration_str}. Unlock scheduled for {unlock_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Log the lock
        log_channel_id = get_log_channel_id(ctx.guild.id)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel and log_channel != channel:
                log_embed = discord.Embed(
                    title="🔒 Channel Locked",
                    color=0xff6600,
                    timestamp=datetime.datetime.now()
                )
                log_embed.add_field(name="Channel", value=channel.mention, inline=True)
                log_embed.add_field(name="Locked by", value=ctx.author.mention, inline=True)
                log_embed.add_field(name="Duration", value=duration_str, inline=True)
                log_embed.add_field(name="Unlock time", value=unlock_time.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
                await log_channel.send(embed=log_embed)

    except asyncio.TimeoutError:
        await ctx.send("Lock cancelled - no response received.")
    except ValueError:
        await ctx.send("Invalid duration. Please enter a number followed by 'm', 'h', or 'd'.")

async def unlock_channel(channel_id):
    """Unlock a channel"""
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            overwrite = channel.overwrites_for(channel.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)

            await channel.send("🔓 Channel has been automatically unlocked.")

            # Remove from locked channels
            locked_data = load_locked_channels()
            if str(channel_id) in locked_data:
                del locked_data[str(channel_id)]
                save_locked_channels(locked_data)

            # Log the unlock
            log_channel_id = get_log_channel_id(channel.guild.id)
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel and log_channel != channel:
                    log_embed = discord.Embed(
                        title="🔓 Channel Unlocked",
                        color=0x00ff00,
                        timestamp=datetime.datetime.now()
                    )
                    log_embed.add_field(name="Channel", value=channel.mention, inline=True)
                    log_embed.add_field(name="Action", value="Automatic unlock", inline=True)
                    await log_channel.send(embed=log_embed)
    except Exception as e:
        print(f"Error unlocking channel {channel_id}: {e}")

@bot.command()
async def announce(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    # Send initial message as ephemeral (only visible to user)
    await ctx.author.send("What should the announcement say?")
    msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel), timeout=60)
    announcement_text = msg.content

    await ctx.author.send("What time should the announcement go out? (e.g., 6:00 PM EST or 3:30 PM PST)")
    msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel), timeout=60)
    time_str = msg.content.strip()

    await ctx.author.send("Which channel should it be posted in? Please type the channel name (e.g., general)")
    msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel), timeout=60)

    # Find channel by name in the correct guild
    channel_name = msg.content.strip().replace('#', '')
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.author.send("Channel not found. Make sure you typed the correct channel name. Cancelled.")
        return

    # Improved time parsing
    try:
        # Clean up the time string and make it uppercase for easier parsing
        time_str_clean = time_str.upper().replace(" ", "")

        # Determine timezone
        if "PST" in time_str_clean or "PT" in time_str_clean:
            timezone = pytz.timezone("US/Pacific")
            tz_name = "PST"
        elif "EST" in time_str_clean or "ET" in time_str_clean:
            timezone = pytz.timezone("US/Eastern")
            tz_name = "EST"
        else:
            # Default to EST if no timezone specified
            timezone = pytz.timezone("US/Eastern")
            tz_name = "EST"

        # Extract time part (remove timezone info)
        time_part = time_str_clean.replace("PST", "").replace("EST", "").replace("PT", "").replace("ET", "")

        # Determine AM/PM
        am_pm = "PM" if "PM" in time_part else "AM"

        # Extract hour and minute
        time_digits = time_part.replace("AM", "").replace("PM", "")

        if ":" in time_digits:
            hour_str, minute_str = time_digits.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
        else:
            # Handle cases like "6PM" without minutes
            hour = int(time_digits)
            minute = 0

        # Convert to 24-hour format
        if am_pm == "PM" and hour != 12:
            hour += 12
        elif am_pm == "AM" and hour == 12:
            hour = 0

        # Create target datetime in the specified timezone
        now = datetime.datetime.now(timezone)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has passed today, schedule for tomorrow
        if target < now:
            target += datetime.timedelta(days=1)

        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(
                channel.send(announcement_text), bot.loop
            ),
            'date',
            run_date=target
        )

        # Format the confirmation message
        time_display = target.strftime(f"%I:%M %p {tz_name}")
        await ctx.author.send(f"Announcement scheduled for {time_display} in #{channel.name}.")

        # Log the announcement creation to the CORRECT log channel (same guild)
        log_channel_id = get_log_channel_id(ctx.guild.id)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="📢 Announcement Scheduled",
                    color=0x00ff00,
                    timestamp=datetime.datetime.now()
                )
                log_embed.add_field(name="Created by", value=ctx.author.mention, inline=True)
                log_embed.add_field(name="Scheduled for", value=time_display, inline=True)
                log_embed.add_field(name="Target Channel", value=f"#{channel.name}", inline=True)
                log_embed.add_field(name="Message", value=announcement_text[:1000] + ("..." if len(announcement_text) > 1000 else ""), inline=False)
                await log_channel.send(embed=log_embed)

    except (ValueError, IndexError) as e:
        await ctx.author.send("Failed to parse time. Please use format like:\n• `6:30 PM EST`\n• `3 PM PST`\n• `11:45 AM EST`")
        print(f"Time parsing error: {e}")

@bot.command()
async def unlock_server(ctx):
    # Check if user has administrator permission
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator permissions to unlock the server.")
        return

    try:
        # Unlock all text channels
        for channel in ctx.guild.text_channels:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = None  # Reset to default
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        await ctx.send("🔓 Server has been unlocked. All channels are now accessible.")

        # Log server unlock
        log_channel_id = get_log_channel_id(ctx.guild.id)
        if log_channel_id:
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                unlock_embed = discord.Embed(
                    title="🔓 Server Unlocked",
                    color=0x00ff00,
                    timestamp=datetime.datetime.now()
                )
                unlock_embed.add_field(name="Unlocked by", value=ctx.author.mention, inline=True)
                unlock_embed.add_field(name="Action", value="All channels unlocked", inline=True)
                await log_channel.send(embed=unlock_embed)
    except Exception as e:
        await ctx.send(f"Error unlocking server: {e}")

# New Commands

@bot.command()
async def poll(ctx, question, *options):
    if len(options) < 2:
        await ctx.send("You need at least 2 options for a poll!")
        return

    if len(options) > 10:
        await ctx.send("Maximum 10 options allowed!")
        return

    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=0x00ff00,
        timestamp=datetime.datetime.now()
    )

    options_text = ""
    for i, option in enumerate(options):
        options_text += f"{reactions[i]} {option}\n"

    embed.add_field(name="Options", value=options_text, inline=False)
    embed.set_footer(text=f"Poll created by {ctx.author}")

    poll_message = await ctx.send(embed=embed)

    for i in range(len(options)):
        await poll_message.add_reaction(reactions[i])

@bot.command()
async def remindme(ctx, duration, *, reminder_text):
    try:
        total_minutes = parse_time_duration(duration)
        if total_minutes <= 0:
            await ctx.send("Invalid duration format! Use format like: `1h30m`, `45m`, `2h`")
            return

        remind_time = datetime.datetime.now() + datetime.timedelta(minutes=total_minutes)

        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(
                ctx.author.send(f"⏰ **Reminder:** {reminder_text}"), bot.loop
            ),
            'date',
            run_date=remind_time
        )

        await ctx.send(f"⏰ Reminder set! I'll DM you in {duration} with: {reminder_text}")

    except Exception as e:
        await ctx.send("Failed to set reminder. Use format like: `!remindme 1h30m Your reminder text`")

@bot.command()
async def greetingset(ctx, channel: discord.TextChannel):
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_guild):
        await ctx.send("You need administrator or manage server permissions to set the greeting channel.")
        return

    set_greeting_channel_id(ctx.guild.id, channel.id)
    await ctx.send(f"Greeting channel set to {channel.mention}. Welcome and leave messages will be posted there.")

@bot.command()
async def setprefix(ctx, new_prefix):
    if not (ctx.author.guild_permissions.administrator):
        await ctx.send("You need administrator permissions to change the bot prefix.")
        return

    if len(new_prefix) > 3:
        await ctx.send("Prefix must be 3 characters or less!")
        return

    set_guild_prefix(ctx.guild.id, new_prefix)
    await ctx.send(f"Bot prefix changed to `{new_prefix}`")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    uptime = datetime.datetime.now() - bot_start_time

    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    embed = discord.Embed(
        title="🏓 Pong!",
        color=0x00ff00,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="Uptime", value=uptime_str, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def xpleaderboard(ctx):
    xp_data = load_xp_data()
    guild_id = ctx.guild.id

    # Filter XP data for current guild
    guild_xp = {k: v for k, v in xp_data.items() if k.startswith(f"{guild_id}_")}

    if not guild_xp:
        await ctx.send("No XP data found for this server!")
        return

    # Create leaderboard
    leaderboard = []
    for user_key, xp in guild_xp.items():
        try:
            parts = user_key.split('_')
            if len(parts) >= 2:
                user_id = int(parts[1])
                user = bot.get_user(user_id)
                if user:
                    level = calculate_level(xp)
                    leaderboard.append((user, xp, level))
        except (ValueError, IndexError):
            continue

    # Sort by XP (descending)
    leaderboard.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        color=0xffd700,
        timestamp=datetime.datetime.now()
    )

    leaderboard_text = ""
    for i, (user, xp, level) in enumerate(leaderboard[:10]):
        leaderboard_text += f"{i+1}. {user.mention} - Level {level} ({xp:,} XP)\n"

    if leaderboard_text:
        embed.add_field(name="Top Users", value=leaderboard_text, inline=False)
    else:
        embed.add_field(name="No Data", value="No XP data available.", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def tokens(ctx):
    tokens_data = load_tokens()
    user_key = get_user_key(ctx.guild.id, ctx.author.id)
    balance = tokens_data.get(user_key, 0)

    embed = discord.Embed(
        title="🪙 Token Balance",
        description=f"{ctx.author.mention}, you have **{balance:,}** tokens!",
        color=0xffd700
    )
    await ctx.send(embed=embed)

@bot.command()
async def guessnumber(ctx):
    number = random.randint(1, 100)

    embed = discord.Embed(
        title="🎲 Guess the Number!",
        description="I'm thinking of a number between 1 and 100. You have 3 guesses!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    guesses = 0
    while guesses < 3:
        try:
            guess_msg = await bot.wait_for('message', check=check, timeout=30)
            guess = int(guess_msg.content)
            guesses += 1

            if guess == number:
                # Award tokens
                tokens_data = load_tokens()
                user_key = get_user_key(ctx.guild.id, ctx.author.id)
                tokens_data[user_key] = tokens_data.get(user_key, 0) + 50
                save_tokens(tokens_data)

                await ctx.send(f"🎉 Correct! The number was {number}! You earned 50 tokens!")
                return
            elif guess < number:
                await ctx.send(f"Too low! Guesses remaining: {3 - guesses}")
            else:
                await ctx.send(f"Too high! Guesses remaining: {3 - guesses}")
        except (ValueError, asyncio.TimeoutError):
            await ctx.send("Please enter a valid number!")
            break

    await ctx.send(f"Game over! The number was {number}. Better luck next time!")

@bot.command()
async def trivia(ctx):
    questions = [
        {"question": "What is the capital of France?", "answer": "paris", "options": ["London", "Berlin", "Paris", "Madrid"]},
        {"question": "What is 2 + 2?", "answer": "4", "options": ["3", "4", "5", "6"]},
        {"question": "What color do you get when you mix red and blue?", "answer": "purple", "options": ["Green", "Purple", "Yellow", "Orange"]},
        {"question": "How many legs does a spider have?", "answer": "8", "options": ["6", "8", "10", "12"]},
        {"question": "What is the largest planet in our solar system?", "answer": "jupiter", "options": ["Earth", "Mars", "Jupiter", "Saturn"]}
    ]

    q = random.choice(questions)

    embed = discord.Embed(
        title="🧠 Trivia Question",
        description=q["question"],
        color=0x0099ff
    )

    options_text = ""
    for i, option in enumerate(q["options"]):
        options_text += f"{i+1}. {option}\n"

    embed.add_field(name="Options", value=options_text, inline=False)
    await ctx.send(embed=embed)

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        answer_msg = await bot.wait_for('message', check=check, timeout=30)
        user_answer = answer_msg.content.lower().strip()

        if user_answer == q["answer"] or user_answer in [str(i+1) for i, opt in enumerate(q["options"]) if opt.lower() == q["answer"]]:
            # Award tokens
            tokens_data = load_tokens()
            user_key = get_user_key(ctx.guild.id, ctx.author.id)
            tokens_data[user_key] = tokens_data.get(user_key, 0) + 30
            save_tokens(tokens_data)

            await ctx.send(f"🎉 Correct! You earned 30 tokens!")
        else:
            await ctx.send(f"❌ Wrong! The correct answer was: {q['answer'].title()}")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Time's up! No answer received.")

@bot.command()
async def slots(ctx):
    symbols = ['🍎', '🍊', '🍋', '🍇', '🍓', '💎', '⭐']

    slot1 = random.choice(symbols)
    slot2 = random.choice(symbols)
    slot3 = random.choice(symbols)

    result_text = f"{slot1} | {slot2} | {slot3}"

    embed = discord.Embed(
        title="🎰 Slot Machine",
        description=result_text,
        color=0xff6600
    )

    tokens_won = 0
    if slot1 == slot2 == slot3:
        if slot1 == '💎':
            tokens_won = 200
        elif slot1 == '⭐':
            tokens_won = 150
        else:
            tokens_won = 100
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        tokens_won = 25

    if tokens_won > 0:
        tokens_data = load_tokens()
        user_key = get_user_key(ctx.guild.id, ctx.author.id)
        tokens_data[user_key] = tokens_data.get(user_key, 0) + tokens_won
        save_tokens(tokens_data)

        embed.add_field(name="Result", value=f"🎉 You won {tokens_won} tokens!", inline=False)
    else:
        embed.add_field(name="Result", value="😢 No match. Better luck next time!", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return

    tokens_data = load_tokens()
    giver_key = get_user_key(ctx.guild.id, ctx.author.id)
    receiver_key = get_user_key(ctx.guild.id, member.id)

    giver_balance = tokens_data.get(giver_key, 0)

    if giver_balance < amount:
        await ctx.send(f"You don't have enough tokens! You have {giver_balance:,} tokens.")
        return

    # Transfer tokens
    tokens_data[giver_key] = giver_balance - amount
    tokens_data[receiver_key] = tokens_data.get(receiver_key, 0) + amount
    save_tokens(tokens_data)

    await ctx.send(f"💰 {ctx.author.mention} gave {amount:,} tokens to {member.mention}!")

@bot.command()
async def reactionrole(ctx, message_id: int, emoji, role: discord.Role):
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_roles):
        await ctx.send("You need administrator or manage roles permissions to set up reaction roles.")
        return

    try:
        message = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("Message not found in this channel!")
        return
    except discord.HTTPException as e:
        await ctx.send(f"Error fetching message: {e}")
        return

    reaction_roles_data = load_reaction_roles()
    message_key = str(message_id)

    if message_key not in reaction_roles_data:
        reaction_roles_data[message_key] = {}

    reaction_roles_data[message_key][str(emoji)] = role.id
    save_reaction_roles(reaction_roles_data)

    await message.add_reaction(emoji)
    await ctx.send(f"Reaction role set! Users can react with {emoji} to get the {role.name} role.")

@bot.command()
async def gamble(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Amount must be positive!")
        return

    tokens_data = load_tokens()
    user_key = get_user_key(ctx.guild.id, ctx.author.id)
    balance = tokens_data.get(user_key, 0)

    if balance < amount:
        await ctx.send(f"You don't have enough tokens! You have {balance:,} tokens.")
        return

    # 40% chance to win, 60% chance to lose
    if random.random() < 0.4:
        winnings = amount * 2
        tokens_data[user_key] = balance + amount  # They get their bet back + winnings
        save_tokens(tokens_data)
        await ctx.send(f"🎉 You won! You gained {winnings:,} tokens! New balance: {tokens_data[user_key]:,}")
    else:
        tokens_data[user_key] = balance - amount
        save_tokens(tokens_data)
        await ctx.send(f"😢 You lost {amount:,} tokens. New balance: {tokens_data[user_key]:,}")

@bot.command()
async def steal(ctx, target: discord.Member):
    if target.bot:
        await ctx.send("You can't steal from bots!")
        return

    if target == ctx.author:
        await ctx.send("You can't steal from yourself!")
        return

    tokens_data = load_tokens()
    thief_key = get_user_key(ctx.guild.id, ctx.author.id)
    target_key = get_user_key(ctx.guild.id, target.id)

    thief_balance = tokens_data.get(thief_key, 0)
    target_balance = tokens_data.get(target_key, 0)

    if target_balance < 10:
        await ctx.send(f"{target.mention} doesn't have enough tokens to steal from!")
        return

    # 30% chance to succeed, 70% chance to fail
    if random.random() < 0.3:
        stolen_amount = min(random.randint(10, 100), target_balance // 2)
        tokens_data[thief_key] = thief_balance + stolen_amount
        tokens_data[target_key] = target_balance - stolen_amount
        save_tokens(tokens_data)
        await ctx.send(f"🥷 {ctx.author.mention} successfully stole {stolen_amount:,} tokens from {target.mention}!")
    else:
        # Failed steal - lose some tokens as penalty
        penalty = min(50, thief_balance)
        tokens_data[thief_key] = max(0, thief_balance - penalty)
        save_tokens(tokens_data)
        await ctx.send(f"🚨 {ctx.author.mention} failed to steal and lost {penalty:,} tokens as penalty!")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🏪 Token Shop",
        description="Spend your tokens on these items!",
        color=0x00ff00
    )

    items = """
    **Ranks & Roles:**
    `VIP` - 1,000 tokens - Special VIP role
    `Premium` - 2,500 tokens - Premium member role
    `Elite` - 5,000 tokens - Elite status role

    **Cosmetics:**
    `color_red` - 500 tokens - Red name color
    `color_blue` - 500 tokens - Blue name color
    `color_gold` - 1,000 tokens - Gold name color

    **Perks:**
    `immunity` - 10,000 tokens - 24h warning immunity
    `double_xp` - 3,000 tokens - 2x XP for 24 hours
    """

    embed.add_field(name="Available Items", value=items, inline=False)
    embed.add_field(name="How to Buy", value="Use `!buy item_name` to purchase", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_name):
    tokens_data = load_tokens()
    user_key = get_user_key(ctx.guild.id, ctx.author.id)
    balance = tokens_data.get(user_key, 0)

    # Define shop items with prices
    shop_items = {
        "vip": {"price": 1000, "role_name": "VIP", "description": "VIP member role"},
        "premium": {"price": 2500, "role_name": "Premium", "description": "Premium member role"},
        "elite": {"price": 5000, "role_name": "Elite", "description": "Elite status role"},
        "color_red": {"price": 500, "role_name": "Red", "description": "Red name color"},
        "color_blue": {"price": 500, "role_name": "Blue", "description": "Blue name color"},
        "color_gold": {"price": 1000, "role_name": "Gold", "description": "Gold name color"},
        "immunity": {"price": 10000, "role_name": "Warning Immunity", "description": "24h warning immunity"},
        "double_xp": {"price": 3000, "role_name": "Double XP", "description": "2x XP for 24 hours"}
    }

    item_name = item_name.lower()

    if item_name not in shop_items:
        await ctx.send("Item not found! Use `!shop` to see available items.")
        return

    item = shop_items[item_name]

    if balance < item["price"]:
        await ctx.send(f"Not enough tokens! You need {item['price']:,} tokens but have {balance:,}.")
        return

    # Try to find or create the role
    role = discord.utils.get(ctx.guild.roles, name=item["role_name"])
    if not role:
        try:
            # Create role with appropriate color
            color = discord.Color.default()
            if "red" in item_name:
                color = discord.Color.red()
            elif "blue" in item_name:
                color = discord.Color.blue()
            elif "gold" in item_name:
                color = discord.Color.gold()
            elif item_name in ["vip", "premium", "elite"]:
                color = discord.Color.purple()

            role = await ctx.guild.create_role(name=item["role_name"], color=color, reason=f"Shop item purchased by {ctx.author}")
        except Exception as e:
            await ctx.send(f"Failed to create role: {e}")
            return

    # Give role to user
    try:
        await ctx.author.add_roles(role, reason="Token shop purchase")

        # Deduct tokens
        tokens_data[user_key] = balance - item["price"]
        save_tokens(tokens_data)

        await ctx.send(f"🎉 Successfully purchased {item['description']}! You now have the {role.mention} role. Remaining tokens: {tokens_data[user_key]:,}")

    except Exception as e:
        await ctx.send(f"Failed to assign role: {e}")

@bot.command()
async def commands(ctx):
    embed = discord.Embed(
        title="🍎 Apple Bot Commands",
        description="Here are all available commands for the Apple bot:",
        color=0xff0000,
        timestamp=datetime.datetime.now()
    )

    # Split commands into multiple fields to avoid 1024 character limit
    mod_commands = """• `!warn` - Warn a user (3 warnings = 12h timeout)
• `!warnings` - View warnings leaderboard
• `!lock` - Lock a channel for specified duration
• `!unlock_server` - Unlock server after raid protection"""

    utility_commands = """• `!announce` - Schedule an announcement
• `!logset #channel` - Set the logging channel
• `!greetingset #channel` - Set welcome/leave messages channel
• `!setprefix ?` - Change bot prefix for this server
• `!ping` - Check bot latency and uptime
• `!poll "Question?" option1 option2...` - Create a reaction poll
• `!remindme 1h30m text` - Set a personal reminder
• `!reactionrole message_id emoji @role` - Set up reaction roles"""

    xp_commands = """• `!xpleaderboard` - View XP leaderboard
• Auto-leveling system with role rewards
• Earn XP by chatting (1 min cooldown)"""

    game_commands = """• `!tokens` - Check your token balance
• `!guessnumber` - Number guessing game
• `!trivia` - Answer trivia questions
• `!slots` - Play slot machine
• `!give @user amount` - Give tokens to another user
• `!gamble amount` - Gamble tokens (40% win chance)
• `!steal @user` - Attempt to steal tokens (30% success)
• `!shop` - View items available for purchase
• `!buy item_name` - Purchase items with tokens"""

    security_features = """• Anti-raid join detection
• Account age verification
• Invite link auto-deletion
• Mention spam detection
• DM spam detection
• Multi-server support"""

    embed.add_field(name="🛡️ Moderation Commands", value=mod_commands, inline=False)
    embed.add_field(name="⚙️ Utility Commands", value=utility_commands, inline=False)
    embed.add_field(name="🏆 XP & Leveling", value=xp_commands, inline=False)
    embed.add_field(name="🎮 Mini-Games & Tokens", value=game_commands, inline=False)
    embed.add_field(name="🔒 Security Features", value=security_features, inline=False)
    embed.add_field(name="Permissions", value="Most moderation commands require Administrator or Manage Messages permissions.", inline=False)
    embed.set_footer(text="Apple Bot v1.0 - All-in-one Discord bot with games, XP, and moderation")

    await ctx.send(embed=embed)

import os
bot.run(os.getenv('DISCORD_TOKEN'))
