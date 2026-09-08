import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
import asyncio
import re

AUTOROLE_ID = 1542415943869931581
user_warns = {}
EMOJIS = ['🛡️', '🛡️', '🛡️', '🛡️', '🛡️']

# Состояния автомодерации
automode_links = True  
automode_chat = True   

bad_words_counters = {}

def get_emoji():
    return "🛡️"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен!')
    try:
        synced = await bot.tree.sync()
        print(f'Успешно синхронизировано слэш-команд: {len(synced)}')
    except Exception as e:
        print(f'Ошибка синхронизации: {e}')

@bot.event
async def on_member_join(member: discord.Member):
    role = member.guild.get_role(AUTOROLE_ID)
    if role:
        try:
            await member.add_roles(role)
            print(f"Автороль @{role.name} выдана пользователю {member.display_name}")
        except Exception as e:
            print(f"Не удалось выдать автороль: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    if automode_links:
        url_pattern = re.compile(r'https?://|www\.|discord\.gg/|discord\.com/invite/')
        if url_pattern.search(content):
            try:
                await message.delete()
                warning = await message.channel.send(f"🛡️ {message.author.mention}, ссылки и приглашения запрещены!")
                await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=4))
                await warning.delete()
                return
            except Exception:
                pass

    if automode_chat:
        bad_words = [
            "сука", "гондон", "пидорас", "пидор", "ебанат", "блядь", "блять", 
            "уебан", "заебал", "заеба", "хуй", "пиздец", "ебать", "еблан", 
            "шлюха", "мразь", "урод", "суки", "хуесос"
        ]
        
        if any(word in content for word in bad_words):
            try:
                await message.delete()
            except Exception:
                pass

            user_id = message.author.id
            if user_id not in bad_words_counters or bad_words_counters[user_id]["date"] != today_str:
                bad_words_counters[user_id] = {"count": 1, "date": today_str}
            else:
                bad_words_counters[user_id]["count"] += 1

            current_count = bad_words_counters[user_id]["count"]

            if current_count < 3:
                try:
                    warning = await message.channel.send(
                        f"🛡️ {message.author.mention}, ваше сообщение было удалено фильтром мата! "
                        f"(Предупреждение **{current_count}/3** на сегодня. Напоминание: после 3 матов в день — мут на 1 день!)"
                    )
                    await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=4))
                    await warning.delete()
                except Exception:
                    pass
            else:
                try:
                    await message.author.timeout(datetime.timedelta(days=1), reason="Превышен лимит матов в день (3/3)")
                    bad_words_counters[user_id]["count"] = 0
                except Exception:
                    pass

                try:
                    dm_embed = discord.Embed(
                        title="🛡️ Наказание за нарушение правил чата",
                        description=(
                            f"Здравствуйте, **{message.author.name}**!\n\n"
                            f"Вы использовали запрещенную лексику **3 раза за сегодня**, "
                            f"что является нарушением правил автомодерации на сервере **{message.guild.name}**.\n\n"
                            f"🔒 Вам был автоматически выдан **мут (таймаут) на 1 день**.\n"
                            f"Пожалуйста, соблюдайте правила общения в чатах!"
                        ),
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    await message.author.send(embed=dm_embed)
                except discord.Forbidden:
                    try:
                        fallback_msg = await message.channel.send(
                            f"🛡️ {message.author.mention}, вы получили 3/3 матов за день и были заглушены на 1 день! 🔒"
                        )
                        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=6))
                        await fallback_msg.delete()
                    except Exception:
                        pass
                return

    await bot.process_commands(message)

class AutomodePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        if automode_links:
            btn_links = discord.ui.Button(label="🔗 Анти-ссылки: Включено", style=discord.ButtonStyle.green, custom_id="toggle_links")
        else:
            btn_links = discord.ui.Button(label="🔗 Анти-ссылки: Отключено", style=discord.ButtonStyle.red, custom_id="toggle_links")
        btn_links.callback = self.links_callback
        self.add_item(btn_links)

        if automode_chat:
            btn_chat = discord.ui.Button(label="🛡️ Анти-мат: Включено", style=discord.ButtonStyle.green, custom_id="toggle_chat")
        else:
            btn_chat = discord.ui.Button(label="🛡️ Анти-мат: Отключено", style=discord.ButtonStyle.red, custom_id="toggle_chat")
        btn_chat.callback = self.chat_callback
        self.add_item(btn_chat)

    async def links_callback(self, interaction: discord.Interaction):
        global automode_links
        automode_links = not automode_links
        self.update_buttons()
        embed = create_automode_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def chat_callback(self, interaction: discord.Interaction):
        global automode_chat
        automode_chat = not automode_chat
        self.update_buttons()
        embed = create_automode_embed()
        await interaction.response.edit_message(embed=embed, view=self)

