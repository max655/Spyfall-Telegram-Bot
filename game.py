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
    game_keyboard = [[KeyboardButton('Запустити голосування')],
                     [KeyboardButton('Вгадати карту')]]
    return ReplyKeyboardMarkup(game_keyboard, resize_keyboard=True)


async def process_game(game_id, host_id, context: CallbackContext):
    random_number = random.randint(1, 5)
    spy_index = random.randint(0, len(rooms[game_id]['players']) - 1)

    for index, user_id in enumerate(rooms[game_id]['players']):
        if index == spy_index:
            text = ('Ви шпигун! Ваша ціль - '
                    'вгадати місце перебування інших гравців, '
                    'не видавши самого себе.')

            rooms[game_id]['players'][user_id]['spy'] = True

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


async def handle_game_message(game_id, text_bot, user_id, username, player_id_list,
                              context: CallbackContext):

    if text_bot == 'Запустити голосування':
        rooms[game_id]['voting'] = True

        for game_player_id in player_id_list:
            player_list = [player['username'] for player_id, player in rooms[game_id]['players'].items()
                           if player_id != game_player_id]
            player_keyboard = [[InlineKeyboardButton(uname, callback_data=f'select_player_{uname}')] for uname in
                               player_list]
            pass_option = [InlineKeyboardButton('Пропустити хід', callback_data=f'skip_turn_{game_player_id}')]
            player_keyboard.append(pass_option)

            reply_markup = InlineKeyboardMarkup(player_keyboard)

            if game_player_id == user_id:
                text_1 = 'Ви запустили голосування.'
                text_2 = '\nВиберіть гравця, якого вважаєте шпигуном або пропустіть хід:'
                text_3 = '\nОберіть гравця або пропустіть хід:'

                if 'spy' in rooms[game_id]['players'][game_player_id]:
                    text = text_1 + text_3
                else:
                    text = text_1 + text_2

            else:
                text_1 = f'{username} запустив(-ла) голосування.'
                text_2 = '\nВиберіть гравця, якого вважаєте шпигуном або пропустіть хід:'
                text_3 = '\nОберіть гравця або пропустіть хід:'

                if 'spy' in rooms[game_id]['players'][game_player_id]:
                    text = text_1 + text_3
                else:
                    text = text_1 + text_2

            await context.bot.send_message(chat_id=game_player_id,
                                           text=text,
                                           reply_markup=reply_markup)

    elif text_bot == 'Вгадати карту':
        await context.bot.send_message(chat_id=user_id,
                                       text='Введіть назву карти:')
        user_states[user_id]['guess_map'] = True

    else:
        await context.bot.send_message(text='Неправильна команда.', chat_id=user_id)
