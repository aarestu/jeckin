from logging import INFO

from jeckin.tunnel.handler.base_tunnel_handler import BaseTunnelHandler


class BaseTunnelProxyHandler(BaseTunnelHandler):
    proxy_host = "0.0.0.0"
    proxy_port = 8080
    sock_proxy = None

    def create_sock_proxy(self):
        self.log(INFO, f'Connecting to remote proxy {self.proxy_host} port {self.proxy_port}')

        self.sock_proxy = self._get_sock(self.proxy_host, self.proxy_port)
        return self.sock_proxy
