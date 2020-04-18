import configparser
import sys
from argparse import ArgumentParser
import os
config = configparser.ConfigParser()


def init():
    global config

    parser = ArgumentParser(prog="main.py", usage=None, description=None, epilog=None)
    parser.add_argument("-e", "--env", help="set environment, should be (forward/dev)", dest="env", default="default")

    args = parser.parse_args()
    config = configparser.ConfigParser()

    if args.env == "dev":
        config.read("./configs/dev.ini")
    elif args.env == "uat":
        config.read("./configs/uat.ini")
    elif args.env == "prod":
        config.read("./configs/prod.ini")
    elif args.env == "local":
        config.read("./configs/local.ini")
    elif args.env == "minerva":
        config.read("./configs/minerva.ini")
    else:
        raise SystemExit('Error: 1 invalid environment argument.')
    

def reset():
    global config

    config = None


def get_string(primary_key: str, secondary_key: str):
    global config
    return str(config[primary_key][secondary_key])
