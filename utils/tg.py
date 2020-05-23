from dao import settingdao
from utils import ts, log
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler
from services import member
import traceback


TOKEN = ""
SUPER_ADMIN_TG_IDS = []
TG_GROUP_ID = ""
LOGGER = None
FOOTPRINT = {}


def init(env):
    global TOKEN, SUPER_ADMIN_TG_IDS, TG_GROUP_ID, LOGGER
    db_setting = settingdao.get(env)
    TOKEN = db_setting['telegram_token']
    SUPER_ADMIN_TG_IDS = db_setting['superAdminTgIds']
    TG_GROUP_ID = db_setting['tgGroupId']
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
    tg_id = str(update.effective_user.id).strip()
    LOGGER.info(f"tg_id={tg_id}")

    db_member = member.find(tg_id=tg_id, tg_group_id=TG_GROUP_ID)

    # if found -> send welcome
    if db_member:
        msg = "Welcome back!"
    # else -> register as inactive member -> send wait for admin approval
    else:
        name = update['message']['from_user']['first_name']
        member.create(tg_id=tg_id, tg_group_id=TG_GROUP_ID, name=name)
        msg = "快啲搵ADMIN幫你approve"

    context.bot.send_message(chat_id=tg_id, text=msg)


def get_footprint(tg_id):
    try:
        return FOOTPRINT[tg_id]
    except KeyError:
        return None


def handle_member(update, context):
    tg_id = str(update.effective_user.id).strip()

    if get_footprint(tg_id):
        _handle_member(update, context, tg_id)

    else:
        keyboard = [
            [InlineKeyboardButton("睇/改某成員資料", callback_data='detail'),
             InlineKeyboardButton("approve", callback_data='approve')],
            [InlineKeyboardButton("＋成員", callback_data='create'),
             InlineKeyboardButton("- 成員", callback_data='delete')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        db_members = member.list_by_tg_group_id(TG_GROUP_ID)
        member_list = '\n'.join([m['name'] for m in db_members])

        update.message.reply_text(member_list, reply_markup=reply_markup)





def handle_me(update, context):
    tg_id = str(update.effective_user.id).strip()
    _handle_member(update, context, tg_id)


def _handle_member(update, context, tg_id):
    return


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
    try:
        traceback.print_exc()
        tg_id = update.effective_user.id
        context.bot.send_message(chat_id=tg_id, text=str(context.error))
        for sa_tg_id in SUPER_ADMIN_TG_IDS:
            context.bot.send_message(chat_id=sa_tg_id, text=f"user({tg_id}): {context.error}")
    except Exception as e:
        traceback.print_exc()


