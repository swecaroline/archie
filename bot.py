# Bot permissions: manage channels, view channels, send messages, manage messages, read message history - value: 76816
# https://discord.com/oauth2/authorize?client_id=[CLIENT_ID]&permissions=2147560464&integration_type=0&scope=applications.commands+bot

import os
import discord
from dotenv import load_dotenv
from discord.ext import tasks, commands
from discord.ext.commands import MissingPermissions
from discord import app_commands
from db import read_server_values, upsert_server, delete_server_record, set_permanent_categories, get_permanent_categories
from ui import CategorySelectView
from utils import get_category, get_category_list
from auto_archive import auto_archive
from http.server import HTTPServer, BaseHTTPRequestHandler
from webserver import setup_hook

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
    daily_auto_archive.start()

@tasks.loop(hours=24)
async def daily_auto_archive():
    print("Auto-archiving")
    activeservers = bot.guilds
    try:
        await auto_archive(bot, activeservers)
    except Exception as e:
        print("Exception while auto-archiving: " + str(e))
    print("Autoarchive done")

@bot.tree.command(description="How Archie works")
async def help(interaction: discord.Interaction):
    descrip = "Hi there! :wave: I'm Archie, a Discord bot that archives inactive channels.\n\n" + \
        "After you set me up, I will check on your server every day and archive channels that haven't been active for a while.\n\n" + \
        "All of this is automatic, so you don't have to worry about calling on me too often, but here are some commands you can use yourself.\n\n" + \
        "Run **/config** to get started.\n\n"
    embed = discord.Embed(title="Archie", description=descrip, color=0xff4912)
    embed.add_field(name="`/config`", value=":open_file_folder: Configure Archie on your server. (`a!config <CATEGORY NAME>`, `a!config <TIME (DAYS)>`, and `a!config <CATEGORY NAME> <TIME (DAYS)>` are valid.)", inline=False)
    embed.add_field(name="`/archive`", value=":open_file_folder: Manually archive the current channel. Type 'readonly' at the end of the command to make the channel read-only, i.e. `a!archive readonly`.", inline=False)
    embed.add_field(name="`/freeze`", value=":open_file_folder: 'Freeze' categories to prevent Archie from modifying them automatically.", inline=False)
    embed.add_field(name="`/delete <TIME (DAYS)>`", value=":open_file_folder: Delete archived channels after they have been inactive for a set amount of time. `a!delete 0` removes the deletion timeout. Read-only channels cannot be automatically deleted.", inline=False)
    embed.add_field(name="`/lock`", value=":open_file_folder: Make an archived channel read-only. Can be reversed with `a!unlock`.", inline=False)
    embed.add_field(name="`/info`", value=":open_file_folder: Display the configurations for this server.", inline=False)
    # embed.add_field(name="/categories", value=" - List all categories in server.", inline=False)
    embed.add_field(name="`/help`", value=":open_file_folder: Display the help menu.\n\n", inline=False)
    embed.add_field(name="`/bug`", value=":warning: Report bugs at https://forms.gle/p9FJiYyfSGtvREXR7.\n\n" + \
        "You can restore an archived channel simply by sending a message in it.\n\n" + \
        "For more information, visit Archie on Top.gg: https://top.gg/bot/857027766976118806\n\n", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(description="Configure Archie for your server")
@app_commands.describe(cat_name="The name of your archive category (can be an existing category)")
@app_commands.rename(cat_name="category_name")
@app_commands.describe(time_to_archival="Days of inactivity before your channel is archived")
@app_commands.describe(time_to_deletion="Days of inactivity before your channel is deleted from the archive")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.default_permissions(manage_guild=True)
async def config(ctx, cat_name: str, time_to_archival: int = None, time_to_deletion: int = None):
    if (time_to_archival != None and time_to_deletion != None and time_to_deletion < time_to_archival + 7):
        await ctx.response.send_message(f"**Could not apply your configuration:** The deletion time must be at least 7 days greater than the archival time.")

    id = ctx.guild.id
    server = read_server_values(id)
    responseMessage = ""
    existing_category = get_category(guild=ctx.guild, name=cat_name)

    # If the archive category does not yet exist, create it
    if existing_category == None:
        responseMessage += "Category **" + cat_name.upper() + "** created.\n"
        new_category = await ctx.guild.create_category(cat_name)
        category_id = new_category.id
    else:
        category_id = existing_category.id


    # If previous deletion timeout < new archive timeout, update
    if (server.timeToDelete != None and server.timeToDelete < time_to_archival + 7):
        responseMessage += f"Deletion timeout changed from **{server.timeToDelete}** to **{time_to_archival+7}**.\n"
        time_to_deletion = time_to_archival + 7

    try:
        upsert_server(id, archiveId=category_id, timeToArchive=time_to_archival, timeToDelete=time_to_deletion)
        responseMessage += "Category **" + cat_name.upper() + "** set as server archive. "
        if (time_to_archival != None):
            responseMessage += "\nChannels inactive for **" + str(time_to_archival) + "** days will be moved to **" + cat_name.upper() + "**."
        if (time_to_deletion != None):
            responseMessage += "\nChannels inactive for **" + str(time_to_deletion) + "** days will be deleted."
    except Exception as e:
        print("Something went wrong")
        responseMessage += "Something went wrong updating your configuration."
        print(e)

    await ctx.response.send_message(responseMessage)

@bot.tree.command(description="Disable messaging in this channel")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return
    if(get_category(guild=interaction.guild, id=server.archiveId) == interaction.channel.category):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("This channel has been locked.")
    else:
        await interaction.response.send_message("`/lock` can only be run on archived channels.")

@bot.tree.command(description="Re-enable messaging in this channel")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    if(overwrite.send_messages == False):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("This channel has been unlocked.")
    else:
        await interaction.response.send_message("This channel is already unlocked.")

@bot.tree.command(description="Configure which categories will NOT be modified by Archie")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.default_permissions(manage_guild=True)
async def freeze(interaction: discord.Interaction):

    id = interaction.guild.id
    server = read_server_values(id)
    if (server == None):
        await interaction.response.send_message("Please set up your server configuration with `/config` before running this command.")
        return

    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    if(overwrite.send_messages == False):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.channel.send("This channel has been unlocked.")

    # Get list of all categories
    cat_list_result = await get_category_list(interaction, False)

    # Map the list of categories to Discord UI SelectOptions
    def parse_cat_list(category):
        return discord.SelectOption(label=category, emoji="📁")
    catList = list(map(parse_cat_list, cat_list_result))

    # Define the callback function for the Discord UI component
    async def process_categories(categories_selected, interaction):
        if (len(categories_selected) == 0):
            await interaction.response.edit_message(view=None, content=f"No categories were selected. All categories may now be automatically modified by Archie.")

        else:
            try:
                def map_name_to_ids(cat_name: id):
                    category = get_category(guild=interaction.guild, name=cat_name)
                    if (category):
                        return category.id
                permanent_ids = map(map_name_to_ids, categories_selected)
                set_permanent_categories(category_ids=permanent_ids, server_id=id)
                def append_emoji(cat: str):
                    return f"📁 {cat}"

                cat_with_emoji = map(append_emoji, categories_selected)
                await interaction.response.edit_message(view=None, content=f"The following categories will NOT be automatically modified by Archie (you may still manually archive channels in this category using `/arch`):\n**{"\n".join(cat_with_emoji)}**")

            except Exception as e:
                await interaction.response.edit_message(view=None, content="Something went wrong")
                print(e)

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

@bot.tree.command(description="Check Archie's configuration in this server")
async def info(interaction: discord.Interaction):
    id = interaction.guild.id
    server = read_server_values(id)
    permanent_categories = get_permanent_categories(id)
    def append_emoji(cat_id: int):
        category = get_category(guild=interaction.guild, id=cat_id)
        return f"📁 {category.name}"

    archiveCategoryName = get_category(guild=interaction.guild, id=server.archiveId).name
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
    embed.add_field(name="`Frozen`", value=f"{"\n".join(map(append_emoji, permanent_categories))}\n:gear: *These categories cannot be modified.*\n\nIf any value is 'None', that means you have not configured it yet.", inline=False)
    await interaction.response.send_message(embed=embed)


# Manually archive a channel
@bot.tree.command(description="Manually archive a channel")
@app_commands.describe(readonly="Whether messaging should be disabled once it is archived")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.default_permissions(manage_channels=True)
async def archive(interaction: discord.Interaction, readonly: bool = None):

    id = interaction.guild.id

    # Get designated archive category
    archive = get_category(guild=interaction.guild, id=read_server_values(id).archiveId)
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
@bot.tree.command(description="Report bugs with Archie")
async def bug(interaction: discord.Interaction):
    if(str(interaction.user.id) == str(OWNER_ID)):
        await bot.tree.sync()

    embed = discord.Embed(title=f"Archie Bug Report", description="Please report bugs at https://forms.fillout.com/t/itgw6QfirSus. Thanks!", color=0xff4912)
    await interaction.response.send_message(embed=embed)

@config.error
@archive.error
@freeze.error
@lock.error
@unlock.error
async def permissions_error(interaction: discord.Interaction, error):
    if isinstance(error, MissingPermissions):
        print("Missing permissions")
        await interaction.response.send_message("You don't have permission to do this!")

# Automatically archive inactive channels after 24 hours
# @tasks.loop(hours=24)
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(message)

    # Get current guild
    id = message.guild.id

    try: # If an archive category exists
        server = read_server_values(id)
        if (server == None):
            return

        archive = get_category(guild=message.guild, id=server.archiveId)

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
                    await message.channel.edit(category=get_category(guild=message.guild, name=cat_name))
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

bot.setup_hook = setup_hook
bot.run(TOKEN)
