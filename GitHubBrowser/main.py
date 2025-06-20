import discord
from discord.ext import commands
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    sys.exit(1)

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is required")
    sys.exit(1)

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True
intents.reactions = True

class AppleBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=lambda bot, message: self.get_prefix(message),
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.db_pool = None
        self.default_prefix = '!'
        # Set bot timezone to Eastern Standard Time
        self.timezone = pytz.timezone('US/Eastern')
        self.start_time = self.get_current_time()
    
    def get_current_time(self):
        """Get current time in bot's timezone (Eastern - automatically switches EST/EDT)"""
        return datetime.now(self.timezone)
    
    def get_timezone_name(self):
        """Get current timezone name (EST or EDT based on daylight saving time)"""
        current_time = self.get_current_time()
        return current_time.strftime('%Z')  # Returns EST or EDT automatically
        
    async def get_prefix(self, message):
        """Get dynamic prefix for guild"""
        if not message.guild:
            return self.default_prefix
        
        # Get guild prefix from database if available
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.fetchval(
                        "SELECT prefix FROM guild_settings WHERE guild_id = $1",
                        message.guild.id
                    )
                    return result if result else self.default_prefix
            except:
                pass
        
        return self.default_prefix
    
    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info("Setting up Apple Bot...")
        
        # Initialize database
        await self.init_database()
        
        # Load all cogs (some may have reduced functionality without database)
        await self.load_cogs()
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")
        
        logger.info("Apple Bot setup complete")
    
    async def init_database(self):
        """Initialize database connection and tables"""
        try:
            import asyncpg
            
            # Skip database initialization if DATABASE_URL is not available
            if not DATABASE_URL or DATABASE_URL == "":
                logger.warning("DATABASE_URL not available, running without database")
                self.db_pool = None
                return
            
            self.db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=5,
                command_timeout=10
            )
            
            # Test connection with timeout
            conn = await asyncio.wait_for(self.db_pool.acquire(), timeout=5.0)
            try:
                await conn.fetchval("SELECT 1")
            finally:
                await self.db_pool.release(conn)
            
            logger.info("Database connection established")
            await self.create_tables()
            
        except asyncio.TimeoutError:
            logger.warning("Database connection timeout - running without database")
            self.db_pool = None
        except Exception as e:
            logger.warning(f"Database unavailable ({e}) - running without database")
            self.db_pool = None
    
    async def create_tables(self):
        """Create all necessary database tables"""
        if not self.db_pool:
            return
        
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id BIGINT PRIMARY KEY,
                    prefix VARCHAR(10) DEFAULT '!',
                    welcome_channel BIGINT,
                    log_channel BIGINT,
                    counting_channel BIGINT,
                    general_channel BIGINT,
                    suggestions_channel BIGINT,
                    bot_commands_channel BIGINT,
                    economy_channel BIGINT,
                    support_category BIGINT,
                    announcements_channel BIGINT,
                    autorole BIGINT,
                    setup_completed BOOLEAN DEFAULT FALSE,
                    economy_enabled BOOLEAN DEFAULT TRUE,
                    leveling_enabled BOOLEAN DEFAULT FALSE,
                    pets_enabled BOOLEAN DEFAULT FALSE,
                    welcome_enabled BOOLEAN DEFAULT FALSE,
                    automod_enabled BOOLEAN DEFAULT FALSE,
                    counting_enabled BOOLEAN DEFAULT FALSE,
                    suggestions_enabled BOOLEAN DEFAULT FALSE,
                    tickets_enabled BOOLEAN DEFAULT FALSE,
                    giveaways_enabled BOOLEAN DEFAULT FALSE,
                    music_enabled BOOLEAN DEFAULT FALSE,
                    maintenance_mode BOOLEAN DEFAULT FALSE,
                    maintenance_reason TEXT,
                    admin_roles BIGINT[],
                    moderator_roles BIGINT[],
                    support_roles BIGINT[],
                    dj_roles BIGINT[],
                    economy_manager_roles BIGINT[],
                    event_manager_roles BIGINT[],
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 0,
                    bank BIGINT DEFAULT 0,
                    xp BIGINT DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    daily_last TIMESTAMP,
                    work_last TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    item_name VARCHAR(100),
                    quantity INTEGER DEFAULT 1,
                    item_type VARCHAR(50),
                    rarity VARCHAR(20),
                    value INTEGER DEFAULT 0,
                    obtained_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS shop_items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE,
                    description TEXT,
                    price INTEGER,
                    item_type VARCHAR(50),
                    rarity VARCHAR(20),
                    sellable BOOLEAN DEFAULT TRUE,
                    in_stock BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS pets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    level INTEGER DEFAULT 1,
                    happiness INTEGER DEFAULT 100,
                    hunger INTEGER DEFAULT 100,
                    health INTEGER DEFAULT 100,
                    xp INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS moderation (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    moderator_id BIGINT NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            

            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message TEXT NOT NULL,
                    remind_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
        logger.info("Database tables created successfully")
    
    async def load_cogs(self):
        """Load all cog modules"""
        cogs = [
            'cogs.help',
            'cogs.moderation',
            'cogs.economy',
            'cogs.pets',
            'cogs.fun',
            'cogs.utility',
            'cogs.leveling',
            'cogs.analytics',
            'cogs.community',
            'cogs.management',
            'cogs.welcome',
            'cogs.giveaways',
            'cogs.invites',
            'cogs.logging',
            'cogs.slash_logging',
            'cogs.applications',
            'cogs.affiliates',
            'cogs.suggestions',
            'cogs.leaderboards',
            'cogs.notifications',
            'cogs.security',
            'cogs.automation',
            'cogs.stickynotes',
            'cogs.support',
            'cogs.serversetup',
            'cogs.settings',
            'cogs.admin'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        from datetime import datetime
        self.start_time = datetime.utcnow()
        self.commands_used = 0
        self.new_members = 0
        self.messages_seen = 0
        
        logger.info(f'Apple Bot is ready!')
        if self.user:
            logger.info(f'Logged in as: {self.user.name}#{self.user.discriminator}')
            logger.info(f'Bot ID: {self.user.id}')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | !help"
            )
        )
    
    async def on_guild_join(self, guild):
        """Handle bot joining a new guild"""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Initialize guild settings
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO guild_settings (guild_id) VALUES ($1) ON CONFLICT DO NOTHING",
                        guild.id
                    )
            except Exception as e:
                logger.error(f"Failed to initialize guild settings: {e}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided.")
        else:
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            await ctx.send("An unexpected error occurred.")

# Create and run bot
bot = AppleBot()

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)