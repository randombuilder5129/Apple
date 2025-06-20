import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SettingsMainView(discord.ui.View):
    """Main settings dashboard"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
    
    @discord.ui.button(label="Channel Settings", style=discord.ButtonStyle.primary, emoji="📺")
    async def channel_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📺 Channel Settings",
            description="Configure channels for bot features",
            color=discord.Color.blue()
        )
        view = ChannelSettingsView(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Feature Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def feature_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Feature Settings",
            description="Enable/disable bot features",
            color=discord.Color.green()
        )
        view = FeatureSettingsView(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Role Permissions", style=discord.ButtonStyle.secondary, emoji="👥")
    async def role_permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👥 Role Permissions",
            description="Configure role-based permissions",
            color=discord.Color.orange()
        )
        view = RolePermissionsView(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Maintenance", style=discord.ButtonStyle.danger, emoji="🔧")
    async def maintenance_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔧 Maintenance Settings",
            description="Server maintenance and bot status",
            color=discord.Color.red()
        )
        view = MaintenanceView(self.cog)
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelSettingsView(discord.ui.View):
    """Channel configuration interface"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
    
    @discord.ui.select(
        placeholder="Select channel type to configure...",
        options=[
            discord.SelectOption(label="Log Channel", description="Moderation logs and audit trail", emoji="📝"),
            discord.SelectOption(label="Welcome Channel", description="Member join/leave messages", emoji="👋"),
            discord.SelectOption(label="Counting Channel", description="Number counting game", emoji="🔢"),
            discord.SelectOption(label="Suggestions Channel", description="Server suggestions", emoji="💡"),
            discord.SelectOption(label="Bot Commands Channel", description="Bot command usage", emoji="🤖"),
            discord.SelectOption(label="Economy Channels", description="Shop and economy features", emoji="💰"),
            discord.SelectOption(label="Support Tickets", description="Ticket system category", emoji="🎫"),
            discord.SelectOption(label="Announcements Channel", description="Server announcements", emoji="📢")
        ]
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        channel_type = select.values[0]
        modal = ChannelConfigModal(self.cog, channel_type)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back to Main", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsMainView(self.cog)
        embed = discord.Embed(
            title="⚙️ Server Settings Dashboard",
            description="Configure all bot settings and features",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelConfigModal(discord.ui.Modal):
    """Modal for channel configuration"""
    
    def __init__(self, cog, channel_type):
        super().__init__(title=f"Configure {channel_type}")
        self.cog = cog
        self.channel_type = channel_type
        
        self.channel_input = discord.ui.TextInput(
            label=f"{channel_type} - Enter channel name or ID",
            placeholder="#channel-name or 123456789",
            required=False,
            max_length=100
        )
        
        self.add_item(self.channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel_input.value.strip()
        guild = interaction.guild
        
        if not channel_input:
            # Clear the setting
            await self.cog.update_channel_setting(guild.id, self.channel_type, None)
            await interaction.response.send_message(f"✅ {self.channel_type} has been cleared.", ephemeral=True)
            return
        
        # Try to find the channel
        channel = None
        if channel_input.startswith('#'):
            channel_name = channel_input[1:]
            channel = discord.utils.get(guild.channels, name=channel_name)
        elif channel_input.isdigit():
            channel = guild.get_channel(int(channel_input))
        else:
            channel = discord.utils.get(guild.channels, name=channel_input)
        
        if not channel:
            await interaction.response.send_message(f"❌ Channel not found: {channel_input}", ephemeral=True)
            return
        
        # Update the setting
        await self.cog.update_channel_setting(guild.id, self.channel_type, channel.id)
        await interaction.response.send_message(f"✅ {self.channel_type} set to {channel.mention}", ephemeral=True)

class FeatureSettingsView(discord.ui.View):
    """Feature enable/disable interface"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
    
    @discord.ui.select(
        placeholder="Select features to toggle...",
        options=[
            discord.SelectOption(label="Economy System", description="Currency, shop, and trading", emoji="💰", value="economy"),
            discord.SelectOption(label="Leveling System", description="XP and level progression", emoji="📈", value="leveling"),
            discord.SelectOption(label="Pet System", description="Virtual pets and care", emoji="🐕", value="pets"),
            discord.SelectOption(label="Welcome Messages", description="Join/leave notifications", emoji="👋", value="welcome"),
            discord.SelectOption(label="Auto Moderation", description="Automatic content filtering", emoji="🛡️", value="automod"),
            discord.SelectOption(label="Counting Game", description="Number counting channel", emoji="🔢", value="counting"),
            discord.SelectOption(label="Suggestions", description="User suggestions system", emoji="💡", value="suggestions"),
            discord.SelectOption(label="Support Tickets", description="Ticket system", emoji="🎫", value="tickets"),
            discord.SelectOption(label="Giveaways", description="Event and giveaway system", emoji="🎁", value="giveaways"),
            discord.SelectOption(label="Music Commands", description="Music playback features", emoji="🎵", value="music")
        ],
        max_values=10
    )
    async def feature_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_features = select.values
        guild_id = interaction.guild.id
        
        # Get current settings
        current_settings = await self.cog.get_feature_settings(guild_id)
        
        embed = discord.Embed(
            title="🔧 Feature Toggle",
            description="Click buttons to enable/disable features",
            color=discord.Color.blue()
        )
        
        for feature in selected_features:
            is_enabled = current_settings.get(feature, True)  # Economy enabled by default
            status = "✅ Enabled" if is_enabled else "❌ Disabled"
            embed.add_field(name=feature.title(), value=status, inline=True)
        
        view = FeatureToggleView(self.cog, selected_features, current_settings)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Back to Main", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsMainView(self.cog)
        embed = discord.Embed(
            title="⚙️ Server Settings Dashboard",
            description="Configure all bot settings and features",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class FeatureToggleView(discord.ui.View):
    """Toggle individual features"""
    
    def __init__(self, cog, features, current_settings):
        super().__init__(timeout=600)
        self.cog = cog
        self.features = features
        self.current_settings = current_settings
        
        for feature in features:
            is_enabled = current_settings.get(feature, feature == 'economy')  # Economy default enabled
            button = discord.ui.Button(
                label=f"{'Disable' if is_enabled else 'Enable'} {feature.title()}",
                style=discord.ButtonStyle.danger if is_enabled else discord.ButtonStyle.success,
                custom_id=f"toggle_{feature}"
            )
            button.callback = self.create_toggle_callback(feature)
            self.add_item(button)
    
    def create_toggle_callback(self, feature):
        async def toggle_callback(interaction):
            guild_id = interaction.guild.id
            current_state = self.current_settings.get(feature, feature == 'economy')
            new_state = not current_state
            
            await self.cog.update_feature_setting(guild_id, feature, new_state)
            self.current_settings[feature] = new_state
            
            status = "enabled" if new_state else "disabled"
            await interaction.response.send_message(f"✅ {feature.title()} has been {status}.", ephemeral=True)
            
        return toggle_callback

class RolePermissionsView(discord.ui.View):
    """Role permission configuration"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
    
    @discord.ui.select(
        placeholder="Select permission level to configure...",
        options=[
            discord.SelectOption(label="Admin Roles", description="Full bot administration", emoji="👑"),
            discord.SelectOption(label="Moderator Roles", description="Moderation commands", emoji="🛡️"),
            discord.SelectOption(label="Support Roles", description="Ticket management", emoji="🎫"),
            discord.SelectOption(label="DJ Roles", description="Music control", emoji="🎵"),
            discord.SelectOption(label="Economy Managers", description="Economy administration", emoji="💰"),
            discord.SelectOption(label="Event Managers", description="Giveaway and event control", emoji="🎁")
        ]
    )
    async def permission_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        permission_type = select.values[0]
        modal = RolePermissionModal(self.cog, permission_type)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back to Main", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsMainView(self.cog)
        embed = discord.Embed(
            title="⚙️ Server Settings Dashboard",
            description="Configure all bot settings and features",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class RolePermissionModal(discord.ui.Modal):
    """Modal for role permission configuration"""
    
    def __init__(self, cog, permission_type):
        super().__init__(title=f"Configure {permission_type}")
        self.cog = cog
        self.permission_type = permission_type
        
        self.role_input = discord.ui.TextInput(
            label=f"{permission_type} - Enter role names (one per line)",
            placeholder="Admin\nModerator\nSupport Team",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        role_input = self.role_input.value.strip()
        guild = interaction.guild
        
        if not role_input:
            await self.cog.update_role_permission(guild.id, self.permission_type, [])
            await interaction.response.send_message(f"✅ {self.permission_type} permissions cleared.", ephemeral=True)
            return
        
        role_names = [name.strip() for name in role_input.split('\n') if name.strip()]
        role_ids = []
        
        for role_name in role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                role_ids.append(role.id)
        
        await self.cog.update_role_permission(guild.id, self.permission_type, role_ids)
        found_roles = len(role_ids)
        total_roles = len(role_names)
        
        await interaction.response.send_message(
            f"✅ {self.permission_type} updated. Found {found_roles}/{total_roles} roles.",
            ephemeral=True
        )

class MaintenanceView(discord.ui.View):
    """Maintenance settings interface"""
    
    def __init__(self, cog):
        super().__init__(timeout=600)
        self.cog = cog
    
    @discord.ui.button(label="Enable Maintenance", style=discord.ButtonStyle.danger, emoji="🔧")
    async def enable_maintenance(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MaintenanceModal(self.cog, True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Disable Maintenance", style=discord.ButtonStyle.success, emoji="✅")
    async def disable_maintenance(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        await self.cog.update_maintenance_mode(guild_id, False, "")
        
        embed = discord.Embed(
            title="✅ Maintenance Mode Disabled",
            description="Bot is now fully operational for all users.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Maintenance Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def maintenance_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        status = await self.cog.get_maintenance_status(guild_id)
        
        if status['enabled']:
            embed = discord.Embed(
                title="🔧 Maintenance Mode Active",
                description=f"**Reason:** {status['reason']}\n**Since:** {status['started']}",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="✅ Bot Operational",
                description="All systems running normally",
                color=discord.Color.green()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Back to Main", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsMainView(self.cog)
        embed = discord.Embed(
            title="⚙️ Server Settings Dashboard",
            description="Configure all bot settings and features",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class MaintenanceModal(discord.ui.Modal):
    """Modal for maintenance configuration"""
    
    def __init__(self, cog, enable):
        super().__init__(title="Maintenance Mode")
        self.cog = cog
        self.enable = enable
        
        self.reason_input = discord.ui.TextInput(
            label="Maintenance Reason",
            placeholder="Server updates, bug fixes, etc.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=200
        )
        
        self.add_item(self.reason_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        reason = self.reason_input.value.strip()
        
        await self.cog.update_maintenance_mode(guild_id, self.enable, reason)
        
        embed = discord.Embed(
            title="🔧 Maintenance Mode Enabled",
            description=f"**Reason:** {reason}\n\nBot commands are now restricted to administrators only.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Settings(commands.Cog):
    """Comprehensive server settings management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="settings")
    @commands.has_permissions(administrator=True)
    async def settings_dashboard(self, ctx):
        """Interactive server settings dashboard"""
        
        embed = discord.Embed(
            title="⚙️ Server Settings Dashboard",
            description="Configure all bot settings and features for your server",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📺 Channel Settings",
            value="Configure channels for logging, welcome messages, counting, suggestions, and more",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Feature Settings",
            value="Enable/disable economy, leveling, pets, auto-moderation, and other features",
            inline=False
        )
        
        embed.add_field(
            name="👥 Role Permissions",
            value="Set up role-based permissions for different bot functions",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Maintenance",
            value="Server maintenance mode and bot status management",
            inline=False
        )
        
        embed.set_footer(text="Use the buttons below to navigate settings")
        
        view = SettingsMainView(self)
        await ctx.send(embed=embed, view=view)
    
    async def update_channel_setting(self, guild_id, channel_type, channel_id):
        """Update channel setting in database"""
        if not self.bot.db_pool:
            return
        
        try:
            # Map channel types to database columns
            column_mapping = {
                "Log Channel": "log_channel",
                "Welcome Channel": "welcome_channel", 
                "Counting Channel": "counting_channel",
                "Suggestions Channel": "suggestions_channel",
                "Bot Commands Channel": "bot_commands_channel",
                "Economy Channels": "economy_channel",
                "Support Tickets": "support_category",
                "Announcements Channel": "announcements_channel"
            }
            
            column = column_mapping.get(channel_type)
            if not column:
                return
            
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO guild_settings (guild_id, {column})
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        {column} = EXCLUDED.{column}
                """, guild_id, channel_id)
        
        except Exception as e:
            logger.error(f"Error updating channel setting: {e}")
    
    async def get_feature_settings(self, guild_id):
        """Get feature settings from database"""
        if not self.bot.db_pool:
            return {"economy": True}  # Default: economy enabled
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT economy_enabled, leveling_enabled, pets_enabled,
                           welcome_enabled, automod_enabled, counting_enabled,
                           suggestions_enabled, tickets_enabled, giveaways_enabled,
                           music_enabled
                    FROM guild_settings WHERE guild_id = $1
                """, guild_id)
                
                if not row:
                    return {"economy": True}  # Default: economy enabled
                
                return {
                    "economy": row["economy_enabled"] if row["economy_enabled"] is not None else True,
                    "leveling": row["leveling_enabled"] or False,
                    "pets": row["pets_enabled"] or False,
                    "welcome": row["welcome_enabled"] or False,
                    "automod": row["automod_enabled"] or False,
                    "counting": row["counting_enabled"] or False,
                    "suggestions": row["suggestions_enabled"] or False,
                    "tickets": row["tickets_enabled"] or False,
                    "giveaways": row["giveaways_enabled"] or False,
                    "music": row["music_enabled"] or False
                }
        
        except Exception as e:
            logger.error(f"Error getting feature settings: {e}")
            return {"economy": True}  # Default: economy enabled
    
    async def update_feature_setting(self, guild_id, feature, enabled):
        """Update feature setting in database"""
        if not self.bot.db_pool:
            return
        
        try:
            column_mapping = {
                "economy": "economy_enabled",
                "leveling": "leveling_enabled",
                "pets": "pets_enabled",
                "welcome": "welcome_enabled",
                "automod": "automod_enabled",
                "counting": "counting_enabled",
                "suggestions": "suggestions_enabled",
                "tickets": "tickets_enabled",
                "giveaways": "giveaways_enabled",
                "music": "music_enabled"
            }
            
            column = column_mapping.get(feature)
            if not column:
                return
            
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO guild_settings (guild_id, {column})
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        {column} = EXCLUDED.{column}
                """, guild_id, enabled)
        
        except Exception as e:
            logger.error(f"Error updating feature setting: {e}")
    
    async def update_role_permission(self, guild_id, permission_type, role_ids):
        """Update role permissions in database"""
        if not self.bot.db_pool:
            return
        
        try:
            # Store as JSON array
            role_ids_json = role_ids
            
            async with self.bot.db_pool.acquire() as conn:
                column_mapping = {
                    "Admin Roles": "admin_roles",
                    "Moderator Roles": "moderator_roles",
                    "Support Roles": "support_roles",
                    "DJ Roles": "dj_roles",
                    "Economy Managers": "economy_manager_roles",
                    "Event Managers": "event_manager_roles"
                }
                
                column = column_mapping.get(permission_type)
                if not column:
                    return
                
                await conn.execute(f"""
                    INSERT INTO guild_settings (guild_id, {column})
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        {column} = EXCLUDED.{column}
                """, guild_id, role_ids_json)
        
        except Exception as e:
            logger.error(f"Error updating role permissions: {e}")
    
    async def update_maintenance_mode(self, guild_id, enabled, reason):
        """Update maintenance mode setting"""
        if not self.bot.db_pool:
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO guild_settings (guild_id, maintenance_mode, maintenance_reason)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        maintenance_mode = EXCLUDED.maintenance_mode,
                        maintenance_reason = EXCLUDED.maintenance_reason
                """, guild_id, enabled, reason)
        
        except Exception as e:
            logger.error(f"Error updating maintenance mode: {e}")
    
    async def get_maintenance_status(self, guild_id):
        """Get maintenance status from database"""
        if not self.bot.db_pool:
            return {"enabled": False, "reason": "", "started": None}
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT maintenance_mode, maintenance_reason, created_at
                    FROM guild_settings WHERE guild_id = $1
                """, guild_id)
                
                if not row:
                    return {"enabled": False, "reason": "", "started": None}
                
                return {
                    "enabled": row["maintenance_mode"] or False,
                    "reason": row["maintenance_reason"] or "",
                    "started": row["created_at"]
                }
        
        except Exception as e:
            logger.error(f"Error getting maintenance status: {e}")
            return {"enabled": False, "reason": "", "started": None}

async def setup(bot):
    await bot.add_cog(Settings(bot))