from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from common import rooms, user_states
from db_spyfall import get_dictionary_name, get_places_for_dictionary
import random

SPY_COUNT = 1


def main_menu():
    game_keyboard = [[KeyboardButton('Запустити голосування')]]
    return ReplyKeyboardMarkup(game_keyboard, resize_keyboard=True)


def spy_menu():
    game_keyboard = [[KeyboardButton('Вгадати карту')]]
    return ReplyKeyboardMarkup(game_keyboard, resize_keyboard=True)


async def process_game(game_id, host_id, context: CallbackContext):
    random_number = random.randint(1, 5)
    spy_index = random.randint(0, len(rooms[game_id]['players']) - 1)

    for index, user_id in enumerate(rooms[game_id]['players']):
        if index == spy_index:
            text = ('Ви шпигун! Ваша ціль - '
                    'вгадати місце перебування інших гравців, '
                    'не видавши самого себе.')

            if user_id == host_id:
                text += ' <b>Ви першим задаєте питання одному із гравців.</b>'

            await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML,
                                           reply_markup=spy_menu())
        else:
            places_str = ', '.join(get_places_for_dictionary(random_number))
            game_map = get_dictionary_name(random_number)
            rooms[game_id]['map'] = game_map

            text = ('<b>Карта:</b>\n'
                    f'{game_map}\n'
                    f'<b>Місця:</b> {places_str}\n'
                    f'Ваша ціль - визначити серед гравців '
                    f'шпигуна, в ході гри шукаючи "своїх" гравців.')

            if user_id == host_id:
                text += ' <b>Ви першим задаєте питання одному із гравців.</b>'

            await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML,
                                           reply_markup=main_menu())


async def handle_game_message(text, user_id, player_list, update: Update, context: CallbackContext):
    player_keyboard = [[InlineKeyboardButton(uname, callback_data=f'select_player_{uname}')] for uname in player_list]
    reply_markup = InlineKeyboardMarkup(player_keyboard)

    if text == 'Запустити голосування':
        await context.bot.send_message(chat_id=user_id,
                                       text='Ви запустили голосування.\n'
                                            'Виберіть гравця, якого вважаєте шпигуном:',
                                       reply_markup=reply_markup)

    elif text == 'Вгадати карту':
        await context.bot.send_message(chat_id=user_id,
                                       text='Введіть назву карти:')
        user_states[user_id]['guess_map'] = True

    else:
        await context.bot.send_message(text='Неправильна команда.', chat_id=user_id)

