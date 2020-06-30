import re
import textwrap

from entities.exceptions import EventError
from utils import ts
from utils.ts import DATE_WITH_WEEK_FORMAT


def format_status(status):
    if "INACTIVE" in status:
        status = "已經唔係度"
    else:
        status = "仲在係度"
    return status


def format_member_type(mtype, expand: int):
    if "ADMIN" in mtype:
        if expand == 0:
            mtype = "*"
        else:
            mtype = "管理員"
    elif "COACH" in mtype:
        if expand == 0:
            mtype = "#"
        else:
            mtype = "教練"
    else:
        if expand == 0:
            mtype = ""
        else:
            mtype = "成員"
    return mtype


def format_attendance(attendance):
    if "GO" == attendance:
        attendance = "黎"
    elif "NOT_GO" == attendance:
        attendance = "唔黎"
    else:
        attendance = ""
    return attendance


def format_member(member):
    mtype = format_member_type(member['type'], expand=1)
    status = format_status(member['status'])
    if 'bornAt' not in member or not (bornAt := ts.to_string_hkt(member['bornAt'])):
        bornAt = "未set"
    if 'defaultAttendance' not in member or not (attendance := format_attendance(member['defaultAttendance'])):
        attendance = "未set"

    return textwrap.dedent(f"""
        {member['name']} ({mtype})
        加入: {ts.to_string_hkt(member['createAt'])}
        生日: {bornAt}
        狀態: {status}
        自動: {attendance}
    """).strip()


def format_members(members, show_tg_id: bool = False):
    members = sorted(members, key=lambda item: item['name'])
    if show_tg_id:
        members = [m['name'] + f"({m['tgId']})" + format_member_type(m['type'], expand=0) for m in members]
    else:
        members = [m['name'] + format_member_type(m['type'], expand=0) for m in members]
    return '\n'.join(members) + "\n\n*=admin, #=coach"


def format_event_type(etype):
    if "PRACTICE" == etype:
        return "練習"
    elif "COMPETITION" == etype:
        return "比賽"
    elif "FDLY" == etype:
        return "FDLY"
    elif "GATHERING" == etype:
        return "聚會"
    else:
        return ""


def deformat_event_type(etype):
    if "練習" in etype:
        return "PRACTICE"
    elif "比賽" in etype:
        return "COMPETITION"
    elif re.search(r'[Ff][Dd][Ll][Yy]', etype) or "友誼賽" in etype:
        return "FDLY"
    elif "聚會" in etype or "玩" in etype:
        return "GATHERING"
    else:
        return ""


# [574] 記得帶水 時間未知 練習
# 2020-03-28 (星期6) 巴富街 19:30 - 22:00
#
# 帶波黎(Nic, Serena, Sin Yau), 拎波走()
#
# 去: 3 (2), 跟操: 0, 唔去: 6, 未知: 0, 未睇MSG: 5

# [id:591] 記得帶水 時間未知 練習
# 2020-03-21 (星期6) 巴富街 19:30 - 22:00
#
# 帶波黎(Gloria, Ngasze), 拎波走()
#
# 去: Christine, Gloria, Kaylaaaaa, Ngasze, Nic, Sin Yau, Siutin, vic
# 去(教練): In, Ming
# 跟操:
#
# 唔去: Fancy, Joanne, Serena(乜乜痛), Yan(*自己入原因), Yuli(*自己入原因)
# 未知:
#
# 雲遊太空中: MaN
def format_event(event, expand: int):
    if expand not in range(1, 4):
        raise EventError(f"invalid expand({expand})")

    if expand == 1:
        return f"{event['name']} {format_event_type(event['type'])} {event['venue']} {event['start']}-{event['end']}"

    who_bring_ball = set()
    who_get_ball = set()
    who_go = set()
    who_coach_go = set()
    who_guest_go = set()
    who_not_go = set()
    who_not_sure = set()

    for member in event['members']:
        name = member['name']
        reason = ''
        if 'reason' in member['attendance']:
            reason = member['attendance']['reason'].strip()
        text = name
        if reason:
            text = f"{name}({reason})"
        mtype = member['type']

        if 'bring' in member['attendance'] and member['attendance']['bring']:
            who_bring_ball.add(name)
        elif 'get' in member['attendance'] and member['attendance']['get']:
            who_get_ball.add(name)

        if 'name' in member['attendance']:
            if member['attendance']['name'] == "GO":
                if mtype == "COACH":
                    who_coach_go.add(text)
                elif mtype == "GUEST":
                    who_guest_go.add(text)
                else:
                    who_go.add(text)
            elif member['attendance']['name'] == "NOT_GO":
                who_not_go.add(text)
            else:
                who_not_sure.add(name)
        else:
            who_not_sure.add(name)

    if expand == 3:
        detail = f"""去({len(who_go)}): {', '.join(who_go)}
            去(教練,{len(who_coach_go)}): {', '.join(who_coach_go)}
            跟操({len(who_guest_go)}): {', '.join(who_guest_go)}
            
            唔去({len(who_not_go)}): {', '.join(who_not_go)}
            未知({len(who_not_sure)}): {', '.join(who_not_sure)}
        """
    else:
        detail = f"去: {len(who_go)} ({len(who_coach_go)}), 跟操: {len(who_guest_go)}, 唔去: {len(who_not_go)}, 未知: {len(who_not_sure)}"

    return textwrap.dedent(f"""
            {event['name']} ({format_event_type(event['type'])}) 
            {ts.to_string_hkt(event['date'], DATE_WITH_WEEK_FORMAT)} {event['venue']} {event['start']}-{event['end']}
            
            帶波黎({', '.join(who_bring_ball)}), 拎波走({', '.join(who_get_ball)})

            {detail}
        """).strip()


def format_member_stats(stats: dict):
    attend_count = stats['attend_count']
    event_count = stats['event_count']
    bring_count = stats['bring_count']
    get_count = stats['get_count']
    attend_rate = 0
    if event_count:
        attend_rate = int(attend_count * 10000 / event_count) / 100

    return textwrap.dedent(f"""
                出席率(%): {attend_rate} 
                出席次數: {attend_count} 
                拎波次數: {get_count} 
                帶波次數: {bring_count} 
                活動數量: {event_count} 

                *由加入起計
            """).strip()


def format_member_group_stats(stats: dict):
    astats = "出席排名(高>低): \n" + stats['attend_stats'].strip()
    bstats = "拎波排名(高>低): \n" + stats['bring_stats'].strip()
    gstats = "帶波排名(高>低): \n" + stats['get_stats'].strip()

    return astats + "\n\n" + bstats + "\n\n" + gstats


# Yield successive n-sized
# chunks from l.
def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

