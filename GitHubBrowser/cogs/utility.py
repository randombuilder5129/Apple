import discord
from discord.ext import commands
import logging
import asyncio

logger = logging.getLogger(__name__)

class Utility(commands.Cog):
    """Core utility functionality"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_utility_tables(self):
        """Create utility tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS utility_data (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT,
                        user_id BIGINT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
        except Exception as e:
            logger.error(f"Database error in utility: {e}")

    @commands.command(name="calculator")
    async def calculator(self, ctx, *, expression: str):
        """Perform mathematical calculations"""
        try:
            # Safe evaluation for basic math
            allowed_chars = set('0123456789+-*/().**. ')
            if not all(c in allowed_chars for c in expression):
                await ctx.send("❌ Invalid characters in expression!")
                return
            
            # Replace ** with pow for safety
            expression = expression.replace('**', '^')
            
            # Basic math operations only
            import ast
            import operator
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_expr(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_expr(node.operand))
                else:
                    raise TypeError(node)
            
            result = eval_expr(ast.parse(expression.replace('^', '**'), mode='eval').body)
            
            embed = discord.Embed(
                title="🧮 Calculator",
                color=0x00ff00
            )
            embed.add_field(name="Expression", value=f"`{expression}`", inline=False)
            embed.add_field(name="Result", value=f"`{result}`", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error calculating: Invalid expression!")
    
    @commands.command(name="weather")
    async def weather_info(self, ctx, *, location: str):
        """Get weather information for any location"""
        embed = discord.Embed(
            title=f"🌤️ Weather for {location}",
            description="Weather service currently unavailable",
            color=0x87ceeb
        )
        embed.add_field(name="Temperature", value="N/A", inline=True)
        embed.add_field(name="Conditions", value="Service Offline", inline=True)
        embed.add_field(name="Humidity", value="N/A", inline=True)
        embed.set_footer(text="Weather API integration required")
        await ctx.send(embed=embed)
    
    @commands.command(name="translate")
    async def translate_text(self, ctx, target_language: str, *, text: str):
        """Translate text between languages"""
        embed = discord.Embed(
            title="🌍 Translation Service",
            color=0x4169e1
        )
        embed.add_field(name="Original", value=text[:1000], inline=False)
        embed.add_field(name=f"Translated ({target_language})", value="Translation service currently unavailable", inline=False)
        embed.set_footer(text="Translation API integration required")
        await ctx.send(embed=embed)
    
    @commands.command(name="timezone")
    async def timezone_convert(self, ctx, timezone: str = "UTC"):
        """Convert time between timezones"""
        from datetime import datetime
        import pytz
        
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            
            embed = discord.Embed(
                title="🕐 Timezone Information",
                color=0x00ff00
            )
            embed.add_field(name="Timezone", value=timezone, inline=True)
            embed.add_field(name="Current Time", value=current_time.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            embed.add_field(name="UTC Offset", value=str(current_time.utcoffset()), inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception:
            await ctx.send(f"❌ Invalid timezone: {timezone}")
    
    @commands.hybrid_command(name="remind")
    async def remind(self, ctx, time: str, *, reminder: str):
        """Set a reminder"""
        try:
            # Parse time
            import re
            time_match = re.match(r'(\d+)([smhd])', time.lower())
            if not time_match:
                await ctx.send("❌ Invalid time format! Use: 5s, 10m, 1h, 2d")
                return
            
            amount, unit = time_match.groups()
            amount = int(amount)
            
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            seconds = amount * multipliers[unit]
            
            if seconds > 604800:  # 7 days max
                await ctx.send("❌ Reminder cannot be longer than 7 days!")
                return
            
            embed = discord.Embed(
                title="⏰ Reminder Set",
                description=f"I'll remind you about: {reminder}",
                color=0x00ff00
            )
            embed.add_field(name="Time", value=f"{amount}{unit}", inline=True)
            
            await ctx.send(embed=embed)
            
            # Wait and send reminder
            await asyncio.sleep(seconds)
            
            reminder_embed = discord.Embed(
                title="⏰ Reminder",
                description=f"{ctx.author.mention}, you asked me to remind you about: {reminder}",
                color=0xffff00
            )
            
            await ctx.send(embed=reminder_embed)
            
        except Exception as e:
            await ctx.send("❌ Error setting reminder!")
    
    @commands.command(name="timer")
    async def start_timer(self, ctx, duration: str):
        """Start a countdown timer"""
        try:
            import re
            time_match = re.match(r'(\d+)([smh])', duration.lower())
            if not time_match:
                await ctx.send("❌ Invalid time format! Use: 30s, 5m, 1h")
                return
            
            amount, unit = time_match.groups()
            amount = int(amount)
            
            multipliers = {'s': 1, 'm': 60, 'h': 3600}
            seconds = amount * multipliers[unit]
            
            if seconds > 3600:  # 1 hour max
                await ctx.send("❌ Timer cannot be longer than 1 hour!")
                return
            
            embed = discord.Embed(
                title="⏱️ Timer Started",
                description=f"Timer set for {amount}{unit}",
                color=0x00ff00
            )
            
            message = await ctx.send(embed=embed)
            
            # Update every 10 seconds for timers > 30 seconds
            if seconds > 30:
                while seconds > 0:
                    if seconds <= 10:
                        break
                    await asyncio.sleep(10)
                    seconds -= 10
                    
                    embed = discord.Embed(
                        title="⏱️ Timer Running",
                        description=f"Time remaining: {seconds}s",
                        color=0xffff00
                    )
                    await message.edit(embed=embed)
            
            # Final countdown
            await asyncio.sleep(seconds)
            
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"{ctx.author.mention}, your timer has finished!",
                color=0xff0000
            )
            
            await message.edit(embed=embed)
            
        except Exception as e:
            await ctx.send("❌ Error starting timer!")
    
    @commands.command(name="qr")
    async def generate_qr(self, ctx, *, text: str):
        """Generate QR codes for text or URLs"""
        embed = discord.Embed(
            title="📱 QR Code Generator",
            description=f"QR code for: {text[:100]}",
            color=0x000000
        )
        embed.add_field(name="Text", value=text[:500], inline=False)
        embed.set_footer(text="QR code generation requires additional setup")
        await ctx.send(embed=embed)
    
    @commands.command(name="shorturl")
    async def shorten_url(self, ctx, url: str):
        """Create shortened URLs"""
        if not url.startswith(('http://', 'https://')):
            await ctx.send("❌ Please provide a valid URL starting with http:// or https://")
            return
        
        embed = discord.Embed(
            title="🔗 URL Shortener",
            color=0x0080ff
        )
        embed.add_field(name="Original URL", value=url, inline=False)
        embed.add_field(name="Shortened URL", value="URL shortening service unavailable", inline=False)
        embed.set_footer(text="URL shortening API integration required")
        await ctx.send(embed=embed)
    
    @commands.command(name="poll")
    async def create_poll(self, ctx, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
        """Create a poll for voting"""
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        if option5:
            options.append(option5)
        
        if len(options) > 5:
            await ctx.send("❌ Maximum 5 options allowed!")
            return
        
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=0x00bfff
        )
        
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        for i, option in enumerate(options):
            embed.add_field(
                name=f"{reactions[i]} Option {i+1}",
                value=option,
                inline=False
            )
        
        embed.set_footer(text=f"Created by {ctx.author.display_name}")
        
        message = await ctx.send(embed=embed)
        
        for i in range(len(options)):
            await message.add_reaction(reactions[i])
    
    @commands.command(name="random")
    async def random_number(self, ctx, min_num: int = 1, max_num: int = 100):
        """Generate random numbers"""
        if min_num >= max_num:
            await ctx.send("❌ Minimum must be less than maximum!")
            return
        
        if max_num - min_num > 1000000:
            await ctx.send("❌ Range too large! Maximum range is 1,000,000")
            return
        
        import random
        result = random.randint(min_num, max_num)
        
        embed = discord.Embed(
            title="🎲 Random Number",
            color=0xff6b35
        )
        embed.add_field(name="Result", value=f"**{result}**", inline=True)
        embed.add_field(name="Range", value=f"{min_num} - {max_num}", inline=True)
        embed.add_field(name="Possibilities", value=f"{max_num - min_num + 1:,}", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))