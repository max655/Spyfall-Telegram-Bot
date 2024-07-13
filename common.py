from telegram import InlineKeyboardButton, InlineKeyboardMarkup

user_states = {}
user_messages = {}
rooms = {}
games_ban_list = {}
start_messages = {}
MAX_ROOM_SIZE = 8

START_KEYBOARD = [[InlineKeyboardButton("Створити гру", callback_data='create_room')],
                  [InlineKeyboardButton("Локації", callback_data='view_locations')]]
START_MARKUP = InlineKeyboardMarkup(START_KEYBOARD)

BACK_KEYBOARD = [[InlineKeyboardButton('Повернутися до меню', callback_data='go_back')]]
BACK_MARKUP = InlineKeyboardMarkup(BACK_KEYBOARD)
