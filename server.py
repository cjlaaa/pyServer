import logging
import socket
import struct
import threading
from msg import UserMsg_pb2
import traceback
import selectors

# 定义服务器地址和端口
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 12345

# 定义客户端列表
connections = {}

sel = selectors.DefaultSelector()


# 循环计数
global_count = 0

# 处理连接断开


def disconnect(conn):
    logging.debug(f"连接断开{connections[conn]}({conn.getpeername()})")
    sel.unregister(conn)
    conn.close()
    del connections[conn]


def accept(sock, mask):
    conn, addr = sock.accept()
    logging.debug(f"收到来自{addr}的连接")
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, read)
    # 添加客户端到列表
    connections[conn] = b''


def read(conn, mask):
    # global_count = global_count + 1
    # logging.debug(f"global_count:{global_count}")
    try:
        header = conn.recv(8)
        if not header:
            # 连接断开
            disconnect(conn)
            return
        header_format = 'ii'  # 消息类型和消息长度都是4字节的整数
        unpacked_header = struct.unpack(header_format, header)
        received_message_type = unpacked_header[0]
        received_message_length = unpacked_header[1]
        received_message = conn.recv(received_message_length)

        # 处理登录请求
        if received_message_type == 1:
            # 解析protobuf消息
            msg = UserMsg_pb2.C2SLogin()
            msg.ParseFromString(received_message)

            # 获取用户名
            account = msg.Account
            connections[conn] = account
            logging.debug(f"用户{account}已登录")

            # 发送登录成功响应
            response_message = UserMsg_pb2.S2CLogin()
            response_message.Res = 999
            response_message.Message = "Hey you!" + account
            response_message.PlayerId = 123456

            # 序列化 protobuf 对象
            response_message_proto = response_message.SerializeToString()
            # 获取包体长度
            response_message_proto_length = len(response_message_proto)

            header_format = 'ii'  # 消息类型和消息长度都是4字节的整数,后面为了测试又加了一个整数
            message_type = 7890
            response_message_header = struct.pack(
                header_format, message_type, response_message_proto_length)
            response_packet = response_message_header + response_message_proto
            conn.send(response_packet)

        # 处理其他请求
        elif received_message_type == 2:
            # 解析protobuf消息
            # msg = UserMsg_pb2.C2SLogin()
            # msg.ParseFromString(received_message)

            # # 广播消息给所有客户端
            # with lock:
            #     for client in clients:
            #         client.send(message.encode())
            pass
        else:
            raise Exception(
                "收到错误的包",
                received_message_type,
                received_message_length,
                received_message)
    except Exception as e:
        logging.debug(f"异常: {e}")
        traceback.print_exc()
        return


def main():
    # 设置日志格式
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s]:%(message)s(%(filename)s:%(lineno)d)')
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s [%(levelname)s]:%(message)s(%(filename)s:%(lineno)d)')

    # 创建服务器socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(socket.SOMAXCONN)
    server_socket.setblocking(False)

    sel.register(server_socket, selectors.EVENT_READ, accept)

    logging.debug(f"服务器正在监听{SERVER_HOST}:{SERVER_PORT}")

    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == "__main__":
    main()
