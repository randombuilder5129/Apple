import discord
import asyncio
import random
from typing import Optional, List

class LoadingAnimation:
    """Handles loading animations for commands"""
    
    def __init__(self):
        self.loading_frames = [
            "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"
        ]
        self.progress_frames = [
            "▱▱▱▱▱▱▱▱▱▱",
            "▰▱▱▱▱▱▱▱▱▱",
            "▰▰▱▱▱▱▱▱▱▱",
            "▰▰▰▱▱▱▱▱▱▱",
            "▰▰▰▰▱▱▱▱▱▱",
            "▰▰▰▰▰▱▱▱▱▱",
            "▰▰▰▰▰▰▱▱▱▱",
            "▰▰▰▰▰▰▰▱▱▱",
            "▰▰▰▰▰▰▰▰▱▱",
            "▰▰▰▰▰▰▰▰▰▱",
            "▰▰▰▰▰▰▰▰▰▰"
        ]
        self.completion_emojis = ["✅", "🎉", "⭐", "🌟", "💫"]
    
    async def show_loading(self, message: discord.Message, text: str = "Processing", duration: int = 5):
        """Show a spinning loading animation"""
        for i in range(duration * 2):  # 2 updates per second
            frame = self.loading_frames[i % len(self.loading_frames)]
            embed = discord.Embed(
                description=f"{frame} {text}...",
                color=0x00ff00
            )
            try:
                await message.edit(embed=embed)
                await asyncio.sleep(0.5)
            except discord.NotFound:
                break
    
    async def show_progress_bar(self, message: discord.Message, text: str = "Loading", steps: int = 10, step_delay: float = 0.5):
        """Show a progress bar animation"""
        for i in range(steps + 1):
            progress = min(i, len(self.progress_frames) - 1)
            bar = self.progress_frames[progress]
            percentage = int((i / steps) * 100)
            
            embed = discord.Embed(
                title=f"{text}",
                description=f"{bar} {percentage}%",
                color=0x00ff00
            )
            
            try:
                await message.edit(embed=embed)
                if i < steps:  # Don't sleep after the last update
                    await asyncio.sleep(step_delay)
            except discord.NotFound:
                break
    
    async def show_completion(self, message: discord.Message, text: str = "Completed", success: bool = True):
        """Show completion message with animation"""
        emoji = random.choice(self.completion_emojis) if success else "❌"
        color = 0x00ff00 if success else 0xff0000
        
        embed = discord.Embed(
            description=f"{emoji} {text}!",
            color=color
        )
        
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass
    
    async def show_countdown(self, message: discord.Message, title: str, seconds: int, description: str = ""):
        """Show animated countdown timer"""
        countdown_emojis = ["🔟", "9️⃣", "8️⃣", "7️⃣", "6️⃣", "5️⃣", "4️⃣", "3️⃣", "2️⃣", "1️⃣", "💥"]
        
        for i in range(seconds, -1, -1):
            if i <= 10:
                emoji = countdown_emojis[10-i] if i > 0 else "💥"
            else:
                emoji = "⏰"
            
            embed = discord.Embed(
                title=f"{emoji} {title}",
                description=f"{description}\n\n**{i} seconds remaining**" if i > 0 else f"{description}\n\n**Time's up!**",
                color=0xff6b35 if i <= 5 else 0xffa500 if i <= 10 else 0x00ff00
            )
            
            # Add visual countdown bar
            if i > 0:
                progress = int((seconds - i) / seconds * 10)
                bar = "▰" * progress + "▱" * (10 - progress)
                embed.add_field(name="Progress", value=bar, inline=False)
            
            try:
                await message.edit(embed=embed)
                if i > 0:
                    await asyncio.sleep(1)
            except discord.NotFound:
                break
    
    async def show_timer(self, message: discord.Message, title: str, total_time: int, current_time: int = 0):
        """Show timer with progress"""
        remaining = total_time - current_time
        minutes = remaining // 60
        seconds = remaining % 60
        
        progress = int((current_time / total_time) * 10) if total_time > 0 else 0
        bar = "▰" * progress + "▱" * (10 - progress)
        percentage = int((current_time / total_time) * 100) if total_time > 0 else 0
        
        embed = discord.Embed(
            title=f"⏲️ {title}",
            description=f"Time remaining: **{minutes:02d}:{seconds:02d}**",
            color=0x00ff00 if remaining > 60 else 0xffa500 if remaining > 30 else 0xff0000
        )
        
        embed.add_field(name=f"Progress ({percentage}%)", value=bar, inline=False)
        
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass

