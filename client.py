import socket
import struct

from msg import UserMsg_pb2


def client_program():
    # 服务器的IP地址和端口号
    server_ip = '127.0.0.1'
    server_port = 12345
    for i in range(1):
        # 创建一个套接字对象
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 连接到服务器
        client_socket.connect((server_ip, server_port))

        # 发送数据到服务器
        # 创建一个空的 protobuf 对象
        message = UserMsg_pb2.C2SLogin()
        # 设置 protobuf 对象的字段
        message.Account = "cjlaaa" + str(i)

        # 序列化 protobuf 对象
        proto_msg = message.SerializeToString()
        # 获取包体长度
        message_length = len(proto_msg)

        # 定义包头格式
        header_format = 'ii'  # 消息类型和消息长度都是4字节的整数,后面为了测试又加了一个整数
        message_type = 1
        # 将消息类型和包体长度打包成字节对象
        header = struct.pack(header_format, message_type, message_length)

        # 拼接包头和包体
        packet = header + proto_msg

        client_socket.send(packet)

        # 接收服务器返回的数据
        data = client_socket.recv(10240)
        print('从服务器收到的消息：', data)

        unpacked_header = struct.unpack(header_format, data[:8])
        received_message_type = unpacked_header[0]
        received_message_length = unpacked_header[1]
        received_message = data[8:]

        received_proto_obj = UserMsg_pb2.S2CLogin()
        received_proto_obj.ParseFromString(received_message)
        print(
            received_message_type,
            received_message_length,
            received_proto_obj)

        # 关闭套接字连接
        client_socket.close()


if __name__ == '__main__':
    client_program()
