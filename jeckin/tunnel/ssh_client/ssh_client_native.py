import logging
import random
import subprocess
import time


class SSHClientNative(object):
    def __init__(self, jeck_host, jeck_port, sock_port):
        self.jeck_host = jeck_host
        self.jeck_port = jeck_port
        self.sock_port = sock_port

        self.account = {}
        self.reconnect = True

    def start(self):
        s = 0
        while True:
            username = self.account.get("username")
            password = self.account.get("password")

            command = f'sshpass -p "{password}" ssh -v -CND 0.0.0.0:{self.sock_port} {self.jeck_host} -p {self.jeck_port} -l "{username}" ' + \
                      f'-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

            response = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            for line in response.stdout:
                line = line.lstrip(rb'(debug1|Warning):').strip() + b'\r'
                try:
                    line = line.decode("ascii")
                    # logging.debug("ssh:" + line)
                except:
                    # logging.debug(b"ssh:" + line )
                    continue

                if 'pledge: proc' in line:
                    self.reconnect = True
                    s = 0
                    logging.info('ssh:Connected')

                elif 'auth' in line.lower():
                    logging.info(line)

                elif 'read_passphrase' in line.lower():
                    logging.error("")

                elif 'Permission denied' in line:
                    logging.error('ssh:Access Denied')
                    break

                elif 'Connection closed' in line:
                    logging.error('ssh:Connection closed')
                    break

                elif 'Could not request local forwarding' in line:
                    logging.error('ssh:Port used by another programs')
                    break

            logging.info('Disconnected')
            if not self.reconnect:
                break

            logging.info(f"ssh:Waiting for {s}s before reconnecting")
            time.sleep(s)
            s = min(s + 1, random.randint(1, 20))