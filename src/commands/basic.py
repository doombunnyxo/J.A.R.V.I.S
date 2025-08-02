import discord
from discord.ext import commands

class BasicCommands(commands.Cog):
    """Basic bot commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='hello')
    async def hello(self, ctx):
        """Greet the user"""
        command_key = f"hello_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate hello command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            await ctx.send(f'Hello {ctx.author.mention}!')
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='ping')
    async def ping(self, ctx):
        """Respond with pong"""
        command_key = f"ping_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate ping command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            await ctx.send('Pong!')
        finally:
            self._executing_commands.discard(command_key)

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))