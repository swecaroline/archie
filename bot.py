# Bot permissions: manage channels, view channels, send messages, manage messages, read message history - value: 68624

import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from db import refresh_connection, upsertServerConfig, readServerValues, updateServer
from ui import CategorySelectView
from utils import getCategory, getLogChannel, getTimeSince, daysSinceActive, checkTimedOut

load_dotenv()
DEBUG = os.getenv('DEBUG')
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = os.getenv('OWNER_ID')

activity = discord.Game(name="a!help | v.2.4.1")
intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='a!', activity=activity, intents=intents)

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

########## BOT FUNCTIONS ##########

# sync the slash command to your server
@client.event
async def on_ready():

    # Run this in all of the servers Archie is active in
    activeservers = client.guilds
    """
    for guild in activeservers:
        print("Syncing slash commands for server" + str(guild.id))

        id = guild.id
        await tree.sync(guild=discord.Object(id=id))
        print("synced slash command")

    if (not DEBUG or DEBUG == 0):
        await autoArchive()
        print("Autoarchive done")
    """

@bot.tree.command()
async def help(interaction: discord.Interaction):
    await bot.tree.sync()
    descrip = "Hi there! :wave: I'm Archie, a Discord bot that archives inactive channels.\n\n" + \
        "After you set me up, I will check on your server every day and archive channels that haven't been active for a while.\n\n" + \
        "All of this is automatic, so you don't have to worry about calling on me too often, but here are some commands you can use yourself.\n\n" + \
        "Run **a!config** to get started.\n\n"
    embed = discord.Embed(title="Archie", description=descrip, color=0xff4912)
    embed.add_field(name="`a!config`", value=":open_file_folder: Configure Archie on your server. (`a!config <CATEGORY NAME>`, `a!config <TIME (DAYS)>`, and `a!config <CATEGORY NAME> <TIME (DAYS)>` are valid.)", inline=False)
    embed.add_field(name="`a!archive`", value=":open_file_folder: Manually archive the current channel. Type 'readonly' at the end of the command to make the channel read-only, i.e. `a!archive readonly`.", inline=False)
    embed.add_field(name="`a!freeze`", value=":open_file_folder: 'Freeze' categories to prevent Archie from modifying them automatically.", inline=False)
    embed.add_field(name="`a!delete <TIME (DAYS)>`", value=":open_file_folder: Delete archived channels after they have been inactive for a set amount of time. `a!delete 0` removes the deletion timeout. Read-only channels cannot be automatically deleted.", inline=False)
    embed.add_field(name="`a!lock`", value=":open_file_folder: Make an archived channel read-only. Can be reversed with `a!unlock`.", inline=False)
    embed.add_field(name="`a!info`", value=":open_file_folder: Display the configurations for this server.", inline=False)
    # embed.add_field(name="a!categories", value=" - List all categories in server.", inline=False)
    embed.add_field(name="`a!help`", value=":open_file_folder: Display the help menu.\n\n", inline=False)
    embed.add_field(name="`a!bug`", value=":warning: Report bugs at https://forms.gle/p9FJiYyfSGtvREXR7.\n\n" + \
        "You can restore an archived channel simply by sending a message in it.\n\n" + \
        "For more information, visit Archie on Top.gg: https://top.gg/bot/857027766976118806\n\n", inline=False)

    await interaction.response.send_message(embed=embed)

async def getCatList(interaction: discord.Interaction, exclude_frozen: bool):
    id = interaction.guild.id
    catList = []
    count = 1
    server = readServerValues(id)
    archive = server.archiveCategoryName
    if(exclude_frozen):
        frozen = server[3]
        if(frozen == None):
            frozen = []
        else:
            frozen = frozen.split("\n")
    else:
        frozen = []
    for category in interaction.guild.categories:
        if category.name != archive and not category.name in frozen: # Exclude the archive category and frozen categories
            catList.append(category.name)
            count += 1
    return catList

