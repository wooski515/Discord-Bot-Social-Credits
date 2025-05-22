import disnake
from disnake.ext import commands
import json
import os
from typing import Optional, Tuple
import re
import datetime # For timeouts

# --- Constants ---
DATA_FILE = "social_credits.json"
FORBIDDEN_STATS_FILE = "forbidden_word_stats.json"

DEFAULT_CREDITS = 1000
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # IMPORTANT: Replace with your bot token!

# Example forbidden pattern (adjust to your needs)
# This example pattern looks for "badword" and its variations
# b_chars = r"[bB8]"
# a_chars = r"[aA@4]"
# d_chars = r"[dD]"
# w_chars = r"[wW]"
# o_chars = r"[oO0]"
# r_chars = r"[rR]"
# FORBIDDEN_PATTERN_REGEX = re.compile(
#     rf"\b{b_chars}{a_chars}{d_chars}\s*{w_chars}{o_chars}{r_chars}{d_chars}\b", # Example: "b4d w0rd"
#     re.IGNORECASE | re.UNICODE
# )
# For now, let's use a simpler placeholder for demonstration. Replace with your actual pattern.
FORBIDDEN_PATTERN_REGEX = re.compile(
    r"\b(examplebadword1|examplebadword2)\b", # Replace with actual words/patterns
    re.IGNORECASE | re.UNICODE
)
FORBIDDEN_WORD_PENALTY = 1000 # Penalty for forbidden words

# --- Embed Colors ---
EMBED_COLOR_SUCCESS = 0x2ecc71 # Green
EMBED_COLOR_ERROR = 0xe74c3c   # Red
EMBED_COLOR_INFO = 0x3498db    # Blue
EMBED_COLOR_PARTY = 0xDAA520   # Gold (Party color)
EMBED_COLOR_WARNING = 0xf1c40f # Orange
EMBED_COLOR_SEVERE_WARNING = 0xc0392b # Dark Red

# --- Ranks and their icons (credits, rank_name, icon, SERVER_ROLE_NAME) ---
# Make sure roles with these names exist on your server!
SOCIAL_RANKS = [
    # (credits, display_name, icon, role_name_on_server)
    (-float('inf'), "Social Outcast", "🚫", "Social Outcast"),
    (0, "Suspicious Citizen", "❓", "Suspicious Citizen"),
    (500, "Ordinary Citizen", "👤", "Ordinary Citizen"),
    (1500, "Model Citizen", "🌟", "Model Citizen"),
    (3000, "Pride of the Party", "🇨🇳", "Pride of the Party"), # Keep the flag for theme if you like
    (5000, "Great Helmsman", "👑", "Great Helmsman")
]

