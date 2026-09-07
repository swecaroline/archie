# Bot permissions: manage channels, view channels, send messages, manage messages, read message history - value: 68624

import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from db import refresh_connection, read_server_values, upsert_server, delete_server_record
from ui import CategorySelectView
from utils import get_category, get_category_list, getLogChannel, get_time_since, get_days_since_active, check_if_timed_out

load_dotenv()
DEBUG = os.getenv('DEBUG')
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = os.getenv('OWNER_ID')
TEST_SERVER_ID = os.getenv('TEST_SERVER_ID')

activity = discord.Game(name="/help | v.3.0.0")
intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='a!', activity=activity, intents=intents)

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@bot.event
async def on_ready():
    print("I'm ready")

    # Run this in all of the servers Archie is active in
    activeservers = bot.guilds
    print(activeservers)

    """
    for guild in activeservers:
        id = guild.id
        if (str(id) == str(TEST_SERVER_ID)):
            print("Found test server")
            if (len(guild.categories) < 30):
                for i in range(30 - len(guild.categories)):
                    await guild.create_category(f"Test {i}")
    """

    if (not DEBUG or str(DEBUG) == '0'):
        try:
            await autoArchive(activeservers)
        except Exception as e:
            print("Exception while auto-archiving: " + str(e))
        print("Autoarchive done")

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

@bot.tree.command()
@has_permissions(manage_guild=True)
async def config(ctx, cat_name: str, time_to_archival: int = None, time_to_deletion: int = None):
    if (time_to_archival != None and time_to_deletion != None and time_to_deletion < time_to_archival + 7):
        await ctx.response.send_message(f"**Could not apply your configuration:** The deletion time must be at least 7 days greater than the archival time.")

    id = ctx.guild.id
    server = read_server_values(id)
    responseMessage = ""
    existing_category = get_category(ctx=ctx, name=cat_name)

    # If the archive category does not yet exist, create it
    if existing_category == None:
        responseMessage += "Category **" + cat_name.upper() + "** created.\n"
        new_category = await ctx.guild.create_category(cat_name)
        category_id = new_category.id
    else:
        category_id = existing_category.id


    # If previous deletion timeout < new archive timeout, update
    if (server.timeToDelete != None and server.timeToDelete < time_to_archival + 7):
        responseMessage += f"Deletion timeout changed from **{server.timeToDelete}** to **{time_to_archival+7}**."
        time_to_deletion = time_to_archival + 7

    try:
        upsert_server(id, archiveId=category_id, timeToArchive=time_to_archival, timeToDelete=time_to_deletion)
        responseMessage += "Category **" + cat_name.upper() + "** set as server archive. "
        if (time_to_archival != None):
            responseMessage += "Channels inactive for **" + str(time_to_archival) + "** days will be moved to **" + cat_name.upper() + "**."
        responseMessage+="\n"
    except Exception as e:
        print("Something went wrong")
        responseMessage += "Something went wrong updating your configuration."
        print(e)

    await ctx.response.send_message(responseMessage)

@bot.tree.command()
@has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return
    if(get_category(ctx=interaction, id=server.archiveId) == interaction.channel.category):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("This channel has been locked.")
    else:
        await interaction.response.send_message("`/lock` can only be run on archived channels.")

@bot.tree.command()
@has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return
    overwrite = interaction.channel.overwrites_for(interaction.message.guild.default_role)
    if(overwrite.send_messages == False):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.channel.send("This channel has been unlocked.")
    else:
        await interaction.channel.send("This channel is already unlocked.")

@bot.tree.command()
@has_permissions(manage_guild=True)
async def freeze(interaction: discord.Interaction):

    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return

    overwrite = interaction.channel.overwrites_for(interaction.message.guild.default_role)
    if(overwrite.send_messages == False):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.channel.send("This channel has been unlocked.")
    else:
        await interaction.channel.send("This channel is already unlocked.")

    # Get list of all categories
    cat_list_result = await get_category_list(interaction, False)

    # Map the list of categories to Discord UI SelectOptions
    def parse_cat_list(category):
        return discord.SelectOption(label=category, emoji="📁")
    catList = map(parse_cat_list, cat_list_result)

    # Define the callback function for the Discord UI component
    async def process_categories(categories_selected, interaction):
        if (len(categories_selected) == 0):
            await interaction.response.edit_message(view=None, content=f"No categories were selected. All categories may now be automatically modified by Archie.")

        else:
            def append_emoji(cat: str):
                return f"📁 {cat}"

            cat_with_emoji = map(append_emoji, categories_selected)
            await interaction.response.edit_message(view=None, content=f"The following categories will NOT be automatically modified by Archie (you may still manually archive channels in this category using `a!arch`):\n**{"\n".join(cat_with_emoji)}**")

    # Create and display the view
    prompt = "Select which categories from which Archie should NOT auto-archive"
    try:
        selectView = CategorySelectView(
            catList=list(catList), 
            process_categories=process_categories, 
            multi=True, 
            prompt=prompt
        )
        await interaction.response.send_message(content=prompt, view=selectView, delete_after=60)
    except Exception as e:
        print("Sometihng went wrong")
        print(e)

