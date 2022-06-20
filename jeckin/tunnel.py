import enum
import logging
import re
from select import select as ss
import socket
import ssl
import threading
import time


class TunnelType(enum.Enum):
    direct = 1
    direct_to_ssl_tls = 2
    direct_to_ssl_tls_payload = 3
    proxy = 4
    proxy_to_ssl_tls = 5
    proxy_to_ssl_tls_payload = 6


class Tunnel(threading.Thread):
    def __init__(self, socket_accept, config=None):
        super(Tunnel, self).__init__()

        self._stop_event = threading.Event()
        if type(config) != dict:
            config = {}

        self.socket_accept = socket_accept
        self.tunnel_type = config.get("mode", TunnelType.direct)

        self.buffer_size = 65535
        self.timeout = 3

        self.socket_tunnel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.config = config
        self.payload = config.get("payload", "").encode()
        self.sni = config.get("sni")
        self.do_handshake_on_connect = config.get("do_handshake_on_connect", True)

    def get_socket_client(self):
        socket_client, null = self.socket_accept
        self.init_socket_client_request = socket_client.recv(self.buffer_size)
        if not self.payload:
            self.payload = self.init_socket_client_request
        find_dest_host = re.findall(rb'([^\s]+):([^\s]+)', self.init_socket_client_request)
        if find_dest_host:
            self.host, self.port = find_dest_host[0]
            self.host, self.port = str(self.host.decode()), int(self.port)
        else:
            self.host, self.port = (self.config.get("ssh_host"), int(self.config.get("ssh_port")))

        return socket_client

    def payload_decode(self, payload):

        payload = payload.replace(b'[real_raw]', b'[raw][crlf][crlf]')
        payload = payload.replace(b'[raw]', b'[method] [host_port] [protocol]')
        payload = payload.replace(b'[method]', b'CONNECT')
        payload = payload.replace(b'[host_port]', b'[host]:[port]')
        payload = payload.replace(b'[host]', str(self.host).encode())
        payload = payload.replace(b'[port]', str(self.port).encode())
        payload = payload.replace(b'[protocol]', b'HTTP/1.1')
        payload = payload.replace(b'[user-agent]', b'User-Agent: Chrome/1.1.3')
        payload = payload.replace(b'[keep-alive]', b'Connection: Keep-Alive')
        payload = payload.replace(b'[close]', b'Connection: Close')
        payload = payload.replace(b'[crlf]', b'[cr][lf]')
        payload = payload.replace(b'[lfcr]', b'[lf][cr]')
        payload = payload.replace(b'[cr]', b'\r')
        payload = payload.replace(b'[lf]', b'\n')

        return payload

    def send_payload(self, payload_encode=b''):

        payload_split = payload_encode.split(b'[split]')

        for i in range(len(payload_split)):
            if i > 0:
                time.sleep(0.200)
            payload = self.payload_decode(payload_split[i])
            logging.debug(f"Payload send: \n\n{payload}\n")
            self.socket_tunnel.sendall(payload)

    def handler(self):
        sockets = [self.socket_tunnel, self.socket_client]
        timeout = 0
        self.socket_client.sendall(
            b'HTTP/1.1 200 Connection established\r\n\r\n')
        logging.info('Connection established')
        while True:
            timeout += 1
            socket_io, null, errors = ss(sockets, [], sockets, 3)
            if errors:
                break
            if socket_io:
                for socket in socket_io:
                    try:
                        data = socket.recv(self.buffer_size)
                        if not data:
                            break
                        if socket is self.socket_tunnel:
                            self.socket_client.sendall(data)
                        elif socket is self.socket_client:
                            self.socket_tunnel.sendall(data)
                        timeout = 0
                    except Exception as e:
                        logging.error(e)
                        break

            if timeout == 30:
                break

    def handler_proxy(self):
        sockets = [self.socket_tunnel, self.socket_client]
        timeout = 0
        logging.info('Connection')
        while True:
            i_sockets, _, errors = ss(sockets, [], [])
            if errors:
                break

            timeout += 1

            if not i_sockets:
                break

            for socket in i_sockets:

                try:
                    data = socket.recv(self.buffer_size)

                    if len(data) <= 0:
                        break
                    if socket is self.socket_tunnel:
                        if data.find(b'HTTP/1.') == 0:
                            ori_header = data.split(b"\r\n")[0].decode("ascii")
                            logging.info(f'Replace {ori_header} -> HTTP/1.1 200 Connection established')
                            data = b'HTTP/1.1 200 Connection established\r\n\r\n'
                        self.socket_client.send(data)
                    elif socket is self.socket_client:

                        if data.split(b" ")[0] == self.init_socket_client_request.split(b" ")[0]:
                            self.send_payload(self.payload)
                            continue
                        self.socket_tunnel.send(data)
                    timeout = 0
                except Exception as e:
                    logging.error(e)
                    break


            if timeout == 30:
                break

    def convert_response(self, response):

        response = response.replace('\r', '').rstrip() + '\n\n'

        if response.startswith('HTTP'):
            response = '\n\n|   {}\n'.format(response.replace('\n', '\n|   '))
        else:
            response = '[W2]\n\n{}\n'.format(
                re.sub(r'\s+', ' ', response.replace('\n', '[CC][Y1]\\n[W2]')))

        return response

    def get_proxy(self):
        proxy_host = self.config.get("proxy_host")
        proxy_port = self.config.get("proxy_port")

        if not (proxy_host and proxy_port):
            raise ValueError("fatal error: please define proxy_host and proxy_port config")
        return proxy_host, int(proxy_port)

    def certificate(self):

        logging.info('Certificate:\n\n{}'.format(
            ssl.DER_cert_to_PEM_cert(self.socket_tunnel.getpeercert(True))))

    def get_protocol_ssl_tls(self, protocol_str=None):
        try:
            return getattr(ssl, f"PROTOCOL_{protocol_str}")
        except AttributeError:
            logging.warning("using default protocol TSLv1_2")
            return ssl.PROTOCOL_TLSv1_2

    def tunnel_direct(self):

        try:
            if self.host and self.port:
                logging.info(f'Connecting to {self.host} port {self.port}')
                self.socket_tunnel.connect((self.host, self.port))
                self.send_payload(self.payload)
                self.handler()
        except socket.timeout:
            pass
        except socket.error:
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def tunnel_direct_to_ssl_tsl(self):
        if not self.sni:
            raise ValueError("fatal error: please define sni config")

        try:

            if self.host and self.port:
                logging.info('Connecting to {} port {}'.format(self.host, self.port))
                self.socket_tunnel.connect((self.host, self.port))
                logging.info(f'Server name indication: {self.sni}')
                protocol = self.get_protocol_ssl_tls(self.config.get("protocol_ssl_tls"))
                self.socket_tunnel = ssl.SSLContext(protocol).wrap_socket(
                    self.socket_tunnel, server_hostname=self.sni, do_handshake_on_connect=self.do_handshake_on_connect)
                self.certificate()
                self.handler()
        except socket.timeout:
            pass
        except socket.error:
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def tunnel_direct_to_ssl_tsl_payload(self):
        if not self.sni:
            raise ValueError("fatal error: please define sni config")

        try:

            if self.host and self.port:
                logging.info('Connecting to {} port {}'.format(self.host, self.port))
                self.socket_tunnel.connect((self.host, self.port))
                logging.info(f'Server name indication: {self.sni}')
                protocol = self.get_protocol_ssl_tls(self.config.get("protocol_ssl_tls"))
                self.socket_tunnel = ssl.SSLContext(protocol).wrap_socket(
                    self.socket_tunnel, server_hostname=self.sni, do_handshake_on_connect=self.do_handshake_on_connect)
                self.certificate()
                self.send_payload(self.payload)
                self.handler()
        except socket.timeout:
            pass
        except socket.error:
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def tunnel_remote_proxy(self):

        try:

            if self.host and self.port:
                proxy_host, proxy_port = self.get_proxy()

                logging.info(f'Connecting to remote proxy {proxy_host} port {proxy_port}')
                self.socket_tunnel.connect((proxy_host, proxy_port))
                logging.info(f'Connecting to {self.host} port {self.port}')
                self.send_payload(self.payload)
                self.handler_proxy()
        except socket.timeout as e:
            raise (e)
            pass
        except socket.error as e:
            raise (e)
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def tunnel_proxy_to_ssl_tls(self):
        if not self.sni:
            raise ValueError("fatal error: please define sni config")

        try:
            if self.host and self.port:
                proxy_host, proxy_port = self.get_proxy()

                logging.info(f'Connecting to remote proxy {proxy_host} port {proxy_port}')
                self.socket_tunnel.connect((proxy_host, proxy_port))

                logging.info(f'Server name indication: {self.sni}')
                protocol = self.get_protocol_ssl_tls(self.config.get("protocol_ssl_tls"))
                self.socket_tunnel = ssl.SSLContext(protocol).wrap_socket(
                    self.socket_tunnel, server_hostname=self.sni,
                    do_handshake_on_connect=self.do_handshake_on_connect)

                self.certificate()
                self.handler()
        except socket.timeout:
            pass
        except socket.error:
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def tunnel_proxy_to_ssl_tls_payload(self):
        if not self.sni:
            raise ValueError("fatal error: please define sni config")

        try:

            if self.host and self.port:
                proxy_host, proxy_port = self.get_proxy()
                payload = self.payload

                logging.info(f'Connecting to remote proxy {proxy_host} port {proxy_port}')
                self.socket_tunnel.connect((proxy_host, proxy_port))

                logging.info(f'Server name indication: {self.sni}')
                protocol = self.get_protocol_ssl_tls(self.config.get("protocol_ssl_tls"))

                self.socket_tunnel = ssl.SSLContext(protocol).wrap_socket(
                    self.socket_tunnel, server_hostname=self.sni,
                    do_handshake_on_connect=self.do_handshake_on_connect)

                self.certificate()
                self.send_payload(payload)
                self.handler()
        except socket.timeout as e:
            logging.warning(e)
            pass
        except socket.error as e:
            logging.warning(e)
            pass
        finally:
            self.socket_tunnel.close()
            self.socket_client.close()

    def get_tunnel_type(self):
        if type(self.tunnel_type) != TunnelType:
            try:
                self.tunnel_type = TunnelType[self.tunnel_type]
            except:
                logging.warning("force to direct type connection")
                self.tunnel_type = TunnelType.direct
        return self.tunnel_type

    def run(self):
        if self.stopped():
            return
        tunnel_type = self.get_tunnel_type()

        self.socket_tunnel.settimeout(self.timeout)
        self.socket_client = self.get_socket_client()

        if tunnel_type is TunnelType.direct:
            self.tunnel_direct()
        elif tunnel_type is TunnelType.direct_to_ssl_tls:
            self.tunnel_direct_to_ssl_tsl()
        elif tunnel_type is TunnelType.direct_to_ssl_tls_payload:
            self.tunnel_direct_to_ssl_tsl_payload()
        elif tunnel_type is TunnelType.proxy:
            self.tunnel_remote_proxy()
        elif tunnel_type is TunnelType.proxy_to_ssl_tls:
            self.tunnel_proxy_to_ssl_tls()
        elif tunnel_type is TunnelType.proxy_to_ssl_tls_payload:
            self.tunnel_proxy_to_ssl_tls_payload()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
