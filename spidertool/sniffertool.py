# !/usr/bin/python
# -*- coding:utf-8 -*-

'''
Created on 2015年10月29日

@author: sherwel
'''

import sys
import nmap   
import os
import time
import SQLTool
import Sqldatatask
import config
import Sqldata

import connectpool
import portscantask
import getLocationTool

import traceback

reload(sys) # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入   

class SniffrtTool(object):
    '''
    classdocs
    '''
    def __init__(self, logger=None):
        '''
        Constructor
        '''
        self.logger = logger
        try:
            self.nma = nmap.PortScanner()     # instantiate nmap.PortScanner object
            self.params='-sS -T4 -A -Pn '
            self.usual_ports='10000,10001,1001,1011,10109,102,1025-1029,10307,10311,1033,10364-10365,10407,10409-10410,10412,10414-10415,10428,10431-10432,10447,10449-10450,106,1089-1091,109-111,11001,1110,113,1158,1170,119,1200,12135-12137,12316,12380,1234,1243,12645,12647-12648,13,135,137-139,13722,13724,13782-13783,143-144,1433-1434,1492,14000,1500,1521,1524,1541,1600,161,1720,1722,1723,1730,1755,177,179,18000,18245,1900,1911,1935,1962,1966,199,1998-2001,2000,2222,20000,2006-2007,2023,2049,20547,2100,2121,21-23,2404,25-26,27017,2717,3000-3001,31,3128,3151,32768,3306,3310,3389,33812,34962-34964,37,34567,37777,38000-38001,38011-38012,38014-38015,38200,38210,38301,38400,38589,38593,38600,38700,389,38971,39129,39278,3986,4000,42,427,443-445,44818,456,45678,4592,465,46666,47808,4800,4840,4843,4899,49152-49157,50000-50016,5000-5004,50018-50021,50025-50028,5007,5009,50110-50111,50123,502,5052,5048,5058,5060,5065,5101,513-515,5190,51960,53,5357,5413,5432,543-544,5450,548,55000-55003,554,55555,556,56001-56099,5601,5631,5666,5800,587,5900-5902,60000,6000-6002,61697,62900,62911,62924,62930,62938,62956-62957,62963,62981-62982,62985,62992,63012,63027-63036,63041,63075,63079,63082,63088,63094,631,636,6379,646,65000,65443,6646,666,67,6711,6776,69,7,7000-7002,7070,7547,771,777,79-82,8000-8001,8008-8009,8080-8082,8086-8090,8099,8101,8181,8400,8443,85,873,88,8800,8888-8889,9,900,9080,9083,9090-9091,9100,9200,9300,9600,99,990,993,995,9999-10000'
#            self.params='-A -sC -R -v -O -T4 -Pn '
#            self.params='-sV -T4 -Pn -O '         #快捷扫描加强版
#            self.params='-sS -sU -T4 -A -v '   #深入扫描
        except nmap.PortScannerError:
            self.logger.error('Nmap not found:%s',sys.exc_info()[0])
        except:
            self.logger.error('Unexpected error:%s',sys.exc_info()[0])

        self.config = config.Config
        self.sqlTool = Sqldatatask.getObject()  # init DBmanager, and connect database and thread number
        self.portscan = portscantask.getObject()    #设置一些网络参数配置, 以及端口扫描的线程数，应该是决定nmap的速度 查看portScantask.log
        # init DBmanager and thread number
        self.getlocationtool = getLocationTool.getObject()

    def scaninfo(self,hosts='localhost', port='', arguments='', hignpersmission='0', callback=''):
        if callback == '': 
            callback = self.callback_result
#	后端添加任务的时候会写port，默认执行nmap自带的扫描
        orders = ''
        if port != '':
	    # 为什么要加，直接使用port不一样吗，在网页输入的时候是逗号分割的port
            orders += port
        else :
            orders = None
        try:
            if hignpersmission == '0' and orders == None:
                acsn_result = self.nma.scan(hosts=hosts,ports=self.usual_ports,arguments=self.params+arguments)
#                self.logger.debug("End scanaddress->%s:%s\n"%(hosts, orders))
#                print ("%s:%s全端口扫描结束\n%s\n"%(hosts, orders, str(acsn_result)))
                return callback(acsn_result) 
            else:
                acsn_result = self.nma.scan(hosts=hosts,ports=orders,arguments=self.params+arguments)
#                print ("%s:%s指定端口扫描结束\n%s\n"%(hosts, orders, str(acsn_result)))
                return callback(acsn_result)
        except nmap.PortScannerError,e:
            self.logger.error("spidertool::scaninfo()", str(traceback.print_exc()))
            return ''
        except:
            self.logger.error('Unexpected error:%s', sys.exc_info())
            return ''

    def callback_result(self, scan_result):
        self.logger.info("End scanaddress, execute sniffertool::callback_result store into DB.")
        tmp = scan_result
        for i in tmp['scan'].keys():
            host = i
            result=''
            try:
                temphosts = str(host)
                localtime = str(time.strftime("%Y-%m-%d %X", time.localtime()))
                self.getlocationtool.add_work([temphosts])	#why add this operator? 在网页上没有执行zmap扫描，所以需要加入位置信息的判断，但是后端添加的任务，相当于执行了两次这个位置信息的扫描
                try :
                    tempvendor=''
                    temposfamily=''
                    temposgen=''
                    tempaccuracy=''
                    if len(tmp['scan'][host]['osmatch']) > 0 and len(tmp['scan'][host]['osmatch'][0]['osclass'])>0:
                        tempvendor = str(tmp['scan'][host]['osmatch'][0]['osclass'][0].get('vendor',''))
                        temposfamily = str(tmp['scan'][host]['osmatch'][0]['osclass'][0].get('osfamily',''))
                        temposgen = str(tmp['scan'][host]['osmatch'][0]['osclass'][0].get('osgen',''))
                        tempaccuracy = str(tmp['scan'][host]['osmatch'][0]['osclass'][0].get('accuracy',''))
                    temphostname = ''
                    tempdecide = tmp['scan'][host].get('hostnames',[])
                    if len(tempdecide) > 0:
                        for y in tmp['scan'][host]['hostnames']:
                            temphostname += str(y.get('name','unknow'))+' '
                    tempstate = str(tmp['scan'][host]['status'].get('state',''))

                    sqldatawprk=[]
                    dic={"table":self.config.iptable,"select_params": ['ip','vendor','osfamily','osgen','accurate','updatetime','hostname','state'],"insert_values": [(temphosts,tempvendor,temposfamily,temposgen,tempaccuracy,localtime,temphostname,tempstate)]}

                    tempwprk=Sqldata.SqlData('replaceinserttableinfo_byparams',dic)
                    sqldatawprk.append(tempwprk)
                    self.sqlTool.add_work(sqldatawprk)               
                except Exception,e:
                    self.logger.error('Nmap system Error::'+str(e))