# --- Data Handling Functions ---
def load_generic_data(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except json.JSONDecodeError:
        print(f"JSON decoding error in {filepath}. Returning empty dictionary.")
        return {}

def save_generic_data(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def load_credits_data(): return load_generic_data(DATA_FILE)
def save_credits_data(data): save_generic_data(data, DATA_FILE)

def get_user_credits(guild_id: int, user_id: int) -> int:
    data = load_credits_data()
    return data.get(str(guild_id), {}).get(str(user_id), DEFAULT_CREDITS)

def update_user_credits(guild_id: int, user_id: int, amount: int, add: bool = True) -> Tuple[int, int]:
    data = load_credits_data()
    guild_data = data.setdefault(str(guild_id), {})
    old_credits = guild_data.get(str(user_id), DEFAULT_CREDITS)
    new_val = old_credits + amount if add else amount
    guild_data[str(user_id)] = new_val
    save_credits_data(data)
    return old_credits, new_val

def load_forbidden_stats(): return load_generic_data(FORBIDDEN_STATS_FILE)
def save_forbidden_stats(data): save_generic_data(data, FORBIDDEN_STATS_FILE)
def update_forbidden_stats(guild_id: int, user_id: int, penalty: int):
    stats = load_forbidden_stats()
    guild_stats = stats.setdefault(str(guild_id), {})
    user_stats = guild_stats.setdefault(str(user_id), {"count": 0, "deducted_credits": 0})
    user_stats["count"] += 1; user_stats["deducted_credits"] += penalty
    save_forbidden_stats(stats)

def get_social_rank_info(credits: int) -> Tuple[str, str, Optional[str]]:
    for threshold, display_name, icon, role_name in reversed(SOCIAL_RANKS):
        if credits >= threshold: return f"{icon} {display_name}", display_name, role_name
    default_rank = SOCIAL_RANKS[0]
    return f"{default_rank[2]} {default_rank[1]}", default_rank[1], default_rank[3]


async def manage_user_status_and_roles(
    member: disnake.Member,
    guild: disnake.Guild,
    old_credits: int,
    new_credits: int,
    interaction: Optional[disnake.ApplicationCommandInteraction] = None,
    channel_to_notify: Optional[disnake.TextChannel] = None
):
    """Manages roles and timeouts based on credit changes."""
    # 1. Update roles
    _, __, new_role_name_from_rank = get_social_rank_info(new_credits)
    
    all_rank_role_names = [r[3] for r in SOCIAL_RANKS if r[3]]
    roles_to_remove_objs = [role for role in member.roles if role.name in all_rank_role_names and role.name != new_role_name_from_rank]

    if roles_to_remove_objs:
        try:
            await member.remove_roles(*roles_to_remove_objs, reason="Social rank updated")
        except disnake.Forbidden:
            print(f"No permissions to remove old rank roles from {member.display_name} on server {guild.name}")
        except disnake.HTTPException as e:
            print(f"HTTP error removing roles from {member.display_name}: {e.status} - {e.text}")

    if new_role_name_from_rank:
        role_to_add_obj = disnake.utils.get(guild.roles, name=new_role_name_from_rank)
        if role_to_add_obj:
            if role_to_add_obj not in member.roles:
                try:
                    await member.add_roles(role_to_add_obj, reason=f"New social rank: {new_role_name_from_rank}")
                except disnake.Forbidden:
                    err_msg = f"No permissions to assign role '{new_role_name_from_rank}' to {member.display_name} on {guild.name}. Check hierarchy."
                    if interaction and interaction.response.is_done(): await interaction.followup.send(err_msg, ephemeral=True)
                    elif interaction: await interaction.response.send_message(err_msg, ephemeral=True)
                    elif channel_to_notify: await channel_to_notify.send(err_msg)
                    print(err_msg)
                except disnake.HTTPException as e:
                    print(f"HTTP error assigning role {new_role_name_from_rank} to {member.display_name}: {e.status} - {e.text}")
        else:
            err_msg = f"Role '{new_role_name_from_rank}' not found on server {guild.name}!"
            if interaction and interaction.response.is_done(): await interaction.followup.send(err_msg, ephemeral=True)
            elif interaction: await interaction.response.send_message(err_msg, ephemeral=True)
            elif channel_to_notify: await channel_to_notify.send(err_msg)
            print(err_msg)

    # 2. Manage timeout based on credits
    MAX_DISCORD_TIMEOUT_SECONDS = 28 * 24 * 60 * 60 # Max Discord timeout (28 days)

    if new_credits >= 0:
        if member._communication_disabled_until and member._communication_disabled_until > disnake.utils.utcnow(): 
            try:
                await member.timeout(until=None, reason="Social credit restored, timeout removed.")
                rehab_msg_embed = disnake.Embed(
                    title="✅ AMNESTY: TIMEOUT LIFTED!",
                    description=(
                        f"Citizen {member.mention} has been re-educated! "
                        f"Rating restored to **{new_credits}** Social Credits. Restrictions lifted.\n"
                    ),
                    color=EMBED_COLOR_SUCCESS
                )
                _, __, current_positive_role_name = get_social_rank_info(new_credits)
                if current_positive_role_name:
                    role_obj = disnake.utils.get(guild.roles, name=current_positive_role_name)
                    if role_obj: rehab_msg_embed.add_field(name="New Citizen Status:", value=role_obj.mention)

                if interaction and interaction.response.is_done(): await interaction.followup.send(embed=rehab_msg_embed)
                elif interaction: await interaction.response.send_message(embed=rehab_msg_embed)
                elif channel_to_notify: await channel_to_notify.send(embed=rehab_msg_embed)
            except disnake.Forbidden: print(f"Failed to lift timeout for {member.display_name}. Check permissions.")
            except Exception as e: print(f"Error lifting timeout for {member.display_name}: {e}")
    
    elif new_credits < 0:
        num_negative_thousands = abs(new_credits) // 1000
        calculated_timeout_seconds = 0
        if num_negative_thousands > 0:
            calculated_timeout_seconds = num_negative_thousands * 10 * 60 # 10 minutes per -1000 credits
            calculated_timeout_seconds = min(calculated_timeout_seconds, MAX_DISCORD_TIMEOUT_SECONDS)

        if calculated_timeout_seconds > 0:
            potential_new_timeout_end_dt = disnake.utils.utcnow() + datetime.timedelta(seconds=calculated_timeout_seconds)
            apply_or_update_timeout = False
            reason_for_timeout_update = f"Social Credit: {new_credits}."

            current_timeout_active = member._communication_disabled_until and member._communication_disabled_until > disnake.utils.utcnow()
            if not current_timeout_active:
                apply_or_update_timeout = True
                reason_for_timeout_update = f"Negative social credit ({new_credits}). Timeout applied."
            elif member._communication_disabled_until is None or potential_new_timeout_end_dt > member._communication_disabled_until:
                apply_or_update_timeout = True
                reason_for_timeout_update = f"Worsening social credit ({new_credits}). Timeout extended."

            if apply_or_update_timeout:
                try:
                    await member.timeout(until=potential_new_timeout_end_dt, reason=reason_for_timeout_update)
                    timeout_minutes_display = calculated_timeout_seconds // 60
                    timeout_msg_embed = disnake.Embed(
                        title="🚫 TEMPORARY ISOLATION!",
                        description=(
                            f"Citizen {member.mention} (Rating: {new_credits} Social Credits) has been sent for re-education.\n"
                            f"Timeout for: **{timeout_minutes_display} minutes**."
                        ),
                        color=EMBED_COLOR_SEVERE_WARNING
                    )
                    _, __, current_negative_role_name = get_social_rank_info(new_credits)
                    if current_negative_role_name:
                        role_obj_embed = disnake.utils.get(guild.roles, name=current_negative_role_name)
                        if role_obj_embed: timeout_msg_embed.add_field(name="Assigned Shameful Status:", value=role_obj_embed.mention)
                    
                    if interaction and interaction.response.is_done(): await interaction.followup.send(embed=timeout_msg_embed)
                    elif interaction: await interaction.response.send_message(embed=timeout_msg_embed)
                    elif channel_to_notify: await channel_to_notify.send(embed=timeout_msg_embed)
                    
                    try:
                        dm_embed = disnake.Embed(
                            title="🚨 ISOLATION FROM SOCIETY!",
                            description=f"Comrade {member.name}, your social rating ({new_credits}) has led to isolation "
                                        f"on server **{guild.name}** for **{timeout_minutes_display} minutes**.\n"
                                        "The Party hopes for your swift correction.",
                            color=EMBED_COLOR_SEVERE_WARNING
                        )
                        if current_negative_role_name:
                             role_obj_dm = disnake.utils.get(guild.roles, name=current_negative_role_name)
                             if role_obj_dm: dm_embed.add_field(name="Your Current Status:", value=role_obj_dm.name)
                        await member.send(embed=dm_embed)
                    except disnake.Forbidden: pass
                except disnake.Forbidden:
                    err_msg = f"Failed to apply/update timeout for {member.display_name}. Check permissions and hierarchy."
                    if interaction and interaction.response.is_done(): await interaction.followup.send(err_msg, ephemeral=True)
                    elif interaction: await interaction.response.send_message(err_msg, ephemeral=True)
                    elif channel_to_notify : await channel_to_notify.send(err_msg)
                    print(err_msg)
                except Exception as e:
                    print(f"Unexpected error applying/updating timeout for {member.display_name}: {e}")

# --- Bot Initialization ---
intents = disnake.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!sc "), # You can change this prefix
                   intents=intents,
                   activity=disnake.Activity(type=disnake.ActivityType.watching, name="over the citizens"),
                   status=disnake.Status.online)

@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} is online and serving the Party!")
    if not os.path.exists(DATA_FILE): save_credits_data({})
    if not os.path.exists(FORBIDDEN_STATS_FILE): save_forbidden_stats({})

