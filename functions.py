from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode
from common import user_messages, rooms, START_MARKUP, user_states, games_ban_list
import secrets


def generate_unique_game_id():
    digits = [str(i) for i in range(10)]
    player_id = ''.join(secrets.choice(digits) for _ in range(6))
    return player_id


def get_unique_username(base_username, existing_usernames):
    count = 1
    new_username = base_username
    while new_username in existing_usernames:
        new_username = f"{base_username}({count})"
        count += 1
    return new_username


def get_player_id_by_username(game_id, username):
    players = rooms.get(game_id, {}).get('players', {})
    for player_id, player_data in players.items():
        if player_data.get("username") == username:
            return int(player_id)
    return None


def find_game_id_with_user(user_id):
    for game_id, room in rooms.items():
        if user_id in room.get('players', []):
            return game_id
    return None


def track_user_message(user_id, message):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message.message_id)


async def clear_previous_message(user_id, context: CallbackContext, update: Update, text=None):
    await context.bot.delete_message(chat_id=user_id, message_id=user_messages[user_id][-1])


async def join_game(user_id, game_id, host_id, username, context: CallbackContext):
    user_id_list = [user_id for user_id in rooms[game_id]['players']]
    msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]
    username_list = [player['username'] for player in rooms[game_id]['players'].values()]

    unique_username = get_unique_username(username, username_list)
    rooms[game_id]['players'][user_id] = {'username': unique_username}

    player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())

    if user_id in user_messages:
        await clear_previous_message(user_id, context)

    keyboard = [[InlineKeyboardButton("Вийти", callback_data=f'exit_game_{game_id}')]]
    exit_markup = InlineKeyboardMarkup(keyboard)

    start_message = await context.bot.send_message(chat_id=user_id,
                                                   text='Ласкаво просимо до гри '
                                                        '<b>Знахідка для шпигуна (Spyfall)</b>!\n'
                                                        'Очікуйте початку гри.\n\n'
                                                        'Гравці:\n'
                                                        f'{player_list}',
                                                   parse_mode=ParseMode.HTML,
                                                   reply_markup=exit_markup)

    await update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context)
    rooms[game_id]['players'][user_id]['message_id'] = start_message.message_id
    track_user_message(user_id, start_message)


async def update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context: CallbackContext,
                          deny_game=False, kick_player=False, kicked_player_id=None, ban_player=False, interact=False):
    player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())
    host_username = rooms[game_id]['players'][host_id]['username']

    if deny_game:
        for user_id, msg_id in zip(user_id_list, msg_id_list):
            if user_id != host_id:
                await context.bot.edit_message_text(chat_id=user_id,
                                                    message_id=msg_id,
                                                    text=f'{host_username} відмінив(-ла) гру.',
                                                    reply_markup=START_MARKUP)
        return

    if kick_player:
        if kicked_player_id != host_id:
            for user_id, msg_id in zip(user_id_list, msg_id_list):
                if user_id == kicked_player_id:
                    if ban_player:
                        text = 'Вас заблокували у грі.'
                        host_text = 'Гравця заблоковано.'

                        if game_id not in games_ban_list:
                            games_ban_list[game_id] = []

                        kicked_player_name = rooms[game_id]['players'][kicked_player_id]['username']
                        games_ban_list[game_id].append(kicked_player_name)
                    else:
                        text = 'Вас вигнали зі гри.'
                        host_text = 'Гравця вигнано.'

                    await context.bot.send_message(chat_id=host_id,
                                                   text=host_text)

                    await context.bot.edit_message_text(chat_id=user_id,
                                                        message_id=msg_id,
                                                        text=text,
                                                        reply_markup=START_MARKUP)

                    del rooms[game_id]['players'][kicked_player_id]

            user_id_list = [user_id for user_id in rooms[game_id]['players']]
            player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())
            msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]

            await default_update(host_id, exit_markup, game_id, player_list, user_id_list, msg_id_list,
                                 context, interact=interact)

            await back_to_admin_menu(host_id, context, interact=interact)
            return
        else:
            if ban_player:
                await context.bot.send_message(chat_id=host_id,
                                               text='Ми не можете заблокувати самого себе.')
            else:
                await context.bot.send_message(chat_id=host_id,
                                               text='Ми не можете вигнати самого себе.')
            return

    await default_update(host_id, exit_markup, game_id, player_list, user_id_list, msg_id_list,
                         context)


async def default_update(host_id, exit_markup, game_id, player_list, user_id_list, msg_id_list,
                         context: CallbackContext, interact=False):

    for user_id, msg_id in zip(user_id_list, msg_id_list):
        if user_id == host_id:
            keyboard = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                        [InlineKeyboardButton('Відмінити гру', callback_data=f'deny_game_{game_id}')],
                        [InlineKeyboardButton('Адмін-меню', callback_data=f'admin_menu_{game_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if interact:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                msg = await context.bot.send_message(chat_id=user_id,
                                                     text=f'Після того, як всі зайдуть, натисніть <b>Почати</b>.\n\n'
                                                          f'Гравці:\n'
                                                          f'{player_list}',
                                                     parse_mode=ParseMode.HTML,
                                                     reply_markup=reply_markup
                                                     )
                rooms[game_id]['players'][user_id]['message_id'] = msg.message_id
                track_user_message(user_id, msg)
            else:
                msg = await context.bot.edit_message_text(chat_id=user_id, message_id=msg_id,
                                                          text=f'Після того, як всі зайдуть, '
                                                               f'натисніть <b>Почати</b>.\n\n'
                                                               f'Гравці:\n'
                                                               f'{player_list}',
                                                          parse_mode=ParseMode.HTML,
                                                          reply_markup=reply_markup
                                                          )
                track_user_message(user_id, msg)
        else:
            msg = await context.bot.edit_message_text(chat_id=user_id, message_id=msg_id,
                                                      text='Ласкаво просимо до гри '
                                                           '<b>Знахідка для шпигуна (Spyfall)</b>!\n'
                                                           'Очікуйте початку гри.\n\n'
                                                           'Гравці:\n'
                                                           f'{player_list}',
                                                      parse_mode=ParseMode.HTML,
                                                      reply_markup=exit_markup)
            rooms[game_id]['players'][user_id]['message_id'] = msg.message_id


async def back_to_admin_menu(user_id, context: CallbackContext, interact=False):
    reply_markup = user_states[user_id]['admin_markup']
    text = user_states[user_id]['admin_text']
    message_id = user_states[user_id]['admin_msg_id']

    if 'kick_player' in user_states[user_id]:
        del user_states[user_id]['kick_player']

    if 'ban_player' in user_states[user_id]:
        del user_states[user_id]['ban_player']

    if 'unban_player' in user_states[user_id]:
        del user_states[user_id]['unban_player']

    if interact:
        await context.bot.delete_message(chat_id=user_id, message_id=message_id)
        msg = await context.bot.send_message(text=text, reply_markup=reply_markup,
                                             chat_id=user_id)
        user_states[user_id]['admin_msg_id'] = msg.message_id
    else:
        await context.bot.edit_message_text(text=text, reply_markup=reply_markup,
                                            message_id=message_id, chat_id=user_id)
