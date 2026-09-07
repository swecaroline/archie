from datetime import datetime, timezone
from db import read_server_values
import discord

# Return category object from string name
def get_category(ctx: discord.Interaction, name: str | None = None, id: int | None = None):
    if (name != None or id != None):
        for category in ctx.guild.categories:
            if(category.id == id or (name != None and category.name.lower() == name.lower())):
                return category
    return None

async def getLogChannel(guild):
    for channel in guild.channels:
        if(channel.name == "archie-logs"):
                return channel
    channel = await guild.create_text_channel('archie-logs')
    return channel

def get_time_since(message):

    id = message.guild.id
    timestamp = message.created_at
    timestamp = timestamp.replace(tzinfo=timezone.utc)

    # Get current time
    now = datetime.now(timezone.utc)

    # Get time difference and convert to seconds
    time_since = now - timestamp
    time_since = time_since.total_seconds()

    return time_since

async def get_days_since_active(channel):

    # Get last message
    if channel.last_message_id == None: # If there are no messages in channel
        return 0

    message = await channel.fetch_message(channel.last_message_id)
    
    if (message != None):
        time_since = int((get_time_since(message) / (60 * 60 * 24)))
        return time_since

    return 0

# Get time since last message
async def check_if_timed_out(channel, timeout):

    days_since = await get_days_since_active(channel)

    if timeout == None:
        return False 

    return days_since > timeout


async def get_category_list(interaction: discord.Interaction, exclude_frozen: bool):
    id = interaction.guild.id
    catList = []
    count = 1
    server = read_server_values(id)
    archive = server.archiveId
    frozen = []
    """""
    if(exclude_frozen):
        frozen = server[3]
        if(frozen == None):
            frozen = []
        else:
            frozen = frozen.split("\n")
    else:
        frozen = []
    """
    for category in interaction.guild.categories:
        if category.id != archive and not category.name in frozen: # Exclude the archive category and frozen categories
            catList.append(category.name)
            count += 1
    return catList