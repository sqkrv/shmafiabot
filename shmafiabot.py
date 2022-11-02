import enum
import random
import os
from typing import Union, List

import peewee
import pyrogram
from pyrogram import Client, filters, types

from db import Member, MentionGroup, GroupAffiliation, RestrictedMember

bot = Client('shmafiabot', os.getenv('API_ID'), os.getenv('API_HASH'), bot_token=os.getenv('BOT_TOKEN'))

CHAT_ID = -1001129909206  # shmafia -1001614109246


class PingGroup(enum.Enum):
    ALL = 1
    DORM = 2


# def text_message(regex: str):
#     return filters.regex(regex) & filters.chat(CHAT_ID) & ~filters.edited & ~filters.text


# def text_command(commands: Union[str, List[str]], case_sensitive: bool = False):
#     """
#     Filter for text commands.
#
#     :param commands:
#         hello
#     :param case_sensitive:
#         whether the text case must be equal as well
#     """
#     async def func(flt: text_command, _, update):
#         print(flt.kwargs)
#         print(update)
#         return True
#         # return flt.text == update.data &
#
#     commands = commands if isinstance(commands, list) else [commands]
#     return filters.create(func, commands=commands, case_sensitive=case_sensitive)


def text_command(strings: Union[str, List[str]]):
    return chat_command(strings, prefix='')


def chat_command(commands: Union[str, List[str]], prefix: Union[str, List[str]] = 0):
    kwargs = {}
    if prefix != 0:
        kwargs['prefixes'] = prefix
    return filters.command(commands, **kwargs) & filters.chat(CHAT_ID)# & ~filters.edited


def admin_command(commands: Union[str, List[str]]):
    return chat_command(commands) & filters.user([356786682, ])  # яся,


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


async def set_title(message, chat, author, title):
    for _ in range(2):
        try:
            return await bot.set_administrator_title(
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


# @bot.on_message(filters.chat(CHAT_ID) & filters.new_chat_members)
# async def on_new_member(_, message: types.Message):
#     member = message.new_chat_members[0]
#     await bot.send_message(
#         message.chat.id,
#         f"Привет, {member.first_name}. В чате есть placeholder. Сдохни командой /set."
#     )


@bot.on_message(chat_command(["set_nametag", "change_nametag"]))
async def set_title_command(_, message: types.Message):
    """
    Установить или изменить "плашку".

    :param message:
    :return:
    """
    author = message.from_user

    if RestrictedMember.get_or_none(RestrictedMember.user_id == author.id):
        await message.reply("You are restricted from changing your title.")
        return

    # with open(FILENAME) as file:
    #     restricted = json.load(file)
    #     if author.id in restricted:
    #         await message.reply("You are restricted from changing your title.")
    #         return

    args = message.command[1:]
    if not args:
        await message.reply("Title is not specified.")
        return

    title = ' '.join(args)
    print(title)

    chat = message.chat

    if result := await set_title(message, chat, author, title):
        await message.reply(f"Your title has been successfully set to `{title}`.")
    elif result is False:
        pass
    else:
        await message.reply(f"Something went wrong.")


@bot.on_message(admin_command(["restrict_member", "unrestrict_member"]))
async def un_restrict_member_command(_, message: types.Message):
    """
    Разрешить или запретить участнику устанавливать "плашку"

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
                    RestrictedMember.create(user_id=member.id)
                except peewee.IntegrityError:
                    await message.reply("Specified member is already restricted.")
                    return
            else:
                if not RestrictedMember.delete().where(RestrictedMember.user_id == member.id).execute():
                    await message.reply("Specified member is not restricted.")
                    return
            await message.reply(f"Successfully {'un' if not to_restrict else ''}restricted access to the specified user.")
        else:
            await message.reply(f"No new users have been {'un' if not to_restrict else ''}restricted.")

        # with open(FILENAME, 'r+') as file:
        #     members = json.load(file)
        #     entity = entities[1]
        #     chat = message.chat
        #     if entity.type == 'mention':
        #         offset = entity.offset
        #         member = message.text[offset:offset + entity.length]
        #         try:
        #             member = await chat.get_member(member)
        #         except pyrogram.errors.exceptions.bad_request_400.UserNotParticipant:
        #             await message.reply("Specified user is not a member of this chat.")
        #             return
        #         member = member.user
        #     elif entity.type == 'text_mention':
        #         member = entity.user
        #
        #     if member:
        #         if restrict:
        #             if member.id in members:
        #                 await message.reply("Specified member is already restricted.")
        #                 return
        #             members.append(member.id)
        #         else:
        #             if member.id not in members:
        #                 await message.reply("Specified member is not restricted.")
        #                 return
        #             members.remove(member.id)
        #         file.seek(0)
        #         file.truncate()
        #         json.dump(members, file)
        #         await message.reply(f"Successfully {'un' if not restrict else ''}restricted access to the specified user.")
        #     else:
        #         await message.reply(f"No new users have been {'un' if not restrict else ''}restricted.")


async def ping_all_func(message: types.Message, group: PingGroup):
    chat = message.chat
    match group:
        case PingGroup.DORM:
            # mentions = [bot.get_users(OBSCHAZHNIKI) for user_id in OBSCHAZHNIKI]
            mentions = [user.mention for user in (await bot.get_users(GroupAffiliation.select().where(GroupAffiliation.mention_group_id == 1)))]
            text_part = "отметить общажников"
        case PingGroup.ALL | _:
            mentions = [member.user.mention async for member in chat.get_members() if not member.user.username.endswith('bot')]
            text_part = "всех отметить"

    ping_message = ' '.join(message.command[1:]) if len(message.command) > 1 else None
    mentions_messages = [' '.join(mentions[i:i + 50]) for i in range(0, len(mentions), 50)]  # 50
    if ping_message:
        mentions_messages[0] = ping_message + '\n' + mentions_messages[0]
    else:
        mentions_messages[0] = f"ВНИМАНИЕ❗️❗️❗\n{message.from_user.mention} решил(а) {text_part}\n" + mentions_messages[0]
    for mentions_message in mentions_messages:
        await message.reply(mentions_message)


@bot.on_message(text_command(["@все", "@all"]))
async def ping_all(_, message: types.Message):
    await ping_all_func(message, PingGroup.ALL)


@bot.on_message(text_command("@общажники"))
async def ping_dorm(_, message: types.Message):
    await ping_all_func(message, PingGroup.DORM)


@bot.on_message(text_command("шар"))
async def a8ball(_, message: types.Message):
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

bot.run()