def create_automode_embed():
    links_status = "🟢 Включено" if automode_links else "🔴 Отключено"
    chat_status = "🟢 Включено" if automode_chat else "🔴 Отключено"
    
    embed = discord.Embed(
        title="🛡️ Меню Авто Модерации",
        description=(
            "Здесь вы можете управлять защитой сервера в реальном времени с помощью кнопок ниже.\n\n"
            f"• **Анти ссылки:** {links_status}\n"
            f"• **Анти мат:** {chat_status}\n\n"
            "📌 *Правило матов: после 3 предупреждений за один день нарушитель автоматически получает мут на 1 день с уведомлением в ЛС!*"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Панель управления защитой сервера")
    return embed

@bot.tree.command(name="automode", description="Открыть меню управления автомодерацией")
@app_commands.checks.has_permissions(administrator=True)
async def automode(interaction: discord.Interaction):
    embed = create_automode_embed()
    view = AutomodePanelView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

def create_warns_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="🛡️ Список варнов сервера:",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    active_warns = {u_id: count for u_id, count in user_warns.items() if count > 0}
    if not active_warns:
        embed.description = "🛡️ **На сервере царит идеальный порядок!**\nНи у одного участника сейчас нет активных предупреждений."
    else:
        lines = []
        for u_id, count in active_warns.items():
            member = guild.get_member(u_id)
            name = member.mention if member else f"ID: {u_id}"
            lines.append(f"• {name} — **{count}/3** варнов")
        embed.description = "\n".join(lines)
    embed.set_footer(text="Авто-обновление списка")
    return embed

class ServerLinksView(discord.ui.View):
    def __init__(self, servers_data):
        super().__init__(timeout=None)
        for name, url in servers_data:
            self.add_item(discord.ui.Button(label=name, url=url, style=discord.ButtonStyle.link))

class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, custom_id=f"role_btn_{role.id}")
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(f"❌ Роль {self.role.mention} была снята с вас!", ephemeral=True)
        else:
            await member.add_roles(self.role)
            await interaction.response.send_message(f"✅ Вам успешно выдана роль {self.role.mention}!", ephemeral=True)

class RoleView(discord.ui.View):
    def __init__(self, roles_data):
        super().__init__(timeout=None)
        for role, label in roles_data:
            if role and label:
                self.add_item(RoleButton(role, label))

@bot.tree.command(name="servers", description="Отправить панель с кнопками для перехода на серверы")
@app_commands.describe(
    н1="Название 1", с1="Ссылка 1", н2="Название 2", с2="Ссылка 2",
    н3="Название 3", с3="Ссылка 3", н4="Название 4", с4="Ссылка 4",
    н5="Название 5", с5="Ссылка 5"
)
@app_commands.check(lambda interaction: interaction.user.id == 1500141349012246549)
async def servers(
    interaction: discord.Interaction, 
    н1: str, с1: str,
    н2: str = None, с2: str = None,
    н3: str = None, с3: str = None,
    н4: str = None, с4: str = None,
    н5: str = None, с5: str = None
):
    raw_servers = [(н1, с1), (н2, с2), (н3, с3), (н4, с4), (н5, с5)]
    servers_list = [(name, url) for name, url in raw_servers if name and url]
    embed = discord.Embed(title="🌐 Навигация по серверам", description="Нажмите на нужную кнопку ниже:", color=discord.Color.blue())
    view = ServerLinksView(servers_list)
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Панель навигации успешно создана!", ephemeral=True)

@bot.tree.command(name="buttonrole", description="Создать панель с кнопками для получения ролей")
@app_commands.describe(
    роль1="Роль 1", кнопка1="Текст 1", роль2="Роль 2", кнопка2="Текст 2",
    роль3="Роль 3", кнопка3="Текст 3", роль4="Роль 4", кнопка4="Текст 4",
    роль5="Роль 5", кнопка5="Текст 5"
)
@app_commands.checks.has_permissions(administrator=True)
async def buttonrole(
    interaction: discord.Interaction, 
    роль1: discord.Role, кнопка1: str,
    роль2: discord.Role = None, кнопка2: str = None,
    роль3: discord.Role = None, кнопка3: str = None,
    роль4: discord.Role = None, кнопка4: str = None,
    роль5: discord.Role = None, кнопка5: str = None
):
    emoji = "🛡️"
    embed = discord.Embed(title="✨ Центр ролей серверов", description=f"{emoji} Нажмите на кнопки ниже для получения ролей:", color=discord.Color.blurple())
    embed.set_footer(text=f"Создал: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    roles_data = [(роль1, кнопка1), (роль2, кнопка2), (роль3, кнопка3), (роль4, кнопка4), (роль5, кнопка5)]
    view = RoleView(roles_data)
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Панель выбора ролей опубликована!", ephemeral=True)

@bot.tree.command(name="warn", description="Выдать предупреждение")
@app_commands.describe(участник="Пользователь", причина="Причина")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, участник: discord.Member, причина: str):
    if участник.top_role >= interaction.user.top_role:
        await interaction.response.send_message("🛡️ Ошибка прав!", ephemeral=True)
        return
    current_warns = user_warns.get(участник.id, 0) + 1
    user_warns[участник.id] = current_warns
    if current_warns < 3:
        msg = f"**Вы получили варн ({current_warns}/3). Причина: {причина}**"
        await interaction.response.send_message(f"🛡️ Пользователю {участник.mention} выдан варн ({current_warns}/3).")
    else:
        await участник.timeout(datetime.timedelta(hours=24), reason=причина)
        msg = "**Вы получили 3/3 варнов и были заглушены на 24 часа 🔒**"
        await interaction.response.send_message(f"🛡️ Пользователь {участник.mention} получил 3/3 варнов и заглушен на 24 часа! 🔒")
    try:
        await участник.send(msg)
    except discord.Forbidden:
        pass

@bot.tree.command(name="unwarn", description="Снять варн")
@app_commands.describe(участник="Пользователь", причина="Причина")
@app_commands.checks.has_permissions(moderate_members=True)
async def unwarn(interaction: discord.Interaction, участник: discord.Member, причина: str):
    current_warns = user_warns.get(участник.id, 0)
    if current_warns <= 0:
        await interaction.response.send_message("🛡️ У пользователя нет варнов!", ephemeral=True)
        return
    current_warns -= 1
    user_warns[участник.id] = current_warns
    await interaction.response.send_message(f"🛡️ С пользователя {участник.mention} снят варн (осталось {current_warns}/3) 🔓")
    try:
        await участник.send("**С вас был снят варн 🔓**")
    except discord.Forbidden:
        pass

@bot.tree.command(name="warns", description="Список варнов")
async def warns(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_warns_embed(interaction.guild))
    message = await interaction.original_response()
    for _ in range(300):
        await asyncio.sleep(1)
        try:
            await message.edit(embed=create_warns_embed(interaction.guild))
        except discord.HTTPException:
            break

@bot.tree.command(name="autorole", description="Установить автороль")
@app_commands.describe(роль="Роль")
@app_commands.checks.has_permissions(manage_roles=True)
async def autorole(interaction: discord.Interaction, роль: discord.Role):
    global AUTOROLE_ID
    AUTOROLE_ID = роль.id
    embed = discord.Embed(description=f"🛡️ Автороль назначена: {роль.mention}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="Информация о боте")
async def info(interaction: discord.Interaction):
    ping = round(bot.latency * 1000)
    embed = discord.Embed(title="🛡️ Волчонок", description=f"Пинг: `{ping}` мс", color=discord.Color.random())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="infobot", description="Список команд")
async def infobot(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ Справка", description="Команды: /servers, /buttonrole, /automode, /warn, /ban, /kick, /mute, /clear", color=discord.Color.random())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Информация о пользователе")
async def userinfo(interaction: discord.Interaction, участник: discord.Member = None):
    target = участник or interaction.user
    embed = discord.Embed(title=f"🛡️ {target.display_name}", color=discord.Color.random())
    embed.add_field(name="ID", value=str(target.id))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Аватар")
async def avatar(interaction: discord.Interaction, участник: discord.Member = None):
    target = участник or interaction.user
    embed = discord.Embed(title="🛡️ Аватар").set_image(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ban", description="Бан")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, участник: discord.Member, причина: str = "Не указана"):
    if участник.top_role >= interaction.user.top_role:
        await interaction.response.send_message("🛡️ Ошибка прав!", ephemeral=True)
        return
    await участник.ban(reason=причина)
    await interaction.response.send_message(f"🛡️ Пользователь {участник.mention} забанен.")

@bot.tree.command(name="unban", description="Разбан")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, тег_или_id: str, причина: str = "Не указана"):
    banned_users = [entry async for entry in interaction.guild.bans()]
    user_to_unban = next((b.user for b in banned_users if тег_или_id in (b.user.name, str(b.user.id))), None)
    if not user_to_unban:
        await interaction.response.send_message("🛡️ Не найден!", ephemeral=True)
        return
    await interaction.guild.unban(user_to_unban, reason=причина)
    await interaction.response.send_message("🛡️ Пользователь разбанен.")

@bot.tree.command(name="kick", description="Кик")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, участник: discord.Member, причина: str = "Не указана"):
    if участник.top_role >= interaction.user.top_role:
        await interaction.response.send_message("🛡️ Ошибка прав!", ephemeral=True)
        return
    await участник.kick(reason=причина)
    await interaction.response.send_message("🛡️ Пользователь выгнан.")

@bot.tree.command(name="mute", description="Мут")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, участник: discord.Member, минуты: int = 10, причина: str = "Не указана"):
    if участник.top_role >= interaction.user.top_role:
        await interaction.response.send_message("🛡️ Ошибка прав!", ephemeral=True)
        return
    await участник.timeout(datetime.timedelta(minutes=минуты), reason=причина)
    await interaction.response.send_message("🛡️ Мут выдал.")

@bot.tree.command(name="clear", description="Очистка")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, количество: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=количество)
    await interaction.followup.send(f"Удалено: {len(deleted)}", ephemeral=True)

@bot.tree.command(name="serverinfo", description="Сервер инфо")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"🛡️ {guild.name}", description=f"Участников: {guild.member_count}")
    await interaction.response.send_message(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        try:
            await interaction.response.send_message("🛡️ У вас недостаточно прав!", ephemeral=True)
        except Exception:
            pass

bot.run('')