#                    print 'nmap system error d '+str(e)

                if 'tcp' in tmp['scan'][host].keys():
                    ports = tmp['scan'][host]['tcp'].keys()

                    for port in ports:
                        tempport = str(port)
                        tempportname = str(tmp['scan'][host]['tcp'][port].get('name',''))
                        tempportstate = str(tmp['scan'][host]['tcp'][port].get('state',''))
                        tempproduct = str(tmp['scan'][host]['tcp'][port].get('product',''))
                        tempportversion = str(tmp['scan'][host]['tcp'][port].get('version',''))
                        tempscript=SQLTool.decodestr(str(tmp['scan'][host]['tcp'][port].get('script','')))

                        if tempportstate.find('open') == -1:
                            self.logger.info("[%s:%s] %s has been %s, passing...%s", temphosts,tempport,tempportname,tempportstate,tempproduct)
                            continue

                        sqldatawprk=[]
                        dic={"table":self.config.porttable,"select_params": ['ip','port','timesearch','state','name','product','version','script','portnumber'],"insert_values": [(temphosts,tempport,localtime,tempportstate,tempportname,tempproduct,tempportversion,tempscript,str(tempport))]}
                        tempwprk=Sqldata.SqlData('replaceinserttableinfo_byparams',dic)

                        sqldatawprk.append(tempwprk)
                        self.sqlTool.add_work(sqldatawprk)
                        # 端口扫描(正常协议|非正常协议)
                        self.portscan.add_work([(tempportname,temphosts,tempport,tempportstate,tempproduct,tempscript)])
                elif 'udp' in  tmp['scan'][host].keys():
                    ports = tmp['scan'][host]['udp'].keys()
                    for port in ports:
                        tempport = str(port)
                        tempportname = str(tmp['scan'][host]['udp'][port].get('name',''))
                        tempportstate = str(tmp['scan'][host]['udp'][port].get('state',''))
                        tempproduct = str(tmp['scan'][host]['udp'][port].get('product',''))
                        tempportversion = str(tmp['scan'][host]['udp'][port].get('version',''))
                        tempscript = str(tmp['scan'][host]['udp'][port].get('script',''))

                        sqldatawprk=[]
                        dic={"table":self.config.porttable,"select_params": ['ip','port','timesearch','state','name','product','version','script','portnumber'],"insert_values": [(temphosts,tempport,localtime,tempportstate,tempportname,tempproduct,tempportversion,tempscript,str(tempport))]}
                        tempwprk=Sqldata.SqlData('replaceinserttableinfo_byparams',dic)
                        sqldatawprk.append(tempwprk)
                        self.sqlTool.add_work(sqldatawprk)
            except Exception,e:
                self.logger.error('Nmap Error'+str(e))
            except IOError,e:
                self.logger.error('错误IOError'+str(e))
            except KeyError,e:
                self.logger.warning('不存在该信息'+str(e))
            finally:
                return str(scan_result)

    def scanaddress(self,hosts=[], ports=[],arguments=''):
        temp=''
        self.logger.info("Begin scanaddress->%s:%s", str(hosts), str(ports))

        for i in range(len(hosts)):
            # 不指定端口，则扫描全部端口, 这里ports=['']虽然会进入指定端口哦，permission=1,但是仍然是NULL，还会扫描全部端口, 所以加了orders==None的判断
            if len(ports) <= i:
                result = self.scaninfo(hosts=hosts[i],arguments=arguments)
                if result is None:
                    pass
                else:
                    temp += result
            else:
                result = self.scaninfo(hosts=hosts[i], port=ports[i], arguments=arguments, hignpersmission='1')
                if result is None:
                    pass
                else:
                    temp+=result
            self.logger.info("End scanaddress->%s:%s", str(hosts), str(ports))
	return temp

    def isrunning(self):
        return self.nma.has_host(self.host)


order=' -P0 -sV -sC  -sU  -O -v  -R -sT  '
orderq='-A -P0   -Pn  -sC  -p '


if __name__  ==  "__main__":   
    hosts = []
    host_file = open(sys.argv[1]).readlines()
    for fi in host_file:
        hosts.append(fi.strip())
#    print hosts
#    hosts=['www.ykgs.gov.cn', 'zhengxie.bjtzh.gov.cn','hbj.bjmtg.gov.cn', 'www.bjchp.gov.cn']
#    hosts=['localhost']
    temp = SniffrtTool()
    localtime = str(time.strftime("%Y-%m-%d %X", time.localtime()))
    temp.scanaddress(hosts, ports=['443'],arguments='')
    print time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))



