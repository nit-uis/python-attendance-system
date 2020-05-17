from dao import settingdao
from utils import ts, log
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler
from services import member
import traceback


TOKEN = ""
LOGGER = None


def init():
    global TOKEN, LOGGER
    TOKEN = settingdao.get_key("telegram_token")
    LOGGER = log.get_logger("tg")


def get_updates():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', handle_start)
    member_handler = CommandHandler('member', handle_member)
    event_handler = CommandHandler('event', handle_event)
    help_handler = CommandHandler('help', handle_help)
    input_handler = MessageHandler(Filters.text & (~Filters.command), handle_input)
    button_handler = CallbackQueryHandler(handle_button)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(member_handler)
    dispatcher.add_handler(event_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(input_handler)
    dispatcher.add_handler(button_handler)

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


def handle_start(update, context):
    msg = ""
    LOGGER.info(update)
    chat_id = str(update.effective_chat.id).strip()
    user_id = str(update.effective_user.id).strip()
    LOGGER.info(f"chat_id={chat_id}")
    LOGGER.info(f"user_id={user_id}")
    chat_type = update['message']['chat']['type']
    if "group" not in chat_type:
        raise Exception("係大gp再行多次 /start")

    db_member = member.find(tg_id=user_id, tg_group_id=chat_id)

    # if found -> send welcome
    if db_member:
        msg = "Welcome back!"
    # else -> register as inactive member -> send wait for admin approval
    else:
        name = update['message']['from_user']['first_name']
        member.create(tg_id=user_id, tg_group_id=chat_id, name=name)
        msg = "快啲搵ADMIN幫你approve"

    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def handle_member(update, context):
    LOGGER.warning(update)
    LOGGER.info(update['message']['chat']['id'])
    db_member = member.find(tg_id=update['message']['chat']['id'])

    context.bot.send_message(chat_id=update.effective_chat.id, text="hello world")


def handle_event(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="hello world")


def handle_help(update, context):
    content = """
    
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=content)


def handle_button(update, context):
    query = update.callback_query
    print(query)
    # {'id': '1424950175065221455', 'chat_instance': '-2484597087886404463', 'message': {'message_id': 28876, 'date': 1589608202, 'chat': {'id': 331772066, 'type': 'private', 'first_name': 'Deleted Account'}, 'text': 'Please choose:', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'reply_markup': {'inline_keyboard': [[{'text': 'Option 1', 'callback_data': '1'}, {'text': 'Option 2', 'callback_data': '2'}], [{'text': 'Option 3', 'callback_data': '3'}]]}, 'from': {'id': 638988595, 'first_name': 'minerva', 'is_bot': True, 'username': 'minerva_hk_bot'}}, 'data': '2', 'from': {'id': 331772066, 'first_name': 'Deleted Account', 'is_bot': False, 'language_code': 'en'}}

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    query.edit_message_text(text="Selected option: {}".format(query.data))


def handle_input(update, context):
    LOGGER.warning(update)
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def error(update, context):
    traceback.print_exc()
    LOGGER.warning(context.error)
    # context.bot.send_message(chat_id=update.effective_chat.id, text=str(context.error))
