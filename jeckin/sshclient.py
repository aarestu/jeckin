import logging
import subprocess


class SSHClient(object):
    def __init__(self, jeck_host, jeck_port, proxy_command=None):
        self.jeck_host = jeck_host
        self.jeck_port = jeck_port
        self.proxy_command = proxy_command
        if not self.proxy_command:
            self.proxy_command = "corkscrew {inject_host} {inject_port} %h %p"
        self.proxy_command = self.proxy_command.format(inject_host=jeck_host, inject_port=jeck_port)

        self.account = {}
        self.reconnect = False

    def start(self):
        while True:
            host = self.account.get("host")
            port = self.account.get("port")
            username = self.account.get("username")
            password = self.account.get("password")
            sockport = self.account.get("sockport", 8289)
            proxy_command = self.proxy_command

            command = f'sshpass -p "{password}" ssh -v  -CND 0.0.0.0:{sockport} {host} -p {port} -l "{username}" ' + \
                      f'-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand="{proxy_command}"'
            response = subprocess.Popen(command,
                                        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            for line in response.stdout:
                line = line.decode().lstrip(r'(debug1|Warning):').strip() + '\r'
                logging.debug("ssh:" + line)

                if 'pledge: proc' in line:
                    self.reconnect = True
                    logging.info('Connected')

                elif 'auth' in line.lower():
                    logging.info(line)

                elif 'read_passphrase' in line.lower():
                    logging.error("")

                elif 'Permission denied' in line:
                    logging.error('Access Denied')
                    break

                elif 'Connection closed' in line:
                    logging.error('Connection closed')
                    break

                elif 'Could not request local forwarding' in line:
                    logging.error('Port used by another programs')
                    break

            logging.info('Disconnected')
            if not self.reconnect:
                break
