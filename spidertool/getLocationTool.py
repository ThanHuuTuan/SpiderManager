#!/usr/bin/python
# -*- coding: utf-8 -*-

import time,datetime
import re
import webtool
from TaskTool import TaskTool
import os
import config
import json,SQLTool,Sqldatatask,Sqldata
getlocationtaskinstance=None

def getObject():
    global getlocationtaskinstance
    if getlocationtaskinstance is None:
        getlocationtaskinstance = GetLocationTask(1)
    return getlocationtaskinstance

def getlocationjsondata(jsondata):
    print jsondata, jsondata.get('status','1')
    if jsondata.get('status','1')  ==  '0':   #get success
        country = jsondata['data'].get('country','0')
        country_id = str(jsondata['data'].get('country_id','0'))
        area = jsondata['data'].get('area','0')
        area_id = str(jsondata['data'].get('area_id','0'))
        region = jsondata['data'].get('province','0')
        region_id = str(jsondata['data'].get('province_id','0'))
        city = jsondata['data'].get('city','0')
        city_id = str(jsondata['data'].get('city_id','0'))
        county = jsondata['data'].get('county','0')
        county_id = str(jsondata['data'].get('county_id','0'))
        isp = jsondata['data'].get('isp','0')
        isp_id = str(jsondata['data'].get('isp_id','0'))

        if area_id == '':
            area_id='0'
        if city_id == '':
            city_id='0'
        if county_id == '':
            county_id='0'
        if isp_id == '':
            isp_id='0'

        return country,country_id,area,area_id,region,region_id,city,city_id,county,county_id,isp,isp_id
    else:
        return '0','0','0','0','0','0','0','0','0','0','0','0'

class GetLocationTask(TaskTool):
    def __init__(self,isThread=1,deamon=True):
        TaskTool.__init__(self,isThread,deamon=deamon)
        self.sqlTool = Sqldatatask.getObject()  #init DBmanager
        self.config = config.Config
        self.set_deal_num(1)

    def task(self, ip, threadname):
        print 'getLocationTool::task() ip location do ......the ip is ' + ip
        jsondata = webtool.getLocationinfo(ip) #使用ip.taobao.com获取该ip对应的信息，返回一个json结构的字典
        country, country_id, area, area_id, region, region_id, city, city_id, county, county_id, isp, isp_id = getlocationjsondata(jsondata)
        localtime = str(time.strftime("%Y-%m-%d %X", time.localtime()))
        insertdata=[]
        insertdata.append((ip,country,country_id,area,area_id,region,region_id,city,city_id,county,county_id,isp,isp_id,localtime))

        extra = ' on duplicate key update updatetime='+SQLTool.formatstring(localtime)+',country='+SQLTool.formatstring(country)+', country_id='+SQLTool.formatstring(country_id)+',area='+SQLTool.formatstring(area)+', area_id='+SQLTool.formatstring(area_id)+',region='+SQLTool.formatstring(region)+', region_id='+SQLTool.formatstring(region_id)+',city='+SQLTool.formatstring(city)+', city_id='+SQLTool.formatstring(city_id)+',county='+SQLTool.formatstring(county)+', county_id='+SQLTool.formatstring(county_id)+',isp='+SQLTool.formatstring(isp)+', isp_id='+SQLTool.formatstring(isp_id)

        sqldatawork=[]
        dic={"table":self.config.iptable,"select_params":['ip','country','country_id','area','area_id','region','region_id','city','city_id','county','county_id','isp','isp_id','updatetime'],"insert_values":insertdata,"extra":extra}
        # 和之前的手工写入数据库操作一样
        tempwork = Sqldata.SqlData('inserttableinfo_byparams', dic)
        sqldatawork.append(tempwork)
        self.sqlTool.add_work(sqldatawork)
        del insertdata
        time.sleep(0.2)
        ans=''
        return ans

def test():
    jsondata = webtool.getLocationinfo('123.123.123.120')
    if jsondata.get('code','1') == 0:
        country=jsondata['data'].get('country','0')
        country_id = str( jsondata['data'].get('country_id','0'))
        area=jsondata['data'].get('area','0')
        area_id = str( jsondata['data'].get('area_id','0'))
        region=jsondata['data'].get('region','0')
        region_id = str( jsondata['data'].get('region_id','0'))
        city=jsondata['data'].get('city','0')
        city_id = str( jsondata['data'].get('city_id','0'))
        county=jsondata['data'].get('county','0')
        county_id = str( jsondata['data'].get('county_id','0'))
        isp=jsondata['data'].get('isp','0')
        isp_id = str( jsondata['data'].get('isp_id','0'))

        return country,country_id,area,area_id,region,region_id,city,city_id,county,county_id,isp,isp_id

if __name__  ==  "__main__":
    a = getObject()
    a.add_work(['www.bgpc.gov.cn'])
    while True:
        pass
