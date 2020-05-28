# {
#   "tgGroupId": "-1001231961771",
#   "tgId": "331772066",
#   "name": "Siutin",
#   "updateAt": 1548086346883,
#   "type": "SUPER_ADMIN",
#   "uuid": "74ed2535-0218-4b01-b3b1-49f7c61e7f87",
#   "createAt": 1548086346883,
#   "status": "ACTIVE"
# }
import textwrap
from itertools import groupby
from operator import itemgetter

from utils import ts
from utils.ts import DATE_WITH_WEEK_FORMAT


def format_member(member):
    if "ADMIN" in member['type']:
        mtype = "管理員"
    elif "COACH" in member['type']:
        mtype = "教練"
    else:
        mtype = "成員"

    if "INACTIVE" in member['status']:
        status = "已經唔係度"
    else:
        status = "仲在係度"

    return textwrap.dedent(f"""
        {member['name']} ({mtype})
        加入日期: {ts.to_string(member['createAt'])}
        狀態: {status}
    """).strip()


def format_members(members):
    members = sorted(members, key=lambda item: item['name'])
    return '\n'.join([m['name'] + format_member_type(m['type']) for m in members])


def format_member_type(mtype):
    if "ADMIN" in mtype:
        return "*"
    elif "COACH" == mtype:
        return "#"
    else:
        return ""


def format_event_type(mtype):
    if "PRACTICE" == mtype:
        return "練習"
    elif "COMPETITION" == mtype:
        return "比賽"
    elif "FDLY" == mtype:
        return "友誼賽"
    elif "GATHERING" == mtype:
        return "聚會"
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
def format_event(event, expand: bool = False):
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
        if reason in member['attendance']:
            reason = member['attendance']['reason'].strip()
        mtype = member['type']

        if 'bring' in member['attendance'] and member['attendance']['bring']:
            who_bring_ball.add(name)
        elif 'get' in member['attendance'] and member['attendance']['get']:
            who_get_ball.add(name)

        if member['attendance']['name'] == "GO":
            text = name
            if reason:
                text = f"{name}({reason})"

            if mtype == "COACH":
                who_coach_go.add(text)
            elif mtype == "GUEST":
                who_guest_go.add(text)
            else:
                who_go.add(text)
        elif member['attendance']['name'] == "NOT_GO":
            text = name
            if reason:
                text = f"{name}({reason})"
            who_not_go.add(text)
        else:
            who_not_sure.add(name)

    if expand:
        detail = f"""去: {', '.join(who_go)}
            去(教練): {', '.join(who_coach_go)}
            跟操: {', '.join(who_guest_go)}
            
            唔去: {', '.join(who_not_go)}
            未知: {', '.join(who_not_sure)}
        """

    else:
        detail = f"去: {len(who_go)} ({len(who_coach_go)}), 跟操: {len(who_guest_go)}, 唔去: {len(who_not_go)}, 未知: {len(who_not_sure)}"

    return textwrap.dedent(f"""
            {event['name']} ({format_event_type(event['type'])}) 
            {ts.to_string(event['date'], DATE_WITH_WEEK_FORMAT)} {event['venue']} {event['start']}-{event['end']}
            
            帶波黎({', '.join(who_bring_ball)}), 拎波走({', '.join(who_get_ball)})

            {detail}
        """).strip()


def test():
    test_str = {
        "date": "1539129600000",
        "venue": "朗屏體育館",
        "members": [
            {
                "attendance": {
                    "name": "GO",
                    "reason": "late",
                    "bring": True,
                    "get": True
                },
                "tgGroupId": "-1001231961771",
                "name": "Yan",
                "tgId": "617799273",
                "updateAt": 1548086347317,
                "type": "GUEST",
                "uuid": "78928faf-029b-445c-99de-561e9e46b76e",
                "createAt": 1548086347317,
                "status": "ACTIVE"
            },
            {
                "attendance": {
                    "name": "GO",
                    "reason": "",
                    "bring": False,
                    "get": False
                },
                "tgGroupId": "-1001231961771",
                "name": "In",
                "tgId": "617799273",
                "updateAt": 1548086347317,
                "type": "COACH",
                "uuid": "78928faf-029b-445c-99de-561e9e46b76e",
                "createAt": 1548086347317,
                "status": "ACTIVE"
            },
            {
                "attendance": {
                    "name": "NOT_GO",
                    "reason": "not go",
                    "bring": False,
                    "get": False
                },
                "tgGroupId": "-1001231961771",
                "name": "Ngasze",
                "tgId": "229071615",
                "updateAt": 1548086346999,
                "type": "MEMBER",
                "uuid": "e5dfab39-379f-472c-ae88-9f64f3c43f7a",
                "createAt": 1548086346999,
                "status": "ACTIVE"
            },
            {
                "attendance": {
                    "name": "NOT_SURE",
                    "reason": "",
                    "bring": False,
                    "get": False
                },
                "tgGroupId": "-1001231961771",
                "name": "MaN",
                "tgId": "675035601",
                "updateAt": 1548086347110,
                "type": "MEMBER",
                "uuid": "973aa170-78e8-491d-b972-67a3d521395f",
                "createAt": 1548086347110,
                "status": "ACTIVE"
            },
        ],
        "name": "LIMIT",
        "start": "20:00",
        "updateAt": 1548086343683,
        "end": "23:00",
        "type": "PRACTICE",
        "uuid": "77c0eb02-e8e5-4cd7-b8d1-65cb82b94155",
        "createAt": 1548086343683,
        "status": "ACTIVE"
    }
    print("---")
    print(format_event(test_str, True))
    print("---")
    print(format_event(test_str, False))
    print("---")


# Yield successive n-sized
# chunks from l.
def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

