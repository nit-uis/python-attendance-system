import re

from dao import settingdao
from entities.exceptions import MemberError, EventError
from utils import ts, log, formatter
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler
from services import member as member_service, event as event_service
import traceback
import json

from utils.ts import DATE_WITH_WEEK_FORMAT, LOCAL_DATE_FORMAT

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


def daily_msg():
    # find active and not passed event
    # for each events: print in expand=true format
    updater = Updater(token=TOKEN, use_context=True)
    db_events = event_service.find_coming(tg_group_id=TG_GROUP_ID)

    for event in db_events:
        text = formatter.format_event(event, expand=True)
        event_id = event['uuid']
        keyboard = [
            [InlineKeyboardButton('黎', callback_data=f"event;attend;{event_id};GO"),
             InlineKeyboardButton("遲黎", callback_data=f"event;attend;{event_id};LATE"),
             InlineKeyboardButton("唔黎", callback_data=f"event;attend;{event_id};NOT_GO"),
             InlineKeyboardButton("未知", callback_data=f"event;attend;{event_id};NOT_SURE"),
             ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        updater.bot.send_message(chat_id=TG_GROUP_ID, text=text, reply_markup=reply_markup)


def handle_start(update, context):
    msg = ""
    LOGGER.info(update)
    tg_id = str(update.effective_user.id).strip()
    LOGGER.info(f"tg_id={tg_id}")

    db_members = member_service.find_by_tg_id(tg_group_id=TG_GROUP_ID, tg_id=tg_id, status=["ACTIVE", "INACTIVE"])

    # if found -> send welcome
    if db_members:
        if db_members[0]['status'] == "INACTIVE":
            name = update['message']['from_user']['first_name']
            context.bot.send_message(chat_id=SUPER_ADMIN_TG_IDS[0],
                                     text=f"{name} 想加入? (Y/N)")
            set_footprint(tg_id=SUPER_ADMIN_TG_IDS[0], command='member', subcommand='approve',
                          data_map={'target_tg_id': tg_id})
            msg = "等緊ADMIN幫你approve"
        else:
            msg = "歡迎番黎!"
    # else -> register as inactive member -> send wait for admin approval
    else:
        name = update['message']['from_user']['first_name']
        member_service.create(tg_group_id=TG_GROUP_ID, tg_id=tg_id, name=name)
        context.bot.send_message(chat_id=SUPER_ADMIN_TG_IDS[0],
                                 text=f"{name} 想加入? (Y/N)")
        set_footprint(tg_id=SUPER_ADMIN_TG_IDS[0], command='member', subcommand='approve',
                      data_map={'target_tg_id': tg_id})
        msg = "快啲搵ADMIN幫你approve"

    context.bot.send_message(chat_id=tg_id, text=msg)


def get_footprint(tg_id):
    try:
        print(FOOTPRINT[str(tg_id).strip()])
        return FOOTPRINT[str(tg_id).strip()]
    except KeyError:
        return None


def clear_footprint(tg_id):
    try:
        fp = get_footprint(tg_id)
        FOOTPRINT[str(tg_id).strip()] = {'command': fp['command'], 'subcommand': fp['subcommand']}
        print("clear", FOOTPRINT)
    except KeyError:
        pass


def set_footprint(tg_id, command: str, subcommand: str = '', data_map: dict = dict()):
    tg_id = str(tg_id).strip()
    fp = get_footprint(tg_id)
    if not fp:
        FOOTPRINT[tg_id] = {}
        fp = FOOTPRINT[tg_id]

    if command:
        fp['command'] = command
    if subcommand:
        fp['subcommand'] = subcommand
    print(data_map)
    for k, v in data_map.items():
        fp[k] = v

    print(FOOTPRINT)


# navigate
# handle /member
def handle_member(update, context):
    tg_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("睇某成員資料", callback_data='detail'),
         InlineKeyboardButton("delete", callback_data='delete')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    db_members = member_service.list(tg_group_id=TG_GROUP_ID, status=["ACTIVE"])
    member_list = formatter.format_members(db_members)

    set_footprint(tg_id, 'member', '')

    update.message.reply_text(member_list, reply_markup=reply_markup)


# handle subcommand
def _handle_member(update, context):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)
    if "detail" == fp['subcommand']:
        if 'input' in fp and fp['input']:
            name = fp['input']
            db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])

            if db_members:
                text = formatter.format_member(db_members[0])
                # clear_footprint(tg_id)
            else:
                text = "冇呢個人wo..打多次個名?"
            # todo add admin buttons with this msg
            context.bot.send_message(chat_id=tg_id, text=text)
        else:
            context.bot.send_message(chat_id=tg_id, text="要睇邊個？(請輸入成員名)")
    elif "delete" == fp['subcommand']:
        # todo revamp like delete event
        if 'input' in fp and fp['input']:
            name = fp['input']
            db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])

            if db_members:
                db_members = member_service.update_status(tg_group_id=TG_GROUP_ID, tg_id=db_members[0]['tgId'],
                                                          status="INACTIVE")
                text = formatter.format_member(db_members[0])
                # clear_footprint(tg_id)
            else:
                text = "冇呢個人wo..打多次個名?"
            context.bot.send_message(chat_id=tg_id, text=text)
        else:
            context.bot.send_message(chat_id=tg_id, text="要減走邊個？(請輸入成員名)")
    elif "approve" == fp['subcommand']:
        if 'target_tg_id' in fp and fp['target_tg_id'] and 'input' in fp and fp['input']:
            target_tg_id = fp['target_tg_id']
            y_n = fp['input']

            if "Y" in y_n:
                db_members = member_service.find_by_tg_id(tg_group_id=TG_GROUP_ID, tg_id=target_tg_id,
                                                          status=["INACTIVE"])

                if db_members:
                    member_service.update_status(tg_group_id=TG_GROUP_ID, tg_id=target_tg_id, status="ACTIVE")
                    text = f"{db_members[0]['name']} 成功加入"
                    context.bot.send_message(chat_id=target_tg_id, text="歡迎你既加入")
                else:
                    text = "冇呢個人wo.."
            else:
                text = "已讀"

            context.bot.send_message(chat_id=tg_id, text=text)
            # clear_footprint(tg_id)
        else:
            raise MemberError(f"cannot approve member, tg_id={tg_id}, tg_group_id={TG_GROUP_ID}")

    # todo review
    # should clean footprint once press button?
    # should clean footprint once whole command is succeeded? seem not
    clear_footprint(tg_id)


