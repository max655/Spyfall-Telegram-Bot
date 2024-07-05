from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode
from common import user_messages, rooms
import secrets


def generate_unique_game_id():
    digits = [str(i) for i in range(10)]
    player_id = ''.join(secrets.choice(digits) for _ in range(6))
    return player_id


def track_user_message(user_id, message):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message.message_id)


async def clear_previous_message(user_id, context):
    await context.bot.delete_message(chat_id=user_id, message_id=user_messages[user_id][-1])


async def join_game(user_id, game_id, host_id, username, context: CallbackContext):
    user_id_list = [user_id for user_id in rooms[game_id]['players']]
    msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]

    rooms[game_id]['players'][user_id] = {'username': username}

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


async def update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context: CallbackContext):
    player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())

    for user_id, msg_id in zip(user_id_list, msg_id_list):
        if user_id == host_id:
            keyboard = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                        [InlineKeyboardButton('Відмінити гру', callback_data=f'deny_game_{game_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.edit_message_text(chat_id=user_id, message_id=msg_id,
                                                text=f'Після того, як всі зайдуть, натисніть <b>Почати</b>.\n\n'
                                                     f'Гравці:\n'
                                                     f'{player_list}',
                                                parse_mode=ParseMode.HTML,
                                                reply_markup=reply_markup
                                                )
        else:
            await context.bot.edit_message_text(chat_id=user_id, message_id=msg_id,
                                                text='Ласкаво просимо до гри '
                                                '<b>Знахідка для шпигуна (Spyfall)</b>!\n'
                                                'Очікуйте початку гри.\n\n'
                                                'Гравці:\n'
                                                f'{player_list}',
                                                parse_mode=ParseMode.HTML,
                                                reply_markup=exit_markup)

