#!/usr/bin/python
# -*- coding: UTF-8 -*-
import serial
import time
import configparser
import os
from binascii import a2b_hex,b2a_hex
import struct
import time


#comp:寄存器或元件的编号，例如"Y10"
def const_addres(comp):
    modle=comp[0].upper()
    serial=int(comp[1:])
    
    if modle=="S":
        base_addr=0x0000
        dev_addr=serial//8
        first_element=dev_addr*8
        address=base_addr+dev_addr    

    if modle=="X":
        base_addr=0x0080
        dev_addr=serial//10
        first_element=dev_addr*10
        address=base_addr+dev_addr
        
    if modle=="Y":
        base_addr=0x00A0
        dev_addr=serial//10
        first_element=dev_addr*10
        address=base_addr+dev_addr
        
    if modle=="T":
        base_addr=0x00C0
        dev_addr=serial//8
        first_element=dev_addr*8
        address=base_addr+dev_addr

        
    if modle=="M":
        base_addr=0x0100
        dev_addr=serial//8
        first_element=dev_addr*8
        address=base_addr+dev_addr
        
    if modle=="D":
        base_addr=0x1000
        first_element=serial
        address=base_addr+serial*2

        
    address=hex(address)[2:].zfill(4)
    address=address.upper()
    return address,first_element

#置位开关地址
def onoff_addres(comp):
    modle=comp[0].upper()
    serial=int(comp[1:])
    
    if modle=="S":
        base_addr=0x0000*8
        dev_addr=serial
        address=base_addr+dev_addr    

    if modle=="X":
        base_addr=0x0080*8
        dev_addr=serial//10*8+serial%10
        address=base_addr+dev_addr
        
    if modle=="Y":
        base_addr=0x00A0*8
        dev_addr=serial//10*8+serial%10
        address=base_addr+dev_addr
        
    if modle=="T":
        base_addr=0x00C0*8
        dev_addr=serial//10*8+serial%10
        address=base_addr+dev_addr

        
    if modle=="M":
        base_addr=0x0100*8
        dev_addr=serial
        address=base_addr+dev_addr
        
        
    address=hex(address)[2:].zfill(4)
    address=address.upper()
    return address


def Checksum(data):
    SUM=hex(sum(data[1:-2]))[-2:].upper()
    SUM=SUM.encode("ascii")
    if SUM==data[-2:]:
        return 1
    else:
        print("和校验错误:数据传输失败")
        return 0


#ADDRESS:位元件的地址，输入字符串格式的地址，例如"00A1",各元件地址详见地址对照表。
#BYTES：读取几个字节的数据，必须输入2位数的字符串,例如"01","02"
def const_read_cmd(ADDRESS,BYTES):
    #起始字符串
    stx=b'\x02'
    #30 读命令，31 写命令
    order=b'\x30'
    
    #元件地址为字符串,按位转换为ascii码
    ADDRESS=ADDRESS.encode("ascii")

    #读取几个字节的数据
    BYTES=BYTES.encode("ascii")
    
    #结束字符串
    etx=b'\x03'    
    
    #计算和校验码
    SUM=ord(order)+sum(ADDRESS)+sum(BYTES)+ord(etx)
    SUM=hex(SUM)[-2:].upper()
    SUM=SUM.encode("ascii")

    cmd=stx+order+ADDRESS+BYTES+etx+SUM
    return cmd

