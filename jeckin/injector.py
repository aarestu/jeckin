import logging
import socket
import threading

from jeckin.tunnel import Tunnel


class Injector(threading.Thread):
    def __init__(self, host, port, config=None):
        super(Injector, self).__init__()
        self._stop_event = threading.Event()
        if not config:
            config = {}
        self.config = config

        self.host_port = self.host, self.port = (host, port)

        self.socket_inject = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_inject.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        try:
            self.socket_inject.bind(self.host_port)
            self.socket_inject.listen(True)

            logging.info(f'Injector service running on {self.host} port {self.port}')
            while not self._stop_event.is_set():
                self.tunnel = Tunnel(self.socket_inject.accept(), self.config)
                self.tunnel.start()
        except OSError:
            logging.error(f'Injector service not running on {self.host} port {self.port} because port used by another programs')

    def stop(self):
        self._stop_event.set()
        if "tunnel" in dir(self) and not self.tunnel.stopped():
            self.tunnel.stop()
            self.tunnel.join()

        socket.socket(socket.AF_INET,
                      socket.SOCK_STREAM).connect(("127.0.0.1", self.port))

    def stopped(self):
        return self._stop_event.is_set()
