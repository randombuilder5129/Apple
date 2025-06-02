
import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json
import datetime
import pytz
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

scheduler = AsyncIOScheduler()

# Multi-server support - store settings per guild
guild_settings = {}
settings_file = "guild_settings.json"
warnings_file = "warnings.json"
locked_channels_file = "locked_channels.json"

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
    print(f'Logged in as {bot.user}')
    scheduler.start()
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
        user_key = f"{ctx.guild.id}_{target_user.id}"  # Guild-specific warnings
        
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
            user_id = int(user_key.split('_')[1])
            user = bot.get_user(user_id)
            if user:
                user_warning_counts.append((user, len(user_warnings)))
        except:
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

@bot.command()
async def commands(ctx):
    embed = discord.Embed(
        title="🍎 Apple Bot Commands",
        description="Here are all available commands for the Apple bot:",
        color=0xff0000,
        timestamp=datetime.datetime.now()
    )
    
    commands_text = """
    **Moderation Commands:**
    • `!warn` - Warn a user (3 warnings = 12h timeout)
    • `!warnings` - View warnings leaderboard
    • `!lock` - Lock a channel for specified duration
    • `!unlock_server` - Unlock server after raid protection
    
    **Utility Commands:**
    • `!announce` - Schedule an announcement
    • `!logset #channel` - Set the logging channel
    • `!commands` - Display this commands list
    
    **Security Features:**
    • Anti-raid join detection (5+ joins in 10s = server lock)
    • Account age verification (3+ days required)
    • Automatic invite link deletion
    • Excessive mention detection (5+ mentions = timeout)
    • DM spam detection with timeout
    • Multi-server support
    """
    
    embed.add_field(name="Available Commands", value=commands_text, inline=False)
    embed.add_field(name="Permissions", value="Most moderation commands require Administrator or Manage Messages permissions.", inline=False)
    embed.set_footer(text="Apple Bot v0.02 - All-in-one Discord moderation bot")
    
    await ctx.send(embed=embed)

import os
bot.run(os.getenv('DISCORD_TOKEN'))
