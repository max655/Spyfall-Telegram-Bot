from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove)
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from common import rooms, user_states, voted_users, vote_counts, START_MARKUP, games_ban_list
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


async def kick_player_from_game(game_id, player_id_list, context: CallbackContext):
    if game_id in vote_counts:
        kicked_player = max(vote_counts[game_id], key=vote_counts[game_id].get)
        vote_count = vote_counts[game_id][kicked_player]

        kicked_player_id = None
        for user_id, player_dict in rooms[game_id]['players'].items():
            if player_dict['username'] == kicked_player:
                kicked_player_id = user_id

        game_over = False
        for player_id in player_id_list:
            await context.bot.send_message(text=f'Голосування завершено! Виганяємо гравця '
                                                f'{kicked_player}, '
                                                f'проголосували: {vote_count}',
                                           chat_id=player_id)

            if 'spy' in rooms[game_id]['players'][kicked_player_id]:
                await context.bot.send_message(text=f'Гра завершена! Гравець {kicked_player} був шпигуном.',
                                               chat_id=player_id)
                game_over = True

                if player_id != kicked_player_id:
                    await context.bot.send_message(chat_id=player_id,
                                                   text='Кінець гри.\n'
                                                        'Створіть нову гру або '
                                                        'приєднайтеся до іншої гри, щоб почати знову.',
                                                   reply_markup=ReplyKeyboardRemove())

                    await context.bot.send_message(chat_id=player_id,
                                                   text='Стартове меню:',
                                                   reply_markup=START_MARKUP)
            else:
                await context.bot.send_message(text=f'Гра продовжується! Гравець {kicked_player} був звичайним гравцем.',
                                               chat_id=player_id)

        del rooms[game_id]['players'][kicked_player_id]

        if game_id not in games_ban_list:
            games_ban_list[game_id] = []

        games_ban_list[game_id].append(kicked_player)

        await context.bot.send_message(chat_id=kicked_player_id, text='Вас вигнали зі гри.',
                                       reply_markup=ReplyKeyboardRemove())

        await context.bot.send_message(chat_id=kicked_player_id,
                                       text='Стартове меню:',
                                       reply_markup=START_MARKUP)

        if game_over:
            del rooms[game_id]
        else:
            del rooms[game_id]['voting']
            
        del voted_users[game_id]
        del vote_counts[game_id]
    else:
        for player_id in player_id_list:
            await context.bot.send_message(text=f'Голосування завершено! Ніхто не проголосував.\n'
                                                f'Гра продовжується.',
                                           chat_id=player_id)

        del rooms[game_id]['voting']
        del voted_users[game_id]
