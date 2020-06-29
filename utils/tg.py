import traceback
import re

from dao import settingdao
from entities.exceptions import MemberError, EventError
from utils import ts, log, formatter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from services import member as member_service, event as event_service, security, cache

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
    me_handler = CommandHandler('me', handle_me)
    event_handler = CommandHandler('event', handle_event)
    input_handler = MessageHandler(Filters.text & (~Filters.command), handle_input)
    button_handler = CallbackQueryHandler(handle_button)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(member_handler)
    dispatcher.add_handler(me_handler)
    dispatcher.add_handler(event_handler)
    dispatcher.add_handler(input_handler)
    dispatcher.add_handler(button_handler)

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


def get_group_keyboard(event_id):
    if not event_id:
        raise EventError("no event id")

    keyboard = [
        [InlineKeyboardButton('黎', callback_data=f"event;attend;{event_id};GO"),
         InlineKeyboardButton("遲黎", callback_data=f"event;attend;{event_id};LATE"),
         InlineKeyboardButton("唔黎", callback_data=f"event;attend;{event_id};NOT_GO"),
         InlineKeyboardButton("未知", callback_data=f"event;attend;{event_id};NOT_SURE"),
         ],
    ]
    return keyboard


def daily_msg():
    LOGGER.info("start daily_msg")

    # find active and not passed event
    # for each events: print in expand=true format
    updater = Updater(token=TOKEN, use_context=True)
    db_events = event_service.find_coming(tg_group_id=TG_GROUP_ID)

    for event in db_events:
        text = formatter.format_event(event, expand=3)
        event_id = event['uuid']
        keyboard = get_group_keyboard(event_id=event_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        updater.bot.send_message(chat_id=TG_GROUP_ID, text=text, reply_markup=reply_markup)


def monthly_stats():
    LOGGER.info("start monthly_stats")

    # if today is the first day of month
    now = ts.to_string(ts.get_hk_now_seconds())[8:10]
    if now == "01":
        db_stats = member_service.find_stats(tg_group_id=TG_GROUP_ID, mtypes=["COACH", "GUEST"], status=["ACTIVE"])
        text = formatter.format_member_group_stats(db_stats)
        updater = Updater(token=TOKEN, use_context=True)
        updater.bot.send_message(chat_id=TG_GROUP_ID, text=text)


def handle_start(update, context):
    # LOGGER.info(update)
    tg_id = str(update.effective_user.id).strip()

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
        # print(FOOTPRINT[str(tg_id).strip()])
        return FOOTPRINT[str(tg_id).strip()]
    except KeyError:
        return None


def clear_footprint(tg_id):
    try:
        fp = get_footprint(tg_id)
        FOOTPRINT[str(tg_id).strip()] = {'command': fp['command'], 'subcommand': fp['subcommand']}
        # print("clear", FOOTPRINT)
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

    LOGGER.info(f"{FOOTPRINT=}")


def pre_handle(update, context):
    tg_id = update.effective_user.id
    db_member = security.authorize(tg_group_id=TG_GROUP_ID, tg_id=tg_id)

    if update.callback_query:
        text = "pressed with data=" + update.callback_query.data
    else:
        text = "entered " + update.message.text
    context.bot.send_message(chat_id=SUPER_ADMIN_TG_IDS[0], text=f"{db_member['tgId']} {text}")
    return db_member


# navigate
# handle /member
def handle_member(update, context):
    db_member = pre_handle(update, context)
    tg_id = db_member['tgId']

    keyboard = [
        [InlineKeyboardButton("睇某成員資料", callback_data='detail')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    db_members = member_service.list(tg_group_id=TG_GROUP_ID, mtypes=["ADMIN", "MEMBER", "COACH", "SUPER_ADMIN"], status=["ACTIVE"])
    members = formatter.format_members(db_members, show_tg_id=security.is_super_admin(db_member))
    if not members:
        members = "冇晒人lu.."

    set_footprint(tg_id=tg_id, command='member', subcommand='', clean_user_data=True)

    context.bot.send_message(chat_id=tg_id, text=members, reply_markup=reply_markup)


# handle subcommand
def _handle_member(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    if "detail" == fp['subcommand']:
        _handle_member_detail(update, context, authorized_member)
    elif "delete" == fp['subcommand']:
        _handle_member_delete(update, context, authorized_member)
    elif "approve" == fp['subcommand']:
        _handle_member_approve(update, context, authorized_member)
    elif "stats" == fp['subcommand']:
        _handle_member_stats(update, context, authorized_member)
    elif "name" == fp['subcommand']:
        _handle_member_name(update, context, authorized_member)
    elif "bday" == fp['subcommand']:
        _handle_member_bday(update, context, authorized_member)
    elif "go" == fp['subcommand']:
        _handle_member_default_attendance(update, context, authorized_member, attendance="GO")
    elif "not_go" == fp['subcommand']:
        _handle_member_default_attendance(update, context, authorized_member, attendance="NOT_GO")


def _handle_member_default_attendance(update, context, authorized_member, attendance):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (db_member := get_member(tg_id, context)):
        return

    db_members = member_service.update_default_attendance(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], attendance=attendance)
    if db_members:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update member default attendance")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': '', "choose": ""})


def get_member(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise MemberError("no fp")

    if 'member_id' in fp and (member_id := fp['member_id']):
        db_members = member_service.find_by_member_id(tg_group_id=TG_GROUP_ID, member_id=member_id, status=["ACTIVE"])
        if db_members:
            return db_members[0]

    if 'input' in fp and (name := fp['input']):
        db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if db_members:
            return db_members[0]

    context.bot.send_message(chat_id=tg_id, text="邊個? (請輸入成員名)")
    return None


def get_confirm_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise MemberError("no fp")

    if 'input' not in fp or (y_n := fp['input']) not in ["Y", "N", "y", "n"]:
        context.bot.send_message(chat_id=tg_id, text="真係要delete? (Y/N)")
        return None

    if y_n == "Y" or y_n == "y":
        return 1
    else:
        return 2


def get_event(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'event_id' in fp and (event_id := fp['event_id']):
        db_events = event_service.find_by_id(tg_group_id=TG_GROUP_ID, event_id=event_id, status=["ACTIVE"])
        if db_events:
            return db_events[0]

    if 'input' in fp and (date := fp['input']):
        date = f"{date} +0800"
        db_events = event_service.find_by_date(tg_group_id=TG_GROUP_ID, date=date, status=["ACTIVE"])
        if db_events and len(db_events) > 1:
            keyboard = [[InlineKeyboardButton(formatter.format_event(i, 1), callback_data=i['uuid'])] for i in
                        db_events]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(chat_id=tg_id, text="邊個?", reply_markup=reply_markup)
            set_footprint(tg_id=tg_id, command='event', data_map={"choose": "event_id", "input": ""})
            return None
        elif db_events and len(db_events) == 1:
            return db_events[0]

    context.bot.send_message(chat_id=tg_id, text="邊日? (Eg. 2020-05-31)")


def get_time_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (time := re.search(r'[0-2][0-9]:[0-5][0-9]', fp['input'])):
        return time[0]

    context.bot.send_message(chat_id=tg_id, text="幾點? 要跟番呢個格式 (Eg. 15:00)")


def get_date_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (date := re.search(r'\d{4}-[0-1][0-9]-[0-3][0-9]', fp['input'])):
        return f"{date[0]} +0800"

    context.bot.send_message(chat_id=tg_id, text="邊日? (Eg. 2020-05-30)")


def get_name_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (name := fp['input']):
        return name

    context.bot.send_message(chat_id=tg_id, text="咩名?")


def get_names_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (names := fp['input']):
        splitted_names = names.split(",")
        if len(splitted_names) == 1:
            splitted_names = names.split("，")
            if len(splitted_names) == 1:
                splitted_names = names.split(" ")
        return splitted_names

    context.bot.send_message(chat_id=tg_id, text="邊個? (可以打多幾個名, Eg: lydia, tszwai)")


def get_venue_input(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (venue := fp['input']):
        return venue

    context.bot.send_message(chat_id=tg_id, text="邊度? (Eg. 花墟/巴富街/花園街體育館/其他地方)")


def get_event_type(tg_id, context):
    if not (fp := get_footprint(tg_id)):
        raise EventError("no fp")

    if 'input' in fp and (etype := formatter.deformat_event_type(fp['input'])):
        return etype

    db_event_types = event_service.find_event_types(tg_group_id=TG_GROUP_ID, status=["ACTIVE"])
    if not db_event_types:
        context.bot.send_message(chat_id=tg_id, text="搵唔到相關活動")
        return

    db_event_types = "/".join([formatter.format_event_type(i) for i in db_event_types])

    context.bot.send_message(chat_id=tg_id, text=f"邊類? (Eg. {db_event_types})")


def _handle_member_detail(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    # validate
    if not (db_member := get_member(tg_id, context)):
        return

    text = formatter.format_member(db_member)
    if security.is_admin(authorized_member):
        keyboard = [
            [InlineKeyboardButton('delete', callback_data='delete'),
             InlineKeyboardButton('stats', callback_data='stats')],
            # todo handle command
            [InlineKeyboardButton('auto <唔黎>', callback_data='not_go'),
             # todo handle command
             InlineKeyboardButton('auto <黎>', callback_data='go')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton('stats', callback_data='stats')],
        ]

    if db_member['uuid'] == authorized_member['uuid']:
        keyboard += [
            # todo handle command
            [InlineKeyboardButton('改名', callback_data='name'),
             # todo handle command
             InlineKeyboardButton('改生日', callback_data='bday')],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_markup)

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'member_id': db_member['uuid'], 'input': ''})


def _handle_member_delete(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_member := get_member(tg_id, context)):
        return
    if not (confirm := get_confirm_input(tg_id, context)):
        return

    if confirm == 1:
        db_members = member_service.update_status(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], status="INACTIVE")
        if db_members:
            context.bot.send_message(chat_id=tg_id, text=f"deleted {db_members[0]['name']}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise MemberError("cannot delete member")
    else:
        context.bot.send_message(chat_id=tg_id, text="撤回")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': ''})


def _handle_member_approve(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # todo remove this
    fp = get_footprint(tg_id)

    # validate
    security.authorize_admin(authorized_member)
    if not (db_member := get_member(tg_id, context)):
        return
    if not (confirm := get_confirm_input(tg_id, context)):
        return

    if confirm == 1:
        db_members = member_service.update_status(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], status="ACTIVE")
        if db_members:
            context.bot.send_message(chat_id=db_members[0]['tgId'], text="歡迎你既加入")
            context.bot.send_message(chat_id=TG_GROUP_ID, text=f"歡迎 {db_members[0]['name']} 成功加入我地既一份子")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise MemberError("cannot approve member")
    else:
        context.bot.send_message(chat_id=tg_id, text="撤回")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': ''})


def _handle_member_stats(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (db_member := get_member(tg_id, context)):
        return

    db_stats = member_service.find_stats_by_member(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], status=["ACTIVE"])

    text = formatter.format_member_stats(db_stats[0])
    context.bot.send_message(chat_id=tg_id, text=text)

    # update footprint
    # set_footprint(tg_id=tg_id, command='member')


def _handle_member_name(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (db_member := get_member(tg_id, context)):
        return
    if not (name := get_name_input(tg_id, context)):
        return
    if " " in name:
        context.bot.send_message(chat_id=tg_id, text=f"名唔可以有空格, 打多次")
        return

    db_members = member_service.update_name(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], name=name)
    if db_members:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update member name")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': '', "choose": ""})


def _handle_member_bday(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (db_member := get_member(tg_id, context)):
        return
    if not (date := get_date_input(tg_id, context)):
        return

    db_members = member_service.update_bday(tg_group_id=TG_GROUP_ID, member_id=db_member['uuid'], bday=date)
    if db_members:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update member bday")

    # update footprint
    set_footprint(tg_id=tg_id, command='member', data_map={'input': '', "choose": ""})


def handle_me(update, context):
    db_member = pre_handle(update, context)
    tg_id = db_member['tgId']

    set_footprint(tg_id=tg_id, command='member', subcommand='', clean_user_data=True)
    set_footprint(tg_id=tg_id, command='member', data_map={'member_id': db_member['uuid']})
    _handle_member_detail(update, context, db_member)


def handle_event(update, context):
    db_member = pre_handle(update, context)
    tg_id = db_member['tgId']

    # find coming events
    db_events = event_service.find_coming(TG_GROUP_ID)

    # list coming event dates in yyyy-MM-dd
    dates = '\n'.join([ts.to_string_hkt(i['date'], format=ts.LOCAL_DATE_FORMAT) for i in db_events if i['date']])
    if not dates:
        dates = "最近冇event.."

    # set footprint
    set_footprint(tg_id=tg_id, command='event', subcommand='', clean_user_data=True)

    # send msg with buttons, list all by EVENT_TYPE
    keyboard = [
        [InlineKeyboardButton("睇某event資料", callback_data='detail')],
        [InlineKeyboardButton("睇唔同種類既event", callback_data='list'),
         InlineKeyboardButton("新event", callback_data='create')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=tg_id, text=dates, reply_markup=reply_markup)


def _handle_event(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id
    fp = get_footprint(tg_id)

    if "detail" == fp['subcommand']:
        _handle_event_detail(update, context, authorized_member)
    elif "list" == fp['subcommand']:
        _handle_event_list(update, context, authorized_member)
    elif "attend" == fp['subcommand']:
        _handle_event_attend(update, context, authorized_member)
    elif "delete" == fp['subcommand']:
        _handle_event_delete(update, context, authorized_member)
    elif "start" == fp['subcommand']:
        _handle_event_time(update, context, authorized_member, start=True)
    elif "end" == fp['subcommand']:
        _handle_event_time(update, context, authorized_member, start=False)
    elif "type" == fp['subcommand']:
        _handle_event_type(update, context, authorized_member)
    elif "date" == fp['subcommand']:
        _handle_event_date(update, context, authorized_member)
    elif "name" == fp['subcommand']:
        _handle_event_name(update, context, authorized_member)
    elif "venue" == fp['subcommand']:
        _handle_event_venue(update, context, authorized_member)
    elif "guest" == fp['subcommand']:
        _handle_event_guest(update, context, authorized_member)
    elif "go" == fp['subcommand']:
        _handle_event_attendance(update, context, authorized_member, "GO")
    elif "not_go" == fp['subcommand']:
        _handle_event_attendance(update, context, authorized_member, "NOT_GO")
    elif "not_sure" == fp['subcommand']:
        _handle_event_attendance(update, context, authorized_member, "NOT_SURE")
    elif "bring" == fp['subcommand']:
        _handle_event_ball(update, context, authorized_member, "bring")
    elif "get" == fp['subcommand']:
        _handle_event_ball(update, context, authorized_member, "get")
    elif "send" == fp['subcommand']:
        _handle_event_send(update, context, authorized_member)
    elif "create" == fp['subcommand']:
        _handle_event_create(update, context, authorized_member)
    elif "duplicate" == fp['subcommand']:
        _handle_event_duplicate(update, context, authorized_member)


def _handle_event_detail(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (db_event := get_event(tg_id, context)):
        return

    text = formatter.format_event(db_event, expand=3)
    if security.is_admin(authorized_member):
        keyboard = [
            [InlineKeyboardButton('改event種類', callback_data='type'),
             InlineKeyboardButton('幾點開始', callback_data='start'),
             InlineKeyboardButton('跟操', callback_data='guest'),
             ],
            [InlineKeyboardButton('改名', callback_data='name'),
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
            [InlineKeyboardButton('delete', callback_data='delete'),
             InlineKeyboardButton('duplicate', callback_data='duplicate'),
             InlineKeyboardButton('sd to gp', callback_data='send'),
             InlineKeyboardButton('F5', callback_data='detail'),
             ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=tg_id, text=text)

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={"event_id": db_event['uuid'], "input": "", "choose": ""})


# todo paging
def _handle_event_list(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    if not (etype := get_event_type(tg_id, context)):
        return

    db_events = event_service.find_by_event_type(tg_group_id=TG_GROUP_ID, etype=etype, status=["ACTIVE"])
    dates = '\n'.join([ts.to_string_hkt(i['date'], format=ts.LOCAL_DATE_FORMAT) for i in db_events if i['date']])
    if not dates:
        context.bot.send_message(chat_id=tg_id, text="搵唔到相關活動")
        return
    keyboard = [
        [InlineKeyboardButton("睇某event資料", callback_data='detail')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=tg_id, text=dates, reply_markup=reply_markup)

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={"input": ""})


def _handle_event_attend(update, context, authorized_member):
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
        keyboard = get_group_keyboard(event_id=event_id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=TG_GROUP_ID, text=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError(f"cannot attend event")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_delete(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (confirm := get_confirm_input(tg_id, context)):
        return

    if confirm == 1:
        db_events = event_service.update_status(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], status="INACTIVE")
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"deleted {ts.to_string_hkt(db_events[0]['date'], format=ts.LOCAL_DATE_FORMAT)}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot delete event")
    else:
        context.bot.send_message(chat_id=tg_id, text="撤回")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_time(update, context, authorized_member, start: bool):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (time := get_time_input(tg_id, context)):
        return

    if start:
        db_events = event_service.update_start_time(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], start_time=time)
    else:
        db_events = event_service.update_end_time(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], end_time=time)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左時間去: {time}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event time")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_type(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (etype := get_event_type(tg_id, context)):
        return

    db_events = event_service.update_type(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], etype=etype)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"轉左種類去 {formatter.format_event_type(etype)}")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event type")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_date(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (date := get_date_input(tg_id, context)):
        return

    db_events = event_service.update_date(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], date=date)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event type")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_name(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (name := get_name_input(tg_id, context)):
        return
    if " " in name:
        context.bot.send_message(chat_id=tg_id, text=f"名唔可以有空格, 打多次")
        return

    db_events = event_service.update_name(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], name=name)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event name")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_venue(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (venue := get_venue_input(tg_id, context)):
        return

    db_events = event_service.update_venue(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], venue=venue)
    if db_events:
        context.bot.send_message(chat_id=tg_id, text=f"OK")
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot update event venue")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_guest(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (names := get_names_input(tg_id, context)):
        return

    for name in names:
        name = name.strip()
        db_guest = member_service.find_or_create_guest(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_guest:
            context.bot.send_message(chat_id=tg_id, text=f"{name} 跟操失敗")
            continue

        db_events = event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], member_id=db_guest['uuid'], attendance="GO", reason='')
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"加左 {name}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event guest")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_attendance(update, context, authorized_member, attendance):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (names := get_names_input(tg_id, context)):
        return

    for name in names:
        name = name.strip()
        db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_members:
            context.bot.send_message(chat_id=tg_id, text=f"加唔到 {name}")
            continue

        db_events = event_service.take_attendance(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], member_id=db_members[0]['uuid'], attendance=attendance, reason='')
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"加左 {name}")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event member attendance")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_ball(update, context, authorized_member, action):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return
    if not (names := get_names_input(tg_id, context)):
        return

    for name in names:
        name = name.strip()
        db_members = member_service.find_by_name(tg_group_id=TG_GROUP_ID, name=name, status=["ACTIVE"])
        if not db_members:
            context.bot.send_message(chat_id=tg_id, text=f"加唔到 {name}")
            continue

        db_events = event_service.take_ball(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'], member_id=db_members[0]['uuid'], action=action)
        if db_events:
            context.bot.send_message(chat_id=tg_id, text=f"{name} Ok")
        else:
            context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
            raise EventError("cannot update event ball")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_send(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return

    if db_event:
        context.bot.send_message(chat_id=TG_GROUP_ID, text=formatter.format_event(db_event, expand=3))
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot send event")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def _handle_event_create(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)

    db_events = event_service.create(tg_group_id=TG_GROUP_ID)
    if db_events:
        set_footprint(tg_id=tg_id, command='event', data_map={'event_id': db_events[0]['uuid']})
        _handle_event_detail(update, context, authorized_member)
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot create event")

    # update footprint
    # set_footprint(tg_id=tg_id, command='event', data_map={'input': ''})


def _handle_event_duplicate(update, context, authorized_member):
    tg_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # validate
    security.authorize_admin(authorized_member)
    if not (db_event := get_event(tg_id, context)):
        return

    db_events = event_service.create(tg_group_id=TG_GROUP_ID, event_id=db_event['uuid'])
    if db_events:
        set_footprint(tg_id=tg_id, command='event', data_map={'event_id': db_events[0]['uuid']})
        _handle_event_detail(update, context, authorized_member)
    else:
        context.bot.send_message(chat_id=tg_id, text=f"我肚痛快啲帶我睇醫生")
        raise EventError("cannot duplicate event")

    # update footprint
    set_footprint(tg_id=tg_id, command='event', data_map={'input': '', "choose": ""})


def handle_button(update, context):
    query = update.callback_query
    db_member = pre_handle(update, context)
    tg_id = db_member['tgId']

    cache.delete()

    # handle group button
    bulk_data = query.data.split(";")
    if len(bulk_data) > 1:
        data_map = {
            'member_id': tg_id,
            'event_id': bulk_data[2],
            'attendance': bulk_data[3]
        }

        set_footprint(tg_id, command=bulk_data[0], subcommand=bulk_data[1], data_map=data_map)

        if "event" == bulk_data[0]:
            _handle_event(update, context, db_member)
    else:
        # handle non-group button
        fp = get_footprint(tg_id)

        if 'command' in fp:
            if "member" == fp['command']:
                set_footprint(tg_id, command='member', subcommand=query.data)
                _handle_member(update, context, db_member)
            elif "event" == fp['command']:
                if 'choose' in fp and 'event_id' == fp['choose']:
                    set_footprint(tg_id, command='event', data_map={fp['choose']: query.data})
                else:
                    set_footprint(tg_id, command='event', subcommand=query.data)

                _handle_event(update, context, db_member)

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()


def handle_input(update, context):
    db_member = pre_handle(update, context)
    tg_id = db_member['tgId']
    fp = get_footprint(tg_id)
    data_map = {'input': update.message.text.strip()}

    if fp and 'command' in fp:
        if "member" == fp['command']:
            set_footprint(tg_id, command='member', data_map=data_map)
            _handle_member(update, context, db_member)
        elif "event" == fp['command']:
            set_footprint(tg_id, command='event', data_map=data_map)
            _handle_event(update, context, db_member)
    else:
        context.bot.send_message(chat_id=tg_id, text="有咩事要搵我地admin?")


def error(update, context):
    tg_id = ""
    try:
        traceback.print_exc()
        tg_id = update.effective_user.id
        context.bot.send_message(chat_id=tg_id, text=str(context.error))
    except Exception as e:
        if DEBUG_MODE:
            traceback.print_exc()
    finally:
        for sa_tg_id in SUPER_ADMIN_TG_IDS:
            context.bot.send_message(chat_id=sa_tg_id, text=f"user({tg_id}): {context.error}")

