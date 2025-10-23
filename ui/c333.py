import socket
import json

class WarnSender(object):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('192.168.2.77', 6666))

    def write_data_slot(self, information):
        send_information = json.dumps(information)
        self.sock.send(send_information.encode())

    def read_data_slot(self):
        data = self.sock.recv(1024)
        json_data = json.loads(data.decode())
        print(json_data)

    def close(self):
        self.sock.close()

if __name__ == '__main__':
    client = WarnSender()
    client.write_data_slot({'name': 'zhangsan'})
    client.read_data_slot()