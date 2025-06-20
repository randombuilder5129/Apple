import discord
from discord.ext import commands, tasks
import asyncio
import asyncpg
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

class GiveawayView(discord.ui.View):
    """Interactive giveaway participation view"""
    
    def __init__(self, giveaway_id, bot):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.bot = bot
    
    @discord.ui.button(label='🎉 Enter Giveaway', style=discord.ButtonStyle.primary, custom_id='enter_giveaway')
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle giveaway entry"""
        if not self.bot.db_pool:
            await interaction.response.send_message("❌ Giveaway system unavailable - database offline.", ephemeral=True)
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Check if user already entered
                existing = await conn.fetchrow(
                    "SELECT id FROM giveaway_entries WHERE giveaway_id = $1 AND user_id = $2",
                    self.giveaway_id, interaction.user.id
                )
                
                if existing:
                    await interaction.response.send_message("❌ You're already entered in this giveaway!", ephemeral=True)
                    return
                
                # Check if giveaway is still active
                giveaway = await conn.fetchrow(
                    "SELECT * FROM giveaways WHERE id = $1 AND status = 'active'",
                    self.giveaway_id
                )
                
                if not giveaway:
                    await interaction.response.send_message("❌ This giveaway is no longer active!", ephemeral=True)
                    return
                
                # Check if giveaway has ended
                if self.bot.get_current_time() > giveaway['end_time']:
                    await interaction.response.send_message("❌ This giveaway has already ended!", ephemeral=True)
                    return
                
                # Add user to giveaway
                await conn.execute(
                    "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES ($1, $2)",
                    self.giveaway_id, interaction.user.id
                )
                
                # Get current entry count
                entry_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = $1",
                    self.giveaway_id
                )
                
                embed = discord.Embed(
                    title="🎉 Giveaway Entry Confirmed",
                    description=f"You're now entered in the giveaway for **{giveaway['prize']}**!",
                    color=0x00ff00
                )
                embed.add_field(name="Total Entries", value=str(entry_count), inline=True)
                embed.add_field(name="Ends", value=f"<t:{int(giveaway['end_time'].timestamp())}:R>", inline=True)
                embed.set_footer(text="Good luck!")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error entering giveaway: {e}")
            await interaction.response.send_message("❌ An error occurred while entering the giveaway.", ephemeral=True)
    
    @discord.ui.button(label='📊 View Entries', style=discord.ButtonStyle.secondary, custom_id='view_entries')
    async def view_entries(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View giveaway entry count and time remaining"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                giveaway = await conn.fetchrow(
                    "SELECT * FROM giveaways WHERE id = $1",
                    self.giveaway_id
                )
                
                if not giveaway:
                    await interaction.response.send_message("❌ Giveaway not found!", ephemeral=True)
                    return
                
                entry_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = $1",
                    self.giveaway_id
                )
                
                embed = discord.Embed(
                    title="📊 Giveaway Statistics",
                    description=f"**Prize:** {giveaway['prize']}",
                    color=0x7289da
                )
                embed.add_field(name="Total Entries", value=str(entry_count), inline=True)
                embed.add_field(name="Winners", value=str(giveaway['winners']), inline=True)
                embed.add_field(name="Status", value=giveaway['status'].title(), inline=True)
                embed.add_field(name="Hosted By", value=f"<@{giveaway['creator_id']}>", inline=True)
                embed.add_field(name="Ends", value=f"<t:{int(giveaway['end_time'].timestamp())}:R>", inline=True)
                
                if giveaway['requirements']:
                    embed.add_field(name="Requirements", value=giveaway['requirements'], inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error viewing giveaway entries: {e}")
            await interaction.response.send_message("❌ An error occurred while fetching giveaway data.", ephemeral=True)

class Giveaways(commands.Cog):
    """Interactive giveaway system with comprehensive management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()
    
    async def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_giveaways.cancel()
    
    async def create_giveaway_tables(self):
        """Create giveaway tables in database"""
        if not self.bot.db_pool:
            return
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message_id BIGINT,
                    creator_id BIGINT NOT NULL,
                    prize TEXT NOT NULL,
                    winners INTEGER DEFAULT 1,
                    end_time TIMESTAMP NOT NULL,
                    requirements TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS giveaway_entries (
                    id SERIAL PRIMARY KEY,
                    giveaway_id INTEGER REFERENCES giveaways(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    entered_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(giveaway_id, user_id)
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS giveaway_winners (
                    id SERIAL PRIMARY KEY,
                    giveaway_id INTEGER REFERENCES giveaways(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    prize_claimed BOOLEAN DEFAULT FALSE,
                    won_at TIMESTAMP DEFAULT NOW()
                )
            ''')
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize giveaway tables when bot is ready"""
        await self.create_giveaway_tables()
    
    @commands.command(name='gcreate')
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, duration: str, winners: int = 1, *, prize: str):
        """Create a new interactive giveaway
        
        Usage: !gcreate <duration> [winners] <prize>
        Example: !gcreate 1h 2 Discord Nitro
        """
        try:
            # Parse duration
            duration_seconds = self.parse_duration(duration)
            if duration_seconds < 60:
                await ctx.send("❌ Giveaway duration must be at least 1 minute!")
                return
            
            if duration_seconds > 7 * 24 * 3600:  # 7 days max
                await ctx.send("❌ Giveaway duration cannot exceed 7 days!")
                return
            
            if winners < 1 or winners > 20:
                await ctx.send("❌ Number of winners must be between 1 and 20!")
                return
            
            end_time = self.bot.get_current_time() + timedelta(seconds=duration_seconds)
            
            # Create giveaway in database
            async with self.bot.db_pool.acquire() as conn:
                giveaway_id = await conn.fetchval(
                    """
                    INSERT INTO giveaways (guild_id, channel_id, creator_id, prize, winners, end_time)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    ctx.guild.id, ctx.channel.id, ctx.author.id, prize, winners, end_time
                )
            
            # Create giveaway embed
            embed = discord.Embed(
                title="🎉 GIVEAWAY! 🎉",
                description=f"**Prize:** {prize}",
                color=0xffd700
            )
            embed.add_field(name="Winners", value=str(winners), inline=True)
            embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.add_field(name="Hosted by", value=ctx.author.mention, inline=True)
            embed.add_field(name="How to Enter", value="Click the 🎉 button below to enter!", inline=False)
            embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
            embed.timestamp = self.bot.get_current_time()
            
            # Send giveaway message with interactive view
            view = GiveawayView(giveaway_id, self.bot)
            message = await ctx.send(embed=embed, view=view)
            
            # Update message ID in database
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE giveaways SET message_id = $1 WHERE id = $2",
                    message.id, giveaway_id
                )
            
            # Delete the command message
            try:
                await ctx.message.delete()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            await ctx.send(f"❌ Error creating giveaway: {str(e)}")
    
    @commands.command(name='gend')
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway(self, ctx, giveaway_id: int):
        """Manually end a giveaway early"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                giveaway = await conn.fetchrow(
                    "SELECT * FROM giveaways WHERE id = $1 AND guild_id = $2 AND status = 'active'",
                    giveaway_id, ctx.guild.id
                )
                
                if not giveaway:
                    await ctx.send("❌ Active giveaway with that ID not found!")
                    return
                
                # End the giveaway
                await self.end_giveaway_process(giveaway)
                await ctx.send(f"✅ Giveaway #{giveaway_id} has been ended manually!")
                
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}")
            await ctx.send(f"❌ Error ending giveaway: {str(e)}")
    
    @commands.command(name='greroll')
    @commands.has_permissions(manage_guild=True)
    async def reroll_giveaway(self, ctx, giveaway_id: int):
        """Reroll winners for a completed giveaway"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                giveaway = await conn.fetchrow(
                    "SELECT * FROM giveaways WHERE id = $1 AND guild_id = $2 AND status = 'completed'",
                    giveaway_id, ctx.guild.id
                )
                
                if not giveaway:
                    await ctx.send("❌ Completed giveaway with that ID not found!")
                    return
                
                # Get all entries
                entries = await conn.fetch(
                    "SELECT user_id FROM giveaway_entries WHERE giveaway_id = $1",
                    giveaway_id
                )
                
                if len(entries) < giveaway['winners']:
                    await ctx.send("❌ Not enough entries to reroll!")
                    return
                
                # Remove old winners
                await conn.execute(
                    "DELETE FROM giveaway_winners WHERE giveaway_id = $1",
                    giveaway_id
                )
                
                # Select new winners
                winners = random.sample(entries, min(giveaway['winners'], len(entries)))
                
                # Add new winners to database
                for winner in winners:
                    await conn.execute(
                        "INSERT INTO giveaway_winners (giveaway_id, user_id) VALUES ($1, $2)",
                        giveaway_id, winner['user_id']
                    )
                
                # Announce reroll
                guild = self.bot.get_guild(giveaway['guild_id'])
                channel = guild.get_channel(giveaway['channel_id'])
                
                if channel:
                    embed = discord.Embed(
                        title="🎉 Giveaway Rerolled!",
                        description=f"**Prize:** {giveaway['prize']}",
                        color=0x00ff00
                    )
                    
                    winner_mentions = [f"<@{w['user_id']}>" for w in winners]
                    embed.add_field(
                        name=f"New Winner{'s' if len(winners) > 1 else ''}",
                        value="\n".join(winner_mentions),
                        inline=False
                    )
                    embed.set_footer(text=f"Rerolled by {ctx.author} • Giveaway ID: {giveaway_id}")
                    
                    await channel.send(embed=embed)
                
                await ctx.send(f"✅ Giveaway #{giveaway_id} has been rerolled!")
                
        except Exception as e:
            logger.error(f"Error rerolling giveaway: {e}")
            await ctx.send(f"❌ Error rerolling giveaway: {str(e)}")
    
    @commands.command(name='glist')
    async def list_giveaways(self, ctx):
        """List all active giveaways in the server"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                giveaways = await conn.fetch(
                    "SELECT * FROM giveaways WHERE guild_id = $1 AND status = 'active' ORDER BY end_time",
                    ctx.guild.id
                )
                
                if not giveaways:
                    embed = discord.Embed(
                        title="🎉 Active Giveaways",
                        description="No active giveaways found!",
                        color=0xff9900
                    )
                    await ctx.send(embed=embed)
                    return
                
                embed = discord.Embed(
                    title="🎉 Active Giveaways",
                    description=f"Found {len(giveaways)} active giveaway{'s' if len(giveaways) != 1 else ''}",
                    color=0x00ff00
                )
                
                for giveaway in giveaways[:10]:  # Limit to 10 for embed size
                    entry_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = $1",
                        giveaway['id']
                    )
                    
                    embed.add_field(
                        name=f"ID: {giveaway['id']} - {giveaway['prize']}",
                        value=f"**Entries:** {entry_count}\n**Ends:** <t:{int(giveaway['end_time'].timestamp())}:R>\n**Channel:** <#{giveaway['channel_id']}>",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error listing giveaways: {e}")
            await ctx.send(f"❌ Error listing giveaways: {str(e)}")
    
    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        """Check for giveaways that need to be ended"""
        try:
            if not self.bot.db_pool:
                return
            
            async with self.bot.db_pool.acquire() as conn:
                expired_giveaways = await conn.fetch(
                    "SELECT * FROM giveaways WHERE status = 'active' AND end_time <= NOW()"
                )
                
                for giveaway in expired_giveaways:
                    await self.end_giveaway_process(giveaway)
                    
        except Exception as e:
            logger.error(f"Error checking giveaways: {e}")
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait for bot to be ready before starting task"""
        await self.bot.wait_until_ready()
    
    async def end_giveaway_process(self, giveaway):
        """Process ending a giveaway and selecting winners"""
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get all entries
                entries = await conn.fetch(
                    "SELECT user_id FROM giveaway_entries WHERE giveaway_id = $1",
                    giveaway['id']
                )
                
                # Mark giveaway as completed
                await conn.execute(
                    "UPDATE giveaways SET status = 'completed' WHERE id = $1",
                    giveaway['id']
                )
                
                guild = self.bot.get_guild(giveaway['guild_id'])
                channel = guild.get_channel(giveaway['channel_id'])
                
                if not channel:
                    return
                
                if len(entries) == 0:
                    # No entries
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended",
                        description=f"**Prize:** {giveaway['prize']}\n\n❌ No valid entries! No winners selected.",
                        color=0xff0000
                    )
                    embed.set_footer(text=f"Giveaway ID: {giveaway['id']}")
                    await channel.send(embed=embed)
                    return
                
                # Select winners
                num_winners = min(giveaway['winners'], len(entries))
                winners = random.sample(entries, num_winners)
                
                # Add winners to database
                for winner in winners:
                    await conn.execute(
                        "INSERT INTO giveaway_winners (giveaway_id, user_id) VALUES ($1, $2)",
                        giveaway['id'], winner['user_id']
                    )
                
                # Create winner announcement
                embed = discord.Embed(
                    title="🎉 Giveaway Ended!",
                    description=f"**Prize:** {giveaway['prize']}",
                    color=0x00ff00
                )
                
                winner_mentions = [f"<@{w['user_id']}>" for w in winners]
                embed.add_field(
                    name=f"Winner{'s' if len(winners) > 1 else ''}",
                    value="\n".join(winner_mentions),
                    inline=False
                )
                embed.add_field(name="Total Entries", value=str(len(entries)), inline=True)
                embed.set_footer(text=f"Giveaway ID: {giveaway['id']} • Contact the host to claim your prize!")
                
                # Send winner announcement
                await channel.send(embed=embed)
                
                # Try to update original message
                try:
                    if giveaway['message_id']:
                        original_message = await channel.fetch_message(giveaway['message_id'])
                        
                        # Create ended giveaway embed
                        ended_embed = discord.Embed(
                            title="🎉 GIVEAWAY ENDED 🎉",
                            description=f"**Prize:** {giveaway['prize']}",
                            color=0x999999
                        )
                        ended_embed.add_field(name="Winners", value="\n".join(winner_mentions), inline=False)
                        ended_embed.add_field(name="Total Entries", value=str(len(entries)), inline=True)
                        ended_embed.set_footer(text=f"Ended • Giveaway ID: {giveaway['id']}")
                        
                        # Disable the view
                        view = GiveawayView(giveaway['id'], self.bot)
                        for item in view.children:
                            item.disabled = True
                        
                        await original_message.edit(embed=ended_embed, view=view)
                except:
                    pass  # Original message might be deleted
                    
        except Exception as e:
            logger.error(f"Error ending giveaway process: {e}")
    
    def parse_duration(self, duration_str):
        """Parse duration string to seconds"""
        duration_str = duration_str.lower()
        total_seconds = 0
        
        # Parse different time units
        time_units = {
            's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
            'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
            'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
            'd': 86400, 'day': 86400, 'days': 86400,
            'w': 604800, 'week': 604800, 'weeks': 604800
        }
        
        # Extract number and unit pairs
        import re
        matches = re.findall(r'(\d+)\s*([a-z]+)', duration_str)
        
        if not matches:
            # Try to parse as just a number (assume minutes)
            try:
                return int(duration_str) * 60
            except:
                raise ValueError("Invalid duration format")
        
        for amount, unit in matches:
            if unit in time_units:
                total_seconds += int(amount) * time_units[unit]
            else:
                raise ValueError(f"Unknown time unit: {unit}")
        
        return total_seconds

async def setup(bot):
    await bot.add_cog(Giveaways(bot))