@bot.tree.command()
@has_permissions(manage_guild=True)
async def config(ctx, cat_name: str, timeout: int = None):
    id = ctx.guild.id
    responseMessage = ""
    if getCategory(cat_name, ctx) == None: # If the archive category does not yet exist, create it
        print("Category created")
        responseMessage += "Category **" + cat_name.upper() + "** created.\n"
        category = await ctx.guild.create_category(cat_name)
    try:
        upsertServerConfig(id, cat_name, timeout)
        responseMessage += "Category **" + cat_name.upper() + "** set as server archive."
        if (timeout != None):
            responseMessage += "Channels inactive for **" + str(timeout) + "** days will be moved to **" + cat_name.upper() + "**."
        responseMessage+="\n"
        print("About to update delete time")
        responseMessage += await updateDeleteTime(ctx)
    except Exception as e:
        print("Something went wrong")
        responseMessage += "Something went wrong updating your configuration."
        print(e)

    await ctx.response.send_message(responseMessage)

async def updateDeleteTime(ctx):
    id = ctx.guild.id
    server = readServerValues(id)
    timeout = server.timeToArchive
    delete_time = server.timeToDeletion
    print("DLETE TIME" + str(delete_time))
    if(delete_time and delete_time < timeout + 7):
        updateServer(id, delete_time=(timeout+7))
        print("Server updated")
        return f"Deletion timeout changed from **{delete_time}** to **{timeout+7}**. Use `a!delete` to update."
    print("No need to update server")
    return ""

async def setArchive(ctx, cat_name):
    id = ctx.message.guild.id
    if getCategory(cat_name, ctx) == None: # If the archive category does not yet exist, create it
        await ctx.message.channel.send("Category **" + cat_name.upper() + "** created.")
        category = await ctx.message.guild.create_category(cat_name)
    updateServer(id, archive=cat_name)
    await ctx.message.channel.send("Category **" + cat_name.upper() + "** set as server archive.")

async def setTimeout(ctx, timeout):
    id = ctx.message.guild.id
    updateServer(id, timeout=timeout)
    await ctx.message.channel.send(f"Channels inactive for **{timeout}** days will be archived.")

@bot.tree.command()
@has_permissions(manage_channels=True)
async def lock(ctx):
    id = ctx.message.guild.id
    if(getCategory(readServerValues(id).archiveCategoryName, ctx) == ctx.message.channel.category):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.message.channel.send("This channel has been locked.")
    else:
        await ctx.message.channel.send("`a!lock` can only be run on archived channels.")

@bot.tree.command()
@has_permissions(manage_channels=True)
async def unlock(ctx):
    overwrite = ctx.message.channel.overwrites_for(ctx.message.guild.default_role)
    if(overwrite.send_messages == False):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.message.channel.send("This channel has been unlocked.")
    else:
        await ctx.message.channel.send("This channel is already unlocked.")

@bot.tree.command()
@has_permissions(manage_guild=True)
async def freeze(ctx):

    id = ctx.message.guild.id
    delete_until = await ctx.message.channel.send("List which categories to freeze.")

    """
    cats = await inputCatList(ctx)
    if cats != []:
        cats = "\n".join(cats)
        updateServer(id, permanent_categories=cats)
        await ctx.message.channel.send(f"The following categories will NOT be automatically modified by Archie (you may still manually archive channels in this category using `a!arch`):\n**{cats.upper()}**")
    else:
        updateServer(id, permanent_categories='NULL')
        await ctx.message.channel.send(f"No categories were selected. All categories may now be automatically modified by Archie.")
    """