def handle_me(update, context):
    tg_id = str(update.effective_user.id).strip()
    _handle_member(update, context, tg_id)


def handle_event(update, context):
    tg_id = update.effective_user.id

    # find coming events
    db_events = event_service.find_coming(TG_GROUP_ID)

    # list coming event dates in yyyy-MM-dd
    dates = '\n'.join([ts.to_string(i['date'], format=LOCAL_DATE_FORMAT) for i in db_events if i['date']])

    # set footprint
    set_footprint(tg_id, 'event', '')

    # send msg with buttons, list all by EVENT_TYPE
    keyboard = [
        [InlineKeyboardButton("睇某活動資料", callback_data='detail')],
        [InlineKeyboardButton("所有活動種類", callback_data='list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(dates, reply_markup=reply_markup)


def _handle_event(update, context):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)
    if "detail" == fp['subcommand']:
        if ('input' in fp and fp['input']) or ('date' in fp and fp['date']):
            date = f"{fp['input']} +0800"
            print(date)

            # find event by date
            db_events = event_service.find_by_date(tg_group_id=TG_GROUP_ID, date=date, status=["ACTIVE"])

            # format
            # send msg with admin buttons
            if db_events:
                # set footprint
                set_footprint(tg_id=tg_id, command='event', subcommand='detail',
                              data_map={'event_id': db_events[0]['uuid'], 'date': fp['input']})

                text = formatter.format_event(db_events[0], expand=True)
                keyboard = [
                    [InlineKeyboardButton('delete', callback_data='delete'),
                     InlineKeyboardButton('幾點開始', callback_data='start'),
                     InlineKeyboardButton('跟操', callback_data='guest'),
                     ],
                    [InlineKeyboardButton('改活動種類', callback_data='type'),
                     InlineKeyboardButton('幾點完', callback_data='end'),
                     InlineKeyboardButton('幫人禁<黎>', callback_data='go'),
                     ],
                    [InlineKeyboardButton('改地點', callback_data='venue'),
                     InlineKeyboardButton('邊個<拎波>', callback_data='get'),
                     InlineKeyboardButton('幫人禁<唔黎>', callback_data='not_go'),
                     ],
                    [InlineKeyboardButton('改日期', callback_data='date'),
                     InlineKeyboardButton('邊個<帶波>', callback_data='bring'),
                     InlineKeyboardButton('<送人番火星>', callback_data='not_sure'),
                     ],
                    [InlineKeyboardButton('repeat', callback_data='repeat'),
                     InlineKeyboardButton('sd去大gp', callback_data='send'),
                     ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_markup)
            else:
                text = "冇呢個活動wo..打多次日期?"
                context.bot.send_message(chat_id=tg_id, text=text)
        else:
            context.bot.send_message(chat_id=tg_id, text="要睇邊個？(請輸入日期, Eg: 2020-05-30)")
    elif "attend" == fp['subcommand']:
        if 'event_id' in fp and fp['event_id'] and 'attendance' in fp and fp['attendance'] and 'member_id' in fp and fp['member_id']:
            event_id = fp['event_id']
            attendance = fp['attendance']
            member_id = fp['member_id']
            reason = ''
            text = ''
            if 'input' in fp:
                reason = fp['input']

            if not reason:
                if "LATE" == attendance:
                    attendance = "GO"
                    text = "咩事要遲黎0_0?"
                elif "NOT_GO" == attendance:
                    text = "點解唔黎既T_T?"
                context.bot.send_message(chat_id=tg_id, text=text)

            # update attendance
            # send formatted msg to group
            event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=event_id, member_id=member_id,
                                          attendance=attendance, reason=reason)
            db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])

            if db_events:
                text = formatter.format_event(db_events[0], expand=False)
                context.bot.send_message(chat_id=TG_GROUP_ID, text=text)
                # clear_footprint(tg_id)
            else:
                raise EventError(f"cannot find event({event_id})")
        else:
            raise EventError(f"cannot take attendance, fp={fp}")
    elif "delete" == fp['subcommand']:
        if 'event_id' in fp and fp['event_id']:
            event_id = fp['event_id']

            if event_id:
                db_events = event_service.update_status(tg_group_id=TG_GROUP_ID, event_id=event_id, status="INACTIVE")

                if db_events:
                    text = f"冇呢個活動啦({ts.to_string(db_events[0]['date'], format=LOCAL_DATE_FORMAT)})"
                else:
                    text = f"刪唔到唔存在既活動"

                context.bot.send_message(chat_id=tg_id, text=text)
            else:
                raise EventError(f"cannot delete event, due to invalid event_id")
        else:
            raise EventError(f"cannot delete event")
    elif "start" == fp['subcommand']:
        if 'event_id' in fp and fp['event_id']:
            event_id = fp['event_id']

            if event_id:
                if 'input' in fp and fp['input']:
                    start_time = fp['input']

                    # validate input
                    valid = re.search(r'[0-2][0-9]:[0-5][0-9]', start_time)
                    if valid:
                        db_events = event_service.update_start_time(tg_group_id=TG_GROUP_ID, event_id=event_id,
                                                                    start_time=start_time)
                        if db_events:
                            context.bot.send_message(chat_id=tg_id, text=f"轉左時間去: {start_time}")
                        else:
                            context.bot.send_message(chat_id=tg_id, text="轉唔到時間, 請聯絡天仔負責人")
                    else:
                        context.bot.send_message(chat_id=tg_id, text="幾點? (Eg. 14:00)")
                else:
                    context.bot.send_message(chat_id=tg_id, text="幾點? (Eg. 14:00)")
            else:
                raise EventError(f"cannot update event start, due to invalid event_id")
        else:
            raise EventError(f"cannot update event start")
    elif "end" == fp['subcommand']:  # todo
        if 'event_id' in fp and fp['event_id']:
            event_id = fp['event_id']

            if event_id:
                if 'input' in fp and fp['input']:
                    end_time = fp['input']

                    # validate input
                    valid = re.search(r'[0-2][0-9]:[0-5][0-9]', end_time)
                    if valid:
                        db_events = event_service.update_end_time(tg_group_id=TG_GROUP_ID, event_id=event_id,
                                                                    end_time=end_time)
                        if db_events:
                            context.bot.send_message(chat_id=tg_id, text=f"轉左時間去: {end_time}")
                        else:
                            context.bot.send_message(chat_id=tg_id, text="轉唔到時間, 請聯絡天仔負責人")
                    else:
                        context.bot.send_message(chat_id=tg_id, text="幾點? (Eg. 14:00)")
                else:
                    context.bot.send_message(chat_id=tg_id, text="幾點? (Eg. 14:00)")
            else:
                raise EventError(f"cannot update event end, due to invalid event_id")
        else:
            raise EventError(f"cannot update event end")
    elif "type" == fp['subcommand']:  # todo
        pass
    elif "date" == fp['subcommand']:  # todo
        pass
    elif "venue" == fp['subcommand']:  # todo
        pass
    elif "guest" == fp['subcommand']:  # todo
        pass
    elif "go" == fp['subcommand']:  # todo
        pass
    elif "not_go" == fp['subcommand']:  # todo
        pass
    elif "not_sure" == fp['subcommand']:  # todo
        pass
    elif "bring" == fp['subcommand']:  # todo
        pass
    elif "get" == fp['subcommand']:  # todo
        pass
    elif "send" == fp['subcommand']:  # todo
        if 'event_id' in fp and fp['event_id']:
            event_id = fp['event_id']
            db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])

            if db_events:
                text = formatter.format_event(db_events[0], expand=True)
                context.bot.send_message(chat_id=TG_GROUP_ID, text=text)
            else:
                context.bot.send_message(chat_id=tg_id, text="send唔到, 請聯絡天仔負責人")
        else:
            raise EventError(f"cannot send, due to invalid event_id")
    elif "repeat" == fp['subcommand']:  # todo
        pass

    # todo review
    # should clean footprint once press button?
    # should clean footprint once whole command is succeeded? seem not
    # clear_footprint(tg_id)


