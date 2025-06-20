import discord
from discord.ext import commands
import logging
import asyncio
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Pets(commands.Cog):
    """Core pets functionality"""
    
    def __init__(self, bot):
        self.bot = bot
        # Initialize database tables
        self.bot.loop.create_task(self.create_pets_tables())
        
        # Pre-set pets for adoption
        self.available_pets = {
            "dog": {
                "names": ["Buddy", "Max", "Charlie", "Lucy", "Bella", "Cooper", "Luna", "Rocky"],
                "emoji": "🐕",
                "base_stats": {"health": 100, "happiness": 80, "energy": 90, "strength": 70},
                "description": "Loyal and energetic companion"
            },
            "cat": {
                "names": ["Whiskers", "Shadow", "Mittens", "Tiger", "Princess", "Smokey", "Oliver", "Cleo"],
                "emoji": "🐱",
                "base_stats": {"health": 90, "happiness": 70, "energy": 80, "agility": 80},
                "description": "Independent and graceful hunter"
            },
            "bird": {
                "names": ["Tweety", "Phoenix", "Sky", "Echo", "Rainbow", "Storm", "Feather", "Sunny"],
                "emoji": "🦅",
                "base_stats": {"health": 70, "happiness": 90, "energy": 100, "speed": 90},
                "description": "Free-spirited aerial acrobat"
            },
            "dragon": {
                "names": ["Blaze", "Ember", "Thunder", "Crystal", "Frost", "Inferno", "Mystic", "Storm"],
                "emoji": "🐉",
                "base_stats": {"health": 120, "happiness": 60, "energy": 100, "power": 100},
                "description": "Mighty magical creature"
            },
            "unicorn": {
                "names": ["Sparkle", "Rainbow", "Star", "Magic", "Luna", "Aurora", "Celestial", "Dream"],
                "emoji": "🦄",
                "base_stats": {"health": 100, "happiness": 100, "energy": 80, "magic": 90},
                "description": "Mystical creature of pure magic"
            },
            "wolf": {
                "names": ["Alpha", "Luna", "Shadow", "Spirit", "Storm", "Winter", "Hunter", "Moon"],
                "emoji": "🐺",
                "base_stats": {"health": 110, "happiness": 70, "energy": 95, "pack_bond": 85},
                "description": "Wild and fierce pack leader"
            }
        }
    
    async def create_pets_tables(self):
        """Create pets tables in database"""
        if not self.bot.db_pool:
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS pets (
                        id SERIAL PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        pet_type VARCHAR(20) NOT NULL,
                        pet_name VARCHAR(50) NOT NULL,
                        level INTEGER DEFAULT 1,
                        experience INTEGER DEFAULT 0,
                        happiness INTEGER DEFAULT 100,
                        hunger INTEGER DEFAULT 100,
                        health INTEGER DEFAULT 100,
                        energy INTEGER DEFAULT 100,
                        strength INTEGER DEFAULT 50,
                        agility INTEGER DEFAULT 50,
                        intelligence INTEGER DEFAULT 50,
                        last_fed TIMESTAMP DEFAULT NOW(),
                        last_played TIMESTAMP DEFAULT NOW(),
                        last_trained TIMESTAMP DEFAULT NOW(),
                        last_cared TIMESTAMP DEFAULT NOW(),
                        battles_won INTEGER DEFAULT 0,
                        battles_lost INTEGER DEFAULT 0,
                        evolution_stage INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(guild_id, user_id, pet_name)
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS pet_items (
                        id SERIAL PRIMARY KEY,
                        pet_id INTEGER REFERENCES pets(id),
                        item_name VARCHAR(50) NOT NULL,
                        item_type VARCHAR(20) NOT NULL,
                        quantity INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                logger.info("Pet tables created successfully")
        except Exception as e:
            logger.error(f"Database error in pets: {e}")
    
    @commands.hybrid_command(name="adopt")
    async def adopt_pet(self, ctx, pet_type: str = None, custom_name: str = None):
        """Adopt a new pet from the shelter"""
        if not pet_type:
            embed = discord.Embed(
                title="🏠 Pet Adoption Center",
                description="Choose a pet type to adopt:",
                color=0x00ff00
            )
            
            for pet_type, pet_data in self.available_pets.items():
                embed.add_field(
                    name=f"{pet_data['emoji']} {pet_type.title()}",
                    value=f"{pet_data['description']}\nExample names: {', '.join(pet_data['names'][:3])}",
                    inline=False
                )
            
            embed.set_footer(text="Usage: !adopt <pet_type> [custom_name]")
            await ctx.send(embed=embed)
            return
        
        pet_type = pet_type.lower()
        
        if pet_type not in self.available_pets:
            valid_types = ", ".join(self.available_pets.keys())
            await ctx.send(f"❌ Invalid pet type! Choose from: {valid_types}")
            return
        
        if not self.bot.db_pool:
            # Simulate adoption without database
            pet_data = self.available_pets[pet_type]
            pet_name = custom_name or random.choice(pet_data['names'])
            
            embed = discord.Embed(
                title="🎉 Pet Adopted!",
                description=f"You adopted a {pet_data['emoji']} **{pet_name}** the {pet_type.title()}!",
                color=0x00ff00
            )
            embed.add_field(name="Type", value=pet_type.title(), inline=True)
            embed.add_field(name="Health", value="100/100", inline=True)
            embed.add_field(name="Happiness", value="100/100", inline=True)
            embed.add_field(name="Energy", value="100/100", inline=True)
            embed.add_field(name="Level", value="1", inline=True)
            embed.add_field(name="Experience", value="0/100", inline=True)
            embed.set_footer(text="Note: Pet data will be saved when database is available")
            
            await ctx.send(embed=embed)
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Check if user already has 3 pets (limit)
                pet_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM pets WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, ctx.author.id
                )
                
                if pet_count >= 3:
                    await ctx.send("❌ You can only have 3 pets maximum! Use `!abandon` to release a pet first.")
                    return
                
                # Generate pet name
                pet_data = self.available_pets[pet_type]
                pet_name = custom_name or random.choice(pet_data['names'])
                
                # Check if name is already taken
                existing_name = await conn.fetchrow(
                    "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                    ctx.guild.id, ctx.author.id, pet_name
                )
                
                if existing_name:
                    await ctx.send(f"❌ You already have a pet named '{pet_name}'! Choose a different name.")
                    return
                
                # Create new pet with random stats based on type
                base_stats = pet_data['base_stats']
                await conn.execute("""
                    INSERT INTO pets (guild_id, user_id, pet_type, pet_name, level, experience, 
                                    happiness, hunger, health, energy, strength, agility, intelligence)
                    VALUES ($1, $2, $3, $4, 1, 0, $5, 100, $6, $7, $8, $9, $10)
                """, ctx.guild.id, ctx.author.id, pet_type, pet_name,
                    base_stats.get('happiness', 100),
                    base_stats.get('health', 100),
                    base_stats.get('energy', 100),
                    base_stats.get('strength', 50) + random.randint(-10, 10),
                    base_stats.get('agility', 50) + random.randint(-10, 10),
                    random.randint(40, 60)
                )
                
                embed = discord.Embed(
                    title="🎉 Pet Adopted Successfully!",
                    description=f"Welcome **{pet_name}** the {pet_type.title()}! {pet_data['emoji']}",
                    color=0x00ff00
                )
                embed.add_field(name="Type", value=pet_type.title(), inline=True)
                embed.add_field(name="Level", value="1", inline=True)
                embed.add_field(name="Health", value=f"{base_stats.get('health', 100)}/100", inline=True)
                embed.add_field(name="Happiness", value=f"{base_stats.get('happiness', 100)}/100", inline=True)
                embed.add_field(name="Energy", value=f"{base_stats.get('energy', 100)}/100", inline=True)
                embed.add_field(name="Experience", value="0/100", inline=True)
                embed.set_footer(text=f"{pet_data['description']} • Use !pet to view your pets")
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error adopting pet: {e}")
            await ctx.send("❌ Error adopting pet!")
    
    @commands.hybrid_command(name="pet_status")
    async def pet_status(self, ctx, member: discord.Member = None):
        """Check your or someone's pets"""
        if not member:
            member = ctx.author
        
        if not self.bot.db_pool:
            await ctx.send("❌ Pet system unavailable!")
            return
        
        try:
            async with self.bot.db_pool.acquire() as conn:
                pets = await conn.fetch(
                    "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2",
                    ctx.guild.id, member.id
                )
                
                if not pets:
                    if member == ctx.author:
                        await ctx.send("❌ You don't have any pets! Use `/adopt` to get one.")
                    else:
                        await ctx.send(f"❌ {member.display_name} doesn't have any pets!")
                    return
                
                embed = discord.Embed(
                    title=f"🐾 {member.display_name}'s Pets",
                    color=discord.Color.blue()
                )
                
                for pet in pets:
                    embed.add_field(
                        name=f"{pet['pet_name']} ({pet['pet_type'].title()})",
                        value=f"❤️ Health: {pet['health']}/100\n"
                              f"😊 Happiness: {pet['happiness']}/100\n"
                              f"🍖 Hunger: {pet['hunger']}/100",
                        inline=True
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error checking pets: {e}")
            await ctx.send("❌ Error checking pets!")
    
    @commands.command(name="pet")
    async def view_pet(self, ctx, pet_name: str = None):
        """View your current pet and its stats"""
        if not self.bot.db_pool:
            embed = discord.Embed(
                title="🐾 Pet Status",
                description="Pet system demonstration mode",
                color=0x00ff00
            )
            embed.add_field(name="Pet Name", value="Demo Pet", inline=True)
            embed.add_field(name="Type", value="Dog", inline=True)
            embed.add_field(name="Level", value="5", inline=True)
            embed.add_field(name="Health", value="85/100", inline=True)
            embed.add_field(name="Happiness", value="90/100", inline=True)
            embed.add_field(name="Energy", value="75/100", inline=True)
            embed.set_footer(text="Database required for full functionality")
            await ctx.send(embed=embed)
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                if pet_name:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                        ctx.guild.id, ctx.author.id, pet_name
                    )
                else:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC LIMIT 1",
                        ctx.guild.id, ctx.author.id
                    )
                
                if not pet:
                    await ctx.send("❌ Pet not found! Use `!adopt` to get a pet.")
                    return
                
                pet_data = self.available_pets.get(pet['pet_type'], {})
                emoji = pet_data.get('emoji', '🐾')
                
                embed = discord.Embed(
                    title=f"{emoji} {pet['pet_name']}",
                    description=f"Level {pet['level']} {pet['pet_type'].title()}",
                    color=0x00ff00
                )
                
                embed.add_field(name="❤️ Health", value=f"{pet['health']}/100", inline=True)
                embed.add_field(name="😊 Happiness", value=f"{pet['happiness']}/100", inline=True)
                embed.add_field(name="⚡ Energy", value=f"{pet['energy']}/100", inline=True)
                embed.add_field(name="💪 Strength", value=f"{pet['strength']}", inline=True)
                embed.add_field(name="🏃 Agility", value=f"{pet['agility']}", inline=True)
                embed.add_field(name="🧠 Intelligence", value=f"{pet['intelligence']}", inline=True)
                embed.add_field(name="📈 Experience", value=f"{pet['experience']}/{pet['level'] * 100}", inline=True)
                embed.add_field(name="🏆 Battles Won", value=f"{pet['battles_won']}", inline=True)
                embed.add_field(name="💔 Battles Lost", value=f"{pet['battles_lost']}", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error viewing pet: {e}")
            await ctx.send("❌ Error viewing pet!")
    
    @commands.command(name="feed")
    async def feed_pet(self, ctx, pet_name: str = None):
        """Feed your pet to keep it healthy"""
        if not self.bot.db_pool:
            await ctx.send("🍖 You fed your pet! Happiness increased! (Database required for persistence)")
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                if pet_name:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                        ctx.guild.id, ctx.author.id, pet_name
                    )
                else:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 ORDER BY last_fed ASC LIMIT 1",
                        ctx.guild.id, ctx.author.id
                    )
                
                if not pet:
                    await ctx.send("❌ Pet not found! Use `!adopt` to get a pet.")
                    return
                
                # Check cooldown (can feed every 4 hours)
                last_fed = pet['last_fed']
                now = datetime.now()
                if last_fed and (now - last_fed).total_seconds() < 14400:  # 4 hours
                    remaining = 14400 - (now - last_fed).total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await ctx.send(f"❌ {pet['pet_name']} isn't hungry yet! Wait {hours}h {minutes}m")
                    return
                
                # Feed the pet
                new_happiness = min(100, pet['happiness'] + random.randint(10, 25))
                new_health = min(100, pet['health'] + random.randint(5, 15))
                new_hunger = min(100, pet['hunger'] + random.randint(20, 40))
                
                await conn.execute("""
                    UPDATE pets SET happiness = $1, health = $2, hunger = $3, last_fed = NOW()
                    WHERE id = $4
                """, new_happiness, new_health, new_hunger, pet['id'])
                
                embed = discord.Embed(
                    title="🍖 Feeding Time!",
                    description=f"You fed **{pet['pet_name']}**!",
                    color=0x00ff00
                )
                embed.add_field(name="Happiness", value=f"{pet['happiness']} → {new_happiness}", inline=True)
                embed.add_field(name="Health", value=f"{pet['health']} → {new_health}", inline=True)
                embed.add_field(name="Hunger", value=f"{pet['hunger']} → {new_hunger}", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error feeding pet: {e}")
            await ctx.send("❌ Error feeding pet!")
    
    @commands.command(name="play")
    async def play_with_pet(self, ctx, pet_name: str = None):
        """Play with your pet to increase happiness"""
        if not self.bot.db_pool:
            activities = ["fetch", "tug of war", "hide and seek", "frisbee", "chase"]
            activity = random.choice(activities)
            await ctx.send(f"🎾 You played {activity} with your pet! They loved it! (Database required for persistence)")
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                if pet_name:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                        ctx.guild.id, ctx.author.id, pet_name
                    )
                else:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 ORDER BY last_played ASC LIMIT 1",
                        ctx.guild.id, ctx.author.id
                    )
                
                if not pet:
                    await ctx.send("❌ Pet not found! Use `!adopt` to get a pet.")
                    return
                
                # Check cooldown (can play every 2 hours)
                last_played = pet['last_played']
                now = datetime.now()
                if last_played and (now - last_played).total_seconds() < 7200:  # 2 hours
                    remaining = 7200 - (now - last_played).total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await ctx.send(f"❌ {pet['pet_name']} is tired! Wait {hours}h {minutes}m")
                    return
                
                # Play with pet
                activities = ["fetch", "tug of war", "hide and seek", "frisbee", "chase", "puzzle games"]
                activity = random.choice(activities)
                
                new_happiness = min(100, pet['happiness'] + random.randint(15, 30))
                new_energy = max(10, pet['energy'] - random.randint(10, 20))
                exp_gain = random.randint(5, 15)
                new_experience = pet['experience'] + exp_gain
                
                await conn.execute("""
                    UPDATE pets SET happiness = $1, energy = $2, experience = $3, last_played = NOW()
                    WHERE id = $4
                """, new_happiness, new_energy, new_experience, pet['id'])
                
                embed = discord.Embed(
                    title="🎾 Playtime!",
                    description=f"You played **{activity}** with **{pet['pet_name']}**!",
                    color=0x00ff00
                )
                embed.add_field(name="Happiness", value=f"{pet['happiness']} → {new_happiness}", inline=True)
                embed.add_field(name="Energy", value=f"{pet['energy']} → {new_energy}", inline=True)
                embed.add_field(name="Experience", value=f"+{exp_gain} XP", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error playing with pet: {e}")
            await ctx.send("❌ Error playing with pet!")
    
    @commands.command(name="train")
    async def train_pet(self, ctx, pet_name: str = None, stat: str = None):
        """Train your pet to improve its abilities"""
        if not self.bot.db_pool:
            stats = ["strength", "agility", "intelligence"]
            trained_stat = stat or random.choice(stats)
            await ctx.send(f"💪 You trained your pet's {trained_stat}! Stats improved! (Database required for persistence)")
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                if pet_name:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                        ctx.guild.id, ctx.author.id, pet_name
                    )
                else:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 ORDER BY last_trained ASC LIMIT 1",
                        ctx.guild.id, ctx.author.id
                    )
                
                if not pet:
                    await ctx.send("❌ Pet not found! Use `!adopt` to get a pet.")
                    return
                
                # Check cooldown (can train every 6 hours)
                last_trained = pet['last_trained']
                now = datetime.now()
                if last_trained and (now - last_trained).total_seconds() < 21600:  # 6 hours
                    remaining = 21600 - (now - last_trained).total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await ctx.send(f"❌ {pet['pet_name']} needs rest! Wait {hours}h {minutes}m")
                    return
                
                # Train the pet
                valid_stats = ["strength", "agility", "intelligence"]
                if not stat or stat.lower() not in valid_stats:
                    stat = random.choice(valid_stats)
                else:
                    stat = stat.lower()
                
                stat_increase = random.randint(3, 8)
                exp_gain = random.randint(10, 25)
                energy_cost = random.randint(15, 25)
                
                new_stat_value = min(100, pet[stat] + stat_increase)
                new_experience = pet['experience'] + exp_gain
                new_energy = max(0, pet['energy'] - energy_cost)
                
                await conn.execute(f"""
                    UPDATE pets SET {stat} = $1, experience = $2, energy = $3, last_trained = NOW()
                    WHERE id = $4
                """, new_stat_value, new_experience, new_energy, pet['id'])
                
                embed = discord.Embed(
                    title="💪 Training Session!",
                    description=f"**{pet['pet_name']}** completed {stat} training!",
                    color=0x00ff00
                )
                embed.add_field(name=f"{stat.title()}", value=f"{pet[stat]} → {new_stat_value}", inline=True)
                embed.add_field(name="Experience", value=f"+{exp_gain} XP", inline=True)
                embed.add_field(name="Energy", value=f"{pet['energy']} → {new_energy}", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error training pet: {e}")
            await ctx.send("❌ Error training pet!")

    @commands.command(name="breed")
    async def breed_pets(self, ctx, pet1_name: str = None, pet2_name: str = None):
        """Breed your pet with another user's pet"""
        if not self.bot.db_pool:
            await ctx.send("💕 Pet breeding initiated! New offspring will arrive soon! (Database required for full functionality)")
            return
            
        embed = discord.Embed(
            title="💕 Pet Breeding System",
            description="Breeding system coming soon! Stay tuned for adorable offspring!",
            color=0xff69b4
        )
        embed.add_field(name="Features", value="• Cross-species breeding\n• Unique offspring traits\n• Breeding cooldowns\n• Genetic combinations", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name="abandon")
    async def abandon_pet(self, ctx, pet_name: str):
        """Abandon your current pet (irreversible)"""
        if not pet_name:
            await ctx.send("❌ Please specify which pet to abandon: `!abandon <pet_name>`")
            return
            
        if not self.bot.db_pool:
            await ctx.send(f"💔 You released {pet_name} back to the wild... (Database required for persistence)")
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                pet = await conn.fetchrow(
                    "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                    ctx.guild.id, ctx.author.id, pet_name
                )
                
                if not pet:
                    await ctx.send(f"❌ You don't have a pet named '{pet_name}'!")
                    return
                
                await conn.execute(
                    "DELETE FROM pets WHERE id = $1",
                    pet['id']
                )
                
                embed = discord.Embed(
                    title="💔 Pet Released",
                    description=f"You released **{pet_name}** back to the wild...",
                    color=0xff0000
                )
                embed.add_field(name="Farewell", value=f"{pet_name} will always remember the good times you shared together.", inline=False)
                embed.set_footer(text="This action is irreversible")
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error abandoning pet: {e}")
            await ctx.send("❌ Error abandoning pet!")
    
    @commands.command(name="petshop")
    async def pet_shop(self, ctx):
        """Browse pet shop for items and accessories"""
        embed = discord.Embed(
            title="🏪 Pet Shop",
            description="Welcome to the Pet Emporium!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🍖 Food & Treats",
            value="• Premium Food - $50\n• Tasty Treats - $20\n• Health Potion - $100\n• Energy Boost - $75",
            inline=True
        )
        
        embed.add_field(
            name="🎾 Toys & Equipment",
            value="• Training Dummy - $150\n• Exercise Ball - $80\n• Puzzle Toy - $60\n• Racing Gear - $200",
            inline=True
        )
        
        embed.add_field(
            name="✨ Accessories",
            value="• Cute Collar - $40\n• Royal Crown - $300\n• Battle Armor - $500\n• Magic Amulet - $250",
            inline=True
        )
        
        embed.set_footer(text="Use !buy <item> to purchase • Coming soon: Full shop integration")
        await ctx.send(embed=embed)
    
    @commands.command(name="petbattle")
    async def pet_battle(self, ctx, opponent: discord.Member = None):
        """Battle your pet against others"""
        if not opponent:
            embed = discord.Embed(
                title="⚔️ Pet Battle Arena",
                description="Challenge another user to a pet battle!",
                color=0xff4500
            )
            embed.add_field(name="Usage", value="`!petbattle @user`", inline=False)
            embed.add_field(name="Battle System", value="• Turn-based combat\n• Stat-based damage\n• Experience rewards\n• Ranking system", inline=False)
            await ctx.send(embed=embed)
            return
            
        if opponent == ctx.author:
            await ctx.send("❌ You can't battle yourself!")
            return
            
        if opponent.bot:
            await ctx.send("❌ You can't battle bots!")
            return
            
        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{ctx.author.mention} challenges {opponent.mention} to a pet battle!",
            color=0xff4500
        )
        embed.add_field(name="Battle System", value="Advanced pet battle system coming soon!", inline=False)
        embed.set_footer(text="React with ⚔️ to accept the challenge")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
    
    @commands.command(name="petrace")
    async def pet_race(self, ctx):
        """Enter your pet in racing competitions"""
        embed = discord.Embed(
            title="🏁 Pet Racing Circuit",
            description="Welcome to the Grand Prix of Pets!",
            color=0x00bfff
        )
        
        embed.add_field(
            name="🏃 Race Categories",
            value="• Sprint Race (Speed focus)\n• Endurance Race (Stamina focus)\n• Obstacle Course (Agility focus)\n• Intelligence Challenge (Brain power)",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Rewards",
            value="• 1st Place: 500 XP + Trophy\n• 2nd Place: 300 XP + Medal\n• 3rd Place: 150 XP + Ribbon\n• Participation: 50 XP",
            inline=False
        )
        
        embed.set_footer(text="Racing system under development • Check back soon!")
        await ctx.send(embed=embed)
    
    @commands.command(name="petcare")
    async def pet_care(self, ctx, pet_name: str = None):
        """Provide medical care for your pet"""
        if not self.bot.db_pool:
            await ctx.send("🏥 You took your pet to the vet! They're feeling much better! (Database required for persistence)")
            return
            
        try:
            async with self.bot.db_pool.acquire() as conn:
                if pet_name:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 AND pet_name = $3",
                        ctx.guild.id, ctx.author.id, pet_name
                    )
                else:
                    pet = await conn.fetchrow(
                        "SELECT * FROM pets WHERE guild_id = $1 AND user_id = $2 ORDER BY health ASC LIMIT 1",
                        ctx.guild.id, ctx.author.id
                    )
                
                if not pet:
                    await ctx.send("❌ Pet not found! Use `!adopt` to get a pet.")
                    return
                
                # Check cooldown (can care every 8 hours)
                last_cared = pet['last_cared']
                now = datetime.now()
                if last_cared and (now - last_cared).total_seconds() < 28800:  # 8 hours
                    remaining = 28800 - (now - last_cared).total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await ctx.send(f"❌ {pet['pet_name']} was recently cared for! Wait {hours}h {minutes}m")
                    return
                
                # Provide care
                care_cost = 100  # Cost in economy currency
                new_health = min(100, pet['health'] + random.randint(20, 40))
                new_happiness = min(100, pet['happiness'] + random.randint(10, 20))
                
                await conn.execute("""
                    UPDATE pets SET health = $1, happiness = $2, last_cared = NOW()
                    WHERE id = $3
                """, new_health, new_happiness, pet['id'])
                
                embed = discord.Embed(
                    title="🏥 Veterinary Care",
                    description=f"**{pet['pet_name']}** received excellent medical care!",
                    color=0x00ff00
                )
                embed.add_field(name="Health", value=f"{pet['health']} → {new_health}", inline=True)
                embed.add_field(name="Happiness", value=f"{pet['happiness']} → {new_happiness}", inline=True)
                embed.add_field(name="Cost", value=f"${care_cost}", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Database error caring for pet: {e}")
            await ctx.send("❌ Error caring for pet!")
    
    @commands.command(name="petevolution")
    async def pet_evolution(self, ctx, pet_name: str = None):
        """Evolve your pet to new forms"""
        embed = discord.Embed(
            title="✨ Pet Evolution System",
            description="Transform your pet into powerful new forms!",
            color=0x9932cc
        )
        
        embed.add_field(
            name="🌟 Evolution Stages",
            value="• Stage 1: Baby (Level 1-10)\n• Stage 2: Juvenile (Level 11-25)\n• Stage 3: Adult (Level 26-50)\n• Stage 4: Elder (Level 51+)",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Evolution Requirements",
            value="• Required level threshold\n• High happiness (80+)\n• Evolution stones\n• Training milestones",
            inline=False
        )
        
        embed.set_footer(text="Evolution system in development • Level up your pets!")
        await ctx.send(embed=embed)
    
    @commands.command(name="pethunting")
    async def pet_hunting(self, ctx, pet_name: str = None):
        """Take your pet hunting for resources"""
        if not self.bot.db_pool:
            resources = ["rabbit", "deer", "wild boar", "treasure chest", "rare herbs"]
            found = random.choice(resources)
            await ctx.send(f"🏹 Your pet found a {found} while hunting! (Database required for inventory)")
            return
            
        embed = discord.Embed(
            title="🏹 Pet Hunting Expedition",
            description="Send your pet on hunting adventures!",
            color=0x8b4513
        )
        
        embed.add_field(
            name="🎯 Hunting Locations",
            value="• Forest (Small game)\n• Mountains (Large game)\n• Swamp (Rare items)\n• Desert (Treasures)",
            inline=True
        )
        
        embed.add_field(
            name="📦 Possible Rewards",
            value="• Food items\n• Crafting materials\n• Gold coins\n• Experience points",
            inline=True
        )
        
        embed.set_footer(text="Hunting expeditions coming soon!")
        await ctx.send(embed=embed)
    
    @commands.command(name="petfishing")
    async def pet_fishing(self, ctx, pet_name: str = None):
        """Go fishing with your pet companion"""
        if not self.bot.db_pool:
            fish_types = ["salmon", "trout", "bass", "golden fish", "treasure chest"]
            caught = random.choice(fish_types)
            await ctx.send(f"🎣 You and your pet caught a {caught}! (Database required for inventory)")
            return
            
        embed = discord.Embed(
            title="🎣 Pet Fishing Adventure",
            description="Cast your line with your faithful companion!",
            color=0x4682b4
        )
        
        embed.add_field(
            name="🌊 Fishing Spots",
            value="• Peaceful Lake (Common fish)\n• Rushing River (Active fish)\n• Deep Ocean (Rare catches)\n• Mystical Pond (Magical fish)",
            inline=True
        )
        
        embed.add_field(
            name="🐟 Possible Catches",
            value="• Common fish\n• Rare fish\n• Treasure items\n• Experience points",
            inline=True
        )
        
        embed.set_footer(text="Fishing system under development!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pets(bot))