@bot.tree.command()
async def info(ctx):
    id = ctx.message.guild.id
    server = readServerValues(id)

    if(server == None):
        print("None")
        server = ["None", "None", "None", "None", "None", "None"]

    embed = discord.Embed(title=f"Archie Configuration Information", description=f"Archie's configuration info for **{ctx.message.guild.name}.**", color=0xff4912)
    embed.add_field(name="`Archive`", value=f"{server[1]}\n️:gear: *Archived channels are moved to the category **{server[1].upper()}**.*", inline=False)
    embed.add_field(name="`Archive Timeout`", value=f"{server[2]}\n️:gear: *Channels are archived after **{server[2]} days** of inactivity.*", inline=False)
    embed.add_field(name="`Deletion Timeout`", value=f"{server[5]}\n:gear: *Channels are deleted from the archive after **{server[5]} days** of inactivity.*", inline=False)
    embed.add_field(name="`Frozen`", value=f"{server[3]}\n:gear: *These categories cannot be modified.*\n\nIf any value is 'None', that means you have not configured it yet.", inline=False)

    await ctx.message.channel.send(embed=embed)


# Manually archive a channel
@bot.tree.command()
@has_permissions(manage_channels=True)
async def archive(ctx, readonly: bool = None):

    id = ctx.message.guild.id

    # Get designated archive category
    archive = getCategory(readServer(id)[1], ctx)
    if archive == None:
        await ctx.message.channel.send("An archive category does not exist. Please use **a!config** to create one.")
    else:
        # Move to archive category if there is space in the archive
        if(len(archive.channels) < 50):
            await ctx.message.channel.edit(category=archive)
            await ctx.message.channel.send("This channel has been archived.")
            message_count = 2
            if(readonly == True):
                await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
                await ctx.message.channel.send("This channel is now read-only.")
                message_count = 3
        else:
           await ctx.message.channel.send(f"Your archive category **{archive.name.upper()}** is full. Please make space in your archive or create a new one.")

# Report bug
@bot.tree.command()
async def bug(ctx):
    embed = discord.Embed(title=f"Archie Bug Report", description="Please report bugs at https://forms.gle/p9FJiYyfSGtvREXR7. Thanks!", color=0xff4912)
    await ctx.message.channel.send(embed=embed)


@bot.tree.command()
@has_permissions(manage_guild=True)
async def delete(ctx, days: int):
    id = ctx.message.guild.id
    timeout = readServer(id)[2]
    if not timeout:
        await ctx.message.channel.send("Please set an inactivity timeout with `a!config` before setting a deletion timeout.")
    elif(int(days) >= timeout + 7):
        updateServer(id, delete_time=int(days))
        await ctx.message.channel.send(f"Archived channels inactive for **{days}** days will be deleted.")
    elif(int(days) == 0):
        updateServer(id, delete_time='NULL')
        await ctx.message.channel.send("Archived channels will no longer be deleted.")
    else:
        await ctx.message.channel.send(f"Deletion time must be greater than {timeout+7}.")


