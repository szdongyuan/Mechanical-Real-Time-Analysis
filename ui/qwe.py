import sys
import json

from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtWidgets import QApplication


class Client(object):
    def __init__(self):
        # self.resize(500, 450)


        # self.send_btn = QPushButton('Send', self)
        # self.close_btn = QPushButton('Close', self)

        # self.h_layout = QHBoxLayout()
        # self.v_layout = QVBoxLayout()

        # 2
        self.sock = QTcpSocket()
        self.sock.connectToHost("192.168.2.77", 6666)
        
        # self.layout_init()
        # self.signal_init()

    # def layout_init(self):
    #     self.h_layout.addStretch(1)
    #     self.h_layout.addWidget(self.close_btn)
    #     self.h_layout.addWidget(self.send_btn)
    #     self.v_layout.addWidget(self.splitter)
    #     self.v_layout.addLayout(self.h_layout)
    #     self.setLayout(self.v_layout)
        
    # def signal_init(self):
    #     # self.send_btn.clicked.connect(self.write_data_slot)    # 3
    #     # self.close_btn.clicked.connect(self.close_slot)        # 4
    #     self.sock.connected.connect(self.connected_slot)       # 5
    #     self.sock.readyRead.connect(self.read_data_slot)       # 6

    def write_data_slot(self, information):
        # message = self.edit.toPlainText()
        # self.browser.append('Client: {}'.format(message))
        # datagram = message.encode()
        datagram = json.dumps(information).encode()
        print(type(datagram), datagram)
        self.sock.write(datagram)
        # self.edit.clear()

    # def connected_slot(self):
    #     message = 'Connected! Ready to chat! :)'
    #     self.browser.append(message)

    def read_data_slot(self):
        while self.sock.bytesAvailable():
            datagram = self.sock.read(self.sock.bytesAvailable())
            message = datagram.decode()
            # print(type(datagram), datagram)
            a = json.loads(message)
            print(a)
            # self.browser.append('Server: {}'.format(a))

    def close_slot(self):
        self.sock.close()
        # self.close()

    # def closeEvent(self, event):
    #     self.sock.close()
    #     event.accept()


if __name__ == '__main__':
    # app = QApplication(sys.argv)
    demo = Client()
    import time
    time.sleep(1)
    demo.write_data_slot({"msg": "Hello from client"})
    # sys.exit(app.exec_())