import time
from logging import INFO
from socketserver import StreamRequestHandler

from jeckin.tunnel.handler.base_tunnel_ssl_tls_handler import BaseTunnelSSLTLSHandler


def get_direct_ssl_tls_ssh_handler(config, ssh_account):
    class Handler(BaseTunnelSSLTLSHandler, StreamRequestHandler):

        def setup(self):
            self.target_host = ssh_account.get("host")
            self.target_port = int(ssh_account.get("port"))
            self.payload = config.get("payload", self.payload).encode()
            self.sni = config.get("sni")
            self.protocol = config.get("protocol")
            if not self.sni:
                raise ValueError("sni required")
            super(Handler, self).setup()

        def create_sock_proxy(self):
            self.log(INFO, f'Connecting to remote {self.target_host} port {self.target_port}')

            self.sock_proxy_http = self._get_sock(self.target_host, self.target_port)
            self.sock_proxy = self.warp_sock_to_ssl_tls(self.sock_proxy_http)
            return self.sock_proxy

        def handle(self):
            if not self.handle_init_conn(self.connection):
                return

            self.log(INFO, self.get_cert_pem())

            self.forward_data(self.sock_proxy, self.connection)
            self.close_proxy()

        def close_proxy(self):
            if self.sock_proxy_http:
                self.sock_proxy_http.close()
                self.sock_proxy_http = None
            super(Handler, self).close_proxy()

    return Handler
