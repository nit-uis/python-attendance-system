# python-member

1 profile serve 1 group

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
