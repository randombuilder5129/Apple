import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Leaderboards(commands.Cog):
    """Advanced leaderboard system for economy, XP, and pet rankings"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='econlb', aliases=['economylb', 'moneylb'])
    async def economy_leaderboard(self, ctx, page: int = 1):
        """Display economy leaderboard with top earners"""
        if not hasattr(self.bot, 'user_data'):
            embed = discord.Embed(
                title="💰 Economy Leaderboard",
                description="No economy data available yet. Start earning coins with economy commands!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Filter and sort users by balance for this guild
        guild_users = []
        for user_id, data in self.bot.user_data.items():
            if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                balance = data.get('balance', 0)
                if balance > 0:
                    guild_users.append({
                        'user_id': user_id,
                        'balance': balance,
                        'username': data.get('username', 'Unknown User')
                    })
        
        if not guild_users:
            embed = discord.Embed(
                title="💰 Economy Leaderboard",
                description="No users with coins found. Start using economy commands to appear here!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by balance (highest first)
        guild_users.sort(key=lambda x: x['balance'], reverse=True)
        
        # Pagination
        per_page = 10
        total_pages = (len(guild_users) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = guild_users[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"💰 Economy Leaderboard - Page {page}/{total_pages}",
            description=f"Top earners in {ctx.guild.name}",
            color=0xf1c40f,
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(page_users):
            rank = start_idx + i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"#{rank}"
            
            try:
                user = await self.bot.fetch_user(user_data['user_id'])
                display_name = user.display_name
            except:
                display_name = user_data['username']
            
            balance = user_data['balance']
            leaderboard_text += f"{medal} **{display_name}** - {balance:,} coins\n"
        
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text=f"Total: {len(guild_users)} users • Use !econlb <page> to navigate")
        
        # Add stats
        if guild_users:
            total_economy = sum(user['balance'] for user in guild_users)
            average_balance = total_economy // len(guild_users)
            embed.add_field(name="📊 Server Stats", 
                          value=f"**Total Economy:** {total_economy:,} coins\n**Average Balance:** {average_balance:,} coins", 
                          inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='xpboard', aliases=['levelboard'])
    async def xp_leaderboard(self, ctx, page: int = 1):
        """Display XP leaderboard with top leveled users"""
        if not hasattr(self.bot, 'user_data'):
            embed = discord.Embed(
                title="⭐ XP Leaderboard",
                description="No XP data available yet. Start chatting to gain XP!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Filter and sort users by XP for this guild
        guild_users = []
        for user_id, data in self.bot.user_data.items():
            if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                xp = data.get('xp', 0)
                level = data.get('level', 1)
                if xp > 0:
                    guild_users.append({
                        'user_id': user_id,
                        'xp': xp,
                        'level': level,
                        'username': data.get('username', 'Unknown User')
                    })
        
        if not guild_users:
            embed = discord.Embed(
                title="⭐ XP Leaderboard",
                description="No users with XP found. Start chatting to appear here!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by XP (highest first)
        guild_users.sort(key=lambda x: x['xp'], reverse=True)
        
        # Pagination
        per_page = 10
        total_pages = (len(guild_users) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = guild_users[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"⭐ XP Leaderboard - Page {page}/{total_pages}",
            description=f"Top leveled users in {ctx.guild.name}",
            color=0x9b59b6,
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(page_users):
            rank = start_idx + i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"#{rank}"
            
            try:
                user = await self.bot.fetch_user(user_data['user_id'])
                display_name = user.display_name
            except:
                display_name = user_data['username']
            
            xp = user_data['xp']
            level = user_data['level']
            leaderboard_text += f"{medal} **{display_name}** - Level {level} ({xp:,} XP)\n"
        
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text=f"Total: {len(guild_users)} users • Use !xpboard <page> to navigate")
        
        # Add stats
        if guild_users:
            total_xp = sum(user['xp'] for user in guild_users)
            average_level = sum(user['level'] for user in guild_users) // len(guild_users)
            embed.add_field(name="📊 Server Stats", 
                          value=f"**Total XP:** {total_xp:,}\n**Average Level:** {average_level}", 
                          inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='petboard', aliases=['petlb', 'petleaderboard'])
    async def pet_leaderboard(self, ctx, category: str = "fame", page: int = 1):
        """Display pet leaderboard (fame, battles, or level)"""
        valid_categories = ['fame', 'battles', 'level', 'wins']
        if category.lower() not in valid_categories:
            embed = discord.Embed(
                title="❌ Invalid Category",
                description=f"Valid categories: {', '.join(valid_categories)}\n\n**Usage:** `!petboard <category> [page]`\n**Example:** `!petboard fame 1`",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if not hasattr(self.bot, 'user_data'):
            embed = discord.Embed(
                title="🐾 Pet Leaderboard",
                description="No pet data available yet. Get a pet with `!pet adopt` to start!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Filter and sort users by pet stats for this guild
        guild_users = []
        category = category.lower()
        
        for user_id, data in self.bot.user_data.items():
            if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                pet_data = data.get('pet', {})
                if pet_data:
                    if category == 'fame':
                        value = pet_data.get('fame', 0)
                    elif category == 'battles':
                        value = pet_data.get('battles_won', 0) + pet_data.get('battles_lost', 0)
                    elif category == 'level':
                        value = pet_data.get('level', 1)
                    elif category == 'wins':
                        value = pet_data.get('battles_won', 0)
                    else:
                        value = 0
                    
                    if value > 0:
                        guild_users.append({
                            'user_id': user_id,
                            'value': value,
                            'pet_name': pet_data.get('name', 'Unnamed Pet'),
                            'pet_type': pet_data.get('type', 'Unknown'),
                            'username': data.get('username', 'Unknown User'),
                            'pet_data': pet_data
                        })
        
        if not guild_users:
            embed = discord.Embed(
                title="🐾 Pet Leaderboard",
                description=f"No pets with {category} data found. Start using pet commands to appear here!",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by value (highest first)
        guild_users.sort(key=lambda x: x['value'], reverse=True)
        
        # Pagination
        per_page = 10
        total_pages = (len(guild_users) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = guild_users[start_idx:end_idx]
        
        # Category specific emojis and colors
        category_info = {
            'fame': {'emoji': '⭐', 'color': 0xf39c12, 'unit': 'fame'},
            'battles': {'emoji': '⚔️', 'color': 0xe74c3c, 'unit': 'battles'},
            'level': {'emoji': '📈', 'color': 0x27ae60, 'unit': 'level'},
            'wins': {'emoji': '🏆', 'color': 0xf1c40f, 'unit': 'wins'}
        }
        
        info = category_info[category]
        
        embed = discord.Embed(
            title=f"{info['emoji']} Pet {category.title()} Leaderboard - Page {page}/{total_pages}",
            description=f"Top pets by {category} in {ctx.guild.name}",
            color=info['color'],
            timestamp=datetime.now()
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(page_users):
            rank = start_idx + i + 1
            
            # Medal emojis for top 3
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"#{rank}"
            
            try:
                user = await self.bot.fetch_user(user_data['user_id'])
                display_name = user.display_name
            except:
                display_name = user_data['username']
            
            value = user_data['value']
            pet_name = user_data['pet_name']
            pet_type = user_data['pet_type']
            
            if category == 'level':
                display_value = f"Level {value}"
            else:
                display_value = f"{value:,} {info['unit']}"
            
            leaderboard_text += f"{medal} **{pet_name}** ({pet_type}) - {display_value}\n└ Owner: {display_name}\n"
        
        embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        embed.set_footer(text=f"Total: {len(guild_users)} pets • Use !petboard {category} <page> to navigate")
        
        # Add stats
        if guild_users:
            total_value = sum(user['value'] for user in guild_users)
            average_value = total_value // len(guild_users)
            
            stats_text = f"**Total {category.title()}:** {total_value:,}\n**Average {category.title()}:** {average_value:,}"
            
            # Add category-specific stats
            if category == 'battles':
                total_wins = sum(user['pet_data'].get('battles_won', 0) for user in guild_users)
                total_losses = sum(user['pet_data'].get('battles_lost', 0) for user in guild_users)
                win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
                stats_text += f"\n**Server Win Rate:** {win_rate:.1f}%"
            
            embed.add_field(name="📊 Server Stats", value=stats_text, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='topleaderboards', aliases=['toplb', 'allboards'])
    async def top_leaderboards(self, ctx):
        """Display combined overview of all leaderboards"""
        embed = discord.Embed(
            title="🏆 Server Leaderboards Overview",
            description=f"Top performers across all categories in {ctx.guild.name}",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        
        # Economy top 3
        if hasattr(self.bot, 'user_data'):
            guild_users = []
            for user_id, data in self.bot.user_data.items():
                if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                    balance = data.get('balance', 0)
                    if balance > 0:
                        guild_users.append({
                            'user_id': user_id,
                            'balance': balance,
                            'username': data.get('username', 'Unknown User')
                        })
            
            if guild_users:
                guild_users.sort(key=lambda x: x['balance'], reverse=True)
                economy_text = ""
                for i, user_data in enumerate(guild_users[:3]):
                    medals = ["🥇", "🥈", "🥉"]
                    try:
                        user = await self.bot.fetch_user(user_data['user_id'])
                        name = user.display_name
                    except:
                        name = user_data['username']
                    economy_text += f"{medals[i]} {name} - {user_data['balance']:,} coins\n"
                
                embed.add_field(name="💰 Top Economy", value=economy_text or "No data", inline=True)
            
            # XP top 3
            xp_users = []
            for user_id, data in self.bot.user_data.items():
                if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                    xp = data.get('xp', 0)
                    level = data.get('level', 1)
                    if xp > 0:
                        xp_users.append({
                            'user_id': user_id,
                            'xp': xp,
                            'level': level,
                            'username': data.get('username', 'Unknown User')
                        })
            
            if xp_users:
                xp_users.sort(key=lambda x: x['xp'], reverse=True)
                xp_text = ""
                for i, user_data in enumerate(xp_users[:3]):
                    medals = ["🥇", "🥈", "🥉"]
                    try:
                        user = await self.bot.fetch_user(user_data['user_id'])
                        name = user.display_name
                    except:
                        name = user_data['username']
                    xp_text += f"{medals[i]} {name} - Level {user_data['level']}\n"
                
                embed.add_field(name="⭐ Top XP", value=xp_text or "No data", inline=True)
            
            # Pet fame top 3
            pet_users = []
            for user_id, data in self.bot.user_data.items():
                if isinstance(data, dict) and data.get('guild_id') == ctx.guild.id:
                    pet_data = data.get('pet', {})
                    if pet_data:
                        fame = pet_data.get('fame', 0)
                        if fame > 0:
                            pet_users.append({
                                'user_id': user_id,
                                'fame': fame,
                                'pet_name': pet_data.get('name', 'Unnamed Pet'),
                                'username': data.get('username', 'Unknown User')
                            })
            
            if pet_users:
                pet_users.sort(key=lambda x: x['fame'], reverse=True)
                pet_text = ""
                for i, user_data in enumerate(pet_users[:3]):
                    medals = ["🥇", "🥈", "🥉"]
                    try:
                        user = await self.bot.fetch_user(user_data['user_id'])
                        name = user.display_name
                    except:
                        name = user_data['username']
                    pet_text += f"{medals[i]} {user_data['pet_name']} - {user_data['fame']} fame\n└ {name}\n"
                
                embed.add_field(name="🐾 Top Pet Fame", value=pet_text or "No data", inline=True)
        
        # Add navigation info
        embed.add_field(
            name="📋 Individual Leaderboards",
            value="• `!econlb` - Economy leaderboard\n• `!xpboard` - XP leaderboard\n• `!petboard <category>` - Pet leaderboards",
            inline=False
        )
        
        embed.set_footer(text="Use individual leaderboard commands for complete rankings")
        
        await ctx.send(embed=embed)
    
    # Slash command versions
    @app_commands.command(name="econlb", description="View economy leaderboard")
    @app_commands.describe(page="Page number for pagination")
    async def slash_economy_leaderboard(self, interaction: discord.Interaction, page: int = 1):
        """Slash command version of economy leaderboard"""
        ctx = await self.bot.get_context(interaction)
        ctx.author = interaction.user
        await self.economy_leaderboard(ctx, page)
    
    @app_commands.command(name="xpboard", description="View XP leaderboard")
    @app_commands.describe(page="Page number for pagination")
    async def slash_xp_leaderboard(self, interaction: discord.Interaction, page: int = 1):
        """Slash command version of XP leaderboard"""
        ctx = await self.bot.get_context(interaction)
        ctx.author = interaction.user
        await self.xp_leaderboard(ctx, page)
    
    @app_commands.command(name="petboard", description="View pet leaderboard")
    @app_commands.describe(
        category="Leaderboard category (fame, battles, level, wins)",
        page="Page number for pagination"
    )
    async def slash_pet_leaderboard(self, interaction: discord.Interaction, category: str = "fame", page: int = 1):
        """Slash command version of pet leaderboard"""
        ctx = await self.bot.get_context(interaction)
        ctx.author = interaction.user
        await self.pet_leaderboard(ctx, category, page)

async def setup(bot):
    await bot.add_cog(Leaderboards(bot))