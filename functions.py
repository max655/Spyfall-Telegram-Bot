from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode
from common import user_states, user_messages, room, games, EXIT_MARKUP


def track_user_message(user_id, message):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message.message_id)


async def clear_previous_message(user_id, context):
    await context.bot.delete_message(chat_id=user_id, message_id=user_messages[user_id][-1])


async def join_game(user_id, username, context: CallbackContext):

    room[user_id] = {}
    room[user_id]['username'] = username

    player_list = "\n".join(player['username'] for player in room.values())

    if user_id in user_messages:
        await clear_previous_message(user_id, context)

    start_message = await context.bot.send_message(chat_id=user_id,
                                                   text='Ласкаво просимо до гри '
                                                        '<b>Знахідка для шпигуна (Spyfall)</b>!\n'
                                                        'Очікуйте початку гри.\n\n'
                                                        'Гравці:\n'
                                                        f'{player_list}',
                                                   parse_mode=ParseMode.HTML,
                                                   reply_markup=EXIT_MARKUP)

    games[user_id] = {}
    games[user_id]['message_id'] = start_message.message_id
    track_user_message(user_id, start_message)
