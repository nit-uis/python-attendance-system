

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

from utils import ts


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
    """)
