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

    if "dev" in args.env:
        config.read("./configs/dev.ini")
    elif "uat" in args.env:
        config.read("./configs/uat.ini")
    elif "prod" in args.env:
        config.read("./configs/prod.ini")
    elif "local" in args.env:
        config.read("./configs/local.ini")
    elif "minerva" in args.env:
        config.read("./configs/minerva.ini")
    else:
        raise SystemExit('Error: 1 invalid environment argument.')

    return args.env.split("-")


def reset():
    global config

    config = None


def get_string(primary_key: str, secondary_key: str):
    global config
    return str(config[primary_key][secondary_key])