#开关量赋值命令
#ser:串口连接实例
#comp:开关编号，"Y04"等
#value:置0或1
def Set_Reset(ser,comp,value):
    modle=comp[0].upper()
    #起始字符串
    stx=b'\x02'
    if value==0:
        #37 置位命令，将开关量设置为1，38 复位命令，将开关量设置为0
        order=b'\x38'
    else:
        order=b'\x37'
    ADDRESS=onoff_addres(comp)
    #元件地址为字符串,按位转换为ascii码
    ADDRESS=ADDRESS[-2:]+ADDRESS[:2]
    ADDRESS=ADDRESS.encode("ascii")
    
    #结束字符串
    etx=b'\x03'    
    
    #计算和校验码
    SUM=ord(order)+sum(ADDRESS)+ord(etx)
    SUM=hex(SUM)[-2:].upper()
    SUM=SUM.encode("ascii")
    cmd=stx+order+ADDRESS+etx+SUM
    ser.write(cmd)
    buffer=ser.read(1)
    
    def case1():
        print("置/复位成功")
    def case2():
        print("置/复位失败")
    def case3():
        print("置/复位返回值为空，超时")
    def default():
        print("置/复位过程发生未预料到的错误，PLC返回值是{}".format(buffer))
    switch = {b'\x06': case1, b'\x15': case2,b'': case3}
    switch.get(buffer, default)()



#ser,串口连接实例
#comp:位元件的编号，例如"Y10"
#size：读取几个元件的数据，8个元件才占用1个字节，因此必须输入8的整数倍
def read_onoff_element(ser,comp,size):
    modle=comp[0].upper()
    
    #查询地址
    ADDRESS,first_element=const_addres(comp)
    last_element=first_element+size-1

    #构造PLC命令
    #01表示读取一个字节，即8位的数据
    cmd=const_read_cmd(ADDRESS,str(int(size/8)).zfill(2))
    ser.write(cmd)
    
    
    #8个元件用string表示是2位,占用2字节
    data_size=int(size/4)
    buffer_size=4+data_size
    buffer=ser.read(buffer_size)

    try:
        if buffer==b"":
            raise ValueError("读取软元件返回值为空，超时，请检查串口连接线是否松动，PLC是否开启")
        else:
            if len(buffer)!=buffer_size:
                raise ValueError("读取软元件返回值长度不足，数据传输出错，请检查串口参数")
            
        #执行和校验，判断数据传输是否出错
        if Checksum(buffer)!=1:
            raise ValueError("读取软元件 Checksum NG,数据传输出错，请检查串口参数")
        
        #接收的数据第二位开始为元件的状态值
        data=buffer[1:1+data_size]
        data=a2b_hex(data)
        rule="<{}B".format(int(size/8))
        t=struct.unpack(rule,data)
        t=["{:08b}".format(i) for i in t]

        i=0
        for x in t:
            if modle=="X" or modle=="Y":
                print("{}{}~{}{}:{}".format(modle,first_element+i*10+7,modle,first_element+i*10,x))
            else:
                print("{}{}~{}{}:{}".format(modle,first_element+i*8+7,modle,first_element+i*8,x))
            i=i+1
        return t
    
    except ValueError as e:
        print('错误信息是:', e)
    
    except BaseException as e:
        print('读取软元件发生未预料到的错误:', e)


#ser,串口连接实例
#comp:寄存器的编号，例如"D10"
#size：连续读取几个寄存器的数据，每个寄存器是16位的（2字节）
def read_register(ser,comp,size):
    modle=comp[0].upper()
    
    #ADDRESS：元件地址为字符串变量，取值参考寄存器的地址对照表
    ADDRESS,first_element=const_addres(comp)


    #构造PLC命令，每个寄存器占用2字节
    cmd=const_read_cmd(ADDRESS,str(size*2).zfill(2))
    ser.write(cmd)
    
    #1个元件用用string表示是4位,占用4字节
    data_size=size*4
    buffer_size=4+data_size
    buffer=ser.read(buffer_size)

    try:
        if buffer==b"":
            raise ValueError("读取寄存器返回值为空，超时，请检查串口连接线是否松动，PLC是否开启")
        else:
            if len(buffer)!=buffer_size:
                raise ValueError("读取寄存器返回值长度不足，数据传输出错，请检查串口参数")
            
        #执行和校验，判断数据传输是否出错
        if Checksum(buffer)!=1:
            raise ValueError("读取寄存器Checksum NG,数据传输出错，请检查串口参数")
                   
        #接收的数据第二位开始为寄存器的值
        data=buffer[1:1+data_size]
        #data=b"\x43\x33\x30\x42\x46\x41\x30\x31"
        data=a2b_hex(data)
        rule="<{}H".format(size)
        t=struct.unpack(rule,data)
        
        for i in range(size):
            print("{}{}:{}".format(modle,first_element+i,t[i]))
            
    except ValueError as e:
        print('错误信息是:', e)
    
    except BaseException as e:
        print('读取寄存器发生未预料到的错误:', e)
        

