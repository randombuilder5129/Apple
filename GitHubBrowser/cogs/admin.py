import discord
from discord.ext import commands
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConfirmRestartView(discord.ui.View):
    """Confirmation view for server restart (channel deletion)"""
    
    def __init__(self, author_id):
        super().__init__(timeout=30)
        self.author_id = author_id
        self.confirmed = False
    
    @discord.ui.button(label="Yes, Delete All Channels", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the command user can confirm this action.", ephemeral=True)
            return
        
        # Double check ownership
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Only the server owner can confirm this action.", ephemeral=True)
            return
        
        self.confirmed = True
        
        await interaction.response.edit_message(
            content="🔥 **DELETING ALL CHANNELS** - This cannot be undone!",
            embed=None,
            view=None
        )
        
        # Start deletion process
        guild = interaction.guild
        deleted_count = 0
        failed_count = 0
        
        # Get all channels before deletion (to avoid list changing during iteration)
        channels_to_delete = [channel for channel in guild.channels if channel.type != discord.ChannelType.category]
        categories_to_delete = [channel for channel in guild.channels if channel.type == discord.ChannelType.category]
        
        # Delete text/voice channels first
        for channel in channels_to_delete:
            try:
                await channel.delete(reason=f"Server restart by {interaction.user}")
                deleted_count += 1
                await asyncio.sleep(0.5)  # Rate limit protection
            except Exception as e:
                logger.error(f"Failed to delete channel {channel.name}: {e}")
                failed_count += 1
        
        # Delete categories last
        for category in categories_to_delete:
            try:
                await category.delete(reason=f"Server restart by {interaction.user}")
                deleted_count += 1
                await asyncio.sleep(0.5)  # Rate limit protection
            except Exception as e:
                logger.error(f"Failed to delete category {category.name}: {e}")
                failed_count += 1
        
        # Create a new general channel to send completion message
        try:
            new_channel = await guild.create_text_channel(
                "general",
                reason=f"Server restart by {interaction.user} - new default channel"
            )
            
            embed = discord.Embed(
                title="🔥 Server Restart Complete",
                description=f"All channels have been deleted and the server has been reset.",
                color=discord.Color.red()
            )
            embed.add_field(name="Channels Deleted", value=str(deleted_count), inline=True)
            embed.add_field(name="Failed Deletions", value=str(failed_count), inline=True)
            embed.add_field(name="Initiated By", value=interaction.user.mention, inline=True)
            embed.set_footer(text="Server restart completed successfully")
            
            await new_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to create new general channel: {e}")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the command user can cancel this action.", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="✅ Server restart cancelled. No channels were deleted.",
            embed=None,
            view=None
        )
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        if not self.confirmed:
            for item in self.children:
                item.disabled = True

class Admin(commands.Cog):
    """Administrative commands for server owners"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="restart")
    async def restart_server(self, ctx):
        """Delete all channels in the server (OWNER ONLY)"""
        
        # Check if user is the server owner
        if ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the server owner can use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create warning embed
        embed = discord.Embed(
            title="⚠️ DANGER - Server Restart",
            description="**THIS WILL DELETE ALL CHANNELS IN THE SERVER**\n\nThis action is irreversible and will:",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="🗑️ What will be deleted:",
            value="• All text channels\n• All voice channels\n• All categories\n• All channel history and messages",
            inline=False
        )
        
        embed.add_field(
            name="💾 What will be preserved:",
            value="• Server roles\n• Server members\n• Server settings\n• Emojis and stickers",
            inline=False
        )
        
        embed.add_field(
            name="⚡ After deletion:",
            value="A new #general channel will be created automatically",
            inline=False
        )
        
        embed.set_footer(text="You have 30 seconds to confirm or cancel this action")
        
        # Create confirmation view
        view = ConfirmRestartView(ctx.author.id)
        
        await ctx.send(embed=embed, view=view)
    
    @restart_server.error
    async def restart_error(self, ctx, error):
        """Handle restart command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            logger.error(f"Restart command error: {error}")
            await ctx.send("❌ An error occurred while processing the restart command.")

async def setup(bot):
    await bot.add_cog(Admin(bot))