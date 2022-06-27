import argparse
import configparser
import logging
import os.path
import signal
import threading
import time
from argparse import ArgumentTypeError
from logging import INFO, DEBUG
from socketserver import ThreadingTCPServer

import paramiko

import jeckin

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
    parser = argparse.ArgumentParser(prog='jeckin', description='HTTP-INJECT tool')
    parser.add_argument('config', metavar='config', type=ConfigType('r'), help='genererate / load config file')
    parser.add_argument('--sshpass-corkscrew', action=argparse.BooleanOptionalAction, default=False)

    args = parser.parse_args()

    logger = jeckin.get_logger("jeckin.main")

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

    server = ThreadingTCPServer(('', 0), tunnel_f(inject, ssh_account))
    server_injector = ((server.address_family, server.socket_type), ('127.0.0.1', server.server_address[1]))
    server.allow_reuse_address = True

    tserver = threading.Thread(target=server.serve_forever)
    tserver.start()


    def handler_stop_signals(signum, frame):
        exit(-1)

    signal.signal(signal.SIGINT, handler_stop_signals)
    signal.signal(signal.SIGTERM, handler_stop_signals)

    if args.sshpass_corkscrew:
        ssh = jeckin.SSHClientSSHPassCorkscrew('127.0.0.1', server.server_address[1], inject.get("socks_port"))
        ssh.account = ssh_account
        ssh.start()
        return

    socks_addr, socks_port = ("127.0.0.1", int(inject.get("socks_port")))
    proxy = jeckin.IPv6EnabledTCPServer((socks_addr, socks_port), jeckin.SOCKS5RequestHandler)

    ssh = jeckin.SSHClientParamiko()
    ssh._args = (server_injector, ssh_account.get("host"), ssh_account.get("port"), ssh_account.get("username"),
                 ssh_account.get("password"))

    proxy.ssh = ssh

    tproxy = threading.Thread(target=proxy.serve_forever)
    tproxy.start()

    while True:
        time.sleep(5)
        if ssh.is_connected:
            continue
        try:
            ssh.open(*ssh._args)
        except paramiko.ssh_exception.SSHException as e:
            logger.log(INFO, e)
