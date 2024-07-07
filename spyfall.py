import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode
from db_spyfall import fetch_table, get_dictionary_name, get_places_for_dictionary
from common import (user_states, user_messages, rooms, START_KEYBOARD, START_MARKUP, BACK_MARKUP, games_ban_list,
                    start_messages)
from functions import (clear_previous_message, track_user_message, join_game, update_messages,
                       generate_unique_game_id, get_player_id_by_username, back_to_admin_menu,
                       find_game_id_with_user)
import copy


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: CallbackContext) -> None:
    args = context.args
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.first_name

    if len(args) == 0:
        if not (any(user_id in room['players'] for room in rooms.values())):

            if user_id in start_messages:
                await context.bot.delete_message(message_id=start_messages[user_id][0],
                                                 chat_id=user_id)

            start_message = await context.bot.send_message(chat_id=user_id,
                                                           text="Вітаємо вас у боті зі грою "
                                                                "<b>Знахідка для шпигуна (Spyfall)</b>!\n"
                                                                "Створіть гру, щоб запросити своїх друзів.",
                                                           reply_markup=START_MARKUP,
                                                           parse_mode=ParseMode.HTML)
            track_user_message(user_id, start_message)
            user_states[user_id] = {}
            start_messages[user_id] = []
            start_messages[user_id].append(start_message.message_id)
        else:
            game_id = find_game_id_with_user(user_id)
            host_id = rooms[game_id]['host_id']

            if user_id == host_id:
                callback_data = f'deny_game_{game_id}'
            else:
                callback_data = f'exit_game_{game_id}'

            keyboard = [[InlineKeyboardButton("Вийти", callback_data=callback_data)]]
            exit_markup = InlineKeyboardMarkup(keyboard)

            text = 'Вийдіть зі гри, якщо хочете почати спочатку.'

            if user_id in user_messages:
                try:
                    if 'exit_markup' in user_states[user_id]:
                        await clear_previous_message(user_id, context, update, text=text)
                except BadRequest:
                    pass

            msg = await context.bot.send_message(chat_id=user_id, text=text,
                                                 reply_markup=exit_markup)
            track_user_message(user_id, msg)
            user_states[user_id]['exit_markup'] = exit_markup

        return

    index_non_digit = text.index('g')

    host_id = int(text[7:index_non_digit])
    game_id = text[index_non_digit+8:]

    if game_id in games_ban_list:
        if username in games_ban_list[game_id]:
            await context.bot.send_message(chat_id=user_id,
                                           text='Вас заблоковано в цій грі.')
            return

    room_with_user = None
    game_with_user = None

    for game_id, room in rooms.items():
        if user_id in room['players']:
            room_with_user = room
            game_with_user = game_id

    if room_with_user:
        game_host_id = room_with_user['host_id']
        user_game_id = game_with_user

        if user_id == game_host_id:
            callback_data = f'deny_game_{user_game_id}'
        else:
            callback_data = f'exit_game_{user_game_id}'

        keyboard = [[InlineKeyboardButton("Вийти", callback_data=callback_data)]]
        exit_markup = InlineKeyboardMarkup(keyboard)

        msg = await context.bot.send_message(chat_id=user_id,
                                             text='Ви вже знаходитесь у грі. '
                                                  'Вийдіть з наявної гри, щоб перейти в іншу гру.',
                                             reply_markup=exit_markup)
        track_user_message(user_id, msg)
        return

    if game_id not in rooms:
        await context.bot.send_message(chat_id=user_id,
                                       text='Не існує гри з таким ідентифікатором.')
        return

    if host_id != user_id:
        if user_id not in user_states:
            user_states[user_id] = {}

        await join_game(user_id, game_id, host_id, username, context)
    else:
        player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())
        if user_id in user_messages:
            await clear_previous_message(user_id, context, update)

        if user_id not in user_states:
            user_states[user_id] = {}

        keyboard = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                    [InlineKeyboardButton('Відмінити гру', callback_data=f'deny_game_{game_id}')],
                    [InlineKeyboardButton('Адмін-меню', callback_data=f'admin_menu_{game_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = await context.bot.send_message(chat_id=user_id,
                                             text=f'Після того, як всі зайдуть, натисніть <b>Почати</b>.\n\n'
                                                  f'Гравці:\n'
                                                  f'{player_list}',
                                             parse_mode=ParseMode.HTML,
                                             reply_markup=reply_markup
                                             )
        track_user_message(user_id, msg)
        rooms[game_id]['players'][user_id]['message_id'] = msg.message_id


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'create_room':
        keyboard = [[InlineKeyboardButton('Створити', callback_data='create_game')],
                    [InlineKeyboardButton('Назад', callback_data='go_back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await query.edit_message_text(text='Для початку гри я згенерую посилання,'
                                                     ' по якому зможуть підключитися друзі.\n'
                                                     'Створити гру?', reply_markup=reply_markup)

        if not (any(user_id in room['players'] for room in rooms.values())):
            track_user_message(user_id, message)

    elif query.data == 'create_game':
        if rooms:
            if any(user_id in room['players'] for room in rooms.values()):
                await context.bot.send_message(chat_id=user_id,
                                               text='Ви вже знаходитесь у грі.')
                return

        if user_id not in user_states:
            user_states[user_id] = {}

        username = query.from_user.first_name

        game_id = generate_unique_game_id()

        rooms[game_id] = {}
        rooms[game_id] = {
            'host_id': user_id,
            'players': {user_id: {'username': username, 'message_id': None}},
        }

        if user_id not in rooms[game_id]:
            rooms[game_id]['players'][user_id]['username'] = username

        keyboard = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                    [InlineKeyboardButton('Відмінити гру', callback_data=f'deny_game_{game_id}')],
                    [InlineKeyboardButton('Адмін-меню', callback_data=f'admin_menu_{game_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        link = f'https://t.me/SpyFallGame11_bot?start={user_id}game_id={game_id}'

        player_list = "\n".join(player['username'] for player in rooms[game_id]['players'].values())

        if user_id in user_messages:
            await clear_previous_message(user_id, context, update)

        await context.bot.send_message(text='Ваше посилання:\n'
                                            f'{link}',
                                       chat_id=user_id)

        message = await context.bot.send_message(text=f'Після того, як всі зайдуть, натисніть <b>Почати</b>.\n\n'
                                                      f'Гравці:\n'
                                                      f'{player_list}',
                                                 parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                                                 chat_id=user_id)

        rooms[game_id]['players'][user_id]['message_id'] = message.message_id
        track_user_message(user_id, message)

    elif query.data == 'view_locations':
        data = fetch_table('Dictionaries')
        message_text = 'Список всіх локацій:\n'

        keyboard = [[InlineKeyboardButton("Створити гру", callback_data='create_game')],
                    [InlineKeyboardButton("Подивитись список місць в локаціях", callback_data="view_places")]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        for dict_id, name in data:
            message_text += f'{dict_id}. {name}\n'

        await query.edit_message_text(message_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    elif query.data == 'view_places':
        data = fetch_table('Dictionaries')
        message_text = ''
        for dict_id, name in data:
            message_text += f'{dict_id}. {name}\n'

        if user_id in user_messages:
            await clear_previous_message(user_id, context, update)

        msg = await context.bot.send_message(text=f'{message_text}Введіть номер локації:', chat_id=user_id,
                                             reply_markup=BACK_MARKUP)
        track_user_message(user_id, msg)

        if user_id in start_messages:
            start_messages[user_id] = []

        start_messages[user_id].append(msg.message_id)

        if user_id not in user_states:
            user_states[user_id] = {}

        user_states[user_id]['view_places'] = True

    elif query.data == 'go_back':
        if any(user_id in room['players'] for room in rooms.values()):
            return

        if user_id in user_states:
            del user_states[user_id]

        if user_id in user_messages:
            await clear_previous_message(user_id, context, update)

        msg = await context.bot.send_message(text='Ви повернулися до головного меню.',
                                             reply_markup=START_MARKUP, chat_id=user_id)

        if user_id not in start_messages:
            start_messages[user_id] = []

        if user_id in start_messages:
            start_messages[user_id] = []

        start_messages[user_id].append(msg.message_id)

        track_user_message(user_id, msg)

    elif query.data.startswith('exit_game_'):
        game_id = query.data.split('_')[-1]

        if user_id in user_messages:
            await clear_previous_message(user_id, context, update)

        if 'exit_markup' in user_states[user_id]:
            del user_states[user_id]['exit_markup']

        if 'message_id' in rooms[game_id]['players'][user_id]:
            try:
                await context.bot.delete_message(chat_id=user_id,
                                                 message_id=rooms[game_id]['players'][user_id]['message_id'])
            except BadRequest:
                pass

        if user_id in rooms[game_id]['players']:
            del rooms[game_id]['players'][user_id]

        user_id_list = [user_id for user_id in rooms[game_id]['players']]
        msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]

        host_id = rooms[game_id]['host_id']

        keyboard = [[InlineKeyboardButton("Вийти", callback_data=f'exit_game_{game_id}')]]
        exit_markup = InlineKeyboardMarkup(keyboard)

        await update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context)
        keyboard = copy.deepcopy(START_KEYBOARD)

        if keyboard == START_KEYBOARD:
            keyboard.append([InlineKeyboardButton('Повернутися до гри', callback_data=f'return_to_game_{game_id}')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = await context.bot.send_message(text='Ви повернулися до головного меню.',
                                             reply_markup=reply_markup, chat_id=user_id)

        if user_id not in start_messages:
            start_messages[user_id] = []

        if user_id in start_messages:
            start_messages[user_id] = []

        start_messages[user_id].append(msg.message_id)
        track_user_message(user_id, msg)

    elif query.data.startswith('return_to_game_'):
        game_id = query.data.split('_')[-1]
        host_id = rooms[game_id]['host_id']

        username = query.from_user.first_name

        await join_game(user_id, game_id, host_id, username, context)

    elif query.data.startswith('deny_game_'):
        game_id = query.data.split('_')[-1]

        user_id_list = [user_id for user_id in rooms[game_id]['players']]
        msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]
        host_id = rooms[game_id]['host_id']

        keyboard = [[InlineKeyboardButton("Вийти", callback_data=f'exit_game_{game_id}')]]
        exit_markup = InlineKeyboardMarkup(keyboard)

        await update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context,
                              deny_game=True)

        if game_id in rooms:
            await clear_previous_message(user_id, context, update)

            if 'admin_msg_id' in user_states[user_id]:
                try:
                    await context.bot.delete_message(chat_id=user_id,
                                                     message_id=user_states[user_id]['admin_msg_id'])
                    del user_states[user_id]['admin_msg_id']
                except BadRequest:
                    pass

            if 'exit_markup' in user_states[user_id]:
                del user_states[user_id]['exit_markup']

            if 'message_id' in rooms[game_id]['players'][user_id]:
                try:
                    await context.bot.delete_message(chat_id=user_id,
                                                     message_id=rooms[game_id]['players'][user_id]['message_id'])
                except BadRequest:
                    pass

            del rooms[game_id]

            msg = await context.bot.send_message(text='Ви успішно відмінили гру.',
                                                 reply_markup=START_MARKUP, chat_id=user_id)
            if user_id not in start_messages:
                start_messages[user_id] = []

            if user_id in start_messages:
                start_messages[user_id] = []

            start_messages[user_id].append(msg.message_id)
            track_user_message(user_id, msg)

    elif query.data.startswith('kick_player_'):
        game_id = query.data.split('_')[-1]
        reply_markup = update.effective_message.reply_markup

        if user_id not in user_states:
            user_states[user_id] = {}

        keyboard = [[InlineKeyboardButton("Повернутися до меню", callback_data='back_to_admin_menu')]]
        cancel_markup = InlineKeyboardMarkup(keyboard)

        msg = await query.edit_message_text(text="Введіть ім'я гравця, якого хочете вигнати:",
                                            reply_markup=cancel_markup)

        user_states[user_id]['kick_player'] = True
        user_states[user_id]['game_id'] = game_id
        user_states[user_id]['admin_msg_id'] = msg.message_id
        user_states[user_id]['admin_markup'] = reply_markup
        user_states[user_id]['admin_text'] = 'Адмін-меню:'

    elif query.data.startswith('ban_player_'):
        game_id = query.data.split('_')[-1]
        reply_markup = update.effective_message.reply_markup

        if user_id not in user_states:
            user_states[user_id] = {}

        keyboard = [[InlineKeyboardButton("Повернутися до меню", callback_data='back_to_admin_menu')]]
        cancel_markup = InlineKeyboardMarkup(keyboard)

        msg = await query.edit_message_text(text="Введіть ім'я гравця, якого хочете заблокувати:",
                                            reply_markup=cancel_markup)

        user_states[user_id]['kick_player'] = True
        user_states[user_id]['ban_player'] = True
        user_states[user_id]['game_id'] = game_id
        user_states[user_id]['admin_msg_id'] = msg.message_id
        user_states[user_id]['admin_markup'] = reply_markup
        user_states[user_id]['admin_text'] = 'Адмін-меню:'

    elif query.data.startswith('unban_player_'):
        game_id = query.data.split('_')[-1]
        reply_markup = update.effective_message.reply_markup
        message_id = update.effective_message.message_id

        if user_id not in user_states:
            user_states[user_id] = {}

        keyboard = [[InlineKeyboardButton("Повернутися до меню", callback_data='back_to_admin_menu')]]
        cancel_markup = InlineKeyboardMarkup(keyboard)

        if game_id in games_ban_list:
            ban_list = games_ban_list.get(game_id)
            if ban_list:
                banned_players = '\n'.join(ban_list)
                await query.edit_message_text(text="Список заблокованих гравців:\n"
                                                   f"{banned_players}\n\n"
                                                   "Введіть ім'я гравця, якого хочете розблокувати:",
                                              reply_markup=cancel_markup)
            else:
                await query.edit_message_text(text='Список заблокованих гравців пустий.',
                                              reply_markup=reply_markup)
        else:
            await query.edit_message_text(text='Список заблокованих гравців пустий.',
                                          reply_markup=reply_markup)

        user_states[user_id]['unban_player'] = True
        user_states[user_id]['game_id'] = game_id
        user_states[user_id]['admin_msg_id'] = message_id
        user_states[user_id]['admin_markup'] = reply_markup
        user_states[user_id]['admin_text'] = 'Адмін-меню:'

    elif query.data == 'back_to_admin_menu':
        await back_to_admin_menu(user_id, context)

    elif query.data.startswith('admin_menu_'):
        if user_id not in user_states:
            user_states[user_id] = {}

        if not (any(user_id in room['players'] for room in rooms.values())):
            return

        if 'admin_msg_id' in user_states[user_id]:
            return

        game_id = query.data.split('_')[-1]
        reply_markup = update.effective_message.reply_markup
        text = update.effective_message.text

        admin_keyboard = [[InlineKeyboardButton('Вигнати гравця', callback_data=f'kick_player_{game_id}')],
                          [InlineKeyboardButton('Заблокувати гравця', callback_data=f'ban_player_{game_id}')],
                          [InlineKeyboardButton('Розблокувати гравця', callback_data=f'unban_player_{game_id}')],
                          [InlineKeyboardButton('Закрити меню', callback_data='close_admin_menu')]]
        admin_markup = InlineKeyboardMarkup(admin_keyboard)

        if user_id not in user_states:
            user_states[user_id] = {}

        msg = await context.bot.send_message(chat_id=user_id, text='Адмін-меню:', reply_markup=admin_markup)

        user_states[user_id]['reply_markup'] = reply_markup
        user_states[user_id]['text'] = text
        user_states[user_id]['admin_msg_id'] = msg.message_id

    elif query.data == 'close_admin_menu':
        await context.bot.delete_message(chat_id=user_id, message_id=user_states[user_id]['admin_msg_id'])
        del user_states[user_id]['admin_msg_id']


async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if user_states.get(user_id, {}).get('view_places'):
        dictionary_id = update.message.text.strip()

        data = fetch_table('Dictionaries')
        count = 0
        numbers = []
        for _ in data:
            count += 1
            numbers.append(count)

        correct = False

        for num in numbers:
            try:
                dictionary_id = int(dictionary_id)
            except ValueError:
                break

            if num == dictionary_id:
                correct = True
                break

        if correct:
            dictionary_name = get_dictionary_name(dictionary_id)
            places = get_places_for_dictionary(dictionary_id)
            places_str = ', '.join(places)
            await context.bot.send_message(text=f'Місця в локації <b>{dictionary_name}</b>: '
                                           f'{places_str}', parse_mode=ParseMode.HTML,
                                           chat_id=user_id)
        else:
            await context.bot.send_message(text=f'Невірний номер. Напишіть номер від 1 до {numbers[-1]}.',
                                           chat_id=user_id)

    elif user_states.get(user_id, {}).get('kick_player'):
        game_id = user_states[user_id]['game_id']
        player_name = update.message.text.strip()
        player_id = get_player_id_by_username(game_id, player_name)

        if player_id:
            keyboard = [[InlineKeyboardButton("Вийти", callback_data=f'exit_game_{game_id}')]]
            exit_markup = InlineKeyboardMarkup(keyboard)

            user_id_list = [user_id for user_id in rooms[game_id]['players']]
            msg_id_list = [player['message_id'] for player in rooms[game_id]['players'].values()]
            host_id = rooms[game_id]['host_id']

            if user_states.get(user_id, {}).get('ban_player'):
                await update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context,
                                      kick_player=True,
                                      kicked_player_id=player_id,
                                      ban_player=True,
                                      interact=True)
            else:
                await update_messages(game_id, exit_markup, user_id_list, msg_id_list, host_id, context,
                                      kick_player=True,
                                      kicked_player_id=player_id,
                                      interact=True)
        else:
            await context.bot.send_message(chat_id=user_id,
                                           text='Немає гравця з таким іменем.')

    elif user_states.get(user_id, {}).get('unban_player'):
        game_id = user_states[user_id]['game_id']
        player_name = update.message.text.strip()

        ban_list = games_ban_list.get(game_id)
        if player_name in ban_list:
            games_ban_list[game_id].remove(player_name)
            del user_states[user_id]['unban_player']

            await back_to_admin_menu(user_id, context)
            await context.bot.send_message(chat_id=user_id,
                                           text='Гравця розблоковано.')
        else:
            await context.bot.send_message(chat_id=user_id,
                                           text='В списку немає такого гравця.')

    else:
        await context.bot.send_message(text='Неправильна команда.', chat_id=user_id)


def main() -> None:
    print(f'Starting bot...')

    with open('credentials.json', 'r') as f:
        data = json.load(f)

    TOKEN = data["TOKEN"]

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


if __name__ == "__main__":
    main()
