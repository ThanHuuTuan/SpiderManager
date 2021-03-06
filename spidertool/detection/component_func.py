#!/usr/bin/python
#coding:utf-8
import traceback

try:
    from plugins import port_template,rsyncdeal,sshdeal,ftp_weakpass
    componentFunc = {
        'mysql':port_template.mysql,
        'rsync':rsyncdeal.rsync,
        'ssh':sshdeal.ssh2,
        'ftp':ftp_weakpass.ftpdeal
    }
except Exception,e:
    print traceback.print_exc()
