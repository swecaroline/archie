import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
DEBUG = os.getenv('DEBUG')
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = os.getenv('OWNER_ID')

activity = discord.Game(name="a!help | v.2.4.1")
intents = discord.Intents.default()

bot = commands.Bot(command_prefix='a!', activity=activity, intents=intents)

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
@tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    if interaction.user.id == OWNER_ID:
        await tree.sync()
        print('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

client.run(TOKEN)