import asyncio
import enum
import os
import random
import re
from datetime import datetime
from typing import Union, List

import peewee
import pyrogram
from pyrogram import filters, types
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler

from db import GroupAffiliation, RestrictedUser, Config

CHAT_ID = int(os.getenv('CHAT_ID'))


def text_command(strings: Union[str, List[str]]):
    return chat_command(strings, prefix='')


def chat_command(commands: Union[str, List[str]], prefix: Union[str, List[str]] = 0):
    kwargs = {}
    if prefix != 0:
        kwargs['prefixes'] = prefix
    return filters.command(commands, **kwargs) & filters.chat(CHAT_ID)


def amsh_command(strings: Union[str, List[str]]):
    return chat_command(strings, prefix=['амш ', 'Амш ', 'ашм ', 'Ашм '])


def admin_command(commands: Union[str, List[str]]):
    return chat_command(commands) & filters.user([356786682, 633834276, 209007669, 55539711])  # яся, Марьям, дед


class PingGroup(enum.Enum):
    ALL = 1
    DORM = 2


class ConfigKey:
    ANTI_FISHING = 'anti_fishing'
    ANTI_PIPISA_ADS = 'anti_pipisa_ads'


class CrocodileGame:
    has_started = None

class ShmafiaBot:
    def __init__(
            self,
            name: str,
            api_id: Union[int, str] = None,
            api_hash: str = None,
            bot_token: str = None
    ):
        self.name = name
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.bot = None
        self.selfbot = None
        # self.bot = pyrogram.Client(name, api_id, api_hash, bot_token=bot_token)
        # self.selfbot = pyrogram.Client(name+"_selfbot", api_id, api_hash)
        self.config = {
            ConfigKey.ANTI_FISHING: Config.get(Config.key == ConfigKey.ANTI_FISHING),
            ConfigKey.ANTI_PIPISA_ADS: Config.get(Config.key == ConfigKey.ANTI_PIPISA_ADS),
        }
        self.current_antipair = None
        self.ANTIPAIR_TIMEDELTA = 6

    async def _set_title(self, message, chat, author, title):
        for _ in range(2):
            try:
                return await self.bot.set_administrator_title(
                    chat_id=chat.id,
                    user_id=author.id,
                    title=title
                )
            except pyrogram.errors.exceptions.bad_request_400.ChatAdminRequired:
                await message.reply("Не смог установить плашку."
                                    "\nВозможные причины:"
                                    "\n- Я не удминистратор"
                                    "\n- У меня нет прав на добавление новых администраторов"
                                    "\n- Вы уже являетесь администратором. Попросить снять с себя роль")
                return False
            except pyrogram.errors.exceptions.bad_request_400.UserCreator:
                await message.reply("Я не могу установить Вашу плашку")
                return False
            except pyrogram.errors.exceptions.bad_request_400.AdminRankInvalid:
                await message.reply("У Вас плашка длиннее 16 символов или просто неправильная")
                return False
            except ValueError:
                result = await chat.promote_member(
                    user_id=author.id,
                    privileges=types.ChatPrivileges(
                        can_manage_chat=False,
                        # can_invite_users=False
                    )
                )
                print(repr(result))

    # @bot.on_message(chat_command(["set_nametag", "change_nametag"]))
    async def set_title_command(self, _, message: types.Message):
        """
        Установить или изменить плашку.

        :param message:
        :return:
        """
        author = message.from_user

        if RestrictedUser.get_or_none(RestrictedUser.user_id == author.id):
            await message.reply("Вам запретили изменять плашку")
            return

        args = message.command[1:]
        if not args:
            await message.reply("Не указано название плашки.")
            return

        title = ' '.join(args)

        chat = message.chat

        if result := await self._set_title(message, chat, author, title):
            await message.reply(f"Ваша плашка была успешно изменена на `{title}`.")
        elif result is False:
            print('idk')
        else:
            print(result)
            await message.reply(f"Что-то пошло не так, попробуйте снова")

    # @bot.on_message(admin_command(["restrict_member", "unrestrict_member"]))
    async def un_restrict_member_command(self, _, message: types.Message):
        """
        Разрешить или запретить участнику изменять плашку

        :param message:
        :return:
        """
        if entities := message.entities:
            if len(entities) < 2:
                await message.reply("Пользователь не указан", quote=True)
                return

            to_restrict = False if message.command[0].startswith('un') else True
            entity = entities[1]
            chat = message.chat
            member = None

            if entity.type == pyrogram.enums.MessageEntityType.MENTION:
                offset = entity.offset
                member = message.text[offset:offset + entity.length]
                try:
                    member = await chat.get_member(member)
                except pyrogram.errors.exceptions.bad_request_400.UserNotParticipant:
                    await message.reply("Указанный пользователь не является участником чата.")
                    return
                else:
                    member = member.user
            elif entity.type == pyrogram.enums.MessageEntityType.TEXT_MENTION:
                member = entity.user

            if member:
                if to_restrict:
                    try:
                        RestrictedUser.create(user_id=member.id)
                    except peewee.IntegrityError:
                        await message.reply("Указанный пользователь уже ограничен")
                        return
                else:
                    if not RestrictedUser.delete().where(RestrictedUser.user_id == member.id).execute():
                        await message.reply("Указанный пользователь не ограничен")
                        return
                await message.reply("Пользователь успешено был ограничен" if to_restrict else "С пользователя успешно были сняты ограничения")
            else:
                await message.reply(f"Пользователь не найден")

    async def ping_func(self, message: types.Message, group: PingGroup):
        chat = message.chat
        all_members = [member async for member in chat.get_members() if not (member.user.username.lower().endswith('bot') if member.user.username else False)]
        match group:
            case PingGroup.DORM:
                mentions = [member.user.mention for member in all_members if GroupAffiliation.get_or_none(GroupAffiliation.user_id == member.user.id)]
                text_part = "отметить общажников"
            case PingGroup.ALL | _:
                mentions = [member.user.mention for member in all_members]
                text_part = "всех отметить"

        ping_message = ' '.join(message.command[1:]) if len(message.command) > 1 else None
        mentions_messages = [' '.join(mentions[i:i + 50]) for i in range(0, len(mentions), 50)]  # 50
        if ping_message:
            mentions_messages[0] = ping_message + '\n' + mentions_messages[0]
        else:
            mentions_messages[0] = f"ВНИМАНИЕ❗️❗️❗\n{message.from_user.mention} решил(а) {text_part}\n" + mentions_messages[0]
        for mentions_message in mentions_messages:
            await message.reply(mentions_message)

    # @bot.on_message(text_command(["@все", "@all"]))
    async def ping_all(self, _, message: types.Message):
        await self.ping_func(message, PingGroup.ALL)

    # @bot.on_message(text_command("@общажники"))
    async def ping_dorm(self, _, message: types.Message):
        await self.ping_func(message, PingGroup.DORM)

    # @bot.on_message(text_command("шар"))
    async def a8ball(self, _, message: types.Message):
        if len(message.command) < 2:
            await message.reply("Я не вижу вопроса", quote=True)
            return

        ball_answers = [
            "Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да", "Можешь быть уверен в этом",
            "Мне кажется — «да»", "Вероятнее всего", "Хорошие перспективы", "Знаки говорят — «да»", "Да",
            "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать", "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять",
            "Даже не думай", "Мой ответ — «нет»", "По моим данным — «нет»", "Перспективы не очень хорошие", "Весьма сомнительно"
        ]
        await message.reply(random.choice(ball_answers), quote=True)

    # @bot.on_message(filters.regex(r"^🎣 \[Рыбалка\] 🎣") & filters.user(200164142) & filters.chat(CHAT_ID))
    async def fishing_msg_deletion(self, _, message: types.Message):
        if not self.config[ConfigKey.ANTI_FISHING]:
            return

        message._client = self.bot
        if you_receive := re.search(r"Вы получаете (.+)", message.text):
            you_receive = you_receive[1]
        if energy_left := re.search(r"Энергии осталось: (.+)", message.text):
            energy_left = energy_left[1]
        if you_receive and energy_left:
            text = f"{you_receive}\n{energy_left}"
        elif energy_left:
            text = f"ничего\n{energy_left}"
        else:
            text = f"нет энергии"

        await message.reply(text)
        await message.delete()

    # @bot.on_message(filters.media & filters.user(1264548383) & filters.chat(CHAT_ID))
    async def pipisa_bot_ad_remover(self, _, message: types.Message):
        if not self.config[ConfigKey.ANTI_PIPISA_ADS]:
            return

        message._client = self.bot
        await message.delete()
        await message.reply("тут была реклама @pipisabot, а может быть Ваша")

    def toggle_config_variable(self, key: Union[str, ConfigKey]) -> bool:
        toggled = not self.config[key]
        self.config[key] = toggled
        Config.update(value=toggled).where(Config.key == key).execute()
        return toggled

    # @bot.on_message(chat_command("config"))
    async def config_command(self, _, message: types.Message):
        if len(message.command) < 2:
            await message.reply("Не указаны параметры. Параметры для изменения:\n"
                                f"• {ConfigKey.ANTI_FISHING} — режим анти-рыбалки\n"
                                f"• {ConfigKey.ANTI_PIPISA_ADS} — режим анти-рекламы пиписы", quote=True)
            return

        match message.command[1]:
            case ConfigKey.ANTI_FISHING:
                state = self.toggle_config_variable(ConfigKey.ANTI_FISHING)
                await message.reply(f"Режим анти-рыбалки {'включен' if state else 'отключен'}")
                return
            case ConfigKey.ANTI_PIPISA_ADS:
                state = self.toggle_config_variable(ConfigKey.ANTI_PIPISA_ADS)
                await message.reply(f"Режим анти-рекламы пиписы {'включен' if state else 'отключен'}")
                return
            case _:
                pass

    async def help_command(self, _, message: types.Message):
        await message.reply("• **/set_nametag** (**/change_nametag**) — установить/изменить плашку\n"
                            "• **/[un]restrict_member** — запретить/разрешить участнику изменять плашку\n"
                            "• **@__<группа>__** — упомянуть определенную группу участников\n"
                            "• **шар** __<вопрос>__ — спросить мнение у шара\n"
                            "• **амш d20** — кинуть d20\n"
                            "• **амш кто** __[описание]__ — выбрать случайного участника\n"
                            "• **амш антипара дня** — выбрать антипару дня\n"
                            "• **/config** — настроить бота\n"
                            "• **/help** — эта помощь\n\n"
                            "||по всем вопросам, замечаниям и предложениям — @sqkrv||", parse_mode=ParseMode.MARKDOWN)

    async def d20(self, _, message: types.Message):
        await message.reply(f"{random.choice(['У Вас выпало', 'На ребре', 'Выпало', 'Вы открыли глаза. На ребре'])} **{str(random.randint(1, 20))}**", quote=True, parse_mode=ParseMode.MARKDOWN)

    async def whos_today(self, _, message: types.Message):
        random_member = random.choice([member async for member in message.chat.get_members() if not (member.user.username.lower().endswith('bot') if member.user.username else False)])
        if len(message.command) > 2:  # because the first (0) element is 'амш кто'
            await message.reply(f"{random_member.user.mention} {' '.join(message.command[1:])}")
        else:
            await message.reply(f"-> {random_member.user.mention} <-")

    async def antipair(self, _, message: types.Message):
        antipair_code = str(datetime.today().day) + str(datetime.now().hour // self.ANTIPAIR_TIMEDELTA + 1)
        if not self.current_antipair or antipair_code != self.current_antipair[0]:
            random_members = random.sample([member async for member in message.chat.get_members() if not (member.user.username.lower().endswith('bot') if member.user.username else False)], 2)
            self.current_antipair = (antipair_code, tuple(random_members))
        antipair_strings: List[str] = [
            "💔 {0[0].user.mention} + {0[1].user.mention} 💔",
            "{0[0].user.mention} + {0[1].user.mention} += 💔",
        ]
        antipair_comments: List[str] = [
            f"Следующую антипару можно будет выбрать в <b>{(datetime.now().hour // self.ANTIPAIR_TIMEDELTA + 1) * self.ANTIPAIR_TIMEDELTA}:00</b> по МСК",
            "Не стоит вам встречаться",
            "Не водитесь вместе",
            "Будет интересно, если вы уже пара",
            "А пара дня какая?",
            "Чем же вы так не угодили друг другу",
        ]
        await message.reply("<b>АнтиПара дня</b>\n\n" +
                            random.choice(antipair_strings).format(self.current_antipair[1]) + '\n\n' +
                            random.choice(antipair_comments), parse_mode=ParseMode.HTML)

    async def crocodile_start(self, _, message: types.Message):
        pass

    def run(self):
        async def run():
            self.bot = pyrogram.Client(self.name, self.api_id, self.api_hash, bot_token=self.bot_token)
            self.selfbot = pyrogram.Client(self.name + "_selfbot", self.api_id, self.api_hash)
            self.bot.add_handler(MessageHandler(self.set_title_command, chat_command(["set_nametag", "change_nametag"])))
            self.bot.add_handler(MessageHandler(self.un_restrict_member_command, admin_command(["restrict_member", "unrestrict_member"])))
            self.bot.add_handler(MessageHandler(self.ping_all, text_command(["@все", "@all", "@типавсе"])))
            self.bot.add_handler(MessageHandler(self.ping_dorm, text_command(["@общажники", "@общага"])))
            self.bot.add_handler(MessageHandler(self.a8ball, text_command("шар")))
            self.bot.add_handler(MessageHandler(self.config_command, chat_command("config")))
            self.bot.add_handler(MessageHandler(self.help_command, filters.command("help")))
            self.bot.add_handler(MessageHandler(self.d20, amsh_command("d20")))
            self.bot.add_handler(MessageHandler(self.whos_today, amsh_command("кто")))
            self.bot.add_handler(MessageHandler(self.antipair, amsh_command("антипара дня")))
            self.selfbot.add_handler(MessageHandler(self.fishing_msg_deletion, filters.regex(r"^🎣 \[Рыбалка\] 🎣") & filters.user(200164142) & filters.chat(CHAT_ID)))
            self.selfbot.add_handler(MessageHandler(self.pipisa_bot_ad_remover, (filters.reply_keyboard | filters.inline_keyboard) & filters.user(1264548383) & filters.chat(CHAT_ID)))
            print("Starting bot(s)...")
            # self.bot.run()
            # self.selfbot.run()

            await pyrogram.compose([self.bot, self.selfbot])

        asyncio.run(run())

# bot.run()
