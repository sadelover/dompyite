# -*- encoding=utf-8 -*-
__author__ = 'yan'

import socket
from logic.Config import heartbeat_config
from logic.LogOperator import LogOperator
import time

#socket操作类
class SocketOperator:

    _clientSock = None
    _connected = False

    @staticmethod
    def initSock():
        socket.setdefaulttimeout(1)
        SocketOperator._clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SocketOperator._connected = False

    @staticmethod
    def closeSock():
        SocketOperator._clientSock.close()
        SocketOperator._connected = False

    @staticmethod
    def sendHeartbeat():
        SocketOperator.connectToServer(heartbeat_config.get('host', 'localhost'), heartbeat_config.get('port', 9501))
        try:
            if SocketOperator._connected:
                SocketOperator._clientSock.sendall(bytes(heartbeat_config.get('cmd'), 'utf8') + bytes(';;\n', 'utf8'))
                return True
        except Exception as e:
            LogOperator().writeLog(str(e))
            SocketOperator.closeSock()
        return False

    @staticmethod
    def connectToServer(addr, port):
        if not SocketOperator._connected:
            while True:
                try:
                    SocketOperator.initSock()
                    SocketOperator._clientSock.connect((addr, port))
                    SocketOperator._connected = True
                    break
                except Exception as e:
                    LogOperator().writeLog(str(e))
                    SocketOperator.closeSock()
                    time.sleep(5)

