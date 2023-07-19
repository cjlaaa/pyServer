# pyServer

### DONE list
1. 自定义socket协议包头,使用protobuf作为包体进行拆包,组包
2. 对错误消息抛异常,并输出日志
3. 使用标准库的logging日志系统
4. 客户端登出简单处理
5. 为每个客户端创建一个线程阻塞收取消息
6. 使用selectors的异步架构

### TODO list 
1. 科学的保存和处理客户端的连接信息
2. 做成无状态服务器,数据存redis