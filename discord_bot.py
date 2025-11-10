
import asyncio
from datetime import datetime, timedelta
import re
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

# --- MODERÁCIÓS PARANCSOK (csak Rendszergazda jogosultsággal) ---

def admin_or_role(ctx):
    """Ellenőrzi, hogy az illető Rendszergazda-e vagy van 'Rendszergazda' szerepköre."""
    is_admin = ctx.author.guild_permissions.administrator
    has_role = discord.utils.get(ctx.author.roles, name="Rendszergazda") is not None
    return is_admin or has_role


@bot.command(name="kick") 
async def kick(ctx, member: discord.Member, *, reason="Nincs megadva"):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    await member.kick(reason=reason)
    await ctx.send(f"👢 {member} ki lett rúgva. Ok: {reason}")


@bot.command(name="ban")
async def ban(ctx, member: discord.Member, *, reason="Nincs megadva"):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} kitiltva. Ok: {reason}")


@bot.command(name="unban")
async def unban(ctx, *, member_name):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    banned_users = await ctx.guild.bans()
    name, discriminator = member_name.split("#")

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (name, discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f"♻️ {user.name} visszaengedve.")
            return

    await ctx.send("❌ Nem található ilyen felhasználó a tiltottak között.")


@bot.command(name="mute")
async def mute(ctx, member: discord.Member, *, reason="Nincs megadva"):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)

    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"🔇 {member} lenémítva. Ok: {reason}")


@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 {member} némítása feloldva.")
    else:
        await ctx.send("❌ A felhasználó nincs némítva.")


@bot.command(name="clear")
async def clear(ctx, amount: int = 5):
    if not admin_or_role(ctx):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
        return

    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 {amount} üzenet törölve.", delete_after=3)


# ---BOTTAL ÜZENETET KÜLDENI---
@bot.command(name="kuld")
async def send_message(ctx, channel_id: int, *, message: str):
    """
    Parancs, amivel a bot bármely csatornába üzenetet küldhet.

    Használat:
    !send 123456789012345678 Ez az üzenet szövege
    """

# Ellenőrizzük, hogy az illető admin vagy van 'Rendszergazda' joggal rendelkező szerepköre
    is_admin = ctx.author.guild_permissions.administrator
    has_role = discord.utils.get(ctx.author.roles, name="*") is not None

    if not (is_admin or has_role):
        await ctx.send("❌ Nincs jogosultságod használni ezt a parancsot.")
        return

    # Csatorna lekérése az ID alapján
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send("❌ Nem találom a csatornát ezzel az ID-val.")
        return

    # Üzenet küldése
    try:
        await channel.send(message)
        await ctx.send(f"✅ Üzenet elküldve a csatornába: {channel.name}")
    except discord.Forbidden:
        await ctx.send("❌ Nincs jogom üzenetet küldeni ebbe a csatornába.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Hiba történt az üzenet küldésekor: {e}")


