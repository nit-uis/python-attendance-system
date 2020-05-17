# python-member


data = {
    "tg_id": {

    }
}

/member detail id
member(command, id) {
  input validation
  todo()
}

handle_callback {
  join command using data[tg_id] + data
  pass command
  clear data[tg_id]
}

handle_input {
  join command using data[tg_id] + data
  pass command
  clear data[tg_id]
}



/admin
    startreceive
    stopreceive
    resetsleep
    stat


/me
    name Input
    defAttend ATTENDANCE EXPIRY_DATE_TYPE Input


/member MEMBER_ID*


/coach COACH_ID*


/guest GUEST_ID*


/delete TYPE ID
/new TYPE ID

/event
    all|FDLY|COMPETITION
    create
    EVENT_ID removeAttend|takeAttendGo|takeAttendNotGo MEMBER_ID
    EVENT_ID repeat|send
    EVENT_ID delete yes|no
    EVENT_ID type EVENT_TYPE
    EVENT_ID date|startTime|endTime|venue|bringBall|getBall|guest Input

/attendance EVENT_ID ATTENDANCE