#如果连接串口成功会返回串口实例，连接失败会返回False
def config_ser():
    #在传递键值对数据时，会将键名 全部转化为小写
    conf = configparser.ConfigParser()
    if os.path.isfile("seting.ini"):
        conf.read("seting.ini")
        COM_No  = conf.get("Serial_settings", "COM_No")
        baud=int(conf.get("Serial_settings","baud"))
        timeout=int(conf.get("Serial_settings","timeout"))
        bytesize=int(conf.get("Serial_settings","bytesize"))
        stopbits=int(conf.get("Serial_settings","stopbits"))    
        parity={"None":serial.PARITY_NONE,"EVEN":serial.PARITY_EVEN,"ODD":serial.PARITY_ODD}
        parity=parity[conf.get("Serial_settings","parity")]
        t=int(conf.get("frequency","Intervals"))
    else:
        conf.add_section('Serial_settings')
        conf.set('Serial_settings', 'COM_No', 'COM5')
        conf.set('Serial_settings', "baud", '9600')
        conf.set('Serial_settings', 'timeout', '1')
        conf.set('Serial_settings', 'bytesize', '7')
        conf.set('Serial_settings', 'stopbits', '1')
        conf.set('Serial_settings', 'parity', 'EVEN')
        conf.set('frequency', 'Intervals', '5')
        conf.write(open('seting.ini', 'w'))
    try:
        ser=serial.Serial(port=COM_No,baudrate=baud,bytesize=bytesize,parity=parity,stopbits = stopbits,timeout=timeout)
        #发送连接测试命令
        ser.write(b'\x05')
        buffer=ser.read(1)

        def case1():
            print("成功连接下位机")
            return ser

        def case2():
            print("测试连接命令的返回值为空，超时，请检查串口连接线是否松动，PLC是否开启")
            return False
            
        def default():
            printprint("测试连接命令的返回值为：{}，请检查串口连接线是否松动，PLC是否开启，串口配置参数是否正确".format(buffer))
            return False

        switch = {b'\x06': case1, b'': case2}
        r=switch.get(buffer, default)()
        return r
        
        '''
        if buffer==b'\x06':
            print("成功连接下位机")
            return ser
        if buffer==b'':
            print("测试连接命令的返回值为空，超时，请检查串口连接线是否松动，PLC是否开启")
        else:
            print("测试连接命令的返回值为：{}，请检查串口连接线是否松动，PLC是否开启，串口配置参数是否正确".format(buffer))
            return False
        '''

    except BaseException as e:
        print("串口连接失败,请核对连线及COM口编号:",e)
        return False


def trans(s):
    return "b'%s'" % ''.join('\\x%.2x' % x for x in s)    


if __name__=="__main__":
    '''
    comp="M0"
    address,first_element=const_addres(comp)
    print("寄存器{}的地址是{},起始寄存器序号{}".format(comp,address,first_element))
    cmd=const_read_cmd(address,"01")
    print("读取命令：",trans(cmd))
    '''
    #创建串口连接
    ser=config_ser()

    if ser !=False:

        #将Y1的值置为1
        Set_Reset(ser,"Y1",1)
        #从Y04的地址开始读取，读取24个开关量
        M=read_onoff_element(ser,"Y04",24)
        #从寄存器D21开始读取，读取3个寄存器的值（16位整数格式）
        read_register(ser,"D21",3)
        ser.close()
