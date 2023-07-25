import logging
import selectors
import socket
import struct
from colorama import Fore, Style

from msg import ProtoType_pb2
from msg import UserMsg_pb2

ERROR_CODE = -999999

# 定义服务器地址和端口
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 12345

# 定义客户端列表
connections = {}
# 定义一个字典，将枚举值与对应的处理函数关联起来
network_handlers = {}
#
sel = selectors.DefaultSelector()


# 处理连接断开
def disconnect(conn):
    if connections[conn] is not None:
        logging.debug(f"连接断开{connections[conn]}({conn.getpeername()})")
    else:
        logging.debug(f"连接断开{conn.getpeername()}")

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


def recv_and_unpack(conn):
    header = conn.recv(8)
    if not header:
        return ERROR_CODE, bytes()

    header_format = 'ii'  # 消息类型和消息长度都是4字节的整数
    unpacked_header = struct.unpack(header_format, header)
    received_message_type = unpacked_header[0]
    received_message_length = unpacked_header[1]
    # received_message = conn.recv(received_message_length)

    # 检查消息长度是否合理
    if 0 < received_message_length <= 40960:
        # 接收消息体
        received_message = b""
        bytes_to_receive = received_message_length
        buffer_size = 1024  # 每次接收的缓冲区大小
        while bytes_to_receive > 0:
            if bytes_to_receive < buffer_size:
                chunk = conn.recv(bytes_to_receive)
            else:
                chunk = conn.recv(buffer_size)
            if not chunk:
                # 连接已关闭，退出循环
                break
            received_message += chunk
            bytes_to_receive -= len(chunk)
    else:
        # 消息长度不合理，进行处理（例如抛出异常）
        raise ValueError(f"消息长度不合理:{received_message_length}")

    return received_message_type, received_message


def pack_and_send(conn, message_type, response_message):
    # 序列化 protobuf 对象
    response_message_proto = response_message.SerializeToString()
    # 获取包体长度
    response_message_proto_length = len(response_message_proto)

    header_format = 'ii'  # 消息类型和消息长度都是4字节的整数,后面为了测试又加了一个整数
    response_message_header = struct.pack(
        header_format, message_type, response_message_proto_length)
    response_packet = response_message_header + response_message_proto
    conn.send(response_packet)


def read(conn, mask):
    try:
        received_message_type, received_message = recv_and_unpack(conn)
        if received_message_type == ERROR_CODE:
            # 连接断开
            disconnect(conn)
            return

        handler = network_handlers.get(received_message_type)
        if handler:
            handler(conn, received_message)
        else:
            raise Exception(
                "收到错误的包",
                received_message_type,
                # received_message_length,
                received_message)

    except socket.error as e:
        if e.errno == 10054:
            logging.debug(f"socket异常: {e}")
            disconnect(conn)
            return
    except struct.error as e:
        logging.debug(f"struct异常: {e}")
        disconnect(conn)
        return
    except Exception as e:
        logging.debug(f"其他异常: {e}")
        disconnect(conn)
        return


# 定义一个函数，用于注册网络处理函数
def register_network_handler(protocol, handler):
    network_handlers[protocol] = handler


# 注册网络处理函数
def init_network_handler():
    register_network_handler(ProtoType_pb2.MSGTYPE.MT_C2S_LOGIN, s2c_login)
    # register_network_handler(NetworkProtocol.TCP, process_tcp)
    # register_network_handler(NetworkProtocol.UDP, process_udp)


def s2c_login(conn, received_message):
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

    pack_and_send(
        conn,
        ProtoType_pb2.MSGTYPE.MT_S2C_LOGIN,
        response_message)


def main():
    # 设置日志格式
    logging.basicConfig(
        level=logging.DEBUG,
        format=f'{Fore.GREEN}%(asctime)s [%(levelname)s]: %(message)s (%(filename)s:%(lineno)d){Style.RESET_ALL}')
    logging.basicConfig(
        level=logging.ERROR,
        format=f'{Fore.RED}%(asctime)s [%(levelname)s]: %(message)s(% (filename)s:%(lineno)d){Style.RESET_ALL}')

    init_network_handler()

    # 创建服务器socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(socket.SOMAXCONN)
    server_socket.setblocking(False)

    sel.register(server_socket, selectors.EVENT_READ, accept)

    print("")
    logging.debug(f"服务器开始监听{SERVER_HOST}:{SERVER_PORT}")

    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == "__main__":
    main()