@config.error
@archive.error
@freeze.error
@delete.error
@lock.error
@unlock.error
async def permissions_error(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.message.channel.send("You don't have permission to do this!")

# Automatically archive inactive channels after 24 hours
# @tasks.loop(hours=24)
async def autoArchive():

    # Update connection in case DATABASE_URL changed
    # global connection
    # connection = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='require')
    refresh_connection()

    # Run this in all of the servers Archie is active in
    activeservers = client.guilds
    for guild in activeservers:

        id = guild.id
        archive = 0

        server = readServer(id)

        if server == None:
            upsertServerConfig(id, "", None)

        archiveIsFull = False

        logChannel = None

        if(guild.system_channel):
            logChannel = guild.system_channel
        else:
            logChannel = await getLogChannel(client, id)

        if(server != None and len(server) > 1): # If that server is in the database

            permanent_categories = server[3]
            if permanent_categories:
                permanent_categories = permanent_categories.split("\n")
            else:
                permanent_categories = []
            timeout = server[2]
            delete_time = server[5]

            error = False

            # Go through every text channel
            for channel in guild.channels:

                # Check if Archie has the permissions to manage this channel
                bot_member = guild.get_member(client.user.id)
                bot_role = bot_member.roles[0]
                if(not bot_role.is_bot_managed()):
                    for role in bot_member.roles:
                        if(role.is_bot_managed()):
                            bot_role = role
                permissions = channel.overwrites_for(bot_role).manage_channels
               
                try:    # If the channel is in a text channel that is not frozen
                    if(permissions != False and str(channel.type) == 'text' and (channel.category == None or not (channel.category.name in permanent_categories))):

                        # Code to delete inactive channels
                        overwrite = channel.overwrites_for(guild.default_role)
                        if(channel.category != None and channel.category.name == server[1] and not overwrite.send_messages == False): # If the channel is in the archive and is not readonly

                            if(delete_time != None and timeout != None and delete_time > timeout): # Check if a delete time has been set

                                days_since = await daysSinceActive(channel) # Check days since last active

                                if days_since + 2 >= delete_time:
                                
                                    if days_since >= delete_time:

                                        await channel.delete()
                                        # pass
                                    
                                    else:
                                        days_until = delete_time - days_since
                                        await logChannel.send(f"**{channel.name}** (<#{channel.id}>) will be deleted in **{days_until} day(s)** if it remains inactive.")
                            else:
                                pass
                        
                        # Code to archive inactive channels if channel is not full
                        elif not archiveIsFull: 
                            inactive = await checkTimedOut(channel, timeout)
                            if inactive:

                                # These two lines exist mainly to get the context
                                lastMessage = await channel.fetch_message(channel.last_message_id)
                                ctx = await tree.get_context(lastMessage)

                                # Get the archive category. If there is no archive category, nothing happens.
                                if archive == 0:
                                    archive = getCategory(server[1], ctx)

                                if archive != None:
                                    # Move to archive category
                                    if(len(archive.channels) < 50): # Unless the archive category is full
                                        await channel.edit(category=archive)
                                    else:
                                        archiveIsFull = True
                except Exception as e:
                    print(channel.name)
                    # await logChannel.send("Error in archiving channels. Please set up an archive category and a timeout with `a!config`.")
                    if not isinstance(e, discord.errors.Forbidden) and not isinstance(e, discord.errors.NotFound):
                        if not error:
                            await logChannel.send("Could not auto-archive. Please set up an archive category and a timeout with `a!config`.")
                            error = True
                    print(e)
            
            if archiveIsFull:
                    await logChannel.send(f"Your archive category **{archive.name.upper()}** is full. Please make space in your archive or create a new one.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        print("Dipping")
        return

    print("Received a message")
    print(message)

    # Get current guild
    id = message.guild.id

    try: # If an archive category exists
        server = readServerValues(id)
        if (server == None):
            return

        archive = getCategory(server.archiveCategoryName, message)
        print("READ SERVER" + str(server))
        print("ARCHIVE" + str(archive))
        print("CHANNEL" + str(message.channel))
        print("CATEGORY" + str(message.channel.category))

        if message.channel.category != None and \
        (archive != None and message.channel.category.name == archive.name) and \
        message.author != client.user:

            print("Hello")

            # Get list of all categories
            catListResult = await getCatList(message, False)

            # Map the list of categories to Discord UI SelectOptions
            def parseCatList(category):
                return discord.SelectOption(label=category, emoji="📁")
            catList = map(parseCatList, catListResult)

            # Define the callback function for the Discord UI component
            async def process_categories(categories_selected, interaction):
                cat_name = categories_selected[0]
                await message.channel.edit(category=getCategory(cat_name, message))
                await interaction.response.edit_message(content="Channel restored to **" + cat_name.upper() + "**.", view=None)

            # Create and display the view
            selectView = CategorySelectView(catList=catList, process_categories=process_categories)
            await message.channel.send("This channel has been archived! Which category would you like to restore it to?", view=selectView, delete_after=60)
            
    except Exception as e: 
        print("Something went wrong in on_message")
        print(e)
        pass
    
@bot.tree.command()
async def sync(interaction: discord.Interaction):
    print("Received sync message")
    print(interaction.user.id)
    print(OWNER_ID)
    if(str(interaction.user.id) == str(OWNER_ID)):
        await bot.tree.sync()
        await interaction.response.send_message("Commands synced successfully")
    else:
        await interaction.response.send_message("Who are you?")

bot.run(TOKEN)