def handle_help(update, context):
    content = """
    
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=content)


def handle_button(update, context):
    tg_id = update.effective_user.id
    query = update.callback_query
    print(query)
    print(update)

    # handle group event command
    try:
        chat_type = update['message']['chat']['type']

        if "group" in chat_type:
            fp = query.data.split(";")
            data_map = {
                'member_id': tg_id,
                'event_id': fp[2],
                'attendance': fp[3]
            }

            if fp:
                set_footprint(tg_id, command=fp[0], subcommand=fp[1], data_map=data_map)

                if "event" == fp[0]:
                    _handle_member(update, context)
    except:
        fp = get_footprint(tg_id)

        if "member" == fp['command']:
            set_footprint(tg_id, command='member', subcommand=query.data)
            _handle_member(update, context)
        elif "me" == fp['command']:
            set_footprint(tg_id, command='me', subcommand=query.data)
            _handle_me(update, context)
        elif "event" == fp['command']:
            set_footprint(tg_id, command='event', subcommand=query.data)
            _handle_event(update, context)
    finally:
        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()
    # {'id': '1424950175065221455', 'chat_instance': '-2484597087886404463', 'message': {'message_id': 28876, 'date': 1589608202, 'chat': {'id': 331772066, 'type': 'private', 'first_name': 'Deleted Account'}, 'text': 'Please choose:', 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'reply_markup': {'inline_keyboard': [[{'text': 'Option 1', 'callback_data': '1'}, {'text': 'Option 2', 'callback_data': '2'}], [{'text': 'Option 3', 'callback_data': '3'}]]}, 'from': {'id': 638988595, 'first_name': 'minerva', 'is_bot': True, 'username': 'minerva_hk_bot'}}, 'data': '2', 'from': {'id': 331772066, 'first_name': 'Deleted Account', 'is_bot': False, 'language_code': 'en'}}


def handle_input(update, context):
    tg_id = update.effective_user.id

    fp = get_footprint(tg_id)
    data_map = {'input': update.message.text.strip()}

    if fp and 'command' in fp:
        if "member" == fp['command']:
            set_footprint(tg_id, command='member', data_map=data_map)
            _handle_member(update, context)
        elif "me" == fp['command']:
            set_footprint(tg_id, command='me', data_map=data_map)
            _handle_me(update, context)
        elif "event" == fp['command']:
            set_footprint(tg_id, command='event', data_map=data_map)
            _handle_event(update, context)
    else:
        context.bot.send_message(chat_id=tg_id, text="有咩事要搵我地admin?")


def error(update, context):
    try:
        traceback.print_exc()
        tg_id = update.effective_user.id
        context.bot.send_message(chat_id=tg_id, text=str(context.error))
        for sa_tg_id in SUPER_ADMIN_TG_IDS:
            context.bot.send_message(chat_id=sa_tg_id, text=f"user({tg_id}): {context.error}")
    except Exception as e:
        traceback.print_exc()
