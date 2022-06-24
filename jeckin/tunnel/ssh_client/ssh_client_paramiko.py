import socket
from logging import INFO, WARNING

import paramiko

from jeckin.utils import get_logger


class SSHClientParamiko(paramiko.SSHClient):
    sock = None

    _args = None
    _kwargs = None

    def __init__(self):
        super(SSHClientParamiko, self).__init__()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.set_log_channel("jeckin.transport")
        self.logger = get_logger("jeckin.ssh")
        self.logger.setLevel(INFO)

    def open(self, server_injector, host, port, username, password, **kwargs):
        try:
            self.sock = socket.socket(*server_injector[0])
            self.sock.connect(server_injector[1])

            if not kwargs.get("sock"):
                kwargs["sock"] = self.sock
            kwargs["banner_timeout"] = 100
            _kwargs = kwargs
            _args = (host, port, username, password)
            self.connect(*_args, **_kwargs)

            self.get_transport().set_keepalive(5)
        except paramiko.ssh_exception.SSHException as e:
            self.log(WARNING, e)

    @property
    def is_connected(self):
        return self.get_transport().active and self.get_transport().authenticated if self.get_transport() else False

    def log(self, level, msg):
        self.logger.log(level, msg)
