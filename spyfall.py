import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode
from db_spyfall import fetch_table, get_dictionary_name, get_places_for_dictionary


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

START_KEYBOARD = [[InlineKeyboardButton("Створити гру", callback_data='create_room')],
                  [InlineKeyboardButton("Локації", callback_data='view_locations')]]
START_MARKUP = InlineKeyboardMarkup(START_KEYBOARD)

BACK_KEYBOARD = [[InlineKeyboardButton('Повернутися до меню', callback_data='go_back')]]
BACK_MARKUP = InlineKeyboardMarkup(BACK_KEYBOARD)

user_states = {}
user_messages = {}
room = {}
games = {}


def track_user_message(user_id, message):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message.message_id)


async def clear_previous_message(user_id, context):
    await context.bot.delete_message(chat_id=user_id, message_id=user_messages[user_id][-1])


async def start(update: Update, context: CallbackContext) -> None:
    args = context.args
    user_id = update.message.from_user.id
    username = update.message.from_user.first_name

    if len(args) == 0:
        start_message = await context.bot.send_message(chat_id=user_id,
                                                       text="Вітаємо вас у боті зі грою "
                                                            "<b>Знахідка для шпигуна (Spyfall)</b>!\n"
                                                            "Створіть гру, щоб запросити своїх друзів.",
                                                       reply_markup=START_MARKUP,
                                                       parse_mode=ParseMode.HTML)
        track_user_message(user_id, start_message)
        return

    host_id = args[0]
    if host_id != user_id:
        room[user_id]['username'] = username
        player_list = "\n".join(player['username'] for player in room.values())
        start_message = await context.bot.send_message(chat_id=user_id,
                                                       text='Ласкаво просимо до гри '
                                                            '<b>Знахідка для шпигуна (Spyfall)</b>!\n'
                                                            'Очікуйте початку гри.\n\n'
                                                            'Гравці:\n'
                                                            f'{player_list}')
        games[user_id]['message_id'] = start_message.message_id
        track_user_message(user_id, start_message)


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'create_room':
        keyboard = [[InlineKeyboardButton('Створити', callback_data='create_game')],
                    [InlineKeyboardButton('Назад', callback_data='go_back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text='Для початку гри я згенерую посилання,'
                                           ' по якому зможуть підключитися друзі.\n'
                                           'Створити гру?', reply_markup=reply_markup)

    elif query.data == 'create_game':
        username = query.from_user.first_name
        if user_id not in room:
            room[user_id] = {'username': username}

        keyboard = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                    [InlineKeyboardButton('Відмінити гру', callback_data='go_back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        link = f'https://t.me/spyfall11_bot?start={user_id}'

        player_list = "\n".join(player['username'] for player in room.values())

        message = await query.edit_message_text(text='Ваше посилання:\n'
                                                     f'{link}\n'
                                                     f'Після того, як всі зайдуть, натисніть <b>Почати</b>.\n\n'
                                                     f'Гравці:\n'
                                                     f'{player_list}',
                                                parse_mode=ParseMode.HTML, reply_markup=reply_markup)

        games[user_id]['message_id'] = message.message_id

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

        await clear_previous_message(user_id, context)
        msg = await context.bot.send_message(text=f'{message_text}Введіть номер локації:', chat_id=user_id,
                                             reply_markup=BACK_MARKUP)
        track_user_message(user_id, msg)
        user_states[user_id] = True

    elif query.data == 'go_back':
        if user_id in user_states:
            del user_states[user_id]

        await clear_previous_message(user_id, context)
        msg = await context.bot.send_message(text='Ви повернулися до головного меню.',
                                             reply_markup=START_MARKUP, chat_id=user_id)
        track_user_message(user_id, msg)


async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    if user_states.get(user_id):
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
