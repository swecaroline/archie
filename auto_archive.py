from db import read_server_values, refresh_connection, get_permanent_categories
from utils import check_if_timed_out, get_category, get_days_since_active, getLogChannel
import discord

async def auto_archive(bot, activeservers):

    refresh_connection()

    for guild in activeservers:
        id = guild.id
        archive = None

        try:
            server = read_server_values(id)
            logChannel = None
            if(guild.system_channel):
                logChannel = guild.system_channel
            else:
                logChannel = await getLogChannel(guild)

            bot_member = guild.get_member(bot.user.id)
            await logChannel.set_permissions(bot_member, send_messages=True)

            if server == None:
                await logChannel.send("Could not auto-archive. Please set up an archive category and a timeout with `/config`.")
                continue

            archive_is_full = False

            if(server != None): # If that server is in the database

                time_to_archive = server.timeToArchive
                time_to_delete = server.timeToDelete
                permanent_categories = get_permanent_categories(id)

                error = False

                # Go through every text channel
                for channel in guild.channels:

                    # Check if Archie has the permissions to manage this channel
                    bot_role = bot_member.roles[0]
                    if(not bot_role.is_bot_managed()):
                        for role in bot_member.roles:
                            if(role.is_bot_managed()):
                                bot_role = role
                    permissions = channel.overwrites_for(bot_role).manage_channels

                    try:    # If the channel is in a text channel that is not frozen
                        if(permissions != False and str(channel.type) == 'text' and (channel.category == None or not (channel.category.id in permanent_categories))):

                            # Code to delete inactive channels
                            overwrite = channel.overwrites_for(guild.default_role)
                            if(channel.category != None and channel.category.id == server.archiveId and not overwrite.send_messages == False): # If the channel is in the archive and is not readonly

                                if(time_to_delete != None and time_to_archive != None and time_to_delete > time_to_archive): # Check if a delete time has been set
                                    days_since = await get_days_since_active(channel) # Check days since last active

                                    if days_since != -1 and days_since + 2 >= time_to_delete:
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

                                    # Get the archive category. If there is no archive category, nothing happens.
                                    if archive == None:
                                        archive = get_category(guild=guild, id=server.archiveId)

                                    if archive != None:
                                        # Move to archive category
                                        if(len(archive.channels) < 50): # Unless the archive category is full
                                            await channel.edit(category=archive)
                                        else:
                                            archive_is_full = True
                    except Exception as e:
                        # await logChannel.send("Error in archiving channels. Please set up an archive category and a timeout with `/config`.")
                        if not isinstance(e, discord.errors.Forbidden) and not isinstance(e, discord.errors.NotFound):
                            if not error:
                                await logChannel.send("Could not auto-archive. Please set up an archive category and a timeout with `/config`.")
                                error = True
                        print(f"Inner try error: {e}")

                if archive_is_full:
                    await logChannel.send(f"Your archive category **{archive.name.upper()}** is full. Please make space in your archive or create a new one.")
        except Exception as e:
            print(f"Error while auto-archiving server {id}: {e}")