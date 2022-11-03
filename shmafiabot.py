import asyncio
import enum
import os
import random
import re
from typing import Union, List

import peewee
import pyrogram
from pyrogram import filters, types
from pyrogram.handlers import MessageHandler

from db import User, GroupAffiliation, RestrictedUser, Config

# bot = Client('shmafiabot', os.getenv('API_ID'), os.getenv('API_HASH'), bot_token=os.getenv('BOT_TOKEN'))

CHAT_ID = -1001129909206  # shmafia -1001614109246


def text_command(strings: Union[str, List[str]]):
    return chat_command(strings, prefix='')


def chat_command(commands: Union[str, List[str]], prefix: Union[str, List[str]] = 0):
    kwargs = {}
    if prefix != 0:
        kwargs['prefixes'] = prefix
    return filters.command(commands, **kwargs) & filters.chat(CHAT_ID)


def admin_command(commands: Union[str, List[str]]):
    return chat_command(commands) & filters.user([356786682, 633834276, 209007669])  # яся, Марьям, дед


class PingGroup(enum.Enum):
    ALL = 1
    DORM = 2


class ConfigKey(enum.Enum):
    ANTI_FISHING = 'anti_fishing'
    ANTI_PIPISA_ADS = 'anti_pipisa_ads'


async def promote_member(chat, author):
    await chat.promote_member(
        user_id=author.id,
        can_manage_chat=False,
        can_change_info=False,
        can_delete_messages=False,
        can_restrict_members=False,
        can_invite_users=True,
        can_promote_members=False,
        can_manage_voice_chats=False
    )


class ShmafiaBot:
    def __init__(
            self,
            name: str,
            api_id: Union[int, str] = None,
            api_hash: str = None,
            bot_token: str = None
    ):
        self.bot = pyrogram.Client(name, api_id, api_hash, bot_token=bot_token)
        self.config = {
            ConfigKey.ANTI_FISHING: Config.get(Config.key == ConfigKey.ANTI_FISHING),
            ConfigKey.ANTI_PIPISA_ADS: Config.get(Config.key == ConfigKey.ANTI_PIPISA_ADS),
        }

    async def _set_title(self, message, chat, author, title):
        for _ in range(2):
            try:
                return await self.bot.set_administrator_title(
                    chat_id=chat.id,
                    user_id=author.id,
                    title=title
                )
            except pyrogram.errors.exceptions.bad_request_400.ChatAdminRequired:
                await message.reply("Couldn't set the title."
                                    "\nOne of these is a reason:"
                                    "\n- I am not an administrator"
                                    "\n- I cannot add new administrators"
                                    "\n- You are already an administrator. Ask an admin to dismiss you.")
                return False
            except pyrogram.errors.exceptions.bad_request_400.UserCreator:
                await message.reply("I cannot set your title, creator.")
                return False
            except pyrogram.errors.exceptions.bad_request_400.AdminRankInvalid:
                await message.reply("Your title is invalid or is longer than 16 characters.")
                return False
            except ValueError:
                await promote_member(chat, author)

    # @bot.on_message(chat_command(["set_nametag", "change_nametag"]))
    async def set_title_command(self, _, message: types.Message):
        """
        Установить или изменить "плашку".

        :param message:
        :return:
        """
        author = message.from_user

        if RestrictedUser.get_or_none(RestrictedUser.user_id == author.id):
            await message.reply("You are restricted from changing your title.")
            return

        args = message.command[1:]
        if not args:
            await message.reply("Title is not specified.")
            return

        title = ' '.join(args)
        print(title)

        chat = message.chat

        if result := await self._set_title(message, chat, author, title):
            await message.reply(f"Your title has been successfully set to `{title}`.")
        elif result is False:
            pass
        else:
            await message.reply(f"Something went wrong.")

    # @bot.on_message(admin_command(["restrict_member", "unrestrict_member"]))
    async def un_restrict_member_command(self, _, message: types.Message):
        """
        Разрешить или запретить участнику изменять "плашку"

        :param message:
        :return:
        """
        if entities := message.entities:
            if len(entities) < 2:
                await message.reply("No arguments provided", quote=True)
                return

            to_restrict = False if message.command[0].startswith('un') else True
            entity = entities[1]
            chat = message.chat
            member = None

            if entity.type == 'mention':
                offset = entity.offset
                member = message.text[offset:offset + entity.length]
                try:
                    member = await chat.get_member(member)
                except pyrogram.errors.exceptions.bad_request_400.UserNotParticipant:
                    await message.reply("Specified user is not a member of this chat.")
                    return
                member = member.user
            elif entity.type == 'text_mention':
                member = entity.user

            if member:
                if to_restrict:
                    try:
                        RestrictedUser.create(user_id=member.id)
                    except peewee.IntegrityError:
                        await message.reply("Specified member is already restricted.")
                        return
                else:
                    if not RestrictedUser.delete().where(RestrictedUser.user_id == member.id).execute():
                        await message.reply("Specified member is not restricted.")
                        return
                await message.reply(f"Successfully {'un' if not to_restrict else ''}restricted access to the specified user.")
            else:
                await message.reply(f"No new users have been {'un' if not to_restrict else ''}restricted.")

    async def ping_func(self, message: types.Message, group: PingGroup):
        chat = message.chat
        match group:
            case PingGroup.DORM:
                mentions = [user.mention for user in
                            (await self.bot.get_users([_.user_id_id for _ in GroupAffiliation.select(GroupAffiliation.user_id_id).join(User).where(GroupAffiliation.mention_group_id == 1 & User.member)]))]
                text_part = "отметить общажников"
            case PingGroup.ALL | _:
                mentions = [member.user.mention async for member in chat.get_members() if not member.user.username.lower().endswith('bot')]
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
        await asyncio.sleep(1)
        await message.delete()

    # @bot.on_message(filters.media & filters.user(1264548383) & filters.chat(CHAT_ID))
    async def pipisa_bot_ad_remover(self, _, message: types.Message):
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
            await message.reply("Не указаны параметры", quote=True)
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

    def run(self):
        self.bot.add_handler(MessageHandler(self.set_title_command, chat_command(["set_nametag", "change_nametag"])))
        self.bot.add_handler(MessageHandler(self.un_restrict_member_command, admin_command(["restrict_member", "unrestrict_member"])))
        self.bot.add_handler(MessageHandler(self.ping_all, text_command(["@все", "@all"])))
        self.bot.add_handler(MessageHandler(self.ping_dorm, text_command("@общажники")))
        self.bot.add_handler(MessageHandler(self.a8ball, text_command("шар")))
        self.bot.add_handler(MessageHandler(self.fishing_msg_deletion, filters.regex(r"^🎣 \[Рыбалка\] 🎣") & filters.user(200164142) & filters.chat(CHAT_ID)))
        self.bot.add_handler(MessageHandler(self.pipisa_bot_ad_remover, (filters.reply_keyboard | filters.inline_keyboard) & filters.user(1264548383) & filters.chat(CHAT_ID)))
        self.bot.add_handler(MessageHandler(self.config_command, chat_command("config")))
        print("Starting bot...")
        self.bot.run()

# bot.run()
