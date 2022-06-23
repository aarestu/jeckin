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

        def handle(self):
            init_data = self.connection.recv(self.buffer_size)

            while True:
                self.sock_proxy_http = self._get_sock(self.target_host, self.target_port)
                self.sock_proxy = self.warp_sock_to_ssl_tls(self.sock_proxy_http)
                self.log(INFO, self.get_cert_pem())
                self.send_payload(self.sock_proxy)
                data = self.sock_proxy.recv(self.buffer_size)
                if b"Switching Protocol" in data:
                    self.sock_proxy.send(init_data)
                    data = self.sock_proxy.recv(self.buffer_size)
                if data.find(b"SSH") == 0:
                    self.connection.send(data)
                    break
                time.sleep(5)

            self.forward_data(self.sock_proxy, self.connection)

            self.sock_proxy_http.close()
            self.sock_proxy.close()

    return Handler
