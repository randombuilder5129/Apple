import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DepartmentSelect(discord.ui.Select):
    """Department selection dropdown"""
    
    def __init__(self):
        departments = [
            discord.SelectOption(label="General Support", description="General questions and issues", emoji="❓"),
            discord.SelectOption(label="Technical Support", description="Technical problems and bugs", emoji="🔧"),
            discord.SelectOption(label="Billing Support", description="Payment and subscription issues", emoji="💳"),
            discord.SelectOption(label="Account Support", description="Account-related problems", emoji="👤"),
            discord.SelectOption(label="Bug Reports", description="Report bugs and glitches", emoji="🐛"),
            discord.SelectOption(label="Feature Requests", description="Suggest new features", emoji="💡"),
            discord.SelectOption(label="Moderation Appeal", description="Appeal moderation actions", emoji="⚖️"),
            discord.SelectOption(label="Other", description="Other issues not listed above", emoji="📝")
        ]
        
        super().__init__(
            placeholder="Select a department...",
            options=departments,
            custom_id="department_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_department = self.values[0]
        await interaction.response.send_modal(TicketReasonModal(self.view.selected_department))

class TicketReasonModal(discord.ui.Modal):
    """Modal for ticket reason input"""
    
    def __init__(self, department):
        super().__init__(title=f"Support Ticket - {department}")
        self.department = department
        
        self.reason_input = discord.ui.TextInput(
            label="Reason for opening ticket",
            placeholder="Please describe your issue in detail...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        
        self.priority_input = discord.ui.TextInput(
            label="Priority Level",
            placeholder="Low, Medium, High, or Urgent",
            style=discord.TextStyle.short,
            required=False,
            max_length=10,
            default="Medium"
        )
        
        self.add_item(self.reason_input)
        self.add_item(self.priority_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Create ticket channel
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Support Tickets")
        
        if not category:
            # Create category if it doesn't exist
            category = await guild.create_category(
                "Support Tickets",
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
                }
            )
        
        # Create ticket channel
        channel_name = f"ticket-{interaction.user.name.lower()}-{interaction.user.discriminator}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # Add department role if exists
        dept_role_names = {
            "General Support": "Support Team",
            "Technical Support": "Tech Support",
            "Billing Support": "Billing Team",
            "Account Support": "Account Team",
            "Bug Reports": "Development Team",
            "Feature Requests": "Development Team",
            "Moderation Appeal": "Moderation Team",
            "Other": "Support Team"
        }
        
        dept_role = discord.utils.get(guild.roles, name=dept_role_names.get(self.department, "Support Team"))
        if dept_role:
            overwrites[dept_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_channel = await category.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"Support ticket for {interaction.user} | Department: {self.department}"
        )
        
        # Create ticket embed
        embed = discord.Embed(
            title="🎫 Support Ticket Created",
            description=f"Welcome {interaction.user.mention}! Your support ticket has been created.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Department", value=self.department, inline=True)
        embed.add_field(name="Priority", value=self.priority_input.value or "Medium", inline=True)
        embed.add_field(name="Ticket ID", value=f"#{ticket_channel.id}", inline=True)
        embed.add_field(name="Reason", value=self.reason_input.value, inline=False)
        
        embed.set_footer(text="A support team member will be with you shortly.")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Create ticket dashboard
        view = TicketDashboard(ticket_channel.id, interaction.user.id)
        
        # Send ticket message
        ticket_message = await ticket_channel.send(embed=embed, view=view)
        await ticket_message.pin()
        
        # Ping department if role exists
        if dept_role:
            await ticket_channel.send(f"{dept_role.mention} New ticket opened!")
        
        # Store ticket data if database available
        cog = interaction.client.get_cog('Support')
        if cog and hasattr(interaction.client, 'db_pool') and interaction.client.db_pool:
            try:
                async with interaction.client.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO support_tickets (
                            guild_id, channel_id, user_id, department, 
                            reason, priority, status, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """, guild.id, ticket_channel.id, interaction.user.id, 
                    self.department, self.reason_input.value, 
                    self.priority_input.value or "Medium", "open", datetime.utcnow())
            except Exception as e:
                logger.error(f"Database error storing ticket: {e}")
        
        # Send confirmation to user
        await interaction.followup.send(
            f"✅ Your support ticket has been created in {ticket_channel.mention}!",
            ephemeral=True
        )

class TicketDashboard(discord.ui.View):
    """Interactive dashboard for ticket management"""
    
    def __init__(self, ticket_id, user_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.user_id = user_id
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the ticket"""
        if not self._has_permission(interaction):
            await interaction.response.send_message("❌ Only the ticket creator or staff can close tickets.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Ticket Closing",
            description="Are you sure you want to close this ticket?",
            color=discord.Color.orange()
        )
        
        view = ConfirmCloseView(self.ticket_id, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the ticket channel"""
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need Manage Channels permission to delete tickets.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🗑️ Ticket Deletion",
            description="⚠️ **WARNING**: This will permanently delete the ticket channel and all messages.\n\nAre you sure you want to continue?",
            color=discord.Color.red()
        )
        
        view = ConfirmDeleteView(self.ticket_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄")
    async def generate_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate a transcript of the ticket"""
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.channel
        messages = []
        
        async for message in channel.history(limit=None, oldest_first=True):
            if not message.author.bot or message.embeds or message.attachments:
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                content = message.content if message.content else "[No text content]"
                
                # Handle embeds
                if message.embeds:
                    for embed in message.embeds:
                        content += f"\n[EMBED: {embed.title or 'No title'}]"
                
                # Handle attachments
                if message.attachments:
                    for attachment in message.attachments:
                        content += f"\n[ATTACHMENT: {attachment.filename}]"
                
                messages.append(f"[{timestamp}] {message.author}: {content}")
        
        # Create transcript content
        transcript_content = f"# Support Ticket Transcript\n"
        transcript_content += f"**Channel:** #{channel.name}\n"
        transcript_content += f"**Created:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        transcript_content += f"**Messages:** {len(messages)}\n\n"
        transcript_content += "---\n\n"
        transcript_content += "\n".join(messages)
        
        # Create file
        import io
        transcript_file = discord.File(
            io.StringIO(transcript_content),
            filename=f"transcript-{channel.name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"
        )
        
        # Send to user
        await interaction.followup.send(
            "📄 Here's your ticket transcript:",
            file=transcript_file,
            ephemeral=True
        )
        
        # Also send to moderation log channel if it exists
        support_cog = interaction.client.get_cog('Support')
        if support_cog:
            await support_cog._send_transcript_to_log(interaction.guild, channel, transcript_content)
    
    def _has_permission(self, interaction):
        """Check if user has permission to manage ticket"""
        return (
            interaction.user.id == self.user_id or
            interaction.user.guild_permissions.manage_channels or
            any(role.name in ["Support Team", "Staff", "Moderator", "Admin"] for role in interaction.user.roles)
        )

class ConfirmCloseView(discord.ui.View):
    """Confirmation view for closing tickets"""
    
    def __init__(self, ticket_id, user_id):
        super().__init__(timeout=30)
        self.ticket_id = ticket_id
        self.user_id = user_id
    
    @discord.ui.button(label="Yes, Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        
        # Update ticket status in database
        cog = interaction.client.get_cog('Support')
        if cog and hasattr(interaction.client, 'db_pool') and interaction.client.db_pool:
            try:
                async with interaction.client.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE support_tickets SET status = 'closed', closed_at = $1 WHERE channel_id = $2",
                        datetime.utcnow(), channel.id
                    )
            except Exception as e:
                logger.error(f"Database error closing ticket: {e}")
        
        # Close the channel
        await channel.edit(
            name=f"closed-{channel.name}",
            overwrites={
                **channel.overwrites,
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False)
            }
        )
        
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.\n\nUse the Delete button to remove this channel.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ticket close cancelled.", embed=None, view=None)

class ConfirmDeleteView(discord.ui.View):
    """Confirmation view for deleting tickets"""
    
    def __init__(self, ticket_id):
        super().__init__(timeout=30)
        self.ticket_id = ticket_id
    
    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        
        # Update ticket status in database
        cog = interaction.client.get_cog('Support')
        if cog and hasattr(interaction.client, 'db_pool') and interaction.client.db_pool:
            try:
                async with interaction.client.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE support_tickets SET status = 'deleted', deleted_at = $1 WHERE channel_id = $2",
                        datetime.utcnow(), channel.id
                    )
            except Exception as e:
                logger.error(f"Database error deleting ticket: {e}")
        
        await interaction.response.send_message("🗑️ Deleting ticket channel in 5 seconds...")
        
        # Generate and send transcript to moderation log before deletion
        support_cog = interaction.client.get_cog('Support')
        if support_cog:
            await support_cog._generate_and_log_transcript(channel, interaction.guild, "deleted")
        
        await asyncio.sleep(5)
        await channel.delete()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ticket deletion cancelled.", embed=None, view=None)

class SupportSelectView(discord.ui.View):
    """Main support view with department selection"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_department = None
        self.add_item(DepartmentSelect())

class Support(commands.Cog):
    """Support ticket system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_support_tables(self):
        """Create support tickets table"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS support_tickets (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        channel_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        department VARCHAR(50) NOT NULL,
                        reason TEXT NOT NULL,
                        priority VARCHAR(20) DEFAULT 'Medium',
                        status VARCHAR(20) DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT NOW(),
                        closed_at TIMESTAMP,
                        deleted_at TIMESTAMP
                    )
                """)
        except Exception as e:
            logger.error(f"Database error creating support tables: {e}")
    
    @app_commands.command(name="support", description="Open a support ticket")
    async def support_command(self, interaction: discord.Interaction):
        """Create a new support ticket"""
        
        # Check if user already has an open ticket
        existing_tickets = [
            channel for channel in interaction.guild.channels 
            if isinstance(channel, discord.TextChannel) and 
            channel.category and channel.category.name == "Support Tickets" and
            interaction.user in channel.members and
            not channel.name.startswith("closed-")
        ]
        
        if existing_tickets:
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing_tickets[0].mention}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎫 Support Ticket System",
            description="Select the department that best matches your issue:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Available Departments:",
            value="""
❓ **General Support** - General questions and issues
🔧 **Technical Support** - Technical problems and bugs  
💳 **Billing Support** - Payment and subscription issues
👤 **Account Support** - Account-related problems
🐛 **Bug Reports** - Report bugs and glitches
💡 **Feature Requests** - Suggest new features
⚖️ **Moderation Appeal** - Appeal moderation actions
📝 **Other** - Other issues not listed above
            """,
            inline=False
        )
        
        embed.set_footer(text="Select a department below to continue")
        
        view = SupportSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="ticket-stats", description="View ticket statistics")
    @app_commands.describe(user="View stats for a specific user (staff only)")
    async def ticket_stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """View ticket statistics"""
        
        if not self.bot.db_pool:
            await interaction.response.send_message("❌ Database unavailable for statistics.", ephemeral=True)
            return
        
        # Check permissions for viewing other users' stats
        if user and user != interaction.user:
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message("❌ You can only view your own ticket statistics.", ephemeral=True)
                return
        
        target_user = user or interaction.user
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get user's ticket stats
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_tickets,
                        COUNT(*) FILTER (WHERE status = 'open') as open_tickets,
                        COUNT(*) FILTER (WHERE status = 'closed') as closed_tickets,
                        COUNT(*) FILTER (WHERE priority = 'High') as high_priority,
                        COUNT(*) FILTER (WHERE priority = 'Urgent') as urgent_tickets
                    FROM support_tickets 
                    WHERE guild_id = $1 AND user_id = $2
                """, interaction.guild.id, target_user.id)
                
                # Get department breakdown
                dept_stats = await conn.fetch("""
                    SELECT department, COUNT(*) as count
                    FROM support_tickets 
                    WHERE guild_id = $1 AND user_id = $2
                    GROUP BY department
                    ORDER BY count DESC
                """, interaction.guild.id, target_user.id)
                
                embed = discord.Embed(
                    title=f"🎫 Ticket Statistics - {target_user.display_name}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="📊 Overview", value=f"""
