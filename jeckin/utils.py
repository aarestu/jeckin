import enum
import logging
import socket
import threading
import time


class TunnelType(enum.Enum):
    direct_ssh = 0
    direct_ssl_tls_ssh = 1
    proxy_ssh = 2
    proxy_ssl_tls_ssh = 3


def payload_decode(payload, host, port):
    payload = payload.replace(b'[real_raw]', b'[raw][crlf][crlf]')
    payload = payload.replace(b'[raw]', b'[method] [host_port] [protocol]')
    payload = payload.replace(b'[method]', b'CONNECT')
    payload = payload.replace(b'[host_port]', b'[host]:[port]')
    payload = payload.replace(b'[host]', str(host).encode())
    payload = payload.replace(b'[port]', str(port).encode())
    payload = payload.replace(b'[protocol]', b'HTTP/1.1')
    payload = payload.replace(b'[user-agent]', b'User-Agent: Chrome/1.1.3')
    payload = payload.replace(b'[keep-alive]', b'Connection: Keep-Alive')
    payload = payload.replace(b'[close]', b'Connection: Close')
    payload = payload.replace(b'[crlf]', b'[cr][lf]')
    payload = payload.replace(b'[lfcr]', b'[lf][cr]')
    payload = payload.replace(b'[cr]', b'\r')
    payload = payload.replace(b'[lf]', b'\n')

    return payload


def loop_payload(payload, host, port):
    payload_split = payload.split(b'[split]')

    for i in range(len(payload_split)):
        if i > 0:
            time.sleep(0.200)
        payload_ts = payload_decode(payload_split[i], host, port)

        yield payload_ts


def get_tunnel_type(tunnel_type):
    if type(tunnel_type) != TunnelType:
        try:
            tunnel_type = TunnelType[tunnel_type]
        except Exception as e:
            logging.warning("use direct type connection")
            tunnel_type = TunnelType.direct
    return tunnel_type


def ip_addr_to_str(addr):
    """
    Return a protocol version aware formatted string for an IP address tuple.
    """
    if ":" in addr[0]:
        return "[{}]:{}".format(addr[0], addr[1])
    return "{}:{}".format(addr[0], addr[1])


def families_and_addresses(hostname, port):
    """
    Yield pairs of address families and addresses to try for connecting.
    :param str hostname: the server to connect to
    :param int port: the server port to connect to
    :returns: Yields an iterable of ``(family, address)`` tuples
    """
    guess = True
    addrinfos = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for (family, socktype, proto, canonname, sockaddr) in addrinfos:
        if socktype == socket.SOCK_STREAM:
            yield family, sockaddr
            guess = False

    # some OS like AIX don't indicate SOCK_STREAM support, so just
    # guess. :(  We only do this if we did not get a single result marked
    # as socktype == SOCK_STREAM.
    if guess:
        for family, _, _, _, sockaddr in addrinfos:
            yield family,


_g_thread_ids = {}
_g_thread_counter = 0
_g_thread_lock = threading.Lock()


def get_thread_id():
    global _g_thread_ids, _g_thread_counter, _g_thread_lock
    tid = id(threading.currentThread())
    try:
        return _g_thread_ids[tid]
    except KeyError:
        _g_thread_lock.acquire()
        try:
            _g_thread_counter += 1
            ret = _g_thread_ids[tid] = _g_thread_counter
        finally:
            _g_thread_lock.release()
        return ret


class PFilter(object):
    def filter(self, record):
        record._threadid = get_thread_id()
        return True


_pfilter = PFilter()


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addFilter(_pfilter)
    return logger