class StatusBar:
    """Advanced status bar for multi-step operations"""
    
    def __init__(self, message: discord.Message, title: str = "Processing"):
        self.message = message
        self.title = title
        self.steps: List[dict] = []
        self.current_step = 0
    
    def add_step(self, name: str, description: str = ""):
        """Add a step to the status bar"""
        self.steps.append({
            "name": name,
            "description": description,
            "status": "pending"  # pending, running, completed, failed
        })
    
    async def start_step(self, step_index: int):
        """Mark a step as running"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "running"
            self.current_step = step_index
            await self.update_display()
    
    async def complete_step(self, step_index: int, success: bool = True):
        """Mark a step as completed or failed"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "completed" if success else "failed"
            await self.update_display()
    
    async def update_display(self):
        """Update the status bar display"""
        embed = discord.Embed(
            title=f"🔄 {self.title}",
            color=0x00ff00
        )
        
        progress_text = ""
        completed_steps = sum(1 for step in self.steps if step["status"] == "completed")
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps):
            if step["status"] == "pending":
                icon = "⏳"
            elif step["status"] == "running":
                icon = "🔄"
            elif step["status"] == "completed":
                icon = "✅"
            else:  # failed
                icon = "❌"
            
            progress_text += f"{icon} {step['name']}\n"
            if step["description"] and step["status"] == "running":
                progress_text += f"   └ {step['description']}\n"
        
        embed.description = progress_text
        embed.set_footer(text=f"Progress: {completed_steps}/{total_steps} steps completed")
        
        try:
            await self.message.edit(embed=embed)
        except discord.NotFound:
            pass
    
    async def finish(self, success: bool = True, final_message: str = ""):
        """Finish the status bar with final message"""
        emoji = "🎉" if success else "💥"
        color = 0x00ff00 if success else 0xff0000
        title = "Completed Successfully" if success else "Process Failed"
        
        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=final_message or "All steps completed!",
            color=color
        )
        
        # Show final step summary
        completed = sum(1 for step in self.steps if step["status"] == "completed")
        failed = sum(1 for step in self.steps if step["status"] == "failed")
        
        embed.add_field(
            name="Summary",
            value=f"✅ Completed: {completed}\n❌ Failed: {failed}",
            inline=False
        )
        
        try:
            await self.message.edit(embed=embed)
        except discord.NotFound:
            pass

def with_loading_animation(duration: int = 3):
    """Decorator to add loading animation to commands"""
    def decorator(func):
        async def wrapper(self, ctx, *args, **kwargs):
            # Send initial loading message
            loading_msg = await ctx.send(embed=discord.Embed(
                description="⠋ Loading...",
                color=0x00ff00
            ))
            
            animation = LoadingAnimation()
            
            # Start loading animation
            animation_task = asyncio.create_task(
                animation.show_loading(loading_msg, "Processing command", duration)
            )
            
            try:
                # Execute the actual command
                result = await func(self, ctx, *args, **kwargs)
                
                # Cancel animation and show completion
                animation_task.cancel()
                await animation.show_completion(loading_msg, "Command completed")
                
                return result
                
            except Exception as e:
                # Cancel animation and show error
                animation_task.cancel()
                await animation.show_completion(loading_msg, f"Error: {str(e)}", success=False)
                raise
        
        return wrapper
    return decorator