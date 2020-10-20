#!/usr/bin/python
# -*- coding: UTF-8 -*-
import socket
import sys
import threading
import json
import time
from datetime import datetime
from App import App  # APP端实体类
from Car import Car  # car实体类

"""
    服务端通信类：
        负责通信，实现多对多的通信，即，多个小车对多个APP端的通信都是经过这里

"""

CAR_STATE_IDLE = 0  # 空闲状态
CAR_STATE_BUSY = 1  # 控制状态

SERVER_ON = 0  # 服务端开
SERVER_OFF = 1  # 服务端关
class Server:


    def __init__(self):
        # 地址、端口
        self.HOST_IP = self.get_host_ip()
        print(self.HOST_IP)
        self.HOST_PORT = 7654
        self.addr = (self.get_host_ip(), self.HOST_PORT)
        # 连接池
        self.connects = []

        # 小车列表
        self.cars = []

        # APP端列表
        self.apps = []

        # 负责监听的socket
        self.socket_server = None


        self.serverControl = SERVER_ON




    """
        初始化服务端
        socket_server的定义、绑定的地址和监听的数量
    """


    def start(self):
        # 初始化服务端
        #global slef.socket_server
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket类型
        self.socket_server.bind(self.addr)  # 绑定地址
        self.socket_server.listen(10)  # 监听数量
        #self.serverControl = SERVER_ON
        print("服务端已启动，等待接入...")
        self.conn()


    """
        这里用无限循环来接收接入的客户端
        接入的客户端会加入线程池（开子线程来处理每个客户端发来的数据）
    """


    def conn(self):
        while True:
            # 如果关闭Server端，循环结束，关闭线程
            if self.serverControl == SERVER_OFF:
                print(11)
                break
            client, (client_host, client_port) = self.socket_server.accept()
            # 加入线程池
            self.connects.append(client)
            # 用子线程来处理客户端接下来的操作
            thread = threading.Thread(target=self.recevice, args=(client, client_host, client_port))
            thread.setDaemon(True)
            thread.start()

        self.socket_server.close()


    """
        客户端连接上服务端后接下来的操作
            client_host: 客户端host   
            client_port: 客户端port
    
        流程：
            第一步，等待接收消息（这个消息用来判断是car还是APP）
            
            第二步，
                （a）car，无限循环接收消息 -> (结束)
                （b）APP，连接car
            第三步，
                （b）APP，无限循环接收消息 -> (结束)
    """


    def recevice(self,client, client_host, client_port):
        # print(client_host, ":"+ str(client_port)+ "   连接到服务器...")
        # 用print会因为多线程的原因，打印会乱，用write加上强制刷新可以解决这个问题
        sys.stdout.write(client_host + ":" + str(client_port) + "   连接到服务器...")
        sys.stdout.flush()

        try:
            # 客户端接入后会先发送一个消息到服务端，用来判断客户端是小车还是APP
            sayHello = client.recv(1024)

        except ConnectionResetError:  # 异常处理（这个是处理非正常断开连接的，就是客户端没有调用close方法，但是连接断开了，例如：软件被杀后台了）
            print("【客户端】{}:{}非正常退出了与服务端的通信...\n".format(client_host, client_port))
            client.close()
            self.connects.remove(client)
            return
        if sayHello.decode():
            # 是小车的话将进行以下操作
            hello = sayHello.decode()
            print(hello)
            hello = self.toDic(hello)
            if hello["code"]==2000 and hello["msg"] == "Car":
                car = Car("小车" + str(len(self.cars)), client, client_host, client_port)
                # 加入小车列表
                self.cars.append(car)
                #print(self.cars)
                time.sleep(2)
                client.send("Hello,car".encode())

                #client.send(self.toJson("server", "", "Hello,car").encode())
                print()
                print("ta是一个小车...")
                print("现在有 {} 辆小车在线, {} 个APP端在线。".format(len(self.cars), len(self.apps)))
                print()
                # 无限循环来接收小车发来的数据
                while True:
                    # 如果关闭Server端，循环结束，关闭线程
                    if self.serverControl == SERVER_OFF:
                        break
                    try:
                        data = client.recv(10)
                        if data.decode():
                            data = self.toDic(data.decode())
                            print("【小车】{}:{}：：".format(client_host, client_port), data["msg"])
                        # 小车端关闭通信后会关闭通话，并且将它从个列表中移除，还有退出这个循环来退出此子线程
                        if data == b"":
                            client.close()  # 关闭通信
                            self.cars.remove(car)  # 从小车列表中移除
                            self.connects.remove(client)  # 从线程池中移除
                            print()
                            print("【小车】{}:{}已离线...".format(client_host, client_port))
                            print("现在有 {} 辆小车在线, {} 个APP端在线。".format(len(self.cars), len(self.apps)))
                            print()
                            # break退出循环，子线程结束
                            break
                    except ConnectionResetError:
                        print("【小车】{}:{}非正常退出了与服务端的通信...".format(client_host, client_port))
                        client.close()
                        self.cars.remove(car)
                        self.connects.remove(client)
                        break
            # 是APP端的话会进行以下操作
            if hello["code"] ==2000 and hello["msg"]== "APP":
                app = App(client, client_host, client_port)
                # 加入APP端列表
                self.apps.append(app)
                # client.send("Hello,APP".encode())
                #client.send((self.toJson(2000, "", "success")+"\n").encode())
                print()
                print("ta是一个APP...")
                print("现在有 {} 辆小车在线, {} 个APP端在线。".format(len(self.cars), len(self.apps)))
                print()
                # sendCarsList(client)
                # 无限循环来接收APP发来的数据
                while True:
                    # 如果关闭Server端，循环结束，关闭线程
                    if self.serverControl == SERVER_OFF:
                        break
                    try:
                        data = client.recv(1024)
                        if data == b"":  # 断开连接
                            if app.getReceiver() != None:
                                car.setState(CAR_STATE_IDLE)
                                app.setReceiver(None)
                                print("【APP端】{}:{}：：".format(client_host, client_port),
                                      "释放了控制小车{}:{}权限".format(car.getHost(), car.getPort()),
                                      datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            client.close()
                            self.apps.remove(app)
                            self.connects.remove(client)
                            print()
                            print("【APP端】{}:{}已离线...".format(client_host, client_port))
                            print("现在有 {} 辆小车在线, {} 个APP端在线。".format(len(self.cars), len(self.apps)))
                            print()
                            break
                        print(data.decode())
                        if data.decode()[len(data.decode())-1]=="}" and len(data.decode())<45:
                            if data.decode():
                                print("【APP端】{}:{}：：".format(client_host, client_port), data.decode())
                                data = self.toDic(data.decode())
                                print(data)
                                if data["code"]==2001:  # 发来的信息是要控制某个小车
                                    # print(judgeIP(data["msg"].split("连接")[1]))
                                    # print("控制")
                                    car = self.findName(data["msg"])
                                    if car != None:
                                        # print(car)
                                        print("【APP端】{}:{}：：".format(client_host, client_port),
                                              "申请控制小车{}:{}权限".format(car.getHost(), car.getPort()))

                                        # print("【APP端】{}:{}：：".format(client_host,client_port),"申请控制小车{}:{}".format(judgeIP(data["msg"].split("连接")[1])[0],judgeIP(data["msg"].split("连接")[1])[1]))
                                        # car=findCar(judgeIP(data["msg"].split("连接")[1])[0],judgeIP(data["msg"].split("连接")[1])[1])#得到一个小车对象
                                        # if car.getState()==None:
                                        #     client.send(toJson("","","连接失败，小车状态错误").encode())
                                        if car.getState() == CAR_STATE_BUSY:  # 如果小车已被控制
                                            client.send((self.toJson(2001, "", "10086")+"\n").encode())#小车已被别人控制
                                        if car.getState() == CAR_STATE_IDLE:  # 如果小车是空闲状态
                                            car.setState(CAR_STATE_BUSY)
                                            app.setReceiver(car.getMe())  # 小车的me设置为app端的接受者
                                            client.send((self.toJson(2001, "", "success")+"\n").encode())
                                            print("【APP端】{}:{}：：".format(client_host, client_port),
                                                  "获得控制小车{}:{}权限".format(car.getHost(), car.getPort()))

                                            # print("【APP端】{}:{}：：".format(client_host,client_port),"获得控制小车{}:{}权限".format(judgeIP(data["msg"].split("连接")[1])[0],judgeIP(data["msg"].split("连接")[1])[1]))
                                if data["code"]==2001 and data["msg"].find("释放") != -1 and app.getReceiver() != None:
                                    car.setState(CAR_STATE_IDLE)
                                    app.setReceiver(None)
                                    print("【APP端】{}:{}：：".format(client_host, client_port),
                                          "释放了控制小车{}:{}权限".format(car.getHost(), car.getPort()))
                                if data["code"]==2002 and app.getReceiver() != None:
                                    print(data["msg"])
                                    # time.sleep(0.2)
                                    car.getMe().send(self.toJson("", "", data["msg"]).encode())
                                if data["code"]==2001 and data["msg"].find("小车列表") > -1:
                                    self.sendCarsList(client)

                            # sendToAll(data)

                    except ConnectionResetError:
                        print("【APP】{}:{}非正常退出了与服务端的通信...".format(client_host, client_port))
                        if app.getReceiver() != None:
                            car.setState(CAR_STATE_IDLE)
                            app.setReceiver(None)
                            print("【APP端】{}:{}：：".format(client_host, client_port),
                                  "释放了控制小车{}:{}权限".format(car.getHost(), car.getPort()))
                        client.close()
                        self.apps.remove(app)
                        self.connects.remove(client)
                        break
            if hello["code"] ==2000 and hello["msg"]== "Auto":
                while True:
                    try:
                        data = client.recv(1024)
                        if data == b"":  # 断开连接
                            client.close
                        else:
                            if data.decode()[len(data.decode())-1]=="}" and len(data.decode())<45:
                                print(data.decode())
                                data = self.toDic(data.decode())
                                if len(self.cars)>0 and data["code"]==2002 :
                                    print(data["msg"])
                                    self.cars[0].getMe().send(self.toJson("", "", data["msg"]).encode())
                    except ConnectionResetError:
                        client.close
                        break



    ############################发送信息#########################################

    """
        服务端转发消息给所有已连接的客户端
    
            msg：要发送的信息  'Hello World'
    """
    def sendToAll(self,msg):
        for i in self.connects:
            data = self.toJson("Server", "All", msg)
            i.send(data.encode())

    """
        给小车发送消息
    
            sender: 发送者ip   '127.0.0.1:666'
            to: 接受者ip   '127.0.0.1:777'
            msg: 需要发送的信息    'Hello World'
            return ：是否发送成功
    """


    def sendToCar(self,sender, to, msg):
        host, port = self.judgeIP(to)
        if port == -1:
            return False
        for i in self.cars:
            if i[1] == host and i[2] == port:
                data = self.toJson(sender, to, msg)
                i[0].sendall(data.encode())
                return True
        return False


    """
        给APP发送消息
        返回的True和False判断是否找到了要发送的APP
    
            sender: 发送者ip   '127.0.0.1:666'
            to: 接受者ip   '127.0.0.1:777'
            msg: 需要发送的信息    'Hello World'
            return ：是否发送成功
    """


    def sendToApp(self,sender, to, msg):
        # 通过host和端口号判断
        host, port = self.judgeIP(to)
        if port == -1:
            return False

        for i in self.apps:
            if i[1] == host and i[2] == port:
                data = self.toJson(sender, to, msg)
                i[0].sendall(data.encode())
                return True
        return False


    """
        发送小车列表 （json格式）
    """


    def sendCarsList(self,client):
        print("发送小车列表函数进入")
        data = {
            "data": []
        }
        for i in self.cars:
            data["data"].append({"name": (str(i.getName())), "state": str(i.getState())})
        data.update(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        dataToJson = json.dumps(data)  # 转换为json格式
        client.sendall(dataToJson.encode("UTF-8"))


    ##########################工具类######################################

    """
            查询本机ip地址
            :return:
        """

    def get_host_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    """
        判断是否符合ip和端口的格式
        return：
            host
            port
            不符合返回'-1'，-1 、 
    """


    def judgeIP(self,addr):
        # 首先判断是主机和端口的格式
        if addr.find(":", 0, len(addr)) != -1:
            host = addr.split(":")[0]
            port = (int)(addr.split(":")[1])
            # 判断是否在在
            for i in host.split("."):
                if int(i) < 0 or int(i) > 255:
                    return -1, -1
            return host, port
        return "-1", -1


    """
        把数据转化为json格式
            sender:发送者地址    例："127.0.0.1:666"
            to:接收者地址    例："127.0.0.1:555"
            mag:信息内容    例："Hello World！"
            return:json格式的数据
    """
    def toJson(self,code, to, msg):
        data = {"code": code, "to": to, "msg": msg, "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        dataToJson = json.dumps(data)  # 转换为json格式
        return dataToJson


    """
        把json格式转化为字典格式（转化为的字典类型的数据必须包含key：msg）
        data：json格式数据
        return:返回字典类型
    """
    def toDic(self,data):
        dataToDic = json.loads(data)
        return dataToDic


    """
        查找小车
        host：要查找小车的主机
        port：要查找小车的端口
        return：查到返回一个car对象，查不到返回None
    """


    def findCar(self,host, port):
        for i in self.cars:
            if i.getHost() == host and i.getPort() == port:
                print(i.toString())
                return i
        return None


    def findName(self,str):
        for i in self.cars:
            if i.getName() == str:
                return i
        return None


    def findmove(self,str):
        str = str.split("移动")[1]
        left01 = str.split(",")[0]
        left02 = str.split(",")[1]
        right01 = str.split(",")[2]
        right02 = str.split(",")[3]
        return (left01, left02, right01, right02)


if __name__ == "__main__":
    server=Server()
    server.start()