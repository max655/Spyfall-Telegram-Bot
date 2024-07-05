from telegram import InlineKeyboardButton, InlineKeyboardMarkup

user_states = {}
user_messages = {}
rooms = {}

START_KEYBOARD = [[InlineKeyboardButton("Створити гру", callback_data='create_room')],
                  [InlineKeyboardButton("Локації", callback_data='view_locations')]]
START_MARKUP = InlineKeyboardMarkup(START_KEYBOARD)

BACK_KEYBOARD = [[InlineKeyboardButton('Повернутися до меню', callback_data='go_back')]]
BACK_MARKUP = InlineKeyboardMarkup(BACK_KEYBOARD)

PROCESS_GAME = [[InlineKeyboardButton('Почати гру', callback_data='start_game')],
                [InlineKeyboardButton('Відмінити гру', callback_data='go_back')]]

PROCESS_GAME_MARKUP = InlineKeyboardMarkup(PROCESS_GAME)