@bot.tree.command()
async def info(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)

    if(server == None):
        print("None")

    archiveCategoryName = get_category(interaction, id=server.archiveId).name
    timeToArchive = server.timeToArchive
    archiveConfigMsg = f"Channels are archived after **{timeToArchive} days** of inactivity."
    if (timeToArchive == None):
        timeToArchive == 'unspecified'
        archiveConfigMsg = "Specify a value to archive channels after this many days of inactivity."
    timeToDelete = server.timeToDelete
    deleteConfigMsg = f"Channels are deleted from the archive after **{server.timeToDelete} days** of inactivity."
    if (timeToDelete == None):
        timeToDelete == 'unspecified'
        deleteConfigMsg = "Specify a value to delete channels from the archive after this many days of inactivity."
    embed = discord.Embed(title=f"Archie Configuration Information", description=f"Archie's configuration info for **{interaction.guild.name}.**", color=0xff4912)
    embed.add_field(name="`Archive`", value=f"{archiveCategoryName}\n️:gear: *Archived channels are moved to the category **{archiveCategoryName}**.*", inline=False)
    embed.add_field(name="`Archive Timeout`", value=f"{timeToArchive}\n️:gear: *{archiveConfigMsg}*", inline=False)
    embed.add_field(name="`Deletion Timeout`", value=f"{timeToDelete}\n:gear: *{deleteConfigMsg}*", inline=False)
    """
    embed.add_field(name="`Frozen`", value=f"{}\n:gear: *These categories cannot be modified.*\n\nIf any value is 'None', that means you have not configured it yet.", inline=False)
    """
    await interaction.response.send_message(embed=embed)


# Manually archive a channel
@bot.tree.command()
@has_permissions(manage_channels=True)
async def archive(interaction: discord.Interaction, readonly: bool = None):

    id = interaction.guild.id

    # Get designated archive category
    archive = get_category(ctx=interaction, id=read_server_values(id).archiveId)
    if archive == None:
        await interaction.response.send_message("An archive category does not exist. Please use **/config** to create one.")
    else:
        # Move to archive category if there is space in the archive
        if(len(archive.channels) < 50):
            await interaction.channel.edit(category=archive)
            await interaction.response.send_message("This channel has been archived.")
            if(readonly == True):
                await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
                await interaction.response.send_message("This channel is now read-only.")
        else:
           await interaction.response.send_message(f"Your archive category **{archive.name.upper()}** is full. Please make space in your archive or create a new one.")

# Report bug
@bot.tree.command()
async def bug(interaction: discord.Interaction):
    embed = discord.Embed(title=f"Archie Bug Report", description="Please report bugs at https://forms.gle/p9FJiYyfSGtvREXR7. Thanks!", color=0xff4912)
    await interaction.response.send_message(embed=embed)


