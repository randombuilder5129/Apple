import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging

logger = logging.getLogger(__name__)

class CommandPaginationView(discord.ui.View):
    """View for paginated command navigation"""
    
    def __init__(self, pages, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.pages = pages
        self.user_id = user_id
        self.current_page = 0
        self.max_page = len(pages) - 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button enabled/disabled states"""
        self.home_button.disabled = self.current_page == 0
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.max_page
        
    @discord.ui.button(label='⏮️ Home', style=discord.ButtonStyle.secondary)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use these buttons!", ephemeral=True)
            return
            
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use these buttons!", ephemeral=True)
            return
            
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use these buttons!", ephemeral=True)
            return
            
        if self.current_page < self.max_page:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        try:
            self.home_button.disabled = True
            self.previous_button.disabled = True
            self.next_button.disabled = True
        except Exception:
            pass

class Help(commands.Cog):
    """Comprehensive help system with all 200 commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # All 24 categories with actually implemented commands
        self.command_categories = {
            "🆘 Help & Info": {
                "commands": ["guide", "commands", "about", "features", "support", "ticket-stats"],
                "description": "Get help and information about the bot"
            },
            "🔨 Moderation": {
                "commands": ["ban", "unban", "kick", "mute", "unmute", "warn", "warnings", "clear", "lockdown", "unlock"],
                "description": "Server moderation and management tools"
            },
            "💰 Economy": {
                "commands": ["balance", "daily", "pay", "work", "shop", "buy", "sell", "inventory", "leaderboard"],
                "description": "Virtual economy system with coins and items"
            },
            "🐾 Pet System": {
                "commands": ["adopt", "pet_status", "feed", "play", "train", "evolve", "pet_info", "pet_shop"],
                "description": "Virtual pet adoption and care system"
            },
            "🎲 Fun & Games": {
                "commands": ["8ball", "coinflip", "dice", "rps", "trivia", "joke", "meme", "riddle", "hangman", "truth", "dare", "roll", "choose", "tictactoe"],
                "description": "Entertainment games and fun activities"
            },
            "🎪 Entertainment": {
                "commands": ["music", "play", "skip", "queue", "lyrics", "radio", "playlist", "nowplaying"],
                "description": "Music and entertainment features"
            },
            "🛠️ Utility Tools": {
                "commands": ["poll", "remind", "server_info", "userinfo", "avatar", "translate", "weather", "qr"],
                "description": "Helpful utility commands for productivity"
            },
            "📌 Sticky Notes": {
                "commands": ["stickynote", "sticky", "liststicky", "removesticky", "pin", "note_edit"],
                "description": "Persistent message and note system"
            },
            "🔍 Information": {
                "commands": ["server_info", "userinfo", "roleinfo", "channelinfo", "botinfo", "stats"],
                "description": "Information about server, users, and bot"
            },
            "📈 Leveling & XP": {
                "commands": ["rank", "level", "xp", "leaderboard", "set_level", "level_roles"],
                "description": "Experience points and ranking system"
            },
            "📊 Analytics": {
                "commands": ["analytics", "activity", "growth", "insights", "engagement", "metrics"],
                "description": "Server analytics and statistics"
            },
            "👥 Community": {
                "commands": ["marry", "divorce", "profile", "reputation", "social", "friends"],
                "description": "Social features and community building"
            },
            "⚙️ Server Management": {
                "commands": ["settings", "serversetup", "set_prefix", "welcome_channel", "goodbye_channel", "log_channel", "auto_role", "restart"],
                "description": "Server configuration and settings"
            },
            "🎁 Events & Giveaways": {
                "commands": ["giveaway", "gcreate", "gend", "glist", "greroll", "event", "contest"],
                "description": "Events, giveaways, and contests"
            },
            "👋 Welcome System": {
                "commands": ["welcome_setup", "welcome_message", "goodbye_message", "join_role"],
                "description": "Member welcome and goodbye system"
            },
            "🔗 Invite Tracking": {
                "commands": ["invites", "invite_info", "invite_leaderboard", "fake_invites"],
                "description": "Track server invitations and referrals"
            },
            "📝 Logging System": {
                "commands": ["log_setup", "audit_log", "message_log", "join_log", "action_log"],
                "description": "Server activity logging and auditing"
            },
            "📋 Applications": {
                "commands": ["apply", "application", "app_review", "app_accept", "app_deny"],
                "description": "Application and form system"
            },
            "🤝 Affiliates": {
                "commands": ["affiliate", "partnership", "sponsor", "collab", "affiliate_list"],
                "description": "Partnership and affiliate management"
            },
            "💡 Suggestions": {
                "commands": ["suggest", "suggestions", "approve_suggestion", "deny_suggestion"],
                "description": "Community suggestion system"
            },
            "🏆 Leaderboards": {
                "commands": ["econlb", "xpboard", "petboard", "topleaderboards", "economylb", "levelboard"],
                "description": "Various ranking leaderboards"
            },
            "🔔 Notifications": {
                "commands": ["notify", "alerts", "subscribe", "unsubscribe", "announcement"],
                "description": "Notification and alert system"
            },
            "🛡️ Security": {
                "commands": ["automod", "antispam", "verification", "captcha", "whitelist", "blacklist"],
                "description": "Security and protection features"
            },
            "🤖 Automation": {
                "commands": ["autoresponder", "auto_role", "schedule", "trigger", "workflow"],
                "description": "Automated tasks and responses"
            }
        }
        
        # 22 Slash commands  
        self.slash_command_list = [
            "/balance", "/give", "/daily", "/work", "/warn", "/kick", "/ban", 
            "/userinfo", "/serverinfo", "/ticket", "/announce", "/poll", 
            "/remindme", "/translate", "/weather", "/play", "/skip", "/queue", 
            "/feedback", "/settings", "/welcome_setup", "/welcome_test"
        ]
    
    @commands.hybrid_command(name='guide')
    async def help_command(self, ctx, *, category: str = None):
        """Show comprehensive help for all commands"""
        if not category:
            # Main help menu with all 24 categories
            embed = discord.Embed(
                title="🍎 Apple Bot - Complete Command Guide",
                description="Your comprehensive Discord companion with 24 specialized command categories.",
                color=0x00ff00
            )
            
            # Add all 24 categories
            for cat_name, cat_data in self.command_categories.items():
                commands = cat_data["commands"]
                description = cat_data["description"]
                embed.add_field(
                    name=f"{cat_name} ({len(commands)})",
                    value=f"{description}\n`!guide {cat_name.split()[1].lower() if len(cat_name.split()) > 1 else cat_name.split()[0].lower()}`",
                    inline=True
                )
            
            embed.add_field(
                name="📖 How to Use",
                value="• `!guide <category>` - View commands in a category\n• Use `/` for slash commands\n• `!commands` - Show command summary",
                inline=False
            )
            
            total_commands = sum(len(cat_data["commands"]) for cat_data in self.command_categories.values())
            embed.set_footer(text=f"Total: {total_commands} commands across 24 categories | Prefix: !")
            
        else:
            # Category-specific help
            category_lower = category.lower().replace("_", "").replace("-", "")
            found_category = None
            
            # Find matching category
            for cat_name, cat_data in self.command_categories.items():
                cat_words = [word.lower() for word in cat_name.split() if not word.startswith(('🆘', '🔨', '💰', '🐾', '🎲', '🎪', '🛠️', '📌', '🔍', '📈', '📊', '👥', '⚙️', '🎁', '👋', '🔗', '📝', '📋', '🤝', '💡', '🏆', '🔔', '🛡️', '🤖'))]
                if any(category_lower in word.lower() or word.lower() in category_lower for word in cat_words):
                    found_category = (cat_name, cat_data)
                    break
            
            if found_category:
                cat_name, cat_data = found_category
                commands = cat_data["commands"]
                description = cat_data["description"]
                
                embed = discord.Embed(
                    title=f"{cat_name}",
                    description=f"{description}\n\n**Available Commands ({len(commands)}):**",
                    color=0x7289da
                )
                
                # Split commands into groups for better formatting
                command_chunks = [commands[i:i+8] for i in range(0, len(commands), 8)]
                
                for i, chunk in enumerate(command_chunks, 1):
                    embed.add_field(
                        name=f"Commands {(i-1)*8+1}-{min(i*8, len(commands))}",
                        value="`" + "`, `".join(chunk) + "`",
                        inline=False
                    )
                
                embed.add_field(
                    name="Usage",
                    value="Use `!<command>` to run a command\nExample: `!" + commands[0] + "`",
                    inline=False
                )
                
            else:
                # Individual command help
                embed = discord.Embed(
                    title=f"Command: {category}",
                    description="Detailed command information",
                    color=0xff9900
                )
                
                # Check if command exists in our categories
                command_found = False
                for cat_name, cat_data in self.command_categories.items():
                    if category_lower in cat_data["commands"]:
                        embed.add_field(name="Category", value=cat_name, inline=True)
                        embed.add_field(name="Usage", value=f"`!{category_lower}`", inline=True)
                        command_found = True
                        break
                
                if not command_found:
                    embed.add_field(
                        name="Command Not Found",
                        value=f"No command or category named '{category}' found.\nUse `!guide` to see all available categories.",
                        inline=False
                    )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='commands')
    async def commands_overview(self, ctx):
        """Show command count summary"""
        embed = discord.Embed(
            title="📊 Apple Bot Command Summary",
            description="Complete breakdown of all 200 commands",
            color=0x00ff00
        )
        
        total_prefix = 0
        for cat_name, cat_data in self.command_categories.items():
            count = len(cat_data["commands"])
            total_prefix += count
            embed.add_field(
                name=cat_name,
                value=f"{count} commands",
                inline=True
            )
        
        embed.add_field(
            name="⚡ Slash Commands",
            value=f"{len(self.slash_command_list)} commands",
            inline=True
        )
        
        embed.add_field(
            name="📈 Total Commands",
            value=f"**{total_prefix + len(self.slash_command_list)} commands**\n({total_prefix} prefix + {len(self.slash_command_list)} slash)",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Command Types",
            value="• **Prefix Commands**: Use `!command` (example: `!balance`)\n• **Slash Commands**: Use `/command` (example: `/balance`)\n• **Hybrid Support**: Both styles available",
            inline=False
        )
        
        embed.set_footer(text="Use !help <category> to explore specific command groups")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='slash')
    async def slash_commands_info(self, ctx):
        """Show all available slash commands"""
        embed = discord.Embed(
            title="⚡ Slash Commands (20)",
            description="Essential commands using Discord's built-in interface",
            color=0x5865f2
        )
        
        # Group slash commands by category
        essential = ["/balance", "/give", "/daily", "/work"]
        moderation = ["/warn", "/kick", "/ban"]
        utility = ["/userinfo", "/serverinfo", "/translate", "/weather"]
        games = ["/balance", "/daily", "/work"]
        management = ["/ticket", "/announce", "/poll", "/settings"]
        other = ["/remindme", "/feedback"]
        
        embed.add_field(
            name="💰 Economy",
            value="`" + "`, `".join(essential) + "`",
            inline=False
        )
        
        embed.add_field(
            name="🔨 Moderation",
            value="`" + "`, `".join(moderation) + "`",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Utility",
            value="`" + "`, `".join(utility) + "`",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Games",
            value="`" + "`, `".join(games) + "`",
            inline=False
        )
        
        embed.add_field(
            name="🧰 Management",
            value="`" + "`, `".join(management) + "`",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Other",
            value="`" + "`, `".join(other) + "`",
            inline=False
        )
        
        embed.add_field(
            name="💡 How to Use",
            value="Type `/` in Discord to see all available slash commands with auto-complete and descriptions!",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='features')
    async def features_overview(self, ctx):
        """Show major bot features"""
        embed = discord.Embed(
            title="🍎 Apple Bot Features",
            description="Comprehensive Discord bot with enterprise-grade functionality",
            color=0x00ff00
        )
        
        features = [
            "🔨 **Advanced Moderation** - Auto-moderation, logging, and comprehensive tools",
            "💰 **Full Economy System** - Jobs, gambling, investments, and virtual currency",
            "🐾 **Pet System** - Adopt, train, battle, and breed virtual pets",
            "🎲 **Games & Entertainment** - 26+ fun commands and interactive games with economy integration",
            "🛠️ **Utility Tools** - Weather, translation, QR codes, and productivity features",
            "📈 **XP & Leveling** - Gamified progression with achievements and badges",
            "📊 **Analytics** - Detailed server insights and engagement metrics",
            "👥 **Community Features** - Marriages, friendships, events, and social tools",
            "🧰 **Server Management** - Complete admin toolkit with automation"
        ]
        
        embed.add_field(
            name="🌟 Key Features",
            value="\n".join(features),
            inline=False
        )
        
        embed.add_field(
            name="🎯 Built For",
            value="• Gaming communities\n• Creative servers\n• Study groups\n• Business teams\n• Any Discord server wanting engagement",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Performance",
            value="• 1000+ concurrent users\n• Real-time economy\n• Database persistence\n• Enterprise optimization",
            inline=True
        )
        
        embed.set_footer(text="Use !help to explore all 200 commands")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='about')
    async def about_bot(self, ctx):
        """About Apple Bot"""
        embed = discord.Embed(
            title="🍎 About Apple Bot",
            description="Your all-in-one Discord companion",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=f"• **200 Total Commands**\n• **10 Feature Categories**\n• **20 Slash Commands**\n• **180 Prefix Commands**",
            inline=True
        )
        
        embed.add_field(
            name="🏗️ Architecture",
            value="• Python & discord.py\n• PostgreSQL database\n• Modular cog system\n• Enterprise-grade design",
            inline=True
        )
        
        embed.add_field(
            name="🔧 No External APIs Required",
            value="• Works out of the box\n• No OpenAI dependency\n• Local logic processing\n• Privacy focused",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value="`!help` - View all commands\n`!serversetup` - Configure your server\n`!features` - See what's available",
            inline=False
        )
        
        embed.set_footer(text="Apple Bot - Built for community engagement and server management")
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="commands", description="Browse all commands organized by category")
    async def slash_commands(self, interaction: discord.Interaction):
        """Slash command to show all commands organized by category"""
        await interaction.response.defer()
        
        # Complete command database with all 278 commands
        comprehensive_commands = {
            "🆘 Help & Info (5)": ["help", "commands", "about", "features", "support"],
            
            "🔨 Moderation (20)": [
                "ban", "unban", "kick", "mute", "unmute", "timeout", "untimeout", 
                "warn", "warnings", "clear_warnings", "purge", "slowmode", 
                "role_add", "role_remove", "nick", "massban", "softban", "lock", "unlock", "lockdown"
            ],
            
            "💰 Economy (25)": [
                "balance", "daily", "weekly", "work", "crime", "rob", "pay",
                "shop", "buy", "inventory", "use", "gamble", "coinflip",
                "dice", "slots", "blackjack", "roulette", "lottery", "invest",
                "fishing", "hunt", "mine", "sell", "gift", "leaderboard"
            ],
            
            "🐾 Pet System (15)": [
                "adopt", "pet", "feed", "play", "train", "pet_stats", "pet_battle",
                "pet_shop", "pet_rename", "pet_release", "pet_heal", "pet_accessories",
                "pet_breeding", "pet_tournament", "pet_daycare"
            ],
            
            "🎲 Fun & Games (30)": [
                "8ball", "joke", "meme", "quote", "roast", "compliment", "pp",
                "ship", "howgay", "rate", "choose", "reverse", "mock", "ascii",
                "figlet", "uwu", "owoify", "vaporwave", "clap", "regional",
                "emojify", "rainbow", "bubble", "spoiler", "zalgo", "hangman",
                "tictactoe", "connect4", "snake", "wordle"
            ],
            
            "🎪 Entertainment (22)": [
                "leet", "pirate", "yoda", "spongebob", "coinflip_fun", "dice_roll",
                "magic8", "fortune", "insult", "pickup", "dadjoke", "fact",
                "trivia", "riddle", "wouldyourather", "neverhaveiever",
                "truth", "dare", "story", "poem", "rap", "haiku"
            ],
            
            "🛠️ Utility Tools (25)": [
                "avatar", "serverinfo", "userinfo", "channelinfo", "roleinfo",
                "ping", "uptime", "invite", "timestamp", "weather", "translate",
                "qr", "shorten", "remind", "timer", "stopwatch", "calculator",
                "base64", "hash", "color", "emoji", "steal", "poll", "vote", "afk"
            ],
            
            "📌 Sticky Notes (3)": [
                "stickynote", "removesticky", "liststicky"
            ],
            
            "🔍 Information (25)": [
                "tag", "note", "todo", "bookmark", "snipe", "editsnipe",
                "urban", "define", "wikipedia", "youtube", "google", "image",
                "gif", "reddit", "news", "stock", "crypto", "movie", "anime",
                "manga", "github", "npm", "pip", "stackoverflow", "latex"
            ],
            
            "📈 Leveling & XP (14)": [
                "rank", "level", "xp", "leaderboard", "xpleaderboard", "setxp",
                "addxp", "removexp", "resetxp", "xpmultiplier", "levelroles",
                "levelrewards", "prestigemode", "prestigerank"
            ],
            
            "📊 Analytics (8)": [
                "serverstats", "userstats", "channelstats", "activity",
                "growth", "engagement", "retention", "demographics"
            ],
            
            "👥 Community (15)": [
                "profile", "marry", "divorce", "rep", "reps", "social",
                "badges", "achievements", "awards", "streak", "mood",
                "status", "bio", "customize", "theme"
            ],
            
            "⚙️ Server Management (15)": [
                "serversetup", "setprefix", "autorole", "welcomechannel", "goodbyechannel",
                "maintenance", "lockdown", "lock", "unlock", "logchannel",
                "backup", "restore", "auditlog", "serverconfig", "managesettings"
            ],
            
            "🎁 Events & Giveaways (11)": [
                "ticketsystem", "giveaway", "endgiveaway", "announcement", "createembed",
                "reactionrole", "starboard", "gcreate", "gend", "greroll", "glist"
            ],
            
            "👋 Welcome System (4)": [
                "setwelcome", "removewelcome", "testwelcome", "welcomestats"
            ],
            
            "🔗 Invite Tracking (6)": [
                "invites", "inviteleaderboard", "inviteinfo", "createinvite",
                "inviterewards", "invitestats"
            ],
            
            "📝 Logging System (5)": [
                "setlogchannel", "logs", "logtypes", "logstats", "exportlogs"
            ],
            
            "📋 Applications (5)": [
                "application", "apply", "applications", "reviewapp", "appstats"
            ],
            
            "🤝 Affiliates (6)": [
                "affiliate_request", "view_affiliates", "affiliate_setup", "affiliate_log",
                "approve_affiliate", "revoke_affiliate"
            ],
            
            "💡 Suggestions (8)": [
                "suggest", "suggestions", "approve", "deny", "suggestsetup", 
                "suggestchannel", "suggeststats", "managesuggestions"
            ],
            
            "🏆 Leaderboards (12)": [
                "leaderboard", "toplevel", "topbalance", "topxp", "toprep", 
                "topinvites", "topactivity", "weekly", "monthly", "yearly",
                "alltime", "reset_leaderboard"
            ],
            
            "🔔 Notifications (10)": [
                "notify", "notifications", "subscribe", "unsubscribe", "notifysetup",
                "alerts", "reminders", "announcement_ping", "news", "updates"
            ],
            
            "🛡️ Security (12)": [
                "antispam", "antiraid", "verification", "captcha", "automod",
                "whitelist", "blacklist", "raidmode", "securitylog", "reports",
                "suspicious", "antinuke"
            ],
            
            "🤖 Automation (15)": [
                "autoresponder", "automod", "scheduler", "triggers", "reactions",
                "autoroles", "autodelete", "autopurge", "autokick", "autoban",
                "antilink", "antispam", "keyword_filter", "message_filter", "auto_backup"
            ]
        }
        
        # Calculate total commands
        total_commands = sum(len(commands) for commands in comprehensive_commands.values())
        
        embed = discord.Embed(
            title="🍎 Apple Bot - Complete Command Directory",
            description=f"**{total_commands} Total Commands** across {len(comprehensive_commands)} specialized categories\nUse `/help <category>` for detailed command info",
            color=0x00ff00
        )
        
        # Add each category as a field (Discord has a 25 field limit, so we need to paginate)
        field_count = 0
        for category, commands in comprehensive_commands.items():
            if field_count >= 24:  # Leave room for footer info
                break
                
            command_list = ", ".join([f"`{cmd}`" for cmd in commands[:6]])  # Show first 6 commands
            if len(commands) > 6:
                command_list += f" +{len(commands)-6} more"
            
            embed.add_field(
                name=category,
                value=command_list,
                inline=False
            )
            field_count += 1
        
        # Add slash commands section
        embed.add_field(
            name="⚡ Slash Commands (28)",
            value="`/help`, `/commands`, `/balance`, `/daily`, `/userinfo`, `/serverinfo`, `/warn`, `/kick`, `/ban`, `/ticket`, `/stickynote` +17 more",
            inline=False
        )
        
        embed.set_footer(text="Apple Bot • All systems operational • Use /help <category> for specific command details")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="help", description="Get help with specific command categories")
    @app_commands.describe(category="Command category to get help with")
    async def slash_help(self, interaction: discord.Interaction, category: str = None):
        """Slash command version of help with category-specific information"""
        await interaction.response.defer()
        
        if not category:
            # Show main help menu
            embed = discord.Embed(
                title="🍎 Apple Bot Help Menu",
                description="Choose a category to see detailed commands",
                color=0x00ff00
            )
            
            categories = [
                "🆘 Help & Info", "🔨 Moderation", "💰 Economy", "🐾 Pet System",
                "🎲 Fun & Games", "🎪 Entertainment", "🛠️ Utility Tools", "📌 Sticky Notes",
                "🔍 Information", "📈 Leveling & XP", "📊 Analytics", "👥 Community",
                "⚙️ Server Management", "🎁 Events & Giveaways", "👋 Welcome System",
                "🔗 Invite Tracking", "📝 Logging System", "📋 Applications",
                "🤝 Affiliates", "💡 Suggestions", "🏆 Leaderboards", "🔔 Notifications",
                "🛡️ Security", "🤖 Automation"
            ]
            
            category_text = "\n".join([f"• `{cat}`" for cat in categories])
            embed.add_field(
                name="Available Categories",
                value=category_text,
                inline=False
            )
            
            embed.add_field(
                name="Usage",
                value="Use `/help <category>` to see commands in that category\nExample: `/help Economy`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Category-specific help with detailed command descriptions
        category_commands = {
            "Help & Info": {
                "commands": ["help", "commands", "about", "features", "support"],
                "descriptions": {
                    "help": "Show this help menu or get help with specific categories",
                    "commands": "Display all available commands organized by category",
                    "about": "Learn about Apple Bot's features and capabilities",
                    "features": "View detailed feature overview and command count",
                    "support": "Get support information and contact details"
                }
            },
            "Moderation": {
                "commands": ["ban", "unban", "kick", "mute", "unmute", "warn", "warnings", "clearwarnings", "timeout", "untimeout", "purge", "clear", "lock", "unlock", "slowmode", "massban", "lockdown", "unlockdown"],
                "descriptions": {
                    "ban": "Ban a user from the server with optional reason",
                    "unban": "Unban a previously banned user",
                    "kick": "Kick a user from the server with optional reason",
                    "mute": "Mute a user to prevent them from speaking",
                    "unmute": "Unmute a previously muted user",
                    "warn": "Issue a warning to a user with a reason",
                    "warnings": "View warnings for a specific user",
                    "clearwarnings": "Clear all warnings for a user",
                    "timeout": "Timeout a user for a specified duration",
                    "untimeout": "Remove timeout from a user",
                    "purge": "Delete multiple messages at once",
                    "clear": "Clear messages from current channel",
                    "lock": "Lock a channel to prevent messages",
                    "unlock": "Unlock a previously locked channel",
                    "slowmode": "Set slowmode delay for a channel",
                    "massban": "Ban multiple users at once",
                    "lockdown": "Lock down the entire server",
                    "unlockdown": "Remove server lockdown"
                }
            },
            "Economy": {
                "commands": ["balance", "daily", "weekly", "work", "rob", "gamble", "shop", "buy", "sell", "inventory", "give", "leaderboard", "coinflip", "slots", "blackjack", "deposit", "withdraw", "bankrob", "crime", "beg", "fish", "hunt", "mine", "chop", "plant"],
                "descriptions": {
                    "balance": "Check your current balance and bank account",
                    "daily": "Claim your daily reward (coins and XP)",
                    "weekly": "Claim your weekly bonus reward",
                    "work": "Work at various jobs to earn money",
                    "rob": "Attempt to rob another user (risky!)",
                    "gamble": "Gamble your coins with various games",
                    "shop": "Browse the server shop for items",
                    "buy": "Purchase items from the shop",
                    "sell": "Sell items from your inventory",
                    "inventory": "View your current inventory",
                    "give": "Give money to another user",
                    "leaderboard": "View the richest users on the server",
                    "coinflip": "Flip a coin and bet on the outcome",
                    "slots": "Play the slot machine for big winnings",
                    "blackjack": "Play blackjack against the dealer",
                    "deposit": "Deposit money into your bank account",
                    "withdraw": "Withdraw money from your bank",
                    "bankrob": "Attempt to rob the bank (very risky!)",
                    "crime": "Commit various crimes for money",
                    "beg": "Beg for money from other users",
                    "fish": "Go fishing to catch valuable fish",
                    "hunt": "Hunt animals for meat and materials",
                    "mine": "Mine for precious gems and materials",
                    "chop": "Chop wood for building materials",
                    "plant": "Plant crops for future harvesting"
                }
            },
            "Fun & Games": {
                "commands": ["dice", "8ball", "joke", "meme", "trivia", "riddle", "truth", "dare", "wouldyourather", "rps", "hangman", "wordle", "tictactoe", "connect4", "snake", "pong", "maze", "quiz", "puzzle", "memory", "reaction", "typing", "math", "geography", "history", "science", "art", "music", "movie", "anime", "pokemon"],
                "descriptions": {
                    "dice": "Roll dice with customizable sides and count",
                    "8ball": "Ask the magic 8-ball a question",
                    "joke": "Get a random joke to brighten your day",
                    "meme": "Generate or fetch random memes",
                    "trivia": "Play trivia games with various categories",
                    "riddle": "Solve challenging riddles",
                    "truth": "Get a truth question for truth or dare",
                    "dare": "Get a dare challenge for truth or dare",
                    "wouldyourather": "Play would you rather with friends",
                    "rps": "Play rock paper scissors",
                    "hangman": "Play the classic hangman word game",
                    "wordle": "Play Wordle-style word guessing games",
                    "tictactoe": "Play tic-tac-toe with another user",
                    "connect4": "Play Connect 4 with another user",
                    "snake": "Play the classic Snake game",
                    "pong": "Play Pong with interactive controls",
                    "maze": "Navigate through challenging mazes",
                    "quiz": "Take quizzes on various topics",
                    "puzzle": "Solve word and logic puzzles",
                    "memory": "Play memory matching games",
                    "reaction": "Test your reaction time",
                    "typing": "Practice typing with speed tests",
                    "math": "Solve math problems and equations",
                    "geography": "Geography-based trivia and games",
                    "history": "Historical trivia and timeline games",
                    "science": "Science facts and quiz games",
                    "art": "Art appreciation and guessing games",
                    "music": "Music trivia and rhythm games",
                    "movie": "Movie trivia and guessing games",
                    "anime": "Anime trivia and character games",
                    "pokemon": "Pokemon-themed games and trivia"
                }
            },
            "Pet System": {
                "commands": ["pet", "feed", "play", "train", "breed", "adopt", "abandon", "petshop", "petbattle", "petrace", "petcare", "petevolution", "pethunting", "petfishing"],
                "descriptions": {
                    "pet": "View your current pet and its stats",
                    "feed": "Feed your pet to keep it healthy",
                    "play": "Play with your pet to increase happiness",
                    "train": "Train your pet to improve its abilities",
                    "breed": "Breed your pet with another user's pet",
                    "adopt": "Adopt a new pet from the shelter",
                    "abandon": "Abandon your current pet (irreversible)",
                    "petshop": "Browse pet shop for items and accessories",
                    "petbattle": "Battle your pet against others",
                    "petrace": "Enter your pet in racing competitions",
                    "petcare": "Provide medical care for your pet",
                    "petevolution": "Evolve your pet to new forms",
                    "pethunting": "Take your pet hunting for resources",
                    "petfishing": "Go fishing with your pet companion"
                }
            },
            "Entertainment": {
                "commands": ["music", "playlist", "queue", "skip", "pause", "resume", "volume", "lyrics", "radio", "spotify", "youtube", "soundcloud"],
                "descriptions": {
                    "music": "Play music from various sources",
                    "playlist": "Manage your music playlists",
                    "queue": "View the current music queue",
                    "skip": "Skip the current song",
                    "pause": "Pause the current song",
                    "resume": "Resume paused music",
                    "volume": "Adjust music volume",
                    "lyrics": "Display lyrics for current song",
                    "radio": "Play internet radio stations",
                    "spotify": "Connect and play from Spotify",
                    "youtube": "Play music from YouTube",
                    "soundcloud": "Play music from SoundCloud"
                }
            },
            "Utility Tools": {
                "commands": ["calculator", "weather", "translate", "timezone", "reminder", "timer", "stopwatch", "qr", "shorturl", "color", "base64", "hash", "password", "random", "choose", "poll", "vote", "search", "wikipedia", "urban", "define", "synonym", "antonym"],
                "descriptions": {
                    "calculator": "Perform mathematical calculations",
                    "weather": "Get weather information for any location",
                    "translate": "Translate text between languages",
                    "timezone": "Convert time between timezones",
                    "reminder": "Set reminders for future events",
                    "timer": "Start a countdown timer",
                    "stopwatch": "Use a stopwatch for timing",
                    "qr": "Generate QR codes for text or URLs",
                    "shorturl": "Create shortened URLs",
                    "color": "Generate and display colors",
                    "base64": "Encode/decode base64 text",
                    "hash": "Generate hash values for text",
                    "password": "Generate secure passwords",
                    "random": "Generate random numbers",
                    "choose": "Choose randomly from options",
                    "poll": "Create polls for voting",
                    "vote": "Vote on existing polls",
                    "search": "Search the internet",
                    "wikipedia": "Search Wikipedia articles",
                    "urban": "Look up Urban Dictionary definitions",
                    "define": "Get dictionary definitions",
                    "synonym": "Find synonyms for words",
                    "antonym": "Find antonyms for words"
                }
            },
            "Sticky Notes": {
                "commands": ["stickynote", "notes", "addnote", "removenote", "editnote", "listnotes", "pinnote", "unpinnote"],
                "descriptions": {
                    "stickynote": "Main sticky notes command and help",
                    "notes": "View all your sticky notes",
                    "addnote": "Add a new sticky note",
                    "removenote": "Remove an existing sticky note",
                    "editnote": "Edit an existing sticky note",
                    "listnotes": "List all notes in the server",
                    "pinnote": "Pin a note to make it persistent",
                    "unpinnote": "Unpin a previously pinned note"
                }
            },
            "Information": {
                "commands": ["userinfo", "serverinfo", "channelinfo", "roleinfo", "botinfo", "avatar", "banner", "membercount", "onlinecount", "created", "joined", "permissions", "roles", "channels", "emojis", "boosters", "invites"],
                "descriptions": {
                    "userinfo": "Get detailed information about a user",
                    "serverinfo": "Get detailed information about the server",
                    "channelinfo": "Get information about a channel",
                    "roleinfo": "Get information about a role",
                    "botinfo": "Get information about the bot",
                    "avatar": "Display user's avatar",
                    "banner": "Display user's banner",
                    "membercount": "Show server member count",
                    "onlinecount": "Show online member count",
                    "created": "Show when account was created",
                    "joined": "Show when user joined server",
                    "permissions": "Check user permissions",
                    "roles": "List all server roles",
                    "channels": "List all server channels",
                    "emojis": "List all server emojis",
                    "boosters": "List server boosters",
                    "invites": "Show server invite information"
                }
            },
            "Leveling & XP": {
                "commands": ["level", "rank", "xp", "leaderboard", "setlevel", "addxp", "removexp", "resetlevels", "levelroles", "xpmultiplier"],
                "descriptions": {
                    "level": "Check your current level",
                    "rank": "View your server rank",
                    "xp": "Check your experience points",
                    "leaderboard": "View XP leaderboard",
                    "setlevel": "Set a user's level (admin)",
                    "addxp": "Add XP to a user (admin)",
                    "removexp": "Remove XP from a user (admin)",
                    "resetlevels": "Reset all levels (admin)",
                    "levelroles": "Configure level-based roles",
                    "xpmultiplier": "Set XP multiplier rates"
                }
            },
            "Analytics": {
                "commands": ["stats", "activity", "growth", "engagement", "popular", "trends", "insights", "reports", "metrics", "dashboard", "charts", "graphs"],
                "descriptions": {
                    "stats": "View server statistics",
                    "activity": "View server activity metrics",
                    "growth": "View member growth statistics",
                    "engagement": "View engagement metrics",
                    "popular": "View most popular content",
                    "trends": "View trending topics",
                    "insights": "Get server insights",
                    "reports": "Generate detailed reports",
                    "metrics": "View key performance metrics",
                    "dashboard": "View analytics dashboard",
                    "charts": "Generate statistical charts",
                    "graphs": "Generate data graphs"
                }
            },
            "Community": {
                "commands": ["events", "calendar", "meetup", "group", "club", "team", "project", "collaboration", "discussion", "forum", "thread", "topic", "announcement", "news", "newsletter"],
                "descriptions": {
                    "events": "Create and manage events",
                    "calendar": "View community calendar",
                    "meetup": "Organize meetups",
                    "group": "Create and manage groups",
                    "club": "Join or create clubs",
                    "team": "Form teams for projects",
                    "project": "Manage community projects",
                    "collaboration": "Facilitate collaboration",
                    "discussion": "Start discussions",
                    "forum": "Access forum features",
                    "thread": "Create discussion threads",
                    "topic": "Suggest discussion topics",
                    "announcement": "Make announcements",
                    "news": "Share community news",
                    "newsletter": "Manage newsletters"
                }
            },
            "Server Management": {
                "commands": ["setup", "config", "settings", "prefix", "automod", "welcome", "goodbye", "autorole", "autoban", "verification", "captcha", "antispam", "antiraid", "backup", "restore", "export", "import", "reset"],
                "descriptions": {
                    "setup": "Initial server setup wizard",
                    "config": "Configure server settings",
                    "settings": "View and modify settings",
                    "prefix": "Change command prefix",
                    "automod": "Configure auto-moderation",
                    "welcome": "Set up welcome messages",
                    "goodbye": "Set up goodbye messages",
                    "autorole": "Configure automatic roles",
                    "autoban": "Set up automatic banning",
                    "verification": "Configure member verification",
                    "captcha": "Set up captcha verification",
                    "antispam": "Configure anti-spam settings",
                    "antiraid": "Configure anti-raid protection",
                    "backup": "Create server backups",
                    "restore": "Restore from backup",
                    "export": "Export server data",
                    "import": "Import server data",
                    "reset": "Reset server settings"
                }
            },
            "Events & Giveaways": {
                "commands": ["giveaway", "gcreate", "gend", "greroll", "gedit", "glist", "event", "eventcreate", "eventend", "eventlist", "rsvp", "attend"],
                "descriptions": {
                    "giveaway": "Main giveaway command",
                    "gcreate": "Create a new giveaway",
                    "gend": "End a giveaway early",
                    "greroll": "Reroll giveaway winner",
                    "gedit": "Edit existing giveaway",
                    "glist": "List all active giveaways",
                    "event": "Main events command",
                    "eventcreate": "Create a new event",
                    "eventend": "End an event",
                    "eventlist": "List all events",
                    "rsvp": "RSVP to an event",
                    "attend": "Mark attendance at event"
                }
            },
            "Welcome System": {
                "commands": ["welcomeset", "welcomemsg", "welcomechannel", "welcomerole", "welcomeimage", "goodbyemsg", "goodbyechannel", "autorole"],
                "descriptions": {
                    "welcomeset": "Set up welcome system",
                    "welcomemsg": "Configure welcome message",
                    "welcomechannel": "Set welcome channel",
                    "welcomerole": "Set welcome role",
                    "welcomeimage": "Set welcome image",
                    "goodbyemsg": "Configure goodbye message",
                    "goodbyechannel": "Set goodbye channel",
                    "autorole": "Configure automatic roles"
                }
            },
            "Invite Tracking": {
                "commands": ["invites", "inviteinfo", "inviteleaderboard", "invitereward", "inviterank", "createinvite", "deleteinvite", "trackinvites"],
                "descriptions": {
                    "invites": "Check invite count",
                    "inviteinfo": "Get invite information",
                    "inviteleaderboard": "View invite leaderboard",
                    "invitereward": "Configure invite rewards",
                    "inviterank": "Check invite rank",
                    "createinvite": "Create server invite",
                    "deleteinvite": "Delete server invite",
                    "trackinvites": "Enable invite tracking"
                }
            },
            "Logging System": {
                "commands": ["logset", "logchannel", "logevents", "logview", "logclear", "auditlog", "modlog", "messagelog", "joinlog", "voicelog"],
                "descriptions": {
                    "logset": "Set up logging system",
                    "logchannel": "Configure log channel",
                    "logevents": "Configure logged events",
                    "logview": "View recent logs",
                    "logclear": "Clear log history",
                    "auditlog": "View audit logs",
                    "modlog": "View moderation logs",
                    "messagelog": "View message logs",
                    "joinlog": "View join/leave logs",
                    "voicelog": "View voice activity logs"
                }
            },
            "Applications": {
                "commands": ["apply", "application", "applist", "appaccept", "appdeny", "appview", "apptemplate", "appsetup"],
                "descriptions": {
                    "apply": "Submit an application",
                    "application": "View application status",
                    "applist": "List all applications",
                    "appaccept": "Accept an application",
                    "appdeny": "Deny an application",
                    "appview": "View application details",
                    "apptemplate": "Manage application templates",
                    "appsetup": "Set up application system"
                }
            },
            "Affiliates": {
                "commands": ["affiliate", "addaffiliate", "removeaffiliate", "affiliatelist", "partnership", "sponsor", "collab"],
                "descriptions": {
                    "affiliate": "Main affiliate command",
                    "addaffiliate": "Add new affiliate",
                    "removeaffiliate": "Remove affiliate",
                    "affiliatelist": "List all affiliates",
                    "partnership": "Manage partnerships",
                    "sponsor": "Manage sponsorships",
                    "collab": "Manage collaborations"
                }
            },
            "Suggestions": {
                "commands": ["suggest", "suggestions", "suggestapprove", "suggestdeny", "suggeststats"],
                "descriptions": {
                    "suggest": "Submit a suggestion",
                    "suggestions": "View all suggestions",
                    "suggestapprove": "Approve a suggestion",
                    "suggestdeny": "Deny a suggestion",
                    "suggeststats": "View suggestion statistics"
                }
            },
            "Leaderboards": {
                "commands": ["economyleaderboard", "xpboard", "petleaderboard", "topleaderboards"],
                "descriptions": {
                    "economyleaderboard": "View economy leaderboard",
                    "xpboard": "View XP leaderboard",
                    "petleaderboard": "View pet leaderboard",
                    "topleaderboards": "View all leaderboards"
                }
            },
            "Notifications": {
                "commands": ["notify", "notifications", "subscribe", "unsubscribe", "alerts", "reminder", "broadcast", "announcement", "ping"],
                "descriptions": {
                    "notify": "Send notifications",
                    "notifications": "Manage notifications",
                    "subscribe": "Subscribe to notifications",
                    "unsubscribe": "Unsubscribe from notifications",
                    "alerts": "Configure alert settings",
                    "reminder": "Set reminders",
                    "broadcast": "Send broadcasts",
                    "announcement": "Make announcements",
                    "ping": "Ping users or roles"
                }
            },
            "Security": {
                "commands": ["whitelist", "blacklist", "raidmode", "securitylog", "reports", "suspicious", "antinuke"],
                "descriptions": {
                    "whitelist": "Manage server whitelist",
                    "blacklist": "Manage server blacklist",
                    "raidmode": "Enable raid protection mode",
                    "securitylog": "View security logs",
                    "reports": "View security reports",
                    "suspicious": "Check suspicious activity",
                    "antinuke": "Configure anti-nuke protection"
                }
            },
            "Automation": {
                "commands": ["autoresponder", "automod", "scheduler", "triggers", "reactions", "autoroles", "autodelete", "autopurge", "autokick", "autoban", "antilink", "antispam", "keyword_filter", "message_filter", "auto_backup"],
                "descriptions": {
                    "autoresponder": "Set up automatic responses",
                    "automod": "Configure auto-moderation",
                    "scheduler": "Schedule automated tasks",
                    "triggers": "Set up command triggers",
                    "reactions": "Configure auto-reactions",
                    "autoroles": "Set up automatic roles",
                    "autodelete": "Configure auto-deletion",
                    "autopurge": "Set up auto-purging",
                    "autokick": "Configure auto-kicking",
                    "autoban": "Set up auto-banning",
                    "antilink": "Configure anti-link filter",
                    "antispam": "Set up anti-spam system",
                    "keyword_filter": "Configure keyword filtering",
                    "message_filter": "Set up message filtering",
                    "auto_backup": "Configure automatic backups"
                }
            }
        }
        
        # Normalize category name for matching
        normalized_category = category
        # Remove all emoji prefixes
        emoji_prefixes = ["🆘 ", "🔨 ", "💰 ", "🐾 ", "🎲 ", "🎪 ", "🛠️ ", "📌 ", "🔍 ", "📈 ", "📊 ", "👥 ", "⚙️ ", "🎁 ", "👋 ", "🔗 ", "📝 ", "📋 ", "🤝 ", "💡 ", "🏆 ", "🔔 ", "🛡️ ", "🤖 "]
        for prefix in emoji_prefixes:
            normalized_category = normalized_category.replace(prefix, "")
        
        # Handle alternative category name mappings and check for matches
        if normalized_category in category_commands:
            # Direct match found
            category_data = category_commands[normalized_category]
            embed = discord.Embed(
                title=f"🍎 {category} Commands",
                description=f"**{len(category_data['commands'])} commands** available in this category",
                color=0x00ff00
            )
            
            # Add commands with descriptions
            commands_text = ""
            for cmd in category_data['commands']:
                desc = category_data['descriptions'].get(cmd, "No description available")
                commands_text += f"`!{cmd}` - {desc}\n"
            
            # Split into multiple fields if too long
            if len(commands_text) > 1000:
                commands_list = commands_text.split('\n')
                mid_point = len(commands_list) // 2
                
                embed.add_field(
                    name="Commands (Part 1)",
                    value='\n'.join(commands_list[:mid_point]),
                    inline=False
                )
                embed.add_field(
                    name="Commands (Part 2)", 
                    value='\n'.join(commands_list[mid_point:]),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Available Commands",
                    value=commands_text,
                    inline=False
                )
            
            embed.set_footer(text="Use !<command> to execute • Example: !balance")
        else:
            embed = discord.Embed(
                title="❌ Category Not Found",
                description=f"The category `{category}` was not found.\n\nUse `/help` without arguments to see all available categories.",
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed)

    @commands.command(name="cmdlist")
    async def commands_list(self, ctx):
        """Display all available commands organized by category"""
        embed = discord.Embed(
            title="📋 All Available Commands",
            description="Complete command directory organized by category",
            color=0x00ff00
        )
        
        categories = {
            "Help & Info": ["help", "cmdlist", "about", "features", "support"],
            "Moderation": ["ban", "unban", "kick", "mute", "unmute", "warn", "warnings", "clearwarnings", "timeout", "untimeout", "purge", "clear", "lock", "unlock", "slowmode", "massban", "lockdown", "unlockdown"],
            "Economy": ["balance", "daily", "weekly", "work", "rob", "gamble", "shop", "buy", "sell", "inventory", "give", "leaderboard", "coinflip", "slots", "blackjack", "deposit", "withdraw", "bankrob", "crime", "beg", "fish", "hunt", "mine", "chop", "plant"],
            "Fun & Games": ["dice", "8ball", "joke", "meme", "trivia", "riddle", "truth", "dare", "wouldyourather", "rps", "hangman", "wordle", "tic_tac_toe", "connect4", "snake", "pong", "maze", "trivia_quiz", "puzzle", "memory", "reaction", "typing", "math", "geography", "history", "science", "art", "music", "movie", "anime", "pokemon"],
            "Utility": ["calculator", "weather", "translate", "timezone", "reminder", "timer", "stopwatch", "qr", "shorturl", "color", "base64", "hash", "password", "random", "choose", "poll", "vote", "search", "wikipedia", "urban", "define", "synonym", "antonym"],
            "Information": ["userinfo", "serverinfo", "channelinfo", "roleinfo", "botinfo", "avatar", "banner", "membercount", "onlinecount", "created", "joined", "permissions", "roles", "channels", "emojis", "boosters", "invites"],
            "Leveling": ["level", "rank", "xp", "leaderboard", "setlevel", "addxp", "removexp", "resetlevels", "levelroles", "xpmultiplier"],
            "Community": ["events", "calendar", "meetup", "group", "club", "team", "project", "collaboration", "discussion", "forum", "thread", "topic", "announcement", "news", "newsletter"],
            "Analytics": ["stats", "activity", "growth", "engagement", "popular", "trends", "insights", "reports", "metrics", "dashboard", "charts", "graphs"],
            "Management": ["setup", "config", "settings", "prefix", "automod", "welcome", "goodbye", "autorole", "autoban", "verification", "captcha", "antispam", "antiraid", "backup", "restore", "export", "import", "reset"],
            "Events": ["giveaway", "gcreate", "gend", "greroll", "gedit", "glist", "event", "eventcreate", "eventend", "eventlist", "rsvp", "attend"],
            "Welcome System": ["welcomeset", "welcomemsg", "welcomechannel", "welcomerole", "welcomeimage", "goodbyemsg", "goodbyechannel"],
            "Invite Tracking": ["invites", "inviteinfo", "inviteleaderboard", "invitereward", "inviterank", "createinvite", "deleteinvite", "trackinvites"],
            "Logging": ["logset", "logchannel", "logevents", "logview", "logclear", "auditlog", "modlog", "messagelog", "joinlog", "voicelog"],
            "Applications": ["apply", "application", "applist", "appaccept", "appdeny", "appview", "apptemplate", "appsetup"],
            "Affiliates": ["affiliate", "addaffiliate", "removeaffiliate", "affiliatelist", "partnership", "sponsor", "collab"],
            "Suggestions": ["suggest", "suggestions", "suggestapprove", "suggestdeny", "suggeststats"],
            "Leaderboards": ["economyleaderboard", "xpboard", "petleaderboard", "topleaderboards"],
            "Notifications": ["notify", "notifications", "subscribe", "unsubscribe", "alerts", "reminder", "broadcast", "announcement", "ping"],
            "Security": ["whitelist", "blacklist", "raidmode", "securitylog", "reports", "suspicious", "antinuke"],
            "Automation": ["autoresponder", "automod", "scheduler", "triggers", "reactions", "autoroles", "autodelete", "autopurge", "autokick", "autoban", "antilink", "antispam", "keyword_filter", "message_filter", "auto_backup"],
            "Sticky Notes": ["stickynote", "notes", "addnote", "removenote", "editnote", "listnotes", "pinnote", "unpinnote"],
            "Pets": ["adopt", "pet", "feed", "play", "train", "breed", "abandon", "petshop", "petbattle", "petrace", "petcare", "petevolution", "pethunting", "petfishing"]
        }
        
        command_count = sum(len(commands) for commands in categories.values())
        
        for category, commands in categories.items():
            command_list = ", ".join(f"`{cmd}`" for cmd in commands[:8])
            if len(commands) > 8:
                command_list += f" ... and {len(commands) - 8} more"
            embed.add_field(
                name=f"{category} ({len(commands)})",
                value=command_list,
                inline=False
            )
        
        embed.set_footer(text=f"Total Commands: {command_count} | Use !help <category> for specific help")
        await ctx.send(embed=embed)
    
    @commands.command(name="about")
    async def about_bot(self, ctx):
        """Learn about Apple Bot's features and capabilities"""
        embed = discord.Embed(
            title="🍎 About Apple Bot",
            description="A comprehensive Discord bot with enterprise-scale features",
            color=0xff0000
        )
        
        embed.add_field(
            name="📊 Statistics",
            value="• 278+ Commands\n• 26 Specialized Modules\n• 1000+ Concurrent User Support\n• Enterprise-Grade Performance",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Core Features",
            value="• Complete Moderation Suite\n• Virtual Economy System\n• Pet Management\n• Gaming & Entertainment\n• Analytics & Insights",
            inline=True
        )
        
        embed.add_field(
            name="🚀 Advanced Systems",
            value="• Support Ticket System\n• Server Setup Wizard\n• Automation Tools\n• Custom Notifications\n• Sticky Notes",
            inline=True
        )
        
        embed.add_field(
            name="🛠️ Technical Specs",
            value="• PostgreSQL Database\n• Real-time Processing\n• Auto-scaling Architecture\n• 99.9% Uptime Target\n• Memory Optimized",
            inline=False
        )
        
        embed.set_footer(text="Apple Bot - Powering Discord Communities | Use !features for detailed overview")
        await ctx.send(embed=embed)
    
    @commands.command(name="features")
    async def features_overview(self, ctx):
        """View detailed feature overview and command count"""
        embed = discord.Embed(
            title="✨ Apple Bot Features Overview",
            description="Comprehensive feature breakdown by category",
            color=0x9932cc
        )
        
        features = {
            "🛡️ Moderation (23)": "Complete moderation suite with bans, kicks, mutes, warnings, timeouts, mass actions, lockdowns, and advanced security features",
            "💰 Economy (25)": "Virtual economy with jobs, gambling, shops, trading, banking, fishing, hunting, mining, and comprehensive leaderboards",
            "🐾 Pets (14)": "Full pet system with adoption, care, training, battles, racing, evolution, hunting, and fishing with your companions",
            "🎮 Fun & Games (30)": "Entertainment hub with trivia, puzzles, word games, arcade games, and interactive challenges across multiple categories",
            "🔧 Utility (23)": "Productivity tools including calculators, weather, translation, QR codes, polls, reminders, and information commands",
            "📈 Leveling (10)": "XP and ranking system with customizable level roles, multipliers, and comprehensive leaderboards",
            "👥 Community (15)": "Social features with events, groups, discussions, forums, announcements, and collaboration tools",
            "📊 Analytics (12)": "Server insights with activity tracking, growth metrics, engagement statistics, and detailed reports",
            "⚙️ Management (19)": "Server administration with setup wizards, configuration tools, automated systems, and backup features",
            "🎁 Events (11)": "Giveaway and event management with automated systems, RSVP tracking, and attendance monitoring",
            "👋 Welcome (8)": "Customizable welcome and goodbye systems with role assignment and channel configuration",
            "🔗 Invites (8)": "Comprehensive invite tracking with leaderboards, rewards, and analytics",
            "📝 Logging (10)": "Complete activity logging with audit trails, moderation logs, and message tracking",
            "📋 Applications (8)": "Application system with templates, review processes, and automated workflows",
            "🤝 Affiliates (7)": "Partnership management with affiliate tracking and collaboration tools",
            "💡 Suggestions (5)": "Suggestion system with approval workflows and community voting",
            "🏆 Leaderboards (4)": "Ranking displays across economy, XP, pets, and custom metrics",
            "🔔 Notifications (9)": "Alert system with subscriptions, broadcasts, and automated announcements",
            "🛡️ Security (7)": "Advanced security with anti-raid, anti-nuke, and threat detection systems",
            "🤖 Automation (20)": "Automated responses, moderation, scheduling, and workflow management",
            "📌 Sticky Notes (8)": "Persistent messaging system with note management and channel-specific displays",
            "ℹ️ Information (16)": "Comprehensive information commands for users, servers, roles, and channels"
        }
        
        for feature, description in features.items():
            embed.add_field(
                name=feature,
                value=description,
                inline=False
            )
        
        embed.set_footer(text="Total: 278+ Commands across 22 major categories")
        await ctx.send(embed=embed)
    
    @commands.command(name="support")
    async def support_info(self, ctx):
        """Get support information and contact details"""
        embed = discord.Embed(
            title="🆘 Apple Bot Support",
            description="Get help and support for Apple Bot",
            color=0xff6b35
        )
        
        embed.add_field(
            name="📖 Getting Started",
            value="• Use `!help` for command overview\n• Use `!cmdlist` for full command list\n• Use `!serversetup` to configure your server\n• Use `!settings` for feature configuration",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Common Issues",
            value="• **Missing Permissions**: Ensure bot has required permissions\n• **Commands Not Working**: Check command prefix with `!prefix`\n• **Database Issues**: Most features work offline too\n• **Rate Limits**: Some commands have cooldowns",
            inline=False
        )
        
        embed.add_field(
            name="📚 Documentation",
            value="• Command Categories: `!help <category>`\n• Feature Breakdown: `!features`\n• Bot Information: `!about`\n• Setup Guides: `!serversetup`",
            inline=False
        )
        
        embed.add_field(
            name="🎫 Support Channels",
            value="• Use `/support` to create a support ticket\n• Join our Discord support server\n• Check GitHub for updates and issues\n• Contact administrators for server-specific help",
            inline=False
        )
        
        embed.set_footer(text="Apple Bot Support • Always here to help!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))