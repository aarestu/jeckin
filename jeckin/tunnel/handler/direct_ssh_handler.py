from logging import ERROR
from socketserver import StreamRequestHandler

from jeckin.tunnel.handler.base_tunnel_handler import BaseTunnelHandler


def get_direct_ssh_handler(config, ssh_account):
    class Handler(BaseTunnelHandler, StreamRequestHandler):
        def setup(self):
            self.target_host = ssh_account.get("host")
            self.target_port = int(ssh_account.get("port"))
            # self.payload = config.get("payload", self.payload).encode()
            self.payload = None
            super(Handler, self).setup()

        def handle(self):

            if not self.handle_init_conn(self.connection):
                return

            try:
                self.forward_data(self.sock_proxy, self.connection)
            except ConnectionResetError as e:
                self.log(ERROR, b"Connection Reset")

            self.sock_proxy.close()

    return Handler
