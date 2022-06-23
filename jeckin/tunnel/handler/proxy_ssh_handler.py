from socketserver import StreamRequestHandler

from jeckin.tunnel.handler.base_tunnel_proxy_handler import BaseTunnelProxyHandler


def get_proxy_ssh_handler(config, ssh_account):
    class Handler(BaseTunnelProxyHandler, StreamRequestHandler):

        def setup(self):
            self.payload = config.get("payload").encode()
            self.target_host = ssh_account.get("host")
            self.target_port = int(ssh_account.get("port"))

            self.proxy_host = config.get("proxy_host")
            self.proxy_port = int(config.get("proxy_port"))

            super(Handler, self).setup()

        def handle(self):
            if not self.handle_init_conn(self.connection):
                return

            self.forward_data(self.sock_proxy, self.connection)

            self.sock_proxy.close()

    return Handler
