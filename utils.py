from datetime import datetime, timezone

# Return category object from string name
def getCategory(name, ctx):
    print("Getting category")
    for category in ctx.guild.categories:
        print(category)
        print(category.id)
        if(category.name.lower() == name.lower()):
            print("This is it")
            return category
    return None

async def getLogChannel(client, id):
    guild = client.get_guild(id)
    for channel in guild.channels:
        if(channel.name == "archie-logs"):
                return channel
    channel = await guild.create_text_channel('archie-logs')
    return channel

def getTimeSince(message):

    id = message.guild.id
    timestamp = message.created_at

    # Get current time
    now = datetime.now(timezone.utc)
    now = now.replace(tzinfo=None)

    # Get time difference and convert to seconds
    time_since = now - timestamp
    time_since = time_since.total_seconds()

    return time_since

async def daysSinceActive(channel):

    # Get last message
    if channel.last_message_id == None: # If there are no messages in channel
        return 0

    message = await channel.fetch_message(channel.last_message_id)
    
    time_since = int((getTimeSince(message) / (60 * 60 * 24)))

    return time_since

# Get time since last message
async def checkTimedOut(channel, timeout):

    days_since = await daysSinceActive(channel)

    if timeout == None:
        return False 

    return days_since > timeout