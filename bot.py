import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json
import datetime
import pytz

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

scheduler = AsyncIOScheduler()
scheduler.start()

log_channel_id = None
log_settings_file = "log_settings.json"

# Load log channel settings
def load_log_channel():
    global log_channel_id
    try:
        with open(log_settings_file, 'r') as f:
            data = json.load(f)
            log_channel_id = data.get("log_channel_id")
    except FileNotFoundError:
        pass

def save_log_channel(channel_id):
    with open(log_settings_file, 'w') as f:
        json.dump({"log_channel_id": channel_id}, f)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_log_channel()

@bot.command()
async def logset(ctx, channel: discord.TextChannel):
    save_log_channel(channel.id)
    await ctx.send(f"Logging channel set to {channel.mention}.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)  # allow commands to run
    if message.author.bot:
        return
    if log_channel_id:
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(
                f"[{message.channel}] {message.author}: {message.content}"
            )

@bot.command()
async def announce(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    await ctx.send("What should the announcement say?")
    msg = await bot.wait_for('message', check=check, timeout=60)
    announcement_text = msg.content

    await ctx.send("What time should the announcement go out? (e.g., 6:00 PM EST)")
    msg = await bot.wait_for('message', check=check, timeout=60)
    time_str = msg.content

    await ctx.send("Which channel should it be posted in? Mention it like #channel.")
    msg = await bot.wait_for('message', check=check, timeout=60)
    channel = msg.channel_mentions[0] if msg.channel_mentions else None

    if not channel:
        await ctx.send("No valid channel mentioned. Cancelled.")
        return

    # Time parsing
    try:
        hour, minute = map(int, time_str.split(":")[0:2])
        am_pm = "PM" if "PM" in time_str.upper() else "AM"
        if am_pm == "PM" and hour != 12:
            hour += 12
        elif am_pm == "AM" and hour == 12:
            hour = 0

        now = datetime.datetime.now(pytz.timezone("US/Eastern"))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now:
            target += datetime.timedelta(days=1)

        scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(
                channel.send(announcement_text), bot.loop
            ),
            'date',
            run_date=target
        )

        await ctx.send(f"Announcement scheduled for {time_str} in {channel.mention}.")
    except Exception as e:
        await ctx.send("Failed to parse time. Try again in format HH:MM AM/PM EST.")
        print(e)

# --- More features like warnings, raid protection, economy will go here ---

bot.run("YOUR_BOT_TOKEN")
