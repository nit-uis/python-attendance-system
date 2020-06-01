import re

from dao import settingdao
from entities.exceptions import MemberError, EventError, Unauthorized
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
DEBUG_MODE = True


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
        text = formatter.format_event(event, expand=3)
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
                          data_map={'member_id': db_members[0]['uuid']})
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
                      data_map={'member_id': tg_id})
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


def set_footprint(tg_id, command: str, subcommand: str = '', data_map: dict = dict(), clean_user_data: bool = False):
    tg_id = str(tg_id).strip()
    fp = get_footprint(tg_id)
    if not fp:
        FOOTPRINT[tg_id] = {}
        fp = FOOTPRINT[tg_id]

    if command:
        fp['command'] = command
    if subcommand:
        fp['subcommand'] = subcommand
    for k, v in data_map.items():
        fp[k] = v

    if clean_user_data:
        for k, v in fp.items():
            if k != "command" and k != "subcommand":
                fp[k] = ''

    print(FOOTPRINT)


# navigate
# handle /member
def handle_member(update, context):
    tg_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("睇某成員資料", callback_data='detail')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    db_members = member_service.list(tg_group_id=TG_GROUP_ID, status=["ACTIVE"])
    members = formatter.format_members(db_members)
    if not members:
        members = "冇晒人lu.."

    set_footprint(tg_id=tg_id, command='member', subcommand='', clean_user_data=True)

    update.message.reply_text(members, reply_markup=reply_markup)


# handle subcommand
def _handle_member(update, context):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)
    db_members = member_service.find_by_tg_id(tg_group_id=TG_GROUP_ID, tg_id=tg_id, status=["ACTIVE"])
    if not db_members:
        raise Unauthorized(f"{tg_id} is trying to access member")

    if "detail" == fp['subcommand']:
        _handle_member_detail(update, context, db_members[0])
    elif "delete" == fp['subcommand']:
        _handle_member_delete(update, context, db_members[0])
    elif "approve" == fp['subcommand']:
        _handle_member_approve(update, context, db_members[0])


def _handle_member_detail(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="要睇邊個? (請輸入成員名)")
        return

    name = fp['input']
    db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
    if not db_members:
        context.bot.send_message(chat_id=tg_id, text="打多次個名?")
        return

    text = formatter.format_member(db_members[0])
    if member_service.is_admin(request_member['type']):
        # todo handle command
        keyboard = [
            [InlineKeyboardButton('delete', callback_data='delete'),
             InlineKeyboardButton('auto <黎>', callback_data='go'),
             InlineKeyboardButton('auto <唔黎>', callback_data='not_go')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=tg_id, text=text)

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'member_id': db_members[0]['uuid'], 'input': ''})


def _handle_member_delete(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to delete someone")

    if 'member_id' not in fp or not fp['member_id']:
        context.bot.send_message(chat_id=tg_id, text="冇人要delete wo")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="真係要delete? (Y/N)")
        return
    elif 'Y' not in fp['input'] and 'y' not in fp['input']:
        context.bot.send_message(chat_id=tg_id, text="唔delete lu")
        set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})
        return

    member_id = fp['member_id']
    db_members = member_service.update_status(tg_group_id=TG_GROUP_ID, member_id=member_id, status="INACTIVE")
    if db_members:
        context.bot.send_message(chat_id=tg_id, text=f"deleted {db_members[0]['name']}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise MemberError("cannot delete member")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': ''})


def _handle_member_approve(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to approve someone")
    if 'member_id' not in fp or not fp['member_id']:
        context.bot.send_message(chat_id=tg_id, text="冇人要approve wo")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="真係要approve? (Y/N)")
        return
    elif 'Y' not in fp['input'] and 'y' not in fp['input']:
        context.bot.send_message(chat_id=tg_id, text="已經reject了")
        set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})
        return

    member_id = fp['member_id']
    db_members = member_service.update_status(tg_group_id=TG_GROUP_ID, member_id=member_id, status="ACTIVE")
    if db_members:
        context.bot.send_message(chat_id=db_members[0]['tgId'], text="歡迎你既加入")
        context.bot.send_message(chat_id=TG_GROUP_ID, text=f"歡迎 {db_members[0]['name']} 成功加入我地既一份子")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise MemberError("cannot approve member")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': ''})


