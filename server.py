import logging
import socket
import struct
import threading
from msg import UserMsg_pb2
import traceback

# 定义服务器地址和端口
SERVER_HOST = 'localhost'
SERVER_PORT = 12345

# 定义客户端列表
clients = []
# 定义锁，用于保护clients列表的并发访问
clients_lock = threading.Lock()

# 循环计数
global_count = 0


def handle_client(client_socket):
    global global_count
    while True:
        global_count = global_count + 1
        logging.debug(f"global_count:{global_count}")
        try:
            header = client_socket.recv(8)
            if not header:
                logging.debug(f"收到错误的头{header}")
                break
            header_format = 'ii'  # 消息类型和消息长度都是4字节的整数
            unpacked_header = struct.unpack(header_format, header)
            received_message_type = unpacked_header[0]
            received_message_length = unpacked_header[1]
            received_message = client_socket.recv(received_message_length)

            # 处理登录请求
            if received_message_type == 1:
                # 解析protobuf消息
                msg = UserMsg_pb2.C2SLogin()
                msg.ParseFromString(received_message)

                # 获取用户名
                account = msg.Account
                logging.debug(f"用户{account}已登录")

                # 添加客户端到列表
                with clients_lock:
                    clients.append(client_socket)

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
                client_socket.send(response_packet)

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
            logging.debug(f"Exception: {e}")
            traceback.print_exc()
            break

    # 客户端断开连接，从列表中移除
    with clients_lock:
        ip_address, port = client_socket.getpeername()
        try:
            clients.remove(client_socket)
            logging.debug(f"{ip_address}:{port}已登出")

        except ValueError:
            logging.debug(f"{ip_address}:{port}非正常登出")

    client_socket.close()


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
    server_socket.listen(5)

    logging.debug(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    while True:
        # 接受客户端连接
        client_socket, client_address = server_socket.accept()
        logging.debug(
            f"New connection from {client_address[0]}:{client_address[1]}")

        # 创建新的线程处理客户端请求
        client_thread = threading.Thread(
            target=handle_client, args=(
                client_socket,))
        client_thread.start()


if __name__ == "__main__":
    main()
