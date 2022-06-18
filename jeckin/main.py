import argparse
import configparser
import logging
import os.path
from argparse import ArgumentTypeError

import jeckin

logging.basicConfig(level=logging.DEBUG)


class ConfigType(argparse.FileType):
    def __call__(self, string):
        try:
            return super().__call__(string)
        except ArgumentTypeError:
            return string


def main():
    parser = argparse.ArgumentParser(
        prog='jeckin',
        description='HTTP-INJECT tool')
    parser.add_argument(
        'config', metavar='config',
        type=ConfigType('r'),
        help='genererate / load config file')

    args = parser.parse_args()

    if type(args.config) == str:
        print(f"generating config {args.config} from template")

        base_dir = os.path.dirname(__file__)
        path_target = args.config
        path_config_template = os.path.join(base_dir, "template-config.ini")
        with open(path_config_template, "r") as f:
            with open(path_target, "w") as ft:
                ft.write(f.read())
        print("OK")
        return

    config = configparser.RawConfigParser(allow_no_value=True)
    config.read_string(args.config.read())

    inject = dict(config.items('inject'))
    account = dict(config.items('ssh'))
    logging.info(inject)
    logging.info(account)

    jeckin_host = inject.get("host")
    jeckin_port = int(inject.get("port"))

    inject["ssh_host"] = account.get("host")
    inject["ssh_port"] = account.get("port")

    injector = jeckin.Injector(jeckin_host, jeckin_port, inject)
    injector.start()

    sshclient = jeckin.SSHClient(jeckin_host, jeckin_port, account.get("proxy_command"))
    sshclient.account = account
    sshclient.start()

    injector.stop()
    injector.join()
