# Archie

Archie is a Discord bot to archive inactive channels, built with Discord.py.

Open-source contribution is welcome, though I am still setting up documentation.

To invite Archie to your server: https://top.gg/bot/857027766976118806

## Required permissions
- Manage roles
- Manage channels
- View channels
- Send messages
- Manage messages
- Read message history
(Permission integer: 268512272)

## Setting up your dev environment
Pre-requisites: pip, Python v3.12 or above

```
# Set up your virtual environment
python3 -m venv .venv
source venv/bin/activate

# Install requirements
pip3 install -r requirements.txt

# Run the bot
python3 bot.py
```

## Environment variables
In `.env`, you will ned the following environment variables:
- DISCORD_TOKEN
- DB_NAME
- DB_USERNAME
- DB_PASSWORD
- DB_HOST
- DB_PORT
