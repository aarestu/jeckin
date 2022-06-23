import ssl
from logging import INFO

from jeckin.tunnel.handler.base_tunnel_proxy_handler import BaseTunnelProxyHandler


class BaseTunnelSSLTLSHandler(BaseTunnelProxyHandler):
    sni = "google.com"
    protocol = ""

    def get_protocol_ssl_tls(self, protocol_str=None):
        try:
            return getattr(ssl, f"PROTOCOL_{protocol_str}")
        except AttributeError as e:
            self.log(INFO, "using default protocol TLSv1_2")
            return ssl.PROTOCOL_TLSv1_2

    def warp_sock_to_ssl_tls(self, sock):
        protocol = self.get_protocol_ssl_tls(self.protocol)
        return ssl.SSLContext(protocol) \
            .wrap_socket(sock, server_hostname=self.sni, do_handshake_on_connect=True)

    def get_cert_pem(self):
        cert = self.sock_proxy.getpeercert(True)
        return ssl.DER_cert_to_PEM_cert(cert)