@bot.event
async def on_message(message: disnake.Message):
    if message.author.bot or not message.guild:
        return

    if not isinstance(message.author, disnake.Member):
        return 

    user: disnake.Member = message.author 
    guild = message.guild

    match = FORBIDDEN_PATTERN_REGEX.search(message.content)
    if match:
        found_expression = match.group(0)
        
        try: await message.delete()
        except disnake.Forbidden: print(f"No permissions to delete message from {user.name} in {guild.name}/{message.channel.name}")
        except Exception as e: print(f"Error deleting message: {e}")

        old_credits, new_credits = update_user_credits(guild.id, user.id, -FORBIDDEN_WORD_PENALTY, add=True)
        update_forbidden_stats(guild.id, user.id, FORBIDDEN_WORD_PENALTY)

        embed_channel = disnake.Embed(
            title="🇨🇳 IDEOLOGICAL SUBVERSION INTERCEPTED!",
            description=(
                f"Citizen {user.mention} used a hostile expression: **'{found_expression}'**.\n"
                f"They are stripped of **{FORBIDDEN_WORD_PENALTY}** Social Credits."
            ),
            color=EMBED_COLOR_SEVERE_WARNING
        )
        embed_channel.add_field(name="Traitor's New Rating:", value=f"**{new_credits}** Social Credits")
        embed_channel.set_footer(text="The Party is vigilant! The enemy will not pass!")
        await message.channel.send(embed=embed_channel)

        await manage_user_status_and_roles(user, guild, old_credits, new_credits, channel_to_notify=message.channel)

        try:
            dm_embed = disnake.Embed(
                title="🚨 SEVERE WARNING!",
                description=(
                    f"Comrade {user.name}, your message on server **'{guild.name}'** contained: `{found_expression}`.\n"
                    f"**{FORBIDDEN_WORD_PENALTY}** Social Credits have been deducted from your account."
                ),
                color=EMBED_COLOR_ERROR
            )
            dm_embed.add_field(name="Your New Rating:", value=f"**{new_credits}** Social Credits")
            await user.send(embed=dm_embed)
        except disnake.Forbidden: pass
        return
    # await bot.process_commands(message) # For prefix-based commands

