import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, filters
from telegram.constants import ParseMode


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

START_KEYBOARD = [[InlineKeyboardButton("Створити гру", callback_data='create_game')],
                  [InlineKeyboardButton("Локації", callback_data='view_places')]]
START_MARKUP = InlineKeyboardMarkup(START_KEYBOARD)


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id

    await context.bot.send_message(chat_id=user_id,
                                   text="Вітаємо вас у боті зі грою "
                                        "<b>Знахідка для шпигуна (Spyfall)</b>!\n"
                                        "Створіть гру, щоб запросити своїх друзів.",
                                   reply_markup=START_MARKUP,
                                   parse_mode=ParseMode.HTML)


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    name = query.from_user.first_name


def main() -> None:
    print(f'Starting bot...')

    with open('credentials.json', 'r') as f:
        data = json.load(f)

    TOKEN = data["TOKEN"]

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()


if __name__ == "__main__":
    main()