**Total Tickets:** {stats['total_tickets']}
**Open Tickets:** {stats['open_tickets']}
**Closed Tickets:** {stats['closed_tickets']}
**High Priority:** {stats['high_priority']}
**Urgent Tickets:** {stats['urgent_tickets']}
                """, inline=True)
                
                if dept_stats:
                    dept_text = "\n".join([f"**{dept['department']}:** {dept['count']}" for dept in dept_stats[:5]])
                    embed.add_field(name="🏢 Top Departments", value=dept_text, inline=True)
                
                embed.set_thumbnail(url=target_user.display_avatar.url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Database error getting ticket stats: {e}")
            await interaction.response.send_message("❌ Error retrieving ticket statistics.", ephemeral=True)
    
    async def _generate_and_log_transcript(self, channel, guild, action_type):
        """Generate transcript and send to moderation log channel"""
        try:
            # Generate transcript content
            messages = []
            async for message in channel.history(limit=None, oldest_first=True):
                if not message.author.bot or message.embeds or message.attachments:
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    content = message.content if message.content else "[No text content]"
                    
                    # Handle embeds
                    if message.embeds:
                        for embed in message.embeds:
                            content += f"\n[EMBED: {embed.title or 'No title'}]"
                    
                    # Handle attachments
                    if message.attachments:
                        for attachment in message.attachments:
                            content += f"\n[ATTACHMENT: {attachment.filename}]"
                    
                    messages.append(f"[{timestamp}] {message.author}: {content}")
            
            # Create transcript content
            transcript_content = f"# Support Ticket Transcript\n"
            transcript_content += f"**Channel:** #{channel.name}\n"
            transcript_content += f"**Action:** Ticket {action_type}\n"
            transcript_content += f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            transcript_content += f"**Messages:** {len(messages)}\n\n"
            transcript_content += "---\n\n"
            transcript_content += "\n".join(messages)
            
            await self._send_transcript_to_log(guild, channel, transcript_content)
            
        except Exception as e:
            logger.error(f"Error generating transcript for log: {e}")
    
    async def _send_transcript_to_log(self, guild, ticket_channel, transcript_content):
        """Send transcript to moderation log channel"""
        try:
            # Find moderation log channel
            log_channel = None
            
            # Look for common log channel names
            log_channel_names = ['mod-logs', 'modlogs', 'logs', 'moderation-logs', 'ticket-logs']
            for channel_name in log_channel_names:
                log_channel = discord.utils.get(guild.channels, name=channel_name)
                if log_channel:
                    break
            
            # Try to get from database if available
            if not log_channel and self.bot.db_pool:
                try:
                    async with self.bot.db_pool.acquire() as conn:
                        log_channel_id = await conn.fetchval(
                            "SELECT log_channel FROM guild_settings WHERE guild_id = $1",
                            guild.id
                        )
                        if log_channel_id:
                            log_channel = guild.get_channel(log_channel_id)
                except Exception as e:
                    logger.error(f"Database error getting log channel: {e}")
            
            if not log_channel:
                return  # No log channel found
            
            # Create transcript file
            import io
            transcript_file = discord.File(
                io.StringIO(transcript_content),
                filename=f"transcript-{ticket_channel.name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"
            )
            
            # Create log embed
            embed = discord.Embed(
                title="🎫 Ticket Transcript",
                description=f"Transcript for ticket channel #{ticket_channel.name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Channel", value=f"#{ticket_channel.name}", inline=True)
            embed.add_field(name="Category", value=ticket_channel.category.name if ticket_channel.category else "None", inline=True)
            embed.add_field(name="Messages", value=str(transcript_content.count('\n[2')), inline=True)
            
            embed.set_footer(text="Automatic ticket transcript")
            
            await log_channel.send(embed=embed, file=transcript_file)
            
        except Exception as e:
            logger.error(f"Error sending transcript to log channel: {e}")

async def setup(bot):
    cog = Support(bot)
    await cog.create_support_tables()
    await bot.add_cog(cog)