# --- Slash Commands ---
@bot.slash_command(name="socialcredit", description="Manage and view Social Credits.")
async def social_credit(inter: disnake.ApplicationCommandInteraction): pass

@social_credit.sub_command(name="check", description="Check a citizen's Social Credit score.")
async def check_credits(inter: disnake.ApplicationCommandInteraction, user: Optional[disnake.Member] = None):
    target_user = user or inter.author
    credits_val = get_user_credits(inter.guild.id, target_user.id) # Renamed to avoid conflict
    rank_text, _, rank_role_name = get_social_rank_info(credits_val)
    embed = disnake.Embed(
        title=f"Citizen Social Profile: {target_user.display_name}",
        color=EMBED_COLOR_PARTY
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.add_field(name="Party Rating:", value=f"**{credits_val}** Social Credits", inline=False)
    embed.add_field(name="Status in Society:", value=rank_text, inline=False)
    if rank_role_name:
        actual_role = disnake.utils.get(target_user.roles, name=rank_role_name)
        if actual_role:
            embed.add_field(name="Current Social Role:", value=actual_role.mention, inline=False)
    
    if target_user._communication_disabled_until and target_user._communication_disabled_until > disnake.utils.utcnow():
        timeout_ends_ts = int(target_user._communication_disabled_until.timestamp())
        embed.add_field(name="🚨 IN ISOLATION UNTIL:", value=f"<t:{timeout_ends_ts}:F> (<t:{timeout_ends_ts}:R>)", inline=False)

    embed.set_footer(text="Serve the Party faithfully and diligently!", icon_url=inter.guild.icon.url if inter.guild.icon else None)
    await inter.response.send_message(embed=embed)

@social_credit.sub_command_group(name="admin", description="Administrative directives for Social Credits.")
@commands.has_permissions(administrator=True)
async def admin_credits(inter: disnake.ApplicationCommandInteraction): pass

async def _admin_credit_operation(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, amount: int, is_delta: bool, operation_title: str, operation_key: str):
    if is_delta:
        old_credits, new_credits = update_user_credits(inter.guild.id, user.id, amount, add=True)
    else:
        old_credits = get_user_credits(inter.guild.id, user.id)
        _, new_credits = update_user_credits(inter.guild.id, user.id, amount, add=False)

    rank_text, _, __ = get_social_rank_info(new_credits)
    
    desc_map = {
        "give": f"Citizen {user.mention} has been awarded **{abs(amount)}** Social Credits.",
        "take": f"**{abs(amount)}** Social Credits have been deducted from Citizen {user.mention}.",
        "set": f"Citizen {user.mention}'s Social Credit score has been set to **{amount}**."
    }
    color_map = {"give": EMBED_COLOR_SUCCESS, "take": EMBED_COLOR_ERROR, "set": EMBED_COLOR_INFO}

    embed = disnake.Embed(
        title=operation_title,
        description=desc_map[operation_key],
        color=color_map[operation_key]
    )
    embed.add_field(name="New Rating:", value=f"**{new_credits}** Social Credits", inline=True)
    embed.add_field(name="New Status:", value=rank_text, inline=True)
    embed.set_footer(text=f"Directive executed by: Comrade {inter.author.display_name}", icon_url=inter.author.display_avatar.url)
    
    if not inter.response.is_done(): await inter.response.send_message(embed=embed)
    else: await inter.followup.send(embed=embed)

    await manage_user_status_and_roles(user, inter.guild, old_credits, new_credits, interaction=inter)

    dm_action_text = ""
    if operation_key == "give": dm_action_text = f"you have been awarded **{abs(amount)}**"
    elif operation_key == "take": dm_action_text = f"**{abs(amount)}** have been deducted from your"
    elif operation_key == "set": dm_action_text = f"your rating has been set to **{amount}**"
    if dm_action_text:
        try:
            dm_embed = disnake.Embed(
                title="🇨🇳 Attention from The Party!",
                description=f"On server **{inter.guild.name}**, {dm_action_text} Social Credits.",
                color=color_map[operation_key]
            )
            dm_embed.add_field(name="Your New Rating:", value=f"{new_credits} Social Credits")
            await user.send(embed=dm_embed)
        except disnake.Forbidden: pass

@admin_credits.sub_command(name="give", description="Award Social Credits to a citizen.")
async def give_credits_cmd(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, amount: commands.Range[int, 1, 1000000]):
    await _admin_credit_operation(inter, user, amount, True, "✅ Party Commendation Executed", "give")

@admin_credits.sub_command(name="take", description="Deduct Social Credits from a citizen.")
async def take_credits_cmd(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, amount: commands.Range[int, 1, 1000000]):
    await _admin_credit_operation(inter, user, -amount, True, "❌ Party Sanction Applied", "take")

@admin_credits.sub_command(name="set", description="Set a citizen's exact Social Credit score.")
async def set_credits_cmd(inter: disnake.ApplicationCommandInteraction, user: disnake.Member, amount: int):
    await _admin_credit_operation(inter, user, amount, False, "⚙️ Citizen Rating Adjusted", "set")


@social_credit.sub_command(name="leaderboard", description="Display the honor roll of model Party citizens.")
async def leaderboard(inter: disnake.ApplicationCommandInteraction, top_n: commands.Range[int, 3, 20] = 10):
    await inter.response.defer()
    data = load_credits_data()
    guild_data = data.get(str(inter.guild.id), {})
    if not guild_data:
        embed = disnake.Embed(title="📋 Honor Roll is Empty", description="The Party awaits its heroes!", color=EMBED_COLOR_INFO)
        await inter.followup.send(embed=embed); return

    sorted_users_credits = sorted(guild_data.items(), key=lambda item: item[1], reverse=True)
    embed = disnake.Embed(
        title=f"🏆 Honor Roll of Loyal Party Members - Top {top_n}",
        description=f"Citizens of server **{inter.guild.name}** who the entire nation looks up to!",
        color=EMBED_COLOR_PARTY
    )
    rank_num = 1; displayed_users = 0
    for user_id_str, credits_val_lb in sorted_users_credits: # Renamed credits_val to avoid conflict
        if displayed_users >= top_n: break
        try:
            user_obj = await inter.guild.fetch_member(int(user_id_str))
            if user_obj:
                rank_text_lb, _, __ = get_social_rank_info(credits_val_lb) # Renamed rank_text
                embed.add_field(name=f"#{rank_num} Comrade {user_obj.display_name}", value=f"Rating: **{credits_val_lb}**\nStatus: {rank_text_lb}", inline=False)
                rank_num += 1; displayed_users +=1
        except disnake.NotFound: continue
        except Exception as e: print(f"Error in leaderboard: {e}"); continue
    if displayed_users == 0: embed.description = "No citizens worthy of mention yet."
    embed.set_footer(text="Glory to the Party! Glory to Labor!")
    await inter.followup.send(embed=embed)


@social_credit.sub_command(name="naughtylist", description="List of citizens who have shown ideological instability.")
async def naughty_list(inter: disnake.ApplicationCommandInteraction, top_n: commands.Range[int, 3, 20] = 10):
    await inter.response.defer()
    stats_data = load_forbidden_stats()
    guild_stats = stats_data.get(str(inter.guild.id), {})
    if not guild_stats:
        embed = disnake.Embed(title="📜 List of Ideological Subversives is Empty", description="All citizens are loyal to the Party! This is pleasing.", color=EMBED_COLOR_SUCCESS)
        await inter.followup.send(embed=embed); return

    sorted_violators = sorted(guild_stats.items(), key=lambda item: (item[1]["count"], item[1]["deducted_credits"]), reverse=True)
    embed = disnake.Embed(
        title=f"🚫 Shameful List of Anti-Party Elements - Top {top_n}",
        description=f"Citizens of server **{inter.guild.name}** who have embarked on the path of betrayal:",
        color=EMBED_COLOR_WARNING
    )
    displayed_count = 0
    for user_id_str, user_data in sorted_violators:
        if displayed_count >= top_n: break
        try:
            user_obj = await inter.guild.fetch_member(int(user_id_str))
            if user_obj:
                embed.add_field(
                    name=f"{displayed_count + 1}. Enemy of the People: {user_obj.display_name}",
                    value=(f"🗣️ Caught in anti-Party agitation: **{user_data['count']}** time(s)\n"
                           f"💸 Total fines: **{user_data['deducted_credits']}** Social Credits"),
                    inline=False
                )
                displayed_count += 1
        except disnake.NotFound: continue
        except Exception as e: print(f"Error in naughty list: {e}"); continue
    if displayed_count == 0:
        embed.description = "No ideological subversives detected. Keep it up, Comrades!"
        embed.color = EMBED_COLOR_SUCCESS
    embed.set_footer(text="The Party sees all. Retribution is inevitable.")
    await inter.followup.send(embed=embed)

@admin_credits.error
async def admin_credits_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.MissingPermissions):
        embed = disnake.Embed(title="🚫 Access Denied", description="Only trusted Party officials can execute these directives.", color=EMBED_COLOR_ERROR)
    elif isinstance(error, commands.RangeError):
        embed = disnake.Embed(title="⚠️ Invalid Order", description="The specified amount is outside the permissible range.", color=EMBED_COLOR_ERROR)
    elif isinstance(error, commands.UserInputError) or isinstance(error, commands.BadArgument):
        embed = disnake.Embed(title="⚠️ Error in Directive", description="Please check the entered data, Comrade.", color=EMBED_COLOR_ERROR)
    else:
        print(f"Unexpected error in admin_credits: {error} (type: {type(error)})")
        embed = disnake.Embed(title="🛠️ System Malfunction", description="An error occurred while executing the directive. The technical department has been notified.", color=EMBED_COLOR_ERROR)
    
    if not inter.response.is_done(): await inter.response.send_message(embed=embed, ephemeral=True)
    else: await inter.followup.send(embed=embed, ephemeral=True)


# --- Bot Startup ---
if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("!!! ATTENTION, COMRADE: PROVIDE THE BOT'S SECRET KEY (BOT_TOKEN) !!!")
    else:
        bot.run(BOT_TOKEN)
