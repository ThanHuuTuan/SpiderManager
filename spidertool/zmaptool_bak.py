#!/usr/bin/python
#coding:utf-8
import time
import re
from subprocess import Popen, PIPE
import os
import SQLTool
import config,portscantask
from nmaptoolbackground.control import taskcontrol
from nmaptoolbackground.model import job
import Sqldatatask
import Sqldata
import   trace 
import getLocationTool
import sniffertask
portname = {'80':'http','8080':'http','443':'https','22':'telnet','3306':'mysql','873':'rsync'} 
zmapinstance=None

def getObject():
    global zmapinstance
    if zmapinstance is None:
        zmapinstance = Zmaptool()
    return zmapinstance

class Zmaptool:
    def __init__(self):
        self.sqlTool = Sqldatatask.getObject()  # init DB
        self.config = config.Config
        self.portscan = portscantask.getObject()
        self.getlocationtool = getLocationTool.getObject()

    def do_scan(self, port='8080', num='10', needdetail='0'):
        path = os.getcwd()
        locate = os.path.split(os.path.realpath(__file__))[0]
        cmd = "zmap -w "+locate+"/iparea.json -B 50M -p "+port+" -q -O json"
        import commandtool

        if True:
            returnmsg = commandtool.command(cmd=cmd)    
            # print "returnmsg:", returnmsg
            p = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
            ip_list = p.findall(returnmsg)
            localtime = str(time.strftime("%Y-%m-%d %X", time.localtime()))
            insertdata = []
            jobs = []
            print "\n\nzmaptool get port:%s, open ip: %d个\n\n"%(str(port), len(ip_list))
            for i in ip_list:
                insertdata.append((str(i), port, localtime, 'open', str(port)))
                print ("zmaptool scan ip:%s"%i)
                self.getlocationtool.add_work([str(i)]) # save ip info(get from ip.taobao.com) to ip_maindata

                if needdetail=='0':
                    global portname
                    nowportname=portname.get(port,'')
                    self.portscan.add_work([(nowportname,str(i), port,'open','','')])
                else:
                    # 执行zmap的时候开放后，默认nmap扫描全部端口；但是通过页面添加任务的时候如果指定了端口，不会扫描全部端口
                    ajob = job.Job(jobaddress=str(i),jobport='',forcesearch='0',isjob='0')
                    jobs.append(ajob)
            if needdetail != '0':
                tasktotally = sniffertask.getObject()
                tasktotally.add_work(jobs)
            extra=' on duplicate key update  state=\'open\' , timesearch=\''+localtime+'\''
#             self.sqlTool.inserttableinfo_byparams(table=self.config.porttable,select_params=['ip','port','timesearch','state'],insert_values=insertdata,extra=extra)
            sqldatawprk=[]
            dic={"table":self.config.porttable,"select_params":['ip','port','timesearch','state','portnumber'],"insert_values":insertdata,"extra":extra}
            tempwprk = Sqldata.SqlData('inserttableinfo_byparams',dic)
            sqldatawprk.append(tempwprk)
            self.sqlTool.add_work(sqldatawprk)
        # try:
        #
        #     p.terminate()
        #
        # except Exception,e:
        #     print e
        #     print 'error'

#             self.sqlTool.closedb()

if __name__ == "__main__":
    temp = Zmaptool()
    temp.do_scan(needdetail='1')


