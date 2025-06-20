import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SetupModeSelect(discord.ui.Select):
    """Setup mode selection dropdown"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Quick Setup (Hands-off)", description="Automatic setup with default settings", emoji="⚡"),
            discord.SelectOption(label="Custom Setup", description="Interactive setup with full customization", emoji="⚙️"),
            discord.SelectOption(label="Minimal Setup", description="Essential channels and roles only", emoji="📋")
        ]
        
        super().__init__(
            placeholder="Choose your setup preference...",
            options=options,
            custom_id="setup_mode_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        setup_mode = self.values[0]
        
        if setup_mode == "Quick Setup (Hands-off)":
            await self.view.start_quick_setup(interaction)
        elif setup_mode == "Custom Setup":
            await self.view.start_custom_setup(interaction)
        else:  # Minimal Setup
            await self.view.start_minimal_setup(interaction)

class ServerSetupView(discord.ui.View):
    """Main server setup view"""
    
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.setup_data = {}
        self.add_item(SetupModeSelect())
    
    async def start_quick_setup(self, interaction):
        """Start hands-off quick setup"""
        await interaction.response.edit_message(
            content="🚀 **Quick Setup Started** - Setting up your server automatically...",
            embed=None,
            view=None
        )
        
        guild = interaction.guild
        progress_embed = discord.Embed(
            title="⚡ Quick Server Setup",
            description="Setting up your server with optimal defaults...",
            color=discord.Color.blue()
        )
        
        # Default setup configuration
        setup_config = {
            'categories': [
                'Staff Only',
                'General',
                'Voice Channels',
                'Support Tickets'
            ],
            'channels': {
                'Staff Only': ['staff-chat', 'mod-logs', 'announcements'],
                'General': ['general', 'bot-commands', 'counting', 'suggestions'],
                'Voice Channels': ['General Voice', 'Music Room', 'Study Hall'],
                'Support Tickets': []  # Will be managed by support system
            },
            'roles': [
                'Owner', 'Admin', 'Moderator', 'Support Team', 'Members', 'Bots'
            ]
        }
        
        await self.cog.execute_setup(interaction, setup_config, progress_embed)
    
    async def start_custom_setup(self, interaction):
        """Start interactive custom setup"""
        embed = discord.Embed(
            title="⚙️ Custom Server Setup",
            description="Let's customize your server step by step!",
            color=discord.Color.green()
        )
        
        view = CustomSetupFlow(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def start_minimal_setup(self, interaction):
        """Start minimal essential setup"""
        await interaction.response.edit_message(
            content="📋 **Minimal Setup Started** - Creating essential server structure...",
            embed=None,
            view=None
        )
        
        setup_config = {
            'categories': ['General', 'Staff'],
            'channels': {
                'General': ['general', 'bot-commands'],
                'Staff': ['mod-logs']
            },
            'roles': ['Admin', 'Moderator', 'Members']
        }
        
        progress_embed = discord.Embed(
            title="📋 Minimal Server Setup",
            description="Creating essential server structure...",
            color=discord.Color.orange()
        )
        
        await self.cog.execute_setup(interaction, setup_config, progress_embed)

class CustomSetupFlow(discord.ui.View):
    """Interactive custom setup flow"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
        self.step = 0
        self.setup_data = {
            'categories': [],
            'channels': {},
            'roles': [],
            'special_channels': {}
        }
    
    @discord.ui.button(label="Start Custom Setup", style=discord.ButtonStyle.primary, emoji="🛠️")
    async def start_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.step_1_roles(interaction)
    
    async def step_1_roles(self, interaction):
        """Step 1: Configure roles"""
        embed = discord.Embed(
            title="Step 1: Server Roles",
            description="Choose which roles to create for your server:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Recommended Roles:",
            value="• Owner\n• Admin\n• Moderator\n• Support Team\n• VIP\n• Members\n• Bots",
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to customize your roles")
        
        view = RoleSetupView(self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def step_2_categories(self, interaction):
        """Step 2: Configure categories"""
        embed = discord.Embed(
            title="Step 2: Channel Categories",
            description="Choose categories to organize your channels:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Recommended Categories:",
            value="• Staff Only\n• General\n• Voice Channels\n• Support Tickets\n• Gaming\n• Community",
            inline=False
        )
        
        view = CategorySetupView(self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def step_3_channels(self, interaction):
        """Step 3: Configure channels"""
        embed = discord.Embed(
            title="Step 3: Server Channels",
            description="Configure channels for each category:",
            color=discord.Color.blue()
        )
        
        categories_text = "\n".join([f"• {cat}" for cat in self.setup_data['categories']])
        embed.add_field(name="Your Categories:", value=categories_text, inline=False)
        
        view = ChannelSetupView(self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def step_4_special(self, interaction):
        """Step 4: Configure special channels"""
        embed = discord.Embed(
            title="Step 4: Special Channels",
            description="Set up special bot features:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Special Features:",
            value="• Counting Channel\n• Suggestions Channel\n• Welcome Messages\n• Moderation Logs\n• Bot Commands",
            inline=False
        )
        
        view = SpecialSetupView(self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def finalize_setup(self, interaction):
        """Finalize and execute the setup"""
        # Convert setup_data to config format
        config = {
            'categories': self.setup_data['categories'],
            'channels': self.setup_data['channels'],
            'roles': self.setup_data['roles']
        }
        
        progress_embed = discord.Embed(
            title="🛠️ Custom Server Setup",
            description="Executing your custom configuration...",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(
            content="🛠️ **Custom Setup Started** - Creating your customized server...",
            embed=None,
            view=None
        )
        
        await self.cog.execute_setup(interaction, config, progress_embed)

class RoleSetupView(discord.ui.View):
    """Role configuration view"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=300)
        self.parent = parent_view
        self.selected_roles = ['Owner', 'Admin', 'Moderator', 'Support Team', 'Members', 'Bots']
    
    @discord.ui.button(label="Use Recommended", style=discord.ButtonStyle.green)
    async def use_recommended(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.setup_data['roles'] = self.selected_roles
        await self.parent.step_2_categories(interaction)
    
    @discord.ui.button(label="Customize Roles", style=discord.ButtonStyle.secondary)
    async def customize_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoleCustomizationModal(self.parent)
        await interaction.response.send_modal(modal)

class RoleCustomizationModal(discord.ui.Modal):
    """Modal for custom role configuration"""
    
    def __init__(self, parent_view):
        super().__init__(title="Customize Server Roles")
        self.parent = parent_view
        
        self.roles_input = discord.ui.TextInput(
            label="Server Roles (one per line)",
            placeholder="Owner\nAdmin\nModerator\nSupport Team\nMembers\nBots",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
            default="Owner\nAdmin\nModerator\nSupport Team\nMembers\nBots"
        )
        
        self.add_item(self.roles_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        roles = [role.strip() for role in self.roles_input.value.split('\n') if role.strip()]
        self.parent.setup_data['roles'] = roles
        await self.parent.step_2_categories(interaction)

class CategorySetupView(discord.ui.View):
    """Category configuration view"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=300)
        self.parent = parent_view
        self.selected_categories = ['Staff Only', 'General', 'Voice Channels', 'Support Tickets']
    
    @discord.ui.button(label="Use Recommended", style=discord.ButtonStyle.green)
    async def use_recommended(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.setup_data['categories'] = self.selected_categories
        self.parent.setup_data['channels'] = {
            'Staff Only': ['staff-chat', 'mod-logs', 'announcements'],
            'General': ['general', 'bot-commands', 'counting', 'suggestions'],
            'Voice Channels': ['General Voice', 'Music Room', 'Study Hall'],
            'Support Tickets': []
        }
        await self.parent.step_4_special(interaction)
    
    @discord.ui.button(label="Customize Categories", style=discord.ButtonStyle.secondary)
    async def customize_categories(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CategoryCustomizationModal(self.parent)
        await interaction.response.send_modal(modal)

class CategoryCustomizationModal(discord.ui.Modal):
    """Modal for custom category configuration"""
    
    def __init__(self, parent_view):
        super().__init__(title="Customize Categories")
        self.parent = parent_view
        
        self.categories_input = discord.ui.TextInput(
            label="Categories (one per line)",
            placeholder="Staff Only\nGeneral\nVoice Channels\nSupport Tickets\nGaming\nCommunity",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500,
            default="Staff Only\nGeneral\nVoice Channels\nSupport Tickets"
        )
        
        self.add_item(self.categories_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        categories = [cat.strip() for cat in self.categories_input.value.split('\n') if cat.strip()]
        self.parent.setup_data['categories'] = categories
        
        # Initialize channels dict
        self.parent.setup_data['channels'] = {cat: [] for cat in categories}
        
        await self.parent.step_3_channels(interaction)

class ChannelSetupView(discord.ui.View):
    """Channel configuration view"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=300)
        self.parent = parent_view
        self.current_category = 0
    
    @discord.ui.button(label="Quick Fill", style=discord.ButtonStyle.green)
    async def quick_fill(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Auto-populate channels based on category names
        default_channels = {
            'Staff Only': ['staff-chat', 'mod-logs', 'announcements'],
            'General': ['general', 'bot-commands', 'counting', 'suggestions'],
            'Voice Channels': ['General Voice', 'Music Room', 'Study Hall'],
            'Support Tickets': [],
            'Gaming': ['game-chat', 'looking-for-group', 'Gaming Voice'],
            'Community': ['events', 'introductions', 'off-topic']
        }
        
        for category in self.parent.setup_data['categories']:
            if category in default_channels:
                self.parent.setup_data['channels'][category] = default_channels[category]
            else:
                # Generic channels for custom categories
                self.parent.setup_data['channels'][category] = [f"{category.lower().replace(' ', '-')}-chat"]
        
        await self.parent.step_4_special(interaction)
    
    @discord.ui.button(label="Custom Configuration", style=discord.ButtonStyle.secondary)
    async def custom_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_category < len(self.parent.setup_data['categories']):
            category = self.parent.setup_data['categories'][self.current_category]
            modal = ChannelCustomizationModal(self.parent, category, self.current_category)
            await interaction.response.send_modal(modal)
        else:
            await self.parent.step_4_special(interaction)

class ChannelCustomizationModal(discord.ui.Modal):
    """Modal for custom channel configuration"""
    
    def __init__(self, parent_view, category, category_index):
        super().__init__(title=f"Channels for {category}")
        self.parent = parent_view
        self.category = category
        self.category_index = category_index
        
        self.channels_input = discord.ui.TextInput(
            label=f"Channels for {category} (one per line)",
            placeholder="general\nbot-commands\nannouncements",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=800
        )
        
        self.add_item(self.channels_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channels = [ch.strip() for ch in self.channels_input.value.split('\n') if ch.strip()]
        self.parent.setup_data['channels'][self.category] = channels
        
        # Move to next category or finish
        self.parent.parent.current_category += 1
        view = ChannelSetupView(self.parent)
        view.current_category = self.parent.parent.current_category
        
        if view.current_category < len(self.parent.setup_data['categories']):
            next_category = self.parent.setup_data['categories'][view.current_category]
            embed = discord.Embed(
                title=f"Configure {next_category}",
                description=f"Set up channels for the {next_category} category:",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await self.parent.step_4_special(interaction)

class SpecialSetupView(discord.ui.View):
    """Special features configuration view"""
    
    def __init__(self, parent_view):
        super().__init__(timeout=300)
        self.parent = parent_view
        self.special_features = {
            'counting': True,
            'suggestions': True,
            'welcome': True,
            'logs': True,
            'bot_commands': True
        }
    
    @discord.ui.button(label="Enable All Features", style=discord.ButtonStyle.green)
    async def enable_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.setup_data['special_channels'] = self.special_features
        await self.parent.finalize_setup(interaction)
    
    @discord.ui.button(label="Customize Features", style=discord.ButtonStyle.secondary)
    async def customize_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SpecialFeaturesModal(self.parent)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Skip Special Features", style=discord.ButtonStyle.danger)
    async def skip_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.setup_data['special_channels'] = {}
        await self.parent.finalize_setup(interaction)

class SpecialFeaturesModal(discord.ui.Modal):
    """Modal for special features configuration"""
    
    def __init__(self, parent_view):
        super().__init__(title="Special Features Configuration")
        self.parent = parent_view
        
        self.features_input = discord.ui.TextInput(
            label="Features to enable (one per line)",
            placeholder="counting\nsuggestions\nwelcome\nlogs\nbot_commands",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=300,
            default="counting\nsuggestions\nwelcome\nlogs\nbot_commands"
        )
        
        self.add_item(self.features_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        features = [f.strip() for f in self.features_input.value.split('\n') if f.strip()]
        
        feature_mapping = {
            'counting': True,
            'suggestions': True,
            'welcome': True,
            'logs': True,
            'bot_commands': True
        }
        
        self.parent.setup_data['special_channels'] = {
            key: key in features for key in feature_mapping
        }
        
        await self.parent.finalize_setup(interaction)

class ServerSetup(commands.Cog):
    """Server setup and configuration"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="serversetup")
    @commands.has_permissions(administrator=True)
    async def server_setup(self, ctx):
        """Interactive server setup with full customization"""
        
        embed = discord.Embed(
            title="🏗️ Apple Bot Server Setup",
            description="Welcome to the comprehensive server setup wizard!\n\nThis tool will help you configure your server with all necessary channels, roles, and categories.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Setup Options:",
            value="""
⚡ **Quick Setup** - Hands-off automatic setup
⚙️ **Custom Setup** - Full interactive customization  
📋 **Minimal Setup** - Essential channels and roles only
            """,
            inline=False
        )
        
        embed.add_field(
            name="What Gets Created:",
            value="• Server roles with proper hierarchy\n• Organized channel categories\n• Essential channels (general, mod-logs, etc.)\n• Special channels (counting, suggestions)\n• Proper permissions for all roles",
            inline=False
        )
        
        embed.set_footer(text="Select your preferred setup mode below")
        
        view = ServerSetupView(self)
        await ctx.send(embed=embed, view=view)
    
    async def execute_setup(self, interaction, config, progress_embed):
        """Execute the server setup with given configuration"""
        guild = interaction.guild
        created_items = {
            'roles': [],
            'categories': [],
            'channels': [],
            'errors': []
        }
        
        try:
            # Update progress
            progress_embed.add_field(name="Status", value="Creating roles...", inline=False)
            message = await interaction.edit_original_response(embed=progress_embed)
            
            # Create roles
            role_colors = {
                'Owner': discord.Color.red(),
                'Admin': discord.Color.dark_red(),
                'Moderator': discord.Color.orange(),
                'Support Team': discord.Color.blue(),
                'VIP': discord.Color.gold(),
                'Members': discord.Color.green(),
                'Bots': discord.Color.light_grey()
            }
            
            for role_name in config.get('roles', []):
                try:
                    if not discord.utils.get(guild.roles, name=role_name):
                        color = role_colors.get(role_name, discord.Color.default())
                        role = await guild.create_role(
                            name=role_name,
                            color=color,
                            reason="Server setup by Apple Bot"
                        )
                        created_items['roles'].append(role.name)
                except Exception as e:
                    created_items['errors'].append(f"Role {role_name}: {str(e)}")
            
            # Update progress
            progress_embed.set_field_at(0, name="Status", value="Creating categories...", inline=False)
            await message.edit(embed=progress_embed)
            
            # Create categories
            for category_name in config.get('categories', []):
                try:
                    if not discord.utils.get(guild.categories, name=category_name):
                        overwrites = self.get_category_permissions(guild, category_name)
                        category = await guild.create_category(
                            category_name,
                            overwrites=overwrites,
                            reason="Server setup by Apple Bot"
                        )
                        created_items['categories'].append(category.name)
                except Exception as e:
                    created_items['errors'].append(f"Category {category_name}: {str(e)}")
            
            # Update progress
            progress_embed.set_field_at(0, name="Status", value="Creating channels...", inline=False)
            await message.edit(embed=progress_embed)
            
            # Create channels
            for category_name, channel_list in config.get('channels', {}).items():
                category = discord.utils.get(guild.categories, name=category_name)
                
                for channel_name in channel_list:
                    try:
                        if not discord.utils.get(guild.channels, name=channel_name):
                            overwrites = self.get_channel_permissions(guild, channel_name, category_name)
                            
                            if channel_name in ['General Voice', 'Music Room', 'Study Hall']:
                                channel = await guild.create_voice_channel(
                                    channel_name,
                                    category=category,
                                    overwrites=overwrites,
                                    reason="Server setup by Apple Bot"
                                )
                            else:
                                channel = await guild.create_text_channel(
                                    channel_name,
                                    category=category,
                                    overwrites=overwrites,
                                    reason="Server setup by Apple Bot"
                                )
                            
                            created_items['channels'].append(f"#{channel.name}")
                            
                            # Set up special channels
                            await self.setup_special_channel(channel, channel_name)
                            
                    except Exception as e:
                        created_items['errors'].append(f"Channel {channel_name}: {str(e)}")
            
            # Update database settings
            await self.update_guild_settings(guild, created_items)
            
            # Final success message
            await self.send_completion_message(interaction, created_items, progress_embed)
            
        except Exception as e:
            logger.error(f"Server setup error: {e}")
            error_embed = discord.Embed(
                title="❌ Setup Error",
                description=f"An error occurred during setup: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=error_embed)
    
    def get_category_permissions(self, guild, category_name):
        """Get appropriate permissions for category"""
        overwrites = {}
        
        if category_name == "Staff Only":
            # Staff only access
            overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
            
            for role_name in ["Owner", "Admin", "Moderator"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        elif category_name == "Support Tickets":
            # Ticket system permissions
            overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
            
            support_role = discord.utils.get(guild.roles, name="Support Team")
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        return overwrites
    
    def get_channel_permissions(self, guild, channel_name, category_name):
        """Get appropriate permissions for specific channels"""
        overwrites = {}
        
        if channel_name == "mod-logs":
            # Mod logs - staff only
            overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
            
            for role_name in ["Owner", "Admin", "Moderator"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
        
        elif channel_name == "announcements":
            # Announcements - read only for members
            overwrites[guild.default_role] = discord.PermissionOverwrite(send_messages=False)
            
            for role_name in ["Owner", "Admin", "Moderator"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(send_messages=True)
        
        return overwrites
    
    async def setup_special_channel(self, channel, channel_name):
        """Set up special channel configurations"""
        try:
            if channel_name == "counting":
                embed = discord.Embed(
                    title="🔢 Counting Channel",
                    description="Start counting from 1! Each person can only send the next number.\n\nRules:\n• Count in order (1, 2, 3...)\n• One number per person\n• No text, just numbers",
                    color=discord.Color.blue()
                )
                await channel.send(embed=embed)
                await channel.send("1")
            
            elif channel_name == "suggestions":
                embed = discord.Embed(
                    title="💡 Suggestions",
                    description="Share your ideas to improve the server!\n\nUse `/suggest <your idea>` to submit suggestions.",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
            
            elif channel_name == "general":
                embed = discord.Embed(
                    title="👋 Welcome to the Server!",
                    description="This is the main chat channel. Feel free to introduce yourself and chat with other members!",
                    color=discord.Color.blue()
                )
                await channel.send(embed=embed)
            
            elif channel_name == "bot-commands":
                embed = discord.Embed(
                    title="🤖 Bot Commands",
                    description="Use this channel for bot commands to keep other channels clean.\n\nTry `/help` to see all available commands!",
                    color=discord.Color.purple()
                )
                await channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error setting up special channel {channel_name}: {e}")
    
    async def update_guild_settings(self, guild, created_items):
        """Update guild settings in database"""
        if not self.bot.db_pool:
            return
        
        try:
            # Find important channels
            log_channel = discord.utils.get(guild.channels, name="mod-logs")
            general_channel = discord.utils.get(guild.channels, name="general")
            counting_channel = discord.utils.get(guild.channels, name="counting")
            
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO guild_settings (
                        guild_id, log_channel, general_channel, counting_channel, setup_completed
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        log_channel = EXCLUDED.log_channel,
                        general_channel = EXCLUDED.general_channel,
                        counting_channel = EXCLUDED.counting_channel,
                        setup_completed = EXCLUDED.setup_completed
                """, guild.id, 
                log_channel.id if log_channel else None,
                general_channel.id if general_channel else None,
                counting_channel.id if counting_channel else None,
                True)
        
        except Exception as e:
            logger.error(f"Database error updating guild settings: {e}")
    
    async def send_completion_message(self, interaction, created_items, progress_embed):
        """Send setup completion message"""
        embed = discord.Embed(
            title="✅ Server Setup Complete!",
            description="Your server has been successfully configured with Apple Bot.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        if created_items['roles']:
            embed.add_field(
                name=f"📝 Roles Created ({len(created_items['roles'])})",
                value=", ".join(created_items['roles'][:10]) + ("..." if len(created_items['roles']) > 10 else ""),
                inline=False
            )
        
        if created_items['categories']:
            embed.add_field(
                name=f"📁 Categories Created ({len(created_items['categories'])})",
                value=", ".join(created_items['categories']),
                inline=False
            )
        
        if created_items['channels']:
            embed.add_field(
                name=f"📺 Channels Created ({len(created_items['channels'])})",
                value=", ".join(created_items['channels'][:15]) + ("..." if len(created_items['channels']) > 15 else ""),
                inline=False
            )
        
        if created_items['errors']:
            embed.add_field(
                name="⚠️ Warnings",
                value=f"{len(created_items['errors'])} items already existed or had errors",
                inline=False
            )
        
        embed.add_field(
            name="🎉 What's Next?",
            value="• Use `/help` to explore bot features\n• Check out your new channels\n• Assign roles to members\n• Customize channel permissions as needed",
            inline=False
        )
        
        embed.set_footer(text="Server setup completed by Apple Bot")
        
        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerSetup(bot))