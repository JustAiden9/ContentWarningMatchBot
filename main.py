import discord
import random
import string
import json
import asyncio
from discord.ext import commands

# Bot token
TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Server ID where the voice channel will be created
SERVER_ID = 'YOUR_SERVER_ID_HERE'

# Role ID for the role that will have access to the voice channels
ROLE_ID = 'YOUR_ROLE_ID_HERE'

# Prefix for the unique string
STRING_PREFIX = 'CW_'

# Voice channel category ID where the private voice channels will be created
CATEGORY_ID = 'YOUR_CATEGORY_ID_HERE'

# Channel ID where the embed will be sent
CHANNEL_ID = 'YOUR_CHANNEL_ID_HERE'

# File to store unique codes
CODES_FILE = 'codes.json'


# Time in seconds before considering a voice channel inactive
INACTIVE_TIMEOUT = 15  # 15 minutes

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.message_content = True  # Add message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store unique codes and corresponding users
unique_codes = {}
# Dictionary to store voice channels and corresponding roles
voice_channels = {}
# Dictionary to store last activity timestamps for voice channels
last_activity = {}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    # Get the channel to send the embed
    channel = bot.get_channel(int(CHANNEL_ID))

    embed = discord.Embed(title='Start Matchmaking', description='Click the button below to start matchmaking', color=discord.Color.green())
    embed.set_footer(text='ContentWarningMatchBot by JustAiden')

    # Send the embed with a button to start matchmaking
    try:
        msg = await channel.send(embed=embed)
        await msg.add_reaction('▶️')
    except Exception as e:
        print(f"An error occurred while sending the embed: {e}")

    # Load unique codes from file
    load_unique_codes()

    # Start background task to check for inactive voice channels
    bot.loop.create_task(check_inactive_channels())

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    # Check if the reaction is on the correct message and emoji
    if str(reaction.emoji) == '▶️' and reaction.message.author == bot.user:
        # Remove the reaction from the user
        try:
            await reaction.remove(user)
        except Exception as e:
            print(f"An error occurred while removing reaction: {e}")
        else:
            # Generate a unique string
            unique_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # Store the unique code and corresponding user
            unique_codes[unique_string] = user.id

            # Save unique codes to file
            save_unique_codes()

            # Send the unique string to the user via DM
            await user.send(f'Your unique code for matchmaking send it to your friends: {STRING_PREFIX}{unique_string}')

            # Get the guild
            guild = bot.get_guild(int(SERVER_ID))

            # Create a role with the unique code
            role = await guild.create_role(name=unique_string)

            # Create a voice channel with the unique code as the name
            category = discord.utils.get(guild.categories, id=int(CATEGORY_ID))
            vc = await category.create_voice_channel(unique_string)

            # Store the voice channel and corresponding role
            voice_channels[vc.id] = role.id

            # Make the voice channel private
            await vc.edit(user_limit=0)

            # Give the role permission to access the voice channel
            await vc.set_permissions(guild.default_role, connect=False)  # Deny @everyone to connect
            await vc.set_permissions(role, connect=True, speak=True, view_channel=True)  # Allow the role to connect and speak
            await vc.set_permissions(guild.me, connect=True, speak=True, view_channel=True)  # Allow the bot to connect and speak

            # Give the user the corresponding role
            await user.add_roles(role)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if the message contains a valid unique code
    if message.content.startswith(STRING_PREFIX):
        # Extract the unique code
        code = message.content[len(STRING_PREFIX):]

        # Check if the code is valid and corresponds to a user
        if code in unique_codes:
            # Get the user ID who sent the code
            user_id = unique_codes[code]

            # Get the guild
            guild = bot.get_guild(int(SERVER_ID))

            # Get the role corresponding to the code
            role = discord.utils.get(guild.roles, name=code)

            if role:
                # Get the voice channel corresponding to the code
                vc = discord.utils.get(guild.voice_channels, name=code)

                if vc:
                    # Send the link to the voice channel
                    await message.author.send(f"<@{user_id}>, Go back to the server and click https://discord.com/channels/{vc.guild.id}/{vc.id} to join your game in {vc.guild.name}/{vc.category.name}/{vc.name}")

                    # Delete the unique code from the dictionary
                    del unique_codes[code]

                    # Save unique codes to file
                    save_unique_codes()

                else:
                    await message.author.send("Voice channel not found.")

            else:
                await message.author.send("Invalid code or code expired.")

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel:
        last_activity[before.channel.id] = asyncio.get_event_loop().time()
    if after.channel:
        last_activity[after.channel.id] = asyncio.get_event_loop().time()

async def check_inactive_channels():
    while True:
        await asyncio.sleep(60)  # Check every minute

        current_time = asyncio.get_event_loop().time()
        inactive_channels = [channel for channel, timestamp in last_activity.items() if current_time - timestamp > INACTIVE_TIMEOUT]

        print("Inactive channels:", inactive_channels)  # Log inactive channels

        for channel_id in inactive_channels:
            channel = bot.get_channel(channel_id)
            if channel:
                # Check if the channel is empty before deleting
                if len(channel.members) == 0:
                    await delete_voice_channel(channel)
                else:
                    print(f"Channel {channel.name} is not empty, not deleting.")

async def delete_voice_channel(channel):
    guild = channel.guild
    role_id = voice_channels.get(channel.id)
    if role_id:
        role = guild.get_role(role_id)
        if role:
            await role.delete()
        del voice_channels[channel.id]
    await channel.delete()

def load_unique_codes():
    global unique_codes
    try:
        with open(CODES_FILE, 'r') as file:
            data = file.read()
            if data:
                unique_codes = json.loads(data)
            else:
                unique_codes = {}  # Initialize as an empty dictionary
    except FileNotFoundError:
        unique_codes = {}  # If file doesn't exist, start with empty dictionary

def save_unique_codes():
    with open(CODES_FILE, 'w') as file:
        json.dump(unique_codes, file)

bot.run(TOKEN)
