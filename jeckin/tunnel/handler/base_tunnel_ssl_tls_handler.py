import ssl

from jeckin.tunnel.handler.base_tunnel_proxy_handler import BaseTunnelProxyHandler


class BaseTunnelSSLTLSHandler(BaseTunnelProxyHandler):
    sni = "google.com"
    protocol = ""
    ssl_auth = False

    def get_protocol_ssl_tls(self, protocol_str=None):
        try:
            return getattr(ssl, f"PROTOCOL_{protocol_str}")
        except AttributeError as e:
            return None

    def warp_sock_to_ssl_tls(self, sock):
        protocol = self.get_protocol_ssl_tls(self.protocol)
        if not protocol:
            self.ssl_auth = (self.ssl_auth.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup']) if type(self.ssl_auth) == str else self.ssl_auth

            purpose = ssl.Purpose.SERVER_AUTH if self.ssl_auth else ssl.Purpose.CLIENT_AUTH
            return ssl.create_default_context(purpose=purpose) \
                .wrap_socket(sock, server_hostname=self.sni, do_handshake_on_connect=True)

        return ssl.SSLContext(protocol) \
            .wrap_socket(sock, server_hostname=self.sni, do_handshake_on_connect=True)

    def get_cert_pem(self):
        cert = self.sock_proxy.getpeercert(True)
        return ssl.DER_cert_to_PEM_cert(cert)