@bot.tree.command()
@has_permissions(manage_guild=True)
async def delete(ctx, days: int):
    id = ctx.message.guild.id
    timeout = read_server_values(id)[2]
    if not timeout:
        await ctx.message.channel.send("Please set an inactivity timeout with `a!config` before setting a deletion timeout.")
    elif(int(days) >= timeout + 7):
        upsert_server(id, delete_time=int(days))
        await ctx.message.channel.send(f"Archived channels inactive for **{days}** days will be deleted.")
    elif(int(days) == 0):
        upsert_server(id, delete_time='NULL')
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
async def autoArchive(activeservers):

    refresh_connection()

    for guild in activeservers:

        print("NEW GUILD")

        id = guild.id
        archive = 0

        server = read_server_values(id)
        logChannel = None
        if(guild.system_channel):
            logChannel = guild.system_channel
        else:
            print("Looking for log channel")
            logChannel = await getLogChannel(guild)


        if server == None:
            await logChannel.send("Could not auto-archive. Please set up an archive category and a timeout with `/config`.")
            continue

        archive_is_full = False

        if(server != None): # If that server is in the database

            time_to_archive = server.timeToArchive
            time_to_delete = server.timeToDelete

            """
            permanent_categories = server[3]
            if permanent_categories:
                permanent_categories = permanent_categories.split("\n")
            else:
                permanent_categories = []
            timeout = server[2]
            delete_time = server[5]
            """

            error = False

            print("About to go through channels")
            print(len(guild.channels))

            # Go through every text channel
            for channel in guild.channels:

                # Check if Archie has the permissions to manage this channel
                bot_member = guild.get_member(bot.user.id)
                bot_role = bot_member.roles[0]
                if(not bot_role.is_bot_managed()):
                    for role in bot_member.roles:
                        if(role.is_bot_managed()):
                            bot_role = role
                permissions = channel.overwrites_for(bot_role).manage_channels
               
                try:    # If the channel is in a text channel that is not frozen
                    if(permissions != False and str(channel.type) == 'text'): # and (channel.category == None)): or not (channel.category.name in permanent_categories))):

                        # Code to delete inactive channels
                        overwrite = channel.overwrites_for(guild.default_role)
                        if(channel.category != None and channel.category.id == server.archiveId and not overwrite.send_messages == False): # If the channel is in the archive and is not readonly

                            if(time_to_delete != None and time_to_archive != None and time_to_delete > time_to_archive): # Check if a delete time has been set
                                days_since = await get_days_since_active(channel) # Check days since last active

                                if days_since + 2 >= time_to_delete:
                                    if days_since >= time_to_delete:
                                        await channel.delete()
                                    
                                    else:
                                        days_until = time_to_delete - days_since
                                        await logChannel.send(f"**{channel.name}** (<#{channel.id}>) will be deleted in **{days_until} day(s)** if it remains inactive.")
                            else:
                                pass
                        
                        # Code to archive inactive channels if channel is not full
                        elif not archive_is_full: 
                            inactive = await check_if_timed_out(channel, time_to_archive)
                            if inactive:

                                # These two lines exist mainly to get the context
                                lastMessage = await channel.fetch_message(channel.last_message_id)
                                ctx = await bot.get_context(lastMessage)

                                # Get the archive category. If there is no archive category, nothing happens.
                                # if archive == 0:
                                archive = get_category(ctx=ctx, id=server.archiveId)
                                print("ARCHIVE FROM CONTEXT" + str(archive))

                                if archive != None:
                                    # Move to archive category
                                    if(len(archive.channels) < 50): # Unless the archive category is full
                                        await channel.edit(category=archive)
                                    else:
                                        archive_is_full = True
                except Exception as e:
                    print(channel.name)
                    # await logChannel.send("Error in archiving channels. Please set up an archive category and a timeout with `a!config`.")
                    if not isinstance(e, discord.errors.Forbidden) and not isinstance(e, discord.errors.NotFound):
                        if not error:
                            await logChannel.send("Could not auto-archive. Please set up an archive category and a timeout with `/config`.")
                            error = True
                    print(e)
            
            if archive_is_full:
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
        server = read_server_values(id)
        if (server == None):
            return

        archive = get_category(ctx=message, id=server.archiveId)

        if message.channel.category != None and \
        (archive != None and message.channel.category.name == archive.name) and \
        message.author != client.user:

            # Get list of all categories
            catListResult = await get_category_list(message, False)

            # Map the list of categories to Discord UI SelectOptions
            def parseCatList(category):
                return discord.SelectOption(label=category, emoji="📁")
            catList = map(parseCatList, catListResult)

            # Define the callback function for the Discord UI component
            async def process_categories(categories_selected, interaction):
                if (len(categories_selected) == 1):
                    cat_name = categories_selected[0]
                    await message.channel.edit(category=get_category(ctx=message, name=cat_name))
                    await interaction.response.edit_message(content="Channel restored to **" + cat_name.upper() + "**.", view=None)
                else:
                    await message.channel.edit(category=None)
                    await interaction.response.edit_message(content="Channel restored.", view=None)

            prompt = "This channel has been archived! Which category would you like to restore it to?"
            # Create and display the view
            selectView = CategorySelectView(
                catList=list(catList), 
                process_categories=process_categories,
                prompt=prompt
            )
            await message.channel.send(content=prompt, view=selectView, delete_after=60)
            
    except Exception as e: 
        print("Something went wrong in on_message")
        print(e)
        pass

@bot.event
async def on_guild_remove(guild):
    delete_server_record(guild.id)
    pass
    
@bot.tree.command()
async def sync(interaction: discord.Interaction):
    if(str(interaction.user.id) == str(OWNER_ID)):
        await bot.tree.sync()
        await interaction.response.send_message("Commands synced successfully")
    else:
        await interaction.response.send_message("Who are you?")

bot.run(TOKEN)