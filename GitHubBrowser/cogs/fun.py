import discord
from discord.ext import commands
import random
import asyncio
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class Fun(commands.Cog):
    """Fun commands and games for entertainment"""
    
    def __init__(self, bot):
        self.bot = bot
        self.trivia_questions = [
            {"question": "What is the capital of France?", "answer": "paris", "options": ["London", "Berlin", "Paris", "Madrid"]},
            {"question": "What is 2 + 2?", "answer": "4", "options": ["3", "4", "5", "6"]},
            {"question": "Which planet is known as the Red Planet?", "answer": "mars", "options": ["Venus", "Mars", "Jupiter", "Saturn"]},
            {"question": "Who painted the Mona Lisa?", "answer": "leonardo da vinci", "options": ["Picasso", "Van Gogh", "Leonardo da Vinci", "Michelangelo"]},
            {"question": "What is the largest mammal?", "answer": "blue whale", "options": ["Elephant", "Blue Whale", "Giraffe", "Hippo"]}
        ]
        
        self.jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a fake noodle? An impasta!",
            "Why did the math book look so sad? Because it had too many problems!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why don't skeletons fight each other? They don't have the guts!",
            "What's orange and sounds like a parrot? A carrot!"
        ]
        
        self.riddles = [
            {"riddle": "What has keys but no locks, space but no room, and you can enter but not go inside?", "answer": "keyboard"},
            {"riddle": "What gets wet while drying?", "answer": "towel"},
            {"riddle": "What has hands but cannot clap?", "answer": "clock"},
            {"riddle": "What can travel around the world while staying in a corner?", "answer": "stamp"},
            {"riddle": "What has a head, a tail, is brown, and has no legs?", "answer": "penny"}
        ]
        
        self.compliments = [
            "You're amazing!",
            "You have great taste in Discord bots!",
            "You're absolutely wonderful!",
            "You brighten everyone's day!",
            "You're incredibly thoughtful!",
            "You have such a positive energy!",
            "You're truly special!",
            "You make the world a better place!"
        ]
        
        self.roasts = [
            "You're like a cloud - when you disappear, it's a beautiful day!",
            "If I wanted to kill myself, I'd climb your ego and jump to your IQ level!",
            "You're not stupid; you just have bad luck thinking!",
            "I'd explain it to you, but I don't have any crayons with me!",
            "You're the reason the gene pool needs a lifeguard!"
        ]
        
        # Game state storage
        self.hangman_games = {}
        self.trivia_sessions = {}
        self.connect4_games = {}
        self.tictactoe_games = {}
    
    @commands.command(name='trivia')
    async def trivia(self, ctx):
        """Start a trivia question"""
        question_data = random.choice(self.trivia_questions)
        
        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=question_data["question"],
            color=0x7289da
        )
        
        options_text = ""
        for i, option in enumerate(question_data["options"], 1):
            options_text += f"{i}. {option}\n"
        
        embed.add_field(name="Options", value=options_text, inline=False)
        embed.add_field(name="How to Answer", value="Type the number (1-4) or the answer directly!", inline=False)
        
        msg = await ctx.send(embed=embed)
        
        # Store trivia session
        self.trivia_sessions[ctx.channel.id] = {
            "answer": question_data["answer"].lower(),
            "options": question_data["options"],
            "asker": ctx.author.id,
            "message": msg
        }
        
        def check(m):
            return m.channel == ctx.channel and m.author != self.bot.user
        
        try:
            response = await self.bot.wait_for("message", timeout=30.0, check=check)
            
            user_answer = response.content.lower().strip()
            correct_answer = self.trivia_sessions[ctx.channel.id]["answer"]
            options = self.trivia_sessions[ctx.channel.id]["options"]
            
            # Check if answer is correct (by number or text)
            is_correct = False
            if user_answer == correct_answer:
                is_correct = True
            elif user_answer.isdigit():
                choice_num = int(user_answer)
                if 1 <= choice_num <= len(options):
                    if options[choice_num - 1].lower() == correct_answer:
                        is_correct = True
            
            if is_correct:
                embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"{response.author.mention} got it right!",
                    color=0x00ff00
                )
                
                # Award points if economy cog is loaded
                if 'Economy' in self.bot.cogs:
                    reward = random.randint(50, 150)
                    await self.bot.cogs['Economy'].update_user_balance(response.author.id, reward)
                    embed.add_field(name="Reward", value=f"+${reward}", inline=True)
            else:
                embed = discord.Embed(
                    title="❌ Wrong!",
                    description=f"The correct answer was: **{correct_answer.title()}**",
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The correct answer was: **{correct_answer.title()}**",
                color=0xffa500
            )
            await ctx.send(embed=embed)
        
        finally:
            # Clean up
            if ctx.channel.id in self.trivia_sessions:
                del self.trivia_sessions[ctx.channel.id]
    
    @commands.command(name='8ball')
    async def eight_ball(self, ctx, *, question: str = None):
        """Ask the magic 8-ball a question"""
        if not question:
            await ctx.send("Please ask a question!")
            return
        
        responses = [
            "It is certain", "Reply hazy, try again", "Don't count on it",
            "It is decidedly so", "Ask again later", "My reply is no",
            "Without a doubt", "Better not tell you now", "My sources say no",
            "Yes definitely", "Cannot predict now", "Outlook not so good",
            "You may rely on it", "Concentrate and ask again", "Very doubtful",
            "As I see it, yes", "Most likely", "Outlook good", "Yes",
            "Signs point to yes"
        ]
        
        answer = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=0x7289da
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"*{answer}*", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='joke')
    async def joke(self, ctx):
        """Get a random joke"""
        joke = random.choice(self.jokes)
        
        embed = discord.Embed(
            title="😂 Here's a joke for you!",
            description=joke,
            color=0xffa500
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='meme')
    async def meme(self, ctx):
        """Get a random meme (text-based)"""
        memes = [
            "This is fine. 🔥🐕🔥",
            "Much wow. Very Discord bot. Such commands.",
            "One does not simply... use a Discord bot without spamming commands.",
            "I don't always use Discord bots, but when I do, I spam !help.",
            "Drake pointing: Regular bots ❌ | Apple Bot ✅",
            "Distracted boyfriend: Me 👨 | Regular bots 👩 | Apple Bot 🔥👩",
            "This is brilliant! But I like this. *points to Apple Bot*"
        ]
        
        meme = random.choice(memes)
        
        embed = discord.Embed(
            title="😎 Meme Time!",
            description=meme,
            color=0x9932cc
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='riddle')
    async def riddle(self, ctx):
        """Get a riddle to solve"""
        riddle_data = random.choice(self.riddles)
        
        embed = discord.Embed(
            title="🤔 Riddle Time!",
            description=riddle_data["riddle"],
            color=0x7289da
        )
        embed.add_field(name="How to Answer", value="Just type your answer!", inline=False)
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.channel == ctx.channel and m.author != self.bot.user
        
        try:
            response = await self.bot.wait_for("message", timeout=60.0, check=check)
            
            if response.content.lower().strip() == riddle_data["answer"].lower():
                embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"{response.author.mention} solved the riddle!",
                    color=0x00ff00
                )
                
                # Award points if economy cog is loaded
                if 'Economy' in self.bot.cogs:
                    reward = random.randint(100, 200)
                    await self.bot.cogs['Economy'].update_user_balance(response.author.id, reward)
                    embed.add_field(name="Reward", value=f"+${reward}", inline=True)
            else:
                embed = discord.Embed(
                    title="❌ Wrong!",
                    description=f"The answer was: **{riddle_data['answer']}**",
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was: **{riddle_data['answer']}**",
                color=0xffa500
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='quiz')
    async def quiz(self, ctx, category: str = "random"):
        """Start a quick quiz"""
        categories = {
            "math": [
                {"q": "What is 15 + 27?", "a": "42"},
                {"q": "What is 8 * 7?", "a": "56"},
                {"q": "What is 100 / 4?", "a": "25"}
            ],
            "science": [
                {"q": "What is H2O?", "a": "water"},
                {"q": "What gas do plants absorb?", "a": "carbon dioxide"},
                {"q": "How many bones are in the human body?", "a": "206"}
            ],
            "history": [
                {"q": "When did World War II end?", "a": "1945"},
                {"q": "Who was the first president of the USA?", "a": "george washington"},
                {"q": "In which year did the Titanic sink?", "a": "1912"}
            ]
        }
        
        if category == "random":
            all_questions = []
            for cat_questions in categories.values():
                all_questions.extend(cat_questions)
            question_data = random.choice(all_questions)
        elif category in categories:
            question_data = random.choice(categories[category])
        else:
            await ctx.send(f"Available categories: {', '.join(categories.keys())}, random")
            return
        
        embed = discord.Embed(
            title=f"📚 Quiz - {category.title()}",
            description=question_data["q"],
            color=0x7289da
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.channel == ctx.channel and m.author != self.bot.user
        
        try:
            response = await self.bot.wait_for("message", timeout=30.0, check=check)
            
            if response.content.lower().strip() == question_data["a"].lower():
                embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"{response.author.mention} got it right!",
                    color=0x00ff00
                )
                
                # Award points
                if 'Economy' in self.bot.cogs:
                    reward = random.randint(75, 125)
                    await self.bot.cogs['Economy'].update_user_balance(response.author.id, reward)
                    embed.add_field(name="Reward", value=f"+${reward}", inline=True)
            else:
                embed = discord.Embed(
                    title="❌ Wrong!",
                    description=f"The answer was: **{question_data['a']}**",
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was: **{question_data['a']}**",
                color=0xffa500
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='rps')
    async def rock_paper_scissors(self, ctx, choice: str = None):
        """Play rock paper scissors"""
        if not choice:
            await ctx.send("Choose: rock, paper, or scissors!")
            return
        
        choice = choice.lower()
        if choice not in ["rock", "paper", "scissors"]:
            await ctx.send("Invalid choice! Choose: rock, paper, or scissors")
            return
        
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        # Determine winner
        if choice == bot_choice:
            result = "It's a tie!"
            color = 0xffa500
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "You win!"
            color = 0x00ff00
            # Award small prize
            if 'Economy' in self.bot.cogs:
                reward = random.randint(25, 75)
                await self.bot.cogs['Economy'].update_user_balance(ctx.author.id, reward)
                result += f" (+${reward})"
        else:
            result = "I win!"
            color = 0xff0000
        
        embed = discord.Embed(
            title="🪨📄✂️ Rock Paper Scissors",
            color=color
        )
        embed.add_field(name="Your Choice", value=choice.title(), inline=True)
        embed.add_field(name="My Choice", value=bot_choice.title(), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='coinflip')
    async def coin_flip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=0xffd700
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='roll')
    async def roll_dice(self, ctx, sides: int = 6):
        """Roll a dice"""
        if sides < 2 or sides > 100:
            await ctx.send("Dice must have between 2 and 100 sides!")
            return
        
        result = random.randint(1, sides)
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"You rolled a **{result}** on a {sides}-sided dice!",
            color=0x7289da
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='dice')
    async def multiple_dice(self, ctx, count: int = 1, sides: int = 6):
        """Roll multiple dice"""
        if count < 1 or count > 10:
            await ctx.send("You can roll between 1 and 10 dice!")
            return
        
        if sides < 2 or sides > 100:
            await ctx.send("Dice must have between 2 and 100 sides!")
            return
        
        results = [random.randint(1, sides) for _ in range(count)]
        total = sum(results)
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"Rolling {count}d{sides}",
            color=0x7289da
        )
        embed.add_field(name="Results", value=" ".join(map(str, results)), inline=True)
        embed.add_field(name="Total", value=str(total), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='choose')
    async def choose(self, ctx, *, choices: str = None):
        """Choose randomly from options"""
        if not choices:
            await ctx.send("Please provide choices separated by commas!")
            return
        
        options = [choice.strip() for choice in choices.split(",")]
        if len(options) < 2:
            await ctx.send("Please provide at least 2 choices!")
            return
        
        chosen = random.choice(options)
        
        embed = discord.Embed(
            title="🤔 Random Choice",
            description=f"I choose: **{chosen}**",
            color=0x7289da
        )
        embed.add_field(name="Options", value=", ".join(options), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='number')
    async def guess_number(self, ctx, guess: int = None, max_num: int = 100):
        """Guess a number game"""
        if guess is None:
            await ctx.send(f"Guess a number between 1 and {max_num}!")
            return
        
        if guess < 1 or guess > max_num:
            await ctx.send(f"Number must be between 1 and {max_num}!")
            return
        
        target = random.randint(1, max_num)
        
        if guess == target:
            result = "🎉 Exactly right!"
            color = 0x00ff00
            if 'Economy' in self.bot.cogs:
                reward = random.randint(100, 250)
                await self.bot.cogs['Economy'].update_user_balance(ctx.author.id, reward)
                result += f" (+${reward})"
        elif abs(guess - target) <= 5:
            result = "🔥 Very close!"
            color = 0xffa500
            if 'Economy' in self.bot.cogs:
                reward = random.randint(25, 50)
                await self.bot.cogs['Economy'].update_user_balance(ctx.author.id, reward)
                result += f" (+${reward})"
        elif abs(guess - target) <= 10:
            result = "😊 Pretty close!"
            color = 0xffff00
        else:
            result = "❌ Not close at all!"
            color = 0xff0000
        
        embed = discord.Embed(
            title="🔢 Number Guessing",
            color=color
        )
        embed.add_field(name="Your Guess", value=str(guess), inline=True)
        embed.add_field(name="Target Number", value=str(target), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='hangman')
    async def hangman(self, ctx):
        """Start a hangman game"""
        if ctx.channel.id in self.hangman_games:
            await ctx.send("A hangman game is already in progress in this channel!")
            return
        
        words = ["python", "discord", "computer", "hangman", "challenge", "programming", "keyboard", "monitor"]
        word = random.choice(words).upper()
        
        self.hangman_games[ctx.channel.id] = {
            "word": word,
            "guessed": set(),
            "wrong_guesses": 0,
            "max_wrong": 6
        }
        
        await self.display_hangman(ctx)
    
    async def display_hangman(self, ctx):
        """Display hangman game state"""
        if ctx.channel.id not in self.hangman_games:
            return
        game = self.hangman_games[ctx.channel.id]
        word = game["word"]
        guessed = game["guessed"]
        wrong_guesses = game["wrong_guesses"]
        
        # Create display word
        display = " ".join([letter if letter in guessed else "_" for letter in word])
        
        # Hangman drawings
        hangman_stages = [
            "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```"
        ]
        
        embed = discord.Embed(
            title="🎪 Hangman Game",
            description=hangman_stages[wrong_guesses],
            color=0x7289da
        )
        embed.add_field(name="Word", value=display, inline=False)
        embed.add_field(name="Wrong Guesses", value=f"{wrong_guesses}/{game['max_wrong']}", inline=True)
        
        if guessed:
            embed.add_field(name="Guessed Letters", value=" ".join(sorted(guessed)), inline=True)
        
        embed.add_field(name="How to Play", value="Type a letter to guess!", inline=False)
        
        # Check win/lose conditions
        if all(letter in guessed for letter in word):
            embed.color = 0x00ff00
            embed.add_field(name="🎉 You Win!", value=f"The word was: **{word}**", inline=False)
            del self.hangman_games[ctx.channel.id]
            
            # Award prize
            if 'Economy' in self.bot.cogs:
                reward = len(word) * 50
                await self.bot.cogs['Economy'].update_user_balance(ctx.author.id, reward)
                embed.add_field(name="Reward", value=f"+${reward}", inline=True)
                
        elif wrong_guesses >= game['max_wrong']:
            embed.color = 0xff0000
            embed.add_field(name="💀 Game Over!", value=f"The word was: **{word}**", inline=False)
            del self.hangman_games[ctx.channel.id]
        
        await ctx.send(embed=embed)
    
    async def display_hangman_message(self, channel, author):
        """Display hangman game state from message event"""
        if channel.id not in self.hangman_games:
            return
            
        game = self.hangman_games[channel.id]
        word = game["word"]
        guessed = game["guessed"]
        wrong_guesses = game["wrong_guesses"]
        
        # Create display word
        display = " ".join([letter if letter in guessed else "_" for letter in word])
        
        # Hangman drawings
        hangman_stages = [
            "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
            "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```"
        ]
        
        embed = discord.Embed(
            title="🎪 Hangman Game",
            description=hangman_stages[wrong_guesses],
            color=0x7289da
        )
        embed.add_field(name="Word", value=display, inline=False)
        embed.add_field(name="Wrong Guesses", value=f"{wrong_guesses}/{game['max_wrong']}", inline=True)
        
        if guessed:
            embed.add_field(name="Guessed Letters", value=" ".join(sorted(guessed)), inline=True)
        
        embed.add_field(name="How to Play", value="Type a letter to guess!", inline=False)
        
        # Check win/lose conditions
        if all(letter in guessed for letter in word):
            embed.color = 0x00ff00
            embed.add_field(name="🎉 You Win!", value=f"The word was: **{word}**", inline=False)
            del self.hangman_games[channel.id]
            
            # Award prize
            if 'Economy' in self.bot.cogs:
                reward = len(word) * 50
                await self.bot.cogs['Economy'].update_user_balance(author.id, reward)
                embed.add_field(name="Reward", value=f"+${reward}", inline=True)
                
        elif wrong_guesses >= game['max_wrong']:
            embed.color = 0xff0000
            embed.add_field(name="💀 Game Over!", value=f"The word was: **{word}**", inline=False)
            del self.hangman_games[channel.id]
        
        await channel.send(embed=embed)
    
    @commands.command(name='tictactoe', aliases=['ttt'])
    async def tictactoe(self, ctx, opponent: discord.Member = None):
        """Start a tic-tac-toe game"""
        if not opponent:
            await ctx.send("Please mention someone to play against!")
            return
        
        if opponent == ctx.author:
            await ctx.send("You can't play against yourself!")
            return
        
        if opponent.bot:
            await ctx.send("You can't play against a bot!")
            return
        
        game_id = f"{ctx.channel.id}-{ctx.author.id}-{opponent.id}"
        
        if game_id in self.tictactoe_games:
            await ctx.send("A game is already in progress between you two!")
            return
        
        # Initialize game
        self.tictactoe_games[game_id] = {
            "board": [[" " for _ in range(3)] for _ in range(3)],
            "current_player": ctx.author.id,
            "players": {ctx.author.id: "X", opponent.id: "O"},
            "channel": ctx.channel.id
        }
        
        await self.display_tictactoe(ctx, game_id)
    
    async def display_tictactoe(self, ctx, game_id):
        """Display tic-tac-toe board"""
        game = self.tictactoe_games[game_id]
        board = game["board"]
        
        # Create board display
        board_str = "```\n"
        for i, row in enumerate(board):
            board_str += " | ".join([cell if cell != " " else str(i*3 + j + 1) for j, cell in enumerate(row)])
            if i < 2:
                board_str += "\n-----------\n"
        board_str += "\n```"
        
        current_player_id = game["current_player"]
        current_player = self.bot.get_user(current_player_id)
        symbol = game["players"][current_player_id]
        
        embed = discord.Embed(
            title="❌⭕ Tic-Tac-Toe",
            description=board_str,
            color=0x7289da
        )
        embed.add_field(name="Current Turn", value=f"{current_player.mention} ({symbol})", inline=True)
        embed.add_field(name="How to Play", value="Type a number (1-9) to place your symbol!", inline=False)
        
        # Check for win/draw
        winner = self.check_tictactoe_winner(board)
        if winner:
            if winner == "draw":
                embed.color = 0xffa500
                embed.add_field(name="🤝 Draw!", value="No one wins this time!", inline=False)
            else:
                winner_id = next(pid for pid, symbol in game["players"].items() if symbol == winner)
                winner_user = self.bot.get_user(winner_id)
                embed.color = 0x00ff00
                embed.add_field(name="🎉 Winner!", value=f"{winner_user.mention} ({winner}) wins!", inline=False)
                
                # Award prize
                if 'Economy' in self.bot.cogs:
                    reward = 200
                    await self.bot.cogs['Economy'].update_user_balance(winner_id, reward)
                    embed.add_field(name="Reward", value=f"+${reward}", inline=True)
            
            del self.tictactoe_games[game_id]
        
        await ctx.send(embed=embed)
    
    def check_tictactoe_winner(self, board):
        """Check for tic-tac-toe winner"""
        # Check rows
        for row in board:
            if row[0] == row[1] == row[2] != " ":
                return row[0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col] != " ":
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2] != " ":
            return board[0][0]
        if board[0][2] == board[1][1] == board[2][0] != " ":
            return board[0][2]
        
        # Check for draw
        if all(board[i][j] != " " for i in range(3) for j in range(3)):
            return "draw"
        
        return None
    
    @commands.command(name='truth')
    async def truth(self, ctx):
        """Get a truth question"""
        truths = [
            "What's your most embarrassing moment?",
            "Who was your first crush?",
            "What's the weirdest thing you've ever eaten?",
            "What's your biggest fear?",
            "What's the most childish thing you still do?",
            "What's your worst habit?",
            "What's the most trouble you've been in?",
            "What's your biggest regret?"
        ]
        
        truth = random.choice(truths)
        
        embed = discord.Embed(
            title="🤔 Truth Question",
            description=truth,
            color=0x7289da
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='dare')
    async def dare(self, ctx):
        """Get a dare challenge"""
        dares = [
            "Send a message in all caps for the next 5 minutes",
            "Change your status to something embarrassing for 10 minutes",
            "Tell a joke in the chat",
            "Compliment everyone who's online",
            "Share an unpopular opinion",
            "Sing a song (or type the lyrics)",
            "Act like your favorite animal for 2 minutes",
            "Tell everyone your most used emoji and why"
        ]
        
        dare = random.choice(dares)
        
        embed = discord.Embed(
            title="😈 Dare Challenge",
            description=dare,
            color=0xff4500
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='story')
    async def story(self, ctx):
        """Generate a random story beginning"""
        characters = ["wizard", "knight", "dragon", "princess", "thief", "merchant", "farmer", "sailor"]
        locations = ["castle", "forest", "mountain", "village", "cave", "ship", "desert", "swamp"]
        objects = ["sword", "treasure", "map", "potion", "book", "crystal", "crown", "ring"]
        
        character = random.choice(characters)
        location = random.choice(locations)
        obj = random.choice(objects)
        
        story = f"Once upon a time, a brave {character} discovered a magical {obj} hidden in an ancient {location}..."
        
        embed = discord.Embed(
            title="📖 Story Starter",
            description=story,
            color=0x9932cc
        )
        embed.add_field(name="Continue the story!", value="What happens next?", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='rap')
    async def rap(self, ctx, *, topic: str = None):
        """Generate a rap verse"""
        if not topic:
            topic = "Discord"
        
        rap_templates = [
            f"Yo, let me tell you 'bout {topic}, it's so fly\nMaking everyone happy, reaching for the sky\nBetter than the rest, that's no lie\n{topic} forever, that's my battle cry!",
            f"Step up to the mic, gonna rap about {topic}\nIt's the best thing ever, never gonna stop it\nFrom the top to the bottom, it's so iconic\n{topic} in the house, feeling so sonic!",
            f"Listen up y'all, {topic} is the name\nChanging the world, that's the game\nNever gonna quit, never gonna be tame\n{topic} is fire, lighting up the flame!"
        ]
        
        rap = random.choice(rap_templates)
        
        embed = discord.Embed(
            title="🎤 Rap Verse",
            description=f"```{rap}```",
            color=0xff1493
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='roast')
    async def roast(self, ctx, member: discord.Member = None):
        """Get roasted (or roast someone else)"""
        target = member or ctx.author
        roast = random.choice(self.roasts)
        
        embed = discord.Embed(
            title="🔥 Roast Time!",
            description=f"{target.mention}: {roast}",
            color=0xff4500
        )
        embed.set_footer(text="Just for fun! Don't take it seriously 😄")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='compliment')
    async def compliment(self, ctx, member: discord.Member = None):
        """Give a compliment"""
        target = member or ctx.author
        compliment = random.choice(self.compliments)
        
        embed = discord.Embed(
            title="💝 Compliment",
            description=f"{target.mention}: {compliment}",
            color=0xff69b4
        )
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle game responses"""
        if message.author.bot:
            return
        
        # Handle hangman guesses
        if message.channel.id in self.hangman_games:
            if len(message.content) == 1 and message.content.isalpha():
                game = self.hangman_games[message.channel.id]
                letter = message.content.upper()
                
                if letter in game["guessed"]:
                    await message.channel.send(f"You already guessed **{letter}**!")
                    return
                
                game["guessed"].add(letter)
                
                if letter not in game["word"]:
                    game["wrong_guesses"] += 1
                
                await self.display_hangman_message(message.channel, message.author)
        
        # Handle tic-tac-toe moves
        for game_id, game in list(self.tictactoe_games.items()):
            if (message.channel.id == game["channel"] and 
                message.author.id == game["current_player"] and
                message.content.isdigit()):
                
                move = int(message.content)
                if 1 <= move <= 9:
                    row, col = (move - 1) // 3, (move - 1) % 3
                    
                    if game["board"][row][col] == " ":
                        game["board"][row][col] = game["players"][message.author.id]
                        
                        # Switch players
                        players = list(game["players"].keys())
                        current_index = players.index(game["current_player"])
                        game["current_player"] = players[1 - current_index]
                        
                        await self.display_tictactoe(message, game_id)
                    else:
                        await message.channel.send("That position is already taken!")

    @commands.command(name="wouldyourather")
    async def would_you_rather(self, ctx):
        """Play would you rather with friends"""
        scenarios = [
            ("Have the ability to fly", "Have the ability to be invisible"),
            ("Always be 10 minutes late", "Always be 20 minutes early"),
            ("Have no internet", "Have no air conditioning/heating"),
            ("Be able to speak all languages", "Be able to talk to animals"),
            ("Have super strength", "Have super speed"),
            ("Never be able to use social media", "Never be able to watch TV/movies"),
            ("Always say what you think", "Never speak again"),
            ("Be famous for something bad", "Be forgotten completely")
        ]
        
        option_a, option_b = random.choice(scenarios)
        
        embed = discord.Embed(
            title="🤔 Would You Rather?",
            description="Choose your preference!",
            color=0x9932cc
        )
        embed.add_field(name="🅰️ Option A", value=option_a, inline=False)
        embed.add_field(name="🅱️ Option B", value=option_b, inline=False)
        embed.set_footer(text="React with 🅰️ or 🅱️ to vote!")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("🅰️")
        await message.add_reaction("🅱️")
    
    @commands.command(name="wordle")
    async def wordle_game(self, ctx):
        """Play Wordle-style word guessing games"""
        embed = discord.Embed(
            title="📝 Wordle Game",
            description="Guess the 5-letter word!",
            color=0x00ff00
        )
        
        words = ["APPLE", "HOUSE", "WORLD", "LIGHT", "MUSIC", "DREAM", "PEACE", "MAGIC"]
        secret_word = random.choice(words)
        
        embed.add_field(
            name="How to Play",
            value="🟩 Correct letter in correct position\n🟨 Correct letter in wrong position\n⬜ Letter not in word",
            inline=False
        )
        embed.add_field(name="Secret Word", value="_ _ _ _ _", inline=False)
        embed.add_field(name="Attempts", value="6 remaining", inline=True)
        embed.set_footer(text="Type your 5-letter guess! (Game simulation)")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="tic_tac_toe")
    async def tic_tac_toe(self, ctx, opponent: discord.Member = None):
        """Play tic-tac-toe with another user"""
        if not opponent:
            await ctx.send("❌ Please mention someone to play with: `!tic_tac_toe @user`")
            return
        
        if opponent == ctx.author:
            await ctx.send("❌ You can't play against yourself!")
            return
        
        if opponent.bot:
            await ctx.send("❌ You can't play against bots!")
            return
        
        embed = discord.Embed(
            title="⭕ Tic-Tac-Toe",
            description=f"{ctx.author.mention} vs {opponent.mention}",
            color=0x00bfff
        )
        
        board = "1️⃣2️⃣3️⃣\n4️⃣5️⃣6️⃣\n7️⃣8️⃣9️⃣"
        
        embed.add_field(name="Game Board", value=board, inline=False)
        embed.add_field(name="Current Turn", value=f"{ctx.author.mention} (❌)", inline=True)
        embed.set_footer(text="React with numbers 1-9 to make your move!")
        
        message = await ctx.send(embed=embed)
        
        # Add number reactions
        for i in range(1, 10):
            await message.add_reaction(f"{i}️⃣")
    
    @commands.command(name="connect4")
    async def connect_four(self, ctx, opponent: discord.Member = None):
        """Play Connect 4 with another user"""
        if not opponent:
            await ctx.send("❌ Please mention someone to play with: `!connect4 @user`")
            return
        
        if opponent == ctx.author:
            await ctx.send("❌ You can't play against yourself!")
            return
        
        embed = discord.Embed(
            title="🔴 Connect 4",
            description=f"{ctx.author.mention} vs {opponent.mention}",
            color=0xff0000
        )
        
        board = "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣\n" + "⚪⚪⚪⚪⚪⚪⚪\n" * 6
        
        embed.add_field(name="Game Board", value=board, inline=False)
        embed.add_field(name="Current Turn", value=f"{ctx.author.mention} (🔴)", inline=True)
        embed.set_footer(text="React with numbers 1-7 to drop your piece!")
        
        message = await ctx.send(embed=embed)
        
        # Add column reactions
        for i in range(1, 8):
            await message.add_reaction(f"{i}️⃣")
    
    @commands.command(name="snake")
    async def snake_game(self, ctx):
        """Play the classic Snake game"""
        embed = discord.Embed(
            title="🐍 Snake Game",
            description="Control the snake to eat food and grow!",
            color=0x00ff00
        )
        
        # Simple snake game representation
        game_board = (
            "🟫🟫🟫🟫🟫🟫🟫🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫⬜🟢🟢⬜⬜⬜🟫\n"
            "🟫⬜⬜🟢⬜🍎⬜🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫🟫🟫🟫🟫🟫🟫🟫"
        )
        
        embed.add_field(name="Game Board", value=game_board, inline=False)
        embed.add_field(name="Score", value="0", inline=True)
        embed.add_field(name="Length", value="3", inline=True)
        embed.set_footer(text="Use ⬆️⬇️⬅️➡️ to control the snake!")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")
    
    @commands.command(name="pong")
    async def pong_game(self, ctx):
        """Play Pong with interactive controls"""
        embed = discord.Embed(
            title="🏓 Pong Game",
            description="Classic arcade game!",
            color=0xffff00
        )
        
        game_display = (
            "🟫🟫🟫🟫🟫🟫🟫🟫🟫🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫🟦⬜⬜⚪⬜⬜⬜🟦🟫\n"
            "🟫🟦⬜⬜⬜⬜⬜⬜🟦🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫🟫🟫🟫🟫🟫🟫🟫🟫🟫"
        )
        
        embed.add_field(name="Game Screen", value=game_display, inline=False)
        embed.add_field(name="Player 1", value="0", inline=True)
        embed.add_field(name="Player 2", value="0", inline=True)
        embed.set_footer(text="Use ⬆️⬇️ to move your paddle!")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")
    
    @commands.command(name="maze")
    async def maze_game(self, ctx):
        """Navigate through challenging mazes"""
        embed = discord.Embed(
            title="🌀 Maze Challenge",
            description="Find your way to the exit!",
            color=0x8b4513
        )
        
        maze = (
            "🟫🟫🟫🟫🟫🟫🟫🟫\n"
            "🟫🔴⬜🟫⬜⬜⬜🟫\n"
            "🟫🟫⬜🟫⬜🟫🟫🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫⬜🟫🟫🟫🟫⬜🟫\n"
            "🟫⬜⬜⬜⬜⬜⬜🟫\n"
            "🟫🟫🟫🟫🟫🟫🚩🟫\n"
            "🟫🟫🟫🟫🟫🟫🟫🟫"
        )
        
        embed.add_field(name="Maze", value=maze, inline=False)
        embed.add_field(name="🔴", value="Your position", inline=True)
        embed.add_field(name="🚩", value="Exit", inline=True)
        embed.set_footer(text="Use ⬆️⬇️⬅️➡️ to navigate!")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")
    
    @commands.command(name="trivia_quiz")
    async def quiz_game(self, ctx, category: str = "random"):
        """Take quizzes on various topics"""
        categories = {
            "science": [
                {"q": "What is the chemical symbol for gold?", "a": "au", "options": ["Au", "Ag", "Fe", "Cu"]},
                {"q": "How many planets are in our solar system?", "a": "8", "options": ["7", "8", "9", "10"]},
            ],
            "history": [
                {"q": "In which year did World War II end?", "a": "1945", "options": ["1944", "1945", "1946", "1947"]},
                {"q": "Who was the first person to walk on the moon?", "a": "neil armstrong", "options": ["Neil Armstrong", "Buzz Aldrin", "John Glenn", "Alan Shepard"]},
            ],
            "geography": [
                {"q": "What is the capital of Australia?", "a": "canberra", "options": ["Sydney", "Melbourne", "Canberra", "Perth"]},
                {"q": "Which is the longest river in the world?", "a": "nile", "options": ["Amazon", "Nile", "Mississippi", "Yangtze"]},
            ]
        }
        
        if category == "random":
            all_questions = []
            for cat_questions in categories.values():
                all_questions.extend(cat_questions)
            question_data = random.choice(all_questions)
        elif category.lower() in categories:
            question_data = random.choice(categories[category.lower()])
        else:
            await ctx.send(f"❌ Available categories: {', '.join(categories.keys())}, random")
            return
        
        embed = discord.Embed(
            title=f"🧠 Quiz - {category.title()}",
            description=question_data["q"],
            color=0x9932cc
        )
        
        for i, option in enumerate(question_data["options"], 1):
            embed.add_field(
                name=f"Option {i}",
                value=option,
                inline=True
            )
        
        embed.set_footer(text="You have 30 seconds to answer! Type the number (1-4)")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            choice = int(response.content)
            
            if 1 <= choice <= len(question_data["options"]):
                chosen_answer = question_data["options"][choice - 1].lower()
                correct_answer = question_data["a"].lower()
                
                if chosen_answer == correct_answer or question_data["a"].lower() in chosen_answer:
                    embed = discord.Embed(
                        title="✅ Correct!",
                        description=f"The answer was: {question_data['options'][choice - 1]}",
                        color=0x00ff00
                    )
                else:
                    # Find correct option
                    correct_option = None
                    for opt in question_data["options"]:
                        if question_data["a"].lower() in opt.lower():
                            correct_option = opt
                            break
                    
                    embed = discord.Embed(
                        title="❌ Incorrect!",
                        description=f"The correct answer was: {correct_option or question_data['a']}",
                        color=0xff0000
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Please choose a valid option (1-4)!")
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description="You didn't answer in time!",
                color=0xffff00
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="puzzle")
    async def word_puzzle(self, ctx):
        """Solve word and logic puzzles"""
        puzzles = [
            {
                "type": "anagram",
                "clue": "Unscramble: DARG",
                "answer": "drag",
                "hint": "To pull something"
            },
            {
                "type": "riddle",
                "clue": "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?",
                "answer": "map",
                "hint": "You use me for navigation"
            },
            {
                "type": "math",
                "clue": "If you have 3 apples and you take away 2, how many do you have?",
                "answer": "2",
                "hint": "Think about what 'take away' means"
            }
        ]
        
        puzzle = random.choice(puzzles)
        
        embed = discord.Embed(
            title=f"🧩 {puzzle['type'].title()} Puzzle",
            description=puzzle["clue"],
            color=0x8b4513
        )
        embed.set_footer(text="You have 60 seconds to solve this puzzle!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', timeout=60.0, check=check)
            
            if response.content.lower().strip() == puzzle["answer"].lower():
                embed = discord.Embed(
                    title="🎉 Puzzle Solved!",
                    description="Congratulations! You solved the puzzle correctly!",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Incorrect Solution",
                    description=f"The correct answer was: **{puzzle['answer']}**\nHint: {puzzle['hint']}",
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was: **{puzzle['answer']}**",
                color=0xffff00
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="memory")
    async def memory_game(self, ctx):
        """Play memory matching games"""
        symbols = ["🍎", "🍌", "🍇", "🍓", "🥝", "🍑"]
        game_symbols = symbols[:3] * 2  # 6 cards, 3 pairs
        random.shuffle(game_symbols)
        
        # Create hidden board
        hidden_board = ["❓"] * 6
        
        embed = discord.Embed(
            title="🧠 Memory Game",
            description="Remember the positions of matching pairs!",
            color=0x9932cc
        )
        
        # Show all cards briefly
        revealed_board = " ".join(f"{i+1}️⃣{sym}" for i, sym in enumerate(game_symbols))
        embed.add_field(name="Memorize these positions (5 seconds):", value=revealed_board, inline=False)
        embed.set_footer(text="Memorize the positions, then they'll be hidden!")
        
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        
        # Hide the cards
        hidden_display = " ".join(f"{i+1}️⃣❓" for i in range(6))
        embed = discord.Embed(
            title="🧠 Memory Game",
            description="Find the matching pairs!",
            color=0x9932cc
        )
        embed.add_field(name="Board:", value=hidden_display, inline=False)
        embed.add_field(name="Instructions", value="Type two numbers (1-6) separated by space to reveal cards", inline=False)
        embed.set_footer(text="Example: 1 3 (to reveal positions 1 and 3)")
        
        await message.edit(embed=embed)
        
        pairs_found = 0
        revealed = [False] * 6
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        while pairs_found < 3:
            try:
                response = await self.bot.wait_for('message', timeout=60.0, check=check)
                
                try:
                    positions = [int(x) - 1 for x in response.content.split()]
                    if len(positions) != 2 or any(p < 0 or p >= 6 for p in positions):
                        await ctx.send("❌ Please enter two valid positions (1-6)!")
                        continue
                    
                    pos1, pos2 = positions
                    
                    if revealed[pos1] or revealed[pos2]:
                        await ctx.send("❌ One or both positions are already revealed!")
                        continue
                    
                    # Reveal the cards
                    temp_display = []
                    for i in range(6):
                        if i == pos1 or i == pos2 or revealed[i]:
                            temp_display.append(f"{i+1}️⃣{game_symbols[i]}")
                        else:
                            temp_display.append(f"{i+1}️⃣❓")
                    
                    embed = discord.Embed(
                        title="🧠 Memory Game",
                        description="Cards revealed!",
                        color=0x9932cc
                    )
                    embed.add_field(name="Board:", value=" ".join(temp_display), inline=False)
                    
                    if game_symbols[pos1] == game_symbols[pos2]:
                        revealed[pos1] = True
                        revealed[pos2] = True
                        pairs_found += 1
                        embed.add_field(name="Result", value="✅ Match found!", inline=False)
                        
                        if pairs_found == 3:
                            embed.add_field(name="🎉 Game Complete!", value="You found all pairs!", inline=False)
                    else:
                        embed.add_field(name="Result", value="❌ No match. Cards will be hidden again.", inline=False)
                    
                    await message.edit(embed=embed)
                    
                    if pairs_found < 3 and game_symbols[pos1] != game_symbols[pos2]:
                        await asyncio.sleep(3)
                        # Hide cards again
                        hidden_display = []
                        for i in range(6):
                            if revealed[i]:
                                hidden_display.append(f"{i+1}️⃣{game_symbols[i]}")
                            else:
                                hidden_display.append(f"{i+1}️⃣❓")
                        
                        embed = discord.Embed(
                            title="🧠 Memory Game",
                            description="Find the matching pairs!",
                            color=0x9932cc
                        )
                        embed.add_field(name="Board:", value=" ".join(hidden_display), inline=False)
                        embed.add_field(name="Pairs Found", value=f"{pairs_found}/3", inline=True)
                        
                        await message.edit(embed=embed)
                    
                except ValueError:
                    await ctx.send("❌ Please enter two numbers separated by space!")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Game timed out!")
                break
    
    @commands.command(name="reaction")
    async def reaction_test(self, ctx):
        """Test your reaction time"""
        import random
        
        embed = discord.Embed(
            title="⚡ Reaction Time Test",
            description="Wait for the signal, then click as fast as you can!",
            color=0xff0000
        )
        embed.add_field(name="Instructions", value="Wait for the 🟢 to appear, then click it!", inline=False)
        
        message = await ctx.send(embed=embed)
        
        # Random delay between 2-6 seconds
        delay = random.uniform(2, 6)
        await asyncio.sleep(delay)
        
        # Show green signal
        embed = discord.Embed(
            title="🟢 GO!",
            description="Click the reaction as fast as you can!",
            color=0x00ff00
        )
        
        start_time = asyncio.get_event_loop().time()
        await message.edit(embed=embed)
        await message.add_reaction("🟢")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "🟢" and reaction.message.id == message.id
        
        try:
            await self.bot.wait_for('reaction_add', timeout=10.0, check=check)
            end_time = asyncio.get_event_loop().time()
            reaction_time = round((end_time - start_time) * 1000)
            
            if reaction_time < 200:
                rating = "⚡ Lightning Fast!"
            elif reaction_time < 300:
                rating = "🔥 Excellent!"
            elif reaction_time < 500:
                rating = "👍 Good!"
            elif reaction_time < 750:
                rating = "😐 Average"
            else:
                rating = "🐌 Slow"
            
            embed = discord.Embed(
                title="⏱️ Reaction Time Results",
                color=0x00ff00
            )
            embed.add_field(name="Your Time", value=f"{reaction_time}ms", inline=True)
            embed.add_field(name="Rating", value=rating, inline=True)
            
            await message.edit(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Too Slow!",
                description="You didn't react in time!",
                color=0xff0000
            )
            await message.edit(embed=embed)
    
    @commands.command(name="typing")
    async def typing_test(self, ctx):
        """Practice typing with speed tests"""
        sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Pack my box with five dozen liquor jugs.",
            "How vexingly quick daft zebras jump!",
            "Sphinx of black quartz, judge my vow.",
            "The five boxing wizards jump quickly.",
            "Crazy Fredrick bought many very exquisite opal jewels.",
            "Jim quickly realized that the beautiful gowns are expensive."
        ]
        
        sentence = random.choice(sentences)
        
        embed = discord.Embed(
            title="⌨️ Typing Test",
            description="Type the following sentence as fast and accurately as you can:",
            color=0x4169e1
        )
        embed.add_field(name="Text to Type", value=f"```{sentence}```", inline=False)
        embed.add_field(name="Instructions", value="Type the sentence exactly as shown. Timer starts now!", inline=False)
        
        await ctx.send(embed=embed)
        
        start_time = asyncio.get_event_loop().time()
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', timeout=60.0, check=check)
            end_time = asyncio.get_event_loop().time()
            
            typed_text = response.content
            time_taken = end_time - start_time
            
            # Calculate accuracy
            correct_chars = sum(1 for a, b in zip(sentence, typed_text) if a == b)
            accuracy = (correct_chars / len(sentence)) * 100 if sentence else 0
            
            # Calculate WPM
            words = len(sentence.split())
            wpm = (words / time_taken) * 60 if time_taken > 0 else 0
            
            embed = discord.Embed(
                title="📊 Typing Test Results",
                color=0x00ff00
            )
            embed.add_field(name="Time", value=f"{time_taken:.2f} seconds", inline=True)
            embed.add_field(name="WPM", value=f"{wpm:.1f}", inline=True)
            embed.add_field(name="Accuracy", value=f"{accuracy:.1f}%", inline=True)
            
            if accuracy == 100:
                embed.add_field(name="Bonus", value="🎉 Perfect accuracy!", inline=False)
            elif accuracy >= 95:
                embed.add_field(name="Rating", value="🔥 Excellent!", inline=False)
            elif accuracy >= 85:
                embed.add_field(name="Rating", value="👍 Good job!", inline=False)
            else:
                embed.add_field(name="Rating", value="📚 Keep practicing!", inline=False)
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description="Typing test timed out after 60 seconds.",
                color=0xffff00
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="math")
    async def math_challenge(self, ctx, difficulty: str = "easy"):
        """Solve math problems and equations"""
        import random
        
        if difficulty.lower() not in ["easy", "medium", "hard"]:
            await ctx.send("❌ Difficulty must be: easy, medium, or hard")
            return
        
        if difficulty.lower() == "easy":
            # Simple addition/subtraction
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            operation = random.choice(['+', '-'])
            if operation == '+':
                answer = a + b
                problem = f"{a} + {b}"
            else:
                # Ensure positive result for subtraction
                if a < b:
                    a, b = b, a
                answer = a - b
                problem = f"{a} - {b}"
        
        elif difficulty.lower() == "medium":
            # Multiplication and division
            if random.choice([True, False]):
                # Multiplication
                a = random.randint(2, 20)
                b = random.randint(2, 20)
                answer = a * b
                problem = f"{a} × {b}"
            else:
                # Division (ensure clean division)
                b = random.randint(2, 12)
                answer = random.randint(2, 20)
                a = answer * b
                problem = f"{a} ÷ {b}"
        
        else:  # hard
            # More complex operations
            operations = [
                lambda: (f"{random.randint(10, 50)}² + {random.randint(1, 20)}", 
                        random.randint(10, 50)**2 + random.randint(1, 20)),
                lambda: (f"√{random.choice([16, 25, 36, 49, 64, 81, 100])}", 
                        int(random.choice([16, 25, 36, 49, 64, 81, 100])**0.5)),
                lambda: (f"{random.randint(2, 8)}³", 
                        random.randint(2, 8)**3)
            ]
            
            problem, answer = random.choice(operations)()
        
        embed = discord.Embed(
            title=f"🧮 Math Challenge - {difficulty.title()}",
            description=f"Solve: **{problem}**",
            color=0x9932cc
        )
        embed.set_footer(text="You have 30 seconds to answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            try:
                user_answer = float(response.content)
                if abs(user_answer - answer) < 0.01:  # Allow small floating point errors
                    embed = discord.Embed(
                        title="✅ Correct!",
                        description=f"The answer is indeed **{answer}**",
                        color=0x00ff00
                    )
                    embed.add_field(name="Time Bonus", value="🎉 Well done!", inline=True)
                else:
                    embed = discord.Embed(
                        title="❌ Incorrect",
                        description=f"The correct answer is **{answer}**",
                        color=0xff0000
                    )
                    embed.add_field(name="Your Answer", value=str(user_answer), inline=True)
                
                await ctx.send(embed=embed)
                
            except ValueError:
                await ctx.send("❌ Please enter a valid number!")
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was **{answer}**",
                color=0xffff00
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))