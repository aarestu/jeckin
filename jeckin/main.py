import argparse
import configparser
import logging
import os.path
import threading
import time
from argparse import ArgumentTypeError
from logging import DEBUG, INFO, NOTSET, ERROR
from socketserver import ThreadingTCPServer

import paramiko

import jeckin
from jeckin.utils import get_logger

logging.basicConfig(level=INFO)


class ConfigType(argparse.FileType):
    def __call__(self, string):
        try:
            return super().__call__(string)
        except ArgumentTypeError:
            return string

def get_handler_f(tunnel_type):
    if tunnel_type is jeckin.TunnelType.direct_ssh:
        return jeckin.get_direct_ssh_handler
    elif tunnel_type is jeckin.TunnelType.direct_ssl_tls_ssh:
        return jeckin.get_direct_ssl_tls_ssh_handler
    elif tunnel_type is jeckin.TunnelType.proxy_ssh:
        return jeckin.get_proxy_ssh_handler
    elif tunnel_type is jeckin.TunnelType.proxy_ssl_tls_ssh:
        return jeckin.get_proxy_ssltls_ssh_handler



def main():
    parser = argparse.ArgumentParser(
        prog='jeckin',
        description='HTTP-INJECT tool')
    parser.add_argument(
        'config', metavar='config',
        type=ConfigType('r'),
        help='genererate / load config file')

    args = parser.parse_args()

    logger = get_logger("jeckin.main")

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
    ssh_account = dict(config.items('ssh'))

    logging.info(inject)
    logging.info(ssh_account)

    tunnel_type = jeckin.get_tunnel_type(inject.get("mode"))
    tunnel_f = jeckin.get_handler_f(tunnel_type)

    while True:
        with ThreadingTCPServer(('', 0), tunnel_f(inject, ssh_account)) as server:
            server_injector = ((server.address_family, server.socket_type),
                               ('127.0.0.1', server.server_address[1]))

            ssh = jeckin.SSHClient()
            ssh._args = (
                server_injector,
                ssh_account.get("host"),
                ssh_account.get("port"),
                ssh_account.get("username"),
                ssh_account.get("password")
            )

            tserver = threading.Thread(target=server.serve_forever)
            tserver.start()

            # ssh.open(*ssh._args)
            # tserver.join()

            try:
                ssh.open(*ssh._args)

                if ssh.is_connected:
                    socks_addr, socks_port = ("127.0.0.1", 8010)
                    with jeckin.IPv6EnabledTCPServer((socks_addr, socks_port), jeckin.SOCKS5RequestHandler) as proxy:
                        proxy.ssh = ssh
                        proxy.serve_forever()
            except paramiko.ssh_exception.SSHException as e:
                logger.log(DEBUG, e)


            server.shutdown()
            time.sleep(5)