# ---BOTTAL ÜZENETKÜLDÉS EMBED FORMÁBAN---
@bot.command(name="kuldembed")
async def send_embed(ctx, channel_id: int, title: str, *, description: str):
    """
    Csak adminok vagy 'Rendszergazda' szerepkörrel rendelkező felhasználók használhatják.
    Embed üzenetet küld a bot nevében.

    Használat:
    !sendembed <csatorna_id> "<cím>" <leírás>
    Példa:
    !sendembed 123456789012345678 "Figyelem!" Ez egy teszt embed üzenet.
    """
    # Jogosultság ellenőrzése
    is_admin = ctx.author.guild_permissions.administrator
    has_role = discord.utils.get(ctx.author.roles, name="*") is not None

    if not (is_admin or has_role):
        await ctx.send("❌ Nincs jogosultságod használni ezt a parancsot.")
        return

    # Csatorna lekérése
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send("❌ Nem találom a csatornát ezzel az ID-val.")
        return

    # Embed létrehozása
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()  # Kék szín, tetszőlegesen változtatható
    )
    embed.set_footer(text=f"Küldve: {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    # Embed küldése
    try:
        await channel.send(embed=embed)
        await ctx.send(f"✅ Embed üzenet elküldve a csatornába: {channel.name}")
    except discord.Forbidden:
        await ctx.send("❌ Nincs jogom üzenetet küldeni ebbe a csatornába.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Hiba történt az üzenet küldésekor: {e}")


# szerver tag statisztikái
@bot.command(name="statisztika", aliases=["stats", "info"])
async def statisztika(ctx, member: discord.Member = None):
    # Ha nincs megadva tag, akkor a parancsot kiadó felhasználót vizsgáljuk
    if member is None:
        member = ctx.author

    # Csatlakozás dátuma
    joined_at = member.joined_at.strftime("%Y.%m.%d. %H:%M")

    # Szerepek listázása, kivéve az @everyone
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_display = ", ".join(roles) if roles else "Nincsenek rangjai"

    # Embed létrehozása
    embed = discord.Embed(
        title=f"📊 Statisztika: {member.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="👤 Felhasználónév", value=f"{member.name}#{member.discriminator}", inline=False)
    embed.add_field(name="🕓 Csatlakozott a szerverhez", value=joined_at, inline=False)
    embed.add_field(name="🏷️ Rangok", value=roles_display, inline=False)
    embed.set_footer(text=f"Kérte: {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)

# szerver statisztikák
@bot.command(name="szerverinfo", aliases=["serverinfo", "guildinfo"])
async def szerverinfo(ctx):
    guild = ctx.guild
    created_at = guild.created_at.strftime("%Y.%m.%d. %H:%M")

    embed = discord.Embed(
        title=f"🏰 Szerver információ: {guild.name}",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="🆔 Szerver ID", value=guild.id, inline=False)
    embed.add_field(name="📅 Létrehozva", value=created_at, inline=False)
    embed.add_field(name="👥 Tagok száma", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Csatornák száma", value=len(guild.channels), inline=True)
    embed.add_field(name="👑 Tulajdonos", value=f"{guild.owner}", inline=False)
    embed.set_footer(
        text=f"Kérte: {ctx.author.name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )

    await ctx.send(embed=embed)



# Hibakezelés: ha nincs jogosultság
@kick.error
@ban.error
@unban.error
@mute.error
@unmute.error
@clear.error
async def mod_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Nincs jogosultságod ehhez a parancshoz.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Hiányzik egy szükséges argumentum.")
    else:
        raise error

import json
import os

# --- REACTION ROLE RENDSZER ---

# JSON fájl, ahol a párosításokat tároljuk

# --- JSON fájl helye ---
REACTION_FILE = "reaction_roles.json"

# --- Adatok betöltése ---
if os.path.exists(REACTION_FILE):
    with open(REACTION_FILE, "r", encoding="utf-8") as f:
        reaction_roles = json.load(f)
else:
    reaction_roles = {}  # {str(message_id): {emoji: role_id}}


def save_reactions():
    """Elmenti a reaction-role párosításokat JSON fájlba."""
    with open(REACTION_FILE, "w", encoding="utf-8") as f:
        json.dump(reaction_roles, f, indent=4, ensure_ascii=False)


@bot.command(name="reakciorang")
@commands.has_permissions(manage_roles=True)
async def reactionrole(ctx, *args):
    """
    Hozzáad egy reaction-role párost egy üzenethez.
    Formátumok:
    - !reakciorang <üzenet_id> <emoji> <@rang>
    - !reakciorang <csatorna_id> <üzenet_id> <emoji> <@rang>
    - !reakciorang <üzenet_link> <emoji> <@rang>
    """
    if len(args) < 3:
        await ctx.send(
            "❌ Használat:\n"
            "`!reakciorang <üzenet_id> <emoji> <@rang>`\n"
            "`!reakciorang <csatorna_id> <üzenet_id> <emoji> <@rang>`\n"
            "`!reakciorang <üzenet_link> <emoji> <@rang>`"
        )
        return

    message = None
    channel = None

    # Az utolsó argumentum lesz a szerep
    role = None
    if ctx.message.role_mentions:
        role = ctx.message.role_mentions[0]
    else:
        await ctx.send("❌ Nem találok érvényes @rang hivatkozást a parancsban.")
        return

    # Link minta
    link_pattern = r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)"

    # --- 1️⃣ Üzenet link ---
    if re.match(link_pattern, args[0]):
        match = re.match(link_pattern, args[0])
        guild_id, channel_id, message_id = map(int, match.groups())
        emoji = args[1]

        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ A bot nem látja a csatornát.")
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Nem található az üzenet a link alapján.")
            return

    # --- 2️⃣ Csatorna + üzenet ID ---
    elif len(args) >= 4 and args[0].isdigit() and args[1].isdigit():
        channel_id = int(args[0])
        message_id = int(args[1])
        emoji = args[2]

        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Nem található csatorna ezzel az ID-val.")
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Nem található üzenet ezzel az ID-val ebben a csatornában.")
            return

    # --- 3️⃣ Csak üzenet ID ---
    elif args[0].isdigit():
        message_id = int(args[0])
        emoji = args[1]
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Nem található üzenet ezzel az ID-val ebben a csatornában.")
            return

    else:
        await ctx.send("❌ Érvénytelen formátum.")
        return

    # --- Emoji hozzáadása ---
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        await ctx.send("❌ Hibás emoji vagy nem tudom hozzáadni.")
        return

    # --- Mentés JSON-be ---
    msg_id_str = str(message.id)
    if msg_id_str not in reaction_roles:
        reaction_roles[msg_id_str] = {}
    reaction_roles[msg_id_str][emoji] = role.id
    save_reactions()

    await ctx.send(f"✅ Hozzáadva: {emoji} → {role.name} a(z) {message.jump_url} üzenethez.")

# --- Reaction-role törlés ---
@bot.command(name="reakciotorles")
@commands.has_permissions(manage_roles=True)
async def reactionrole_delete(ctx, first: str = None, second: str = None, emoji: str = None):
    """
    Töröl egy reaction-role párost, vagy ha nincs megadva semmi, az összeset törli.
    - !reakciotorles <üzenet_id> <emoji>
    - !reakciotorles <csatorna_id> <üzenet_id> <emoji>
    - !reakciotorles <üzenet_link> <emoji>
    - !reakciotorles   ← minden reaction-role törlése a szerveren
    """

    # --- NINCS PARAMÉTER → ÖSSZES TÖRLÉSE ---
    @bot.command()
    async def delete_all_reaction_roles(ctx):
    # Ellenőrizzük, van-e bármi törlendő
        if not reaction_roles:  # reaction_roles legyen a te adatstruktúrád
            await ctx.send("❌ Nincsenek elmentett reaction-role beállítások.")
        return

    # Megerősítő embed létrehozása
    embed = discord.Embed(
        title="Reaction-role törlés megerősítés",
        description="Biztosan törölni akarod az összes reaction-role-t a szerveren?",
        color=discord.Color.orange()
    )
    embed.set_footer(text="Válaszd ki a ✅ vagy ❌ emojit a megerősítéshez.")

    confirm_msg = await ctx.send(embed=embed)

    # Reakciók hozzáadása
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    # Várjuk a felhasználó reakcióját
    def check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in ["✅", "❌"]
            and reaction.message.id == confirm_msg.id
        )

    try:
        reaction, user = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏳ Időtúllépés",
            description="A törlés megszakítva, nem érkezett reakció időben.",
            color=discord.Color.red()
        )
        await ctx.send(embed=timeout_embed)
        return

    if str(reaction.emoji) == "✅":
        # Itt töröld a reaction-role adatokat
        reaction_roles.clear()  # Példa: ha egy dict/list tárolja
        success_embed = discord.Embed(
            title="✅ Sikeres törlés",
            description="Az összes reaction-role törlésre került!",
            color=discord.Color.green()
        )
        await ctx.send(embed=success_embed)
    else:
        cancel_embed = discord.Embed(
            title="❌ Törlés megszakítva",
            description="A reaction-role törlés megszakítva.",
            color=discord.Color.red()
        )
        await ctx.send(embed=cancel_embed)


    

# --- Reaction hozzáadás esemény ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    msg_id_str = str(payload.message_id)
    if msg_id_str in reaction_roles:
        emoji = str(payload.emoji)
        if emoji in reaction_roles[msg_id_str]:
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(reaction_roles[msg_id_str][emoji])
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.add_roles(role)
                try:
                    await member.send(f"🎉 Megkaptad a **{role.name}** rangot a **{guild.name}** szerveren!")
                except discord.Forbidden:
                    pass


# --- Reaction eltávolítás esemény ---
@bot.event
async def on_raw_reaction_remove(payload):
    msg_id_str = str(payload.message_id)
    if msg_id_str in reaction_roles:
        emoji = str(payload.emoji)
        if emoji in reaction_roles[msg_id_str]:
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(reaction_roles[msg_id_str][emoji])
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role)
                try:
                    await member.send(f"❌ Elvettük tőled a **{role.name}** rangot a **{guild.name}** szerveren.")
                except discord.Forbidden:
                    pass


# --- Indítás ---
@bot.event
async def on_ready():
    print(f"✅ Bejelentkezve: {bot.user}")


@bot.command(name="reakcioinfo")
@commands.has_permissions(manage_roles=True)
async def reactionroles(ctx):
    """Kiírja az összes reaction-role párosítást a szerveren."""
    if not reaction_roles:
        await ctx.send("❌ Nincsenek beállított reaction-role-ok.")
        return

    embed = discord.Embed(
        title="📋 Reaction Role beállítások",
        color=discord.Color.blurple()
    )

    for msg_id_str, emoji_roles in reaction_roles.items():
        try:
            message = await ctx.fetch_message(int(msg_id_str))
            msg_link = message.jump_url
            value_lines = []
            for emoji, role_id in emoji_roles.items():
                role = ctx.guild.get_role(role_id)
                if role:
                    value_lines.append(f"{emoji} → {role.name}")
                else:
                    value_lines.append(f"{emoji} → (törölt vagy nem elérhető rang)")
            embed.add_field(name=f"Üzenet: [link]({msg_link})", value="\n".join(value_lines), inline=False)
        except discord.NotFound:
            embed.add_field(name=f"Üzenet: {msg_id_str}", value="Nem található üzenet", inline=False)

    await ctx.send(embed=embed)


#---EMLÉKEZTETŐS ÜZENETKÜLDÉS BOTTAL---
@bot.command(name="emlekezteto")
async def emlekezteto(ctx, ido: str, kanal: discord.TextChannel, *, uzenet: str):
    """
    Időzített emlékeztető parancs.
    Használat:
    !emlekezteto 14:30 #csatorna Ez egy fontos emlékeztető!

    A bot egy beágyazott üzenetet küld, majd 5 perccel a megadott időpont előtt
    emlékeztetőt küld a kiválasztott csatornába.
    """
    try:
        # Idő feldolgozása (óra:perc)
        ora, perc = map(int, ido.split(":"))
        most = datetime.now()
        cel_ido = most.replace(hour=ora, minute=perc, second=0, microsecond=0)

        # Ha a megadott idő már elmúlt → holnapra állítjuk
        if cel_ido <= most:
            cel_ido += timedelta(days=1)

        # Embed visszajelzés a beállításról
        embed = discord.Embed(
            title="⏰ Emlékeztető beállítva!",
            description=(
                f"**Üzenet:** {uzenet}\n"
                f"**Időpont:** {cel_ido.strftime('%H:%M')}\n"
                f"**Csatorna:** {kanal.mention}"
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

        # Kiszámoljuk, mikor kell az emlékeztetőt küldeni (5 perccel előtte)
        emlekezteto_ido = cel_ido - timedelta(minutes=5)
        varakozas = (emlekezteto_ido - datetime.now()).total_seconds()

        # Ha túl közel van az időpont → azonnal emlékeztet
        if varakozas <= 0:
            await kanal.send(
                f"🔔 **Emlékeztető!** 5 perc múlva elérkezik az időpont: **{ido}**\n> {uzenet}"
            )
            return

        # Várunk addig
        await asyncio.sleep(varakozas)

        # Emlékeztető üzenet küldése a megadott csatornába
        await kanal.send(
            f"🔔 **Emlékeztető!** 5 perc múlva elérkezik az időpont: **{ido}**\n> {uzenet}"
        )

    except ValueError:
        await ctx.send("⚠️ Helytelen formátum! Használat: `!emlekezteto 14:30 #csatorna Szöveg`")
    except discord.Forbidden:
        await ctx.send("🚫 Nincs jogosultságom üzenetet küldeni abba a csatornába.")
    except Exception as e:
        await ctx.send(f"⚠️ Hiba történt: `{e}`")




# ---HELP PARANCS---
@bot.command(name="helper")
async def help_command(ctx):
    """
    Embed formában listázza az összes bot parancsot, leírással és használattal.
    """

    embed = discord.Embed(
        title="📘 Bot parancsok listája",
        description="Itt találod a bot összes elérhető parancsát, rövid leírással és használati példákkal.",
        color=discord.Color.blurple()
    )

    # --- Moderációs parancsok ---
    embed.add_field(
        name="👢 !kick",
        value=(
            "**Leírás:** Kirúgja a megadott felhasználót a szerverről.\n"
            "**Használat:** `!kick @felhasználó [ok]`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    embed.add_field(
        name="🔨 !ban",
        value=(
            "**Leírás:** Kitiltja a megadott felhasználót a szerverről.\n"
            "**Használat:** `!ban @felhasználó [ok]`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    embed.add_field(
        name="♻️ !unban",
        value=(
            "**Leírás:** Visszaengedi a korábban kitiltott felhasználót.\n"
            "**Használat:** `!unban név#discriminator`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    embed.add_field(
        name="🔇 !mute",
        value=(
            "**Leírás:** Létrehoz (ha még nem létezik) egy `Muted` rangot, és lenémítja a felhasználót.\n"
            "**Használat:** `!mute @felhasználó [ok]`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    embed.add_field(
        name="🔊 !unmute",
        value=(
            "**Leírás:** Feloldja a felhasználó némítását.\n"
            "**Használat:** `!unmute @felhasználó`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 !clear",
        value=(
            "**Leírás:** Tömegesen töröl üzeneteket a csatornából.\n"
            "**Használat:** `!clear [mennyiség]`\n"
            "**Példa:** `!clear 10`\n"
            "**Jogosultság:** Rendszergazda jogosultág"
        ),
        inline=False
    )

    # --- Üzenetküldés ---
    embed.add_field(
        name="💬 !kuld",
        value=(
            "**Leírás:** A bot üzenetet küld egy megadott csatornába.\n"
            "**Használat:** `!kuld <csatorna_id> <üzenet szövege>`\n"
            "**Jogosultság:** Rendszergazda vagy admin jogosultágú szerepkör"
        ),
        inline=False
    )

    embed.add_field(
        name="🖼️ !kuldembed",
        value=(
            "**Leírás:** A bot beágyazott (embed) üzenetet küld egy csatornába.\n"
            "**Használat:** `!kuldembed <csatorna_id> \"<cím>\" <leírás>`\n"
            "**Példa:** `!kuldembed 123456789012345678 \"Figyelem!\" Ez egy teszt üzenet.`\n"
            "**Jogosultság:** Rendszergazda vagy admin jogosultágú szerepkör"
        ),
        inline=False
    )

    # --- Információs parancsok ---
    embed.add_field(
        name="📊 !statisztika",
        value=(
            "**Leírás:** Kiírja a megadott (vagy a parancsot kiadó) tag adatait.\n"
            "**Használat:** `!statisztika [@felhasználó]`\n"
            "**Aliasok:** `!stats`, `!info`"
        ),
        inline=False
    )

    embed.add_field(
        name="🏰 !szerverinfo",
        value=(
            "**Leírás:** Megmutatja a szerver statisztikáit és alapadatait.\n"
            "**Használat:** `!szerverinfo`\n"
            "**Aliasok:** `!serverinfo`, `!guildinfo`"
        ),
        inline=False
    )

    # --- Reaction Role rendszer ---
    embed.add_field(
        name="🎭 !reakciorang",
        value=(
            "**Leírás:** "" Hozzáad egy reaction-role párost egy üzenethez.\n"
            "**Használati variációk 1.:** `!reakciorang <üzenet_id> <emoji> <@rang>`\n"
            "**Használati variációk 2.:** `!reakciorang <csatorna_id> <üzenet_id> <emoji> <@rang>`\n"
            "**Használati variációk 3.:** `!reakciorang <üzenet_link> <emoji> <@rang>`\n"
            "**Jogosultság:** Manage Roles"
        ),
        inline=False
    )

    embed.add_field(
        name="❌ !reakciotorles",
        value=(
            "**Leírás:** "" Töröl egy reaction-role párost, vagy ha nincs megadva semmi, az összeset törli.\n"
            "**Használati variációk 1.:** `!reakciotorles <üzenet_id> <emoji>`\n"
            "**Használati variációk 2.:** `!reakciotorles <csatorna_id> <üzenet_id> <emoji>`\n"
            "**Használati variációk 3.:** `!reakciotorles <üzenet_link> <emoji>`\n"
            "**Használati variációk 4.:** `!reakciotorles   ← minden reaction-role törlése a szerveren`\n"
            "**Jogosultság:** Manage Roles"
        ),
        inline=False
    )

    embed.add_field(
        name="📋 !reakcioinfo",
        value=(
            "**Leírás:** Listázza az összes reaction-role beállítást.\n"
            "**Használat:** `!reakcioinfo`\n"
            "**Jogosultság:** Manage Roles"
        ),
        inline=False
    )

    embed.add_field(
        name="⏰ !emlekezteto",
        value=(
            "**Leírás:** Időpontot készít, amely 5 perccel az idő lejárta előtt újra emlékeztetőt küld a csatornába. .\n"
            "**Használat:** `!emlekezteto 14:30 #csatorna Szöveg`\n"
            "**Jogosultság:** Manage Messages"
        ),
        inline=False
    )
    # --- Help parancs magáról ---
    embed.add_field(
        name="❓ !helper",
        value=(
            "**Leírás:** Kiírja ezt a súgót embed formában.\n"
            "**Használat:** `!helper`"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"Kérte: {ctx.author.display_name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )

    await ctx.send(embed=embed)



# --- Bot indítása ---
bot.run("MTQzNTY2MTI0MzM1MTMwMjIzNQ.GV5E0M.UBnrYdx3jGDpKxkJrn1b2NzZN2urwg0PXh4pbg")
