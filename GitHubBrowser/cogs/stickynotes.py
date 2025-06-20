import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StickyNotes(commands.Cog):
    """Sticky note system - keeps messages pinned to the bottom of channels"""
    
    def __init__(self, bot):
        self.bot = bot
        # Store sticky notes: {channel_id: {'message': content, 'message_id': id, 'author_id': user_id}}
        self.sticky_notes: Dict[int, dict] = {}
        # Track the last message in each channel to avoid infinite loops
        self.last_messages: Dict[int, int] = {}
        # Initialize database tables
        self.bot.loop.create_task(self.create_sticky_tables())
    
    async def create_sticky_tables(self):
        """Create sticky notes tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sticky_notes (
                        id SERIAL PRIMARY KEY,
                        channel_id BIGINT NOT NULL,
                        guild_id BIGINT NOT NULL,
                        message_content TEXT NOT NULL,
                        message_id BIGINT,
                        author_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(channel_id)
                    )
                """)
                
                # Load existing sticky notes from database
                rows = await conn.fetch("SELECT * FROM sticky_notes")
                for row in rows:
                    self.sticky_notes[row['channel_id']] = {
                        'message': row['message_content'],
                        'message_id': row['message_id'],
                        'author_id': row['author_id']
                    }
                    if row['message_id']:
                        self.last_messages[row['channel_id']] = row['message_id']
                        
                logger.info(f"Loaded {len(rows)} sticky notes from database")
        except Exception as e:
            logger.error(f"Database error creating sticky tables: {e}")
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle sticky note reposting when new messages are sent"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
            
        channel_id = message.channel.id
        
        # Check if this channel has a sticky note
        if channel_id not in self.sticky_notes:
            return
            
        # Avoid infinite loops - don't repost if this is the sticky note itself
        if message.id == self.last_messages.get(channel_id):
            return
            
        # Also check if the message content starts with ! to avoid reposting on commands
        if message.content.startswith('!'):
            return
            
        # Wait a moment to avoid rate limiting and let other messages settle
        await asyncio.sleep(2)
        
        try:
            # Verify the channel still exists and we have permission
            if not message.channel.permissions_for(message.guild.me).send_messages:
                return
                
            # Delete the old sticky note
            sticky_data = self.sticky_notes[channel_id]
            if sticky_data.get('message_id'):
                try:
                    old_message = await message.channel.fetch_message(sticky_data['message_id'])
                    await old_message.delete()
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    logger.warning(f"No permission to delete old sticky note in channel {channel_id}")
                except Exception as e:
                    logger.error(f"Error deleting old sticky note: {e}")
                    
            # Send the new sticky note
            embed = discord.Embed(
                title="📌 Sticky Note",
                description=sticky_data['message'],
                color=0xffd700
            )
            
            # Add author info
            author = self.bot.get_user(sticky_data['author_id'])
            if author:
                embed.set_footer(text=f"Sticky note by {author.display_name}", icon_url=author.avatar.url if author.avatar else None)
            else:
                embed.set_footer(text="Sticky note")
                
            new_sticky = await message.channel.send(embed=embed)
            
            # Update stored data
            self.sticky_notes[channel_id]['message_id'] = new_sticky.id
            self.last_messages[channel_id] = new_sticky.id
            
            # Update database
            await self.update_sticky_in_db(channel_id, new_sticky.id)
            
            logger.debug(f"Reposted sticky note in channel {channel_id}")
            
        except discord.Forbidden:
            logger.warning(f"No permission to send sticky note in channel {channel_id}")
        except Exception as e:
            logger.error(f"Error reposting sticky note in channel {channel_id}: {e}")
    
    async def update_sticky_in_db(self, channel_id: int, message_id: int):
        """Update sticky note message ID in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE sticky_notes SET message_id = $1 WHERE channel_id = $2
                """, message_id, channel_id)
        except Exception as e:
            logger.error(f"Database error updating sticky note: {e}")
    
    async def show_sticky_commands(self, ctx):
        """Display all available sticky note commands"""
        embed = discord.Embed(
            title="📌 Sticky Notes Commands",
            description="Keep important messages visible at the bottom of channels",
            color=0xffd700
        )
        
        embed.add_field(
            name="📝 Create Sticky Note",
            value="`!stickynote <message>` - Create or update sticky note\n"
                  "`!sticky <message>` - Same as stickynote\n"
                  "`!pin <message>` - Alternative command",
            inline=False
        )
        
        embed.add_field(
            name="🗑️ Remove Sticky Note",
            value="`!removesticky` - Remove sticky note from channel\n"
                  "`!unsticky` - Same as removesticky\n"
                  "`!removestickynote` - Alternative command",
            inline=False
        )
        
        embed.add_field(
            name="📋 View Sticky Notes",
            value="`!liststicky` - List all sticky notes in server\n"
                  "`!stickyinfo` - Alternative command\n"
                  "`!stickydetails` - Show system status",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Slash Command",
            value="`/stickynote <message>` - Create sticky note with slash command",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ How It Works",
            value="• Sticky notes automatically repost after every message\n"
                  "• Previous sticky note is deleted to prevent spam\n"
                  "• Only one sticky note per channel\n"
                  "• Requires 'Manage Messages' permission",
            inline=False
        )
        
        embed.add_field(
            name="📖 Examples",
            value="`!stickynote Welcome to our server! Please read #rules`\n"
                  "`!stickynote commands` - Show this help menu\n"
                  "`!removesticky` - Remove current sticky note",
            inline=False
        )
        
        embed.set_footer(text="Sticky notes keep your important messages visible!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='stickynote', aliases=['sticky', 'pin'])
    @commands.has_permissions(manage_messages=True)
    async def create_sticky_note(self, ctx, *, message: str = None):
        """Create or update a sticky note for this channel
        
        Args:
            message: The message content for the sticky note, or 'commands' to show help
            
        Usage:
            !stickynote Welcome to our server! Please read the rules.
            !stickynote commands - Show all sticky note commands
            !sticky Remember to be respectful to all members.
        """
        # Show commands list if requested
        if message and message.lower() == 'commands':
            await self.show_sticky_commands(ctx)
            return
            
        # Require message content for creating sticky note
        if not message:
            await ctx.send("❌ Please provide a message for the sticky note or use `!stickynote commands` to see available commands.")
            return
        if len(message) > 2000:
            await ctx.send("❌ Sticky note message is too long! Please keep it under 2000 characters.")
            return
            
        channel_id = ctx.channel.id
        
        # Remove old sticky note if it exists
        if channel_id in self.sticky_notes:
            old_sticky_id = self.sticky_notes[channel_id].get('message_id')
            if old_sticky_id:
                try:
                    old_message = await ctx.channel.fetch_message(old_sticky_id)
                    await old_message.delete()
                except discord.NotFound:
                    pass  # Already deleted
                except discord.Forbidden:
                    pass  # No permission
        
        # Create the sticky note embed
        embed = discord.Embed(
            title="📌 Sticky Note",
            description=message,
            color=0xffd700
        )
        embed.set_footer(text=f"Sticky note by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Send the sticky note
        try:
            sticky_message = await ctx.channel.send(embed=embed)
            
            # Store the sticky note data
            self.sticky_notes[channel_id] = {
                'message': message,
                'message_id': sticky_message.id,
                'author_id': ctx.author.id
            }
            self.last_messages[channel_id] = sticky_message.id
            
            # Save to database
            await self.save_sticky_to_db(channel_id, ctx.guild.id, message, sticky_message.id, ctx.author.id)
            
            # Delete the command message
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
                
            # Send confirmation in DM or ephemeral message
            confirmation = f"✅ Sticky note created in {ctx.channel.mention}!"
            try:
                await ctx.author.send(confirmation)
            except discord.Forbidden:
                # If DM fails, send a temporary message
                temp_msg = await ctx.channel.send(confirmation)
                await asyncio.sleep(5)
                try:
                    await temp_msg.delete()
                except:
                    pass
                    
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to send messages in this channel!")
        except Exception as e:
            await ctx.send(f"❌ Error creating sticky note: {str(e)}")
            logger.error(f"Error creating sticky note: {e}")
    
    async def save_sticky_to_db(self, channel_id: int, guild_id: int, message_content: str, message_id: int, author_id: int):
        """Save sticky note to database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sticky_notes (channel_id, guild_id, message_content, message_id, author_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (channel_id) DO UPDATE SET
                        message_content = EXCLUDED.message_content,
                        message_id = EXCLUDED.message_id,
                        author_id = EXCLUDED.author_id,
                        created_at = NOW()
                """, channel_id, guild_id, message_content, message_id, author_id)
        except Exception as e:
            logger.error(f"Database error saving sticky note: {e}")
    
    @commands.command(name='removesticky', aliases=['unsticky', 'removestickynote'])
    @commands.has_permissions(manage_messages=True)
    async def remove_sticky_note(self, ctx):
        """Remove the sticky note from this channel
        
        Usage:
            !removesticky
            !unsticky
        """
        channel_id = ctx.channel.id
        
        if channel_id not in self.sticky_notes:
            await ctx.send("❌ No sticky note found in this channel.")
            return
            
        # Delete the sticky note message
        sticky_data = self.sticky_notes[channel_id]
        if sticky_data.get('message_id'):
            try:
                sticky_message = await ctx.channel.fetch_message(sticky_data['message_id'])
                await sticky_message.delete()
            except discord.NotFound:
                pass  # Already deleted
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to delete the sticky note message.")
                return
        
        # Remove from storage
        del self.sticky_notes[channel_id]
        if channel_id in self.last_messages:
            del self.last_messages[channel_id]
            
        # Remove from database
        await self.remove_sticky_from_db(channel_id)
            
        await ctx.send("✅ Sticky note removed from this channel.")
    
    async def remove_sticky_from_db(self, channel_id: int):
        """Remove sticky note from database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("DELETE FROM sticky_notes WHERE channel_id = $1", channel_id)
        except Exception as e:
            logger.error(f"Database error removing sticky note: {e}")
    
    @commands.command(name='liststicky', aliases=['stickyinfo'])
    @commands.has_permissions(manage_messages=True)
    async def list_sticky_notes(self, ctx):
        """List all sticky notes in this server
        
        Usage:
            !liststicky
            !stickystatus
        """
        guild_stickies = []
        
        for channel_id, sticky_data in self.sticky_notes.items():
            channel = self.bot.get_channel(channel_id)
            if channel and channel.guild.id == ctx.guild.id:
                author = self.bot.get_user(sticky_data['author_id'])
                author_name = author.display_name if author else "Unknown User"
                
                # Truncate long messages
                message_preview = sticky_data['message']
                if len(message_preview) > 100:
                    message_preview = message_preview[:97] + "..."
                    
                guild_stickies.append(f"**{channel.mention}**\n└ By: {author_name}\n└ Message: {message_preview}")
        
        if not guild_stickies:
            await ctx.send("📌 No sticky notes found in this server.")
            return
            
        embed = discord.Embed(
            title="📌 Sticky Notes in This Server",
            description="\n\n".join(guild_stickies),
            color=0xffd700
        )
        embed.set_footer(text=f"Total: {len(guild_stickies)} sticky note(s)")
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="stickynote", description="Create a sticky note that stays at the bottom of the channel")
    @app_commands.describe(message="The message content for the sticky note")
    async def slash_sticky_note(self, interaction: discord.Interaction, message: str):
        """Slash command version of sticky note creation"""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need the 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        if len(message) > 2000:
            await interaction.response.send_message("❌ Sticky note message is too long! Please keep it under 2000 characters.", ephemeral=True)
            return
            
        channel_id = interaction.channel.id
        
        # Remove old sticky note if it exists
        if channel_id in self.sticky_notes:
            old_sticky_id = self.sticky_notes[channel_id].get('message_id')
            if old_sticky_id:
                try:
                    old_message = await interaction.channel.fetch_message(old_sticky_id)
                    await old_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    pass
        
        # Create the sticky note embed
        embed = discord.Embed(
            title="📌 Sticky Note",
            description=message,
            color=0xffd700
        )
        embed.set_footer(text=f"Sticky note by {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        try:
            # Send the sticky note
            sticky_message = await interaction.channel.send(embed=embed)
            
            # Store the sticky note data
            self.sticky_notes[channel_id] = {
                'message': message,
                'message_id': sticky_message.id,
                'author_id': interaction.user.id
            }
            self.last_messages[channel_id] = sticky_message.id
            
            # Save to database
            await self.save_sticky_to_db(channel_id, interaction.guild.id, message, sticky_message.id, interaction.user.id)
            
            await interaction.response.send_message(f"✅ Sticky note created in {interaction.channel.mention}!", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to send messages in this channel!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating sticky note: {str(e)}", ephemeral=True)
            logger.error(f"Error creating sticky note via slash command: {e}")
    
    @commands.command(name='stickydetails')
    @commands.has_permissions(manage_messages=True)
    async def sticky_status(self, ctx):
        """Show detailed status of sticky notes system"""
        embed = discord.Embed(
            title="📌 Sticky Notes System Status",
            color=0xffd700
        )
        
        # Count sticky notes in this server
        server_stickies = 0
        for channel_id, sticky_data in self.sticky_notes.items():
            channel = self.bot.get_channel(channel_id)
            if channel and channel.guild.id == ctx.guild.id:
                server_stickies += 1
        
        embed.add_field(
            name="📊 Statistics",
            value=f"• Server sticky notes: {server_stickies}\n• Total sticky notes: {len(self.sticky_notes)}\n• Active channels: {len(self.last_messages)}",
            inline=False
        )
        
        # Check current channel
        current_sticky = self.sticky_notes.get(ctx.channel.id)
        if current_sticky:
            author = self.bot.get_user(current_sticky['author_id'])
            author_name = author.display_name if author else "Unknown User"
            message_preview = current_sticky['message'][:100] + "..." if len(current_sticky['message']) > 100 else current_sticky['message']
            
            embed.add_field(
                name="📌 Current Channel",
                value=f"• Has sticky note: ✅\n• Author: {author_name}\n• Preview: {message_preview}",
                inline=False
            )
        else:
            embed.add_field(
                name="📌 Current Channel",
                value="• Has sticky note: ❌",
                inline=False
            )
        
        embed.add_field(
            name="🔧 System Info",
            value="• Auto-reposting: ✅ Active\n• Database persistence: ✅ Enabled\n• Rate limiting: ✅ Protected",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StickyNotes(bot))