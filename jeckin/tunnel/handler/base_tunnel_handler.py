import random
import socket
import time
from errno import ECONNREFUSED, EHOSTUNREACH
from logging import INFO, DEBUG, ERROR

from paramiko.ssh_exception import NoValidConnectionsError
from paramiko.util import retry_on_signal
from select import select as ss

from jeckin.utils import get_logger
from jeckin.utils import loop_payload, families_and_addresses


class BaseTunnelHandler:
    buffer_size = 2 ** 15
    payload = "[real_raw]"
    target_host = "0.0.0.0"
    target_port = 22

    con_ce = b'HTTP/1.1 200 Connection established\r\n\r\n'

    def __init__(self, *args, **kwargs):
        self.logger = get_logger("jeckin.injector")
        super(BaseTunnelHandler, self).__init__(*args, **kwargs)

    def handle_init_conn(self, ssh_client):
        initial_con = self.read_res_sock(ssh_client)
        if not self.payload:
            self.payload = initial_con

        ok = False
        retry = 0

        while not ok:
            self.sock_proxy = self.create_sock_proxy()

            self.send_payload(self.sock_proxy)
            data = self.read_res_sock(self.sock_proxy)

            if data.find(b'HTTP/1.') == 0:
                if data.find(b"HTTP/1.1"): # GOOD SIGN! Switching Protocol
                    self.log(INFO, f'GOOD SIGN!')

                if initial_con.find(b'CONNECT') == 0:
                    ori_header = data.split(b"\r\n")[0].decode("ascii")
                    self.log(INFO, f'Replace {ori_header} -> {self.con_ce}')
                    ssh_client.send(self.con_ce)
                    initial_con = self.read_res_sock(ssh_client)

                self.sock_proxy.send(initial_con)
                data = self.read_res_sock(self.sock_proxy)

            if not self._is_valid_init_data(data):  # try to continue with initial con
                self.sock_proxy.send(initial_con)
                data = self.read_res_sock(self.sock_proxy)

            if self._is_valid_init_data(data):
                ssh_client.send(data)
                ok = True
                server_name = data.split(b"\r\n")[0].decode()
                self.log(INFO, f"OK! possible connect to {server_name}")

            if not ok:
                retry = min(retry + 1, random.randint(2, 20))

                self.close_proxy()

                self.log(INFO, f"waiting for {retry}s before reconnecting")
                time.sleep(retry)
        return ok

    def _is_valid_init_data(self, data):
        return data.find(b'SSH') == 0 or b"\r\n\r\nSSH" in data

    def _get_sock(self, hostname, port):
        sock = None
        errors = {}
        to_try = list(families_and_addresses(hostname, port))
        for af, addr in to_try:
            try:
                sock = socket.socket(af, socket.SOCK_STREAM)
                retry_on_signal(lambda: sock.connect(addr))
                break
            except socket.error as e:
                if e.errno not in (ECONNREFUSED, EHOSTUNREACH):
                    self.server.shutdown()
                    raise
                errors[addr] = e

        if len(errors) == len(to_try):
            raise NoValidConnectionsError(errors)

        return sock

    def send_payload(self, sock):
        for payload in loop_payload(self.payload, self.target_host, self.target_port):
            self.log(INFO, f"Payload sending: \n\n{payload}\n")
            sock.send(payload)

    def read_res_sock(self, sock):

        response = []

        while True:
            try:
                chunk = sock.recv(self.buffer_size)
                if not chunk:
                    break
                response.append(chunk)
                if b"\r\n" in chunk:
                    break
            except socket.error as e:
                self.log(DEBUG, e)
                break
        response = b''.join(response)
        return response

    def log(self, level, msg):
        self.logger.log(level, msg)

    def forward_data(self, remote, client):
        self.log(INFO, "forward data connection")
        try:
            while True:
                sockets = [remote, client]

                r, _, _ = ss(sockets, [], [])

                if client in r:
                    data = client.recv(self.buffer_size)
                    # self.log(INFO, b"fc:" + data)
                    if remote.send(data) <= 0:
                        break

                if remote in r:
                    data = remote.recv(self.buffer_size)
                    # self.log(INFO, b"fs:" + data)
                    if client.send(data) <= 0:
                        break
        except ConnectionError as e:
            self.log(DEBUG, e)

    def create_sock_proxy(self):
        self.log(INFO, f'Connecting to remote proxy {self.target_host} port {self.target_port}')
        self.sock_proxy = self._get_sock(self.target_host, self.target_port)
        return self.sock_proxy

    def close_proxy(self):
        if self.sock_proxy:
            self.sock_proxy.close()
            self.sock_proxy = None
