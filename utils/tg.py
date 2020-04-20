from telegram import InlineQueryResultArticle, InputTextMessageContent

from dao import settingdao
from main import LOGGER
from utils import ts
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler

TOKEN = ""


def init():
    global TOKEN
    TOKEN = settingdao.get_key("telegram_token")


def get_updates():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    caps_handler = CommandHandler('caps', caps)
    inline_caps_handler = InlineQueryHandler(inline_caps)
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(caps_handler)
    dispatcher.add_handler(inline_caps_handler)
    dispatcher.add_handler(echo_handler)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="hello world")


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    print(update.message.text)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Caps',
            input_message_content=InputTextMessageContent(query.upper())
        )
    )
    context.bot.answer_inline_query(update.inline_query.id, results)


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="唔知你UP乜。。請由頭黎過")


def send_msg():
    print("received admin command")


def patch_command():
    pass # todo