def handle_me(update, context):
    tg_id = str(update.effective_user.id).strip()
    _handle_member(update, context, tg_id)


def handle_event(update, context):
    tg_id = update.effective_user.id

    # find coming events
    db_events = event_service.find_coming(TG_GROUP_ID)

    # list coming event dates in yyyy-MM-dd
    dates = '\n'.join([ts.to_string_hkt(i['date'], format=LOCAL_DATE_FORMAT) for i in db_events if i['date']])
    if not dates:
        dates = "最近冇event.."

    # set footprint
    set_footprint(tg_id=tg_id, command='event', subcommand='', clean_user_data=True)

    # send msg with buttons, list all by EVENT_TYPE
    keyboard = [
        [InlineKeyboardButton("睇唔同種類既event", callback_data='list')],
        [InlineKeyboardButton("睇某event資料", callback_data='detail'),
         InlineKeyboardButton("新event", callback_data='create')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(dates, reply_markup=reply_markup)


def _handle_event(update, context):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)
    db_members = member_service.find_by_tg_id(tg_group_id=TG_GROUP_ID, tg_id=tg_id, status=["ACTIVE"])
    if not db_members:
        raise Unauthorized(f"{tg_id} is trying to access event")

    if "detail" == fp['subcommand']:
        _handle_event_detail(update, context, db_members[0])
    elif "attend" == fp['subcommand']:
        _handle_event_attend(update, context, db_members[0])
    elif "delete" == fp['subcommand']:
        _handle_event_delete(update, context, db_members[0])
    elif "start" == fp['subcommand']:
        _handle_event_time(update, context, db_members[0], start=True)
    elif "end" == fp['subcommand']:
        _handle_event_time(update, context, db_members[0], start=False)
    elif "type" == fp['subcommand']:
        _handle_event_type(update, context, db_members[0])
    elif "date" == fp['subcommand']:
        _handle_event_date(update, context, db_members[0])
    elif "venue" == fp['subcommand']:
        _handle_event_venue(update, context, db_members[0])
    elif "guest" == fp['subcommand']:
        _handle_event_guest(update, context, db_members[0])
    elif "go" == fp['subcommand']:
        _handle_event_attendance(update, context, db_members[0], "GO")
    elif "not_go" == fp['subcommand']:
        _handle_event_attendance(update, context, db_members[0], "NOT_GO")
    elif "not_sure" == fp['subcommand']:
        _handle_event_attendance(update, context, db_members[0], "NOT_SURE")
    elif "bring" == fp['subcommand']:
        _handle_event_ball(update, context, db_members[0], "BRING")
    elif "get" == fp['subcommand']:
        _handle_event_ball(update, context, db_members[0], "GET")
    elif "send" == fp['subcommand']:
        _handle_event_send(update, context, db_members[0])
    elif "create" == fp['subcommand']:
        _handle_event_create(update, context, db_members[0])
    elif "duplicate" == fp['subcommand']:
        _handle_event_duplicate(update, context, db_members[0])


# fixme when clear event_id in fp?
def _handle_event_detail(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if ('input' not in fp or not fp['input']) and ('date' not in fp or not fp['date']) and ('event_id' not in fp or not fp['event_id']):
        context.bot.send_message(chat_id=tg_id, text="邊日? (Eg. 2020-05-31)")
        return

    if 'input' in fp and fp['input']:
        date = f"{fp['input']} +0800"
        db_events = event_service.find_by_date(tg_group_id=TG_GROUP_ID, date=date, status=["ACTIVE"])
    elif 'date' in fp and fp['date']:
        # fixme sometimes cant find existing events, time range has bugs?
        date = f"{fp['date']} +0800"
        db_events = event_service.find_by_date(tg_group_id=TG_GROUP_ID, date=date, status=["ACTIVE"])
    elif 'event_id' in fp and fp['event_id']:
        event_id = fp['event_id']
        db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])
    else:
        context.bot.send_message(chat_id=tg_id, text="打多次日期?")
        return

    if not db_events:
        context.bot.send_message(chat_id=tg_id, text="打多次日期?")
        return
    elif len(db_events) > 1:
        # fixme what if same date have 2 event? let user choose?
        keyboard = [[InlineKeyboardButton(formatter.format_event(i, 1), callback_data=i['uuid'])] for i in db_events]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=tg_id, text="邊個?", reply_markup=reply_markup)
        set_footprint(tg_id=tg_id, command='event', data_map={"choose": "event_id", "input": ""})
        return

    text = formatter.format_event(db_events[0], expand=3)
    if member_service.is_admin(request_member['type']):
        keyboard = [
            [InlineKeyboardButton('delete', callback_data='delete'),
             InlineKeyboardButton('幾點開始', callback_data='start'),
             InlineKeyboardButton('跟操', callback_data='guest'),
             ],
            [InlineKeyboardButton('改event種類', callback_data='type'),
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
            [InlineKeyboardButton('duplicate', callback_data='duplicate'),
             InlineKeyboardButton('sd去大gp', callback_data='send'),
             InlineKeyboardButton('F5', callback_data='detail'),
             ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=tg_id, text=text)

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={"event_id": db_events[0]['uuid'], "input": "", "choose": ""})


def _handle_event_attend(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if 'event_id' not in fp or not fp['event_id'] or 'attendance' not in fp or not fp['attendance'] or 'member_id' not in fp or not fp['member_id']:
        context.bot.send_message(chat_id=tg_id, text="禁多次制?")
        return

    event_id = fp['event_id']
    attendance = fp['attendance']
    member_id = fp['member_id']
    reason = ''
    if 'input' in fp:
        reason = fp['input']
    if not reason:
        if "LATE" == attendance:
            context.bot.send_message(chat_id=tg_id, text="咩事要遲黎0_0?")
            return
        elif "NOT_GO" == attendance:
            context.bot.send_message(chat_id=tg_id, text="點解唔黎既T_T?")
            return
    if "LATE" == attendance:
        attendance = "GO"

    # update attendance
    # send formatted msg to group
    event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=event_id, member_id=member_id,
                                  attendance=attendance, reason=reason)
    db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])
    if db_events:
        text = formatter.format_event(db_events[0], expand=2)
        context.bot.send_message(chat_id=TG_GROUP_ID, text=text)
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError(f"cannot attend event")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_delete(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to delete some events")

    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="冇event要delete wo")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="真係要delete? (Y/N)")
        return
    elif 'Y' not in fp['input'] and 'y' not in fp['input']:
        context.bot.send_message(chat_id=tg_id, text="唔delete lu")
        set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})
        return

    event_id = fp['event_id']
    db_events = event_service.update_status(tg_group_id=TG_GROUP_ID, event_id=event_id, status="INACTIVE")
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"deleted {ts.to_string_hkt(db_events[0]['date'], format=LOCAL_DATE_FORMAT)}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot delete event")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_time(update, context, request_member, start: bool):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")

    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return

    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="幾點? (Eg. 14:00)")
        return
    elif not re.search(r'[0-2][0-9]:[0-5][0-9]', fp['input']):
        context.bot.send_message(chat_id=tg_id, text="幾點? 要跟番呢個格式 (Eg. 15:00)")
        return

    event_id = fp['event_id']
    time = fp['input']

    if start:
        db_events = event_service.update_start_time(tg_group_id=TG_GROUP_ID, event_id=event_id, start_time=time)
    else:
        db_events = event_service.update_end_time(tg_group_id=TG_GROUP_ID, event_id=event_id, end_time=time)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左時間去: {time}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event time")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_type(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to send some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="轉邊種? (練習/FDLY/比賽/玩)")
        return

    event_id = fp['event_id']
    etype = formatter.deformat_event_type(fp['input'])

    db_events = event_service.update_type(tg_group_id=TG_GROUP_ID, event_id=event_id, etype=etype)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左種類去 {formatter.format_event_type(etype)}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event type")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_date(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="邊日? (Eg. 2020-05-31)")
        return

    event_id = fp['event_id']
    date = f"{fp['input']} +0800"

    db_events = event_service.update_date(tg_group_id=TG_GROUP_ID, event_id=event_id, date=date)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左去 {fp['input']}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event type")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_venue(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="邊度? (Eg. 花墟/巴富街/花園街體育館/其他地方)")
        return

    event_id = fp['event_id']
    venue = fp['input'].replace(" ", "")

    db_events = event_service.update_venue(tg_group_id=TG_GROUP_ID, event_id=event_id, venue=venue)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左去 {fp['input']}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event venue")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_guest(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="邊個? (可以打多幾個名, Eg: lydia, tszwai)")
        return

    event_id = fp['event_id']
    names = fp['input'].split(",")
    if len(names) == 1:
        names = fp['input'].split("，")

    for name in names:
        name = name.strip()
        db_guest = member_service.find_or_create_guest(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_guest:
            context.bot.send_message(chat_id=tg_id, text=f"{name} 跟操失敗")
            continue

        db_events = event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=event_id, member_id=db_guest['uuid'], attendance="GO", reason='')
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"加左 {name}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event guest")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_attendance(update, context, request_member, attendance):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="邊個? (可以打多幾個名, Eg: lydia, tszwai)")
        return

    event_id = fp['event_id']
    names = fp['input'].split(",")
    if len(names) == 1:
        names = fp['input'].split("，")

    for name in names:
        name = name.strip()
        db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_members:
            context.bot.send_message(chat_id=tg_id, text=f"加唔到 {name}")
            continue

        db_events = event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=event_id, member_id=db_members[0]['uuid'], attendance=attendance, reason='')
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"加左 {name}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event member attendance")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_ball(update, context, request_member, action):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to update some events")
    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return
    if 'input' not in fp or not fp['input']:
        context.bot.send_message(chat_id=tg_id, text="邊個? (可以打多幾個名, Eg: lydia, tszwai)")
        return

    event_id = fp['event_id']
    names = fp['input'].split(",")
    if len(names) == 1:
        names = fp['input'].split("，")

    for name in names:
        name = name.strip()
        db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_members:
            context.bot.send_message(chat_id=tg_id, text=f"加唔到 {name}")
            continue

        db_events = event_service.take_ball(tg_group_id=TG_GROUP_ID, event_id=event_id, member_id=db_members[0]['uuid'], action=action)
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"加左 {name}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event ball")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_send(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to send some events")

    if 'event_id' not in fp or not fp['event_id']:
        context.bot.send_message(chat_id=tg_id, text="你肯定你簡好邊個event?")
        return

    event_id = fp['event_id']

    db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])
    if db_events:
        context.bot.send_message(chat_id=TG_GROUP_ID, text=formatter.format_event(db_events[0], expand=3))
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot send event")

    # update footprint
    # set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_create(update, context, request_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not member_service.is_admin(request_member['type']):
        raise Unauthorized(f"{request_member['name']} is trying to create some events")

    db_events = event_service.create(tg_group_id=TG_GROUP_ID)
    if db_events:
        set_footprint(tg_id=tg_id, command='event', data_map={'event_id': db_events[0]['uuid']})
        _handle_event_detail(update, context, request_member)
        # context.bot.send_message(chat_id=tg_id, text=formatter.format_event(db_events[0], expand=3))
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot create event")

    # update footprint
    # set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def handle_help(update, context):
    content = """
    
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=content)


def handle_button(update, context):
    tg_id = update.effective_user.id
    query = update.callback_query
    # print(query)
    # print(update)

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
            if 'choose' in fp and "event_id" == fp['choose']:
                set_footprint(tg_id, command='event', data_map={fp['choose']: query.data})
            else:
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
        if DEBUG_MODE:
            traceback.print_exc()

