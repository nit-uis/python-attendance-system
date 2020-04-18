from dao import settingdao
from main import LOGGER
from utils import ts
from telegram.ext import Updater, CommandHandler

TOKEN = ""


def init():
    global TOKEN
    TOKEN = settingdao.get_key("telegram_token")


def get_updates():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', send_msg)
    dispatcher.add_handler(start_handler)

    updater.start_polling()


def send_msg():
    return "test"


def patch_command():
    pass # todo
