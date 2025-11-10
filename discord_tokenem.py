import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]

# Intents engedélyezése (szükséges a moderációhoz)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot prefix (pl. !kick, !ban stb.)
bot = commands.Bot(command_prefix="!", intents=intents)

# Esemény: Bot készen áll
@bot.event
async def on_ready():
    print(f"✅ Bejelentkezve: {bot.user}")


bot.run("MTQzNTY2MTI0MzM1MTMwMjIzNQ.GtqXh2.pt5AUuz7uBh_rpOGxthH0qztry5a3VyR__gahE")