#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import urlparse
import httplib

import re
import threading
import Queue
from bs4 import BeautifulSoup
import time
import glob
import socket
#import ipaddress
import os
import traceback
import webbrowser
from lib.interface import InfoDisScannerBase
import callbackfuzz

from __builtin__ import str

class InfoDisScanner(InfoDisScannerBase):
    def __init__(self, timeout=600, depth=2,logger=None):
        self.START_TIME = time.time()
        self.TIME_OUT = timeout
        self.LINKS_LIMIT = 20       # max number of links
        self.logger=logger
        self.final_severity = None
        self._init_rules()

    def _init_rules(self):
        try:
            self.url_dict = []
            p_severity = re.compile('{severity=(\d)}')
            p_tag = re.compile('{tag="([^"]+)"}')
            p_status = re.compile('{status=(\d{3})}')
            p_content_type = re.compile('{type="([^"]+)"}')
            p_content_type_no = re.compile('{type_no="([^"]+)"}')
            for rule_file in glob.glob(os.path.split(os.path.realpath(__file__))[0]+'/rules/*.txt'):
                infile = open(rule_file, 'r')
                for url in infile:
                    if url.startswith('/'):
                        _ = p_severity.search(url)
                        severity = int(_.group(1)) if _ else 3
                        _ = p_tag.search(url)
                        tag = _.group(1) if _ else ''
                        _ = p_status.search(url)
                        status = int(_.group(1)) if _ else 0
                        _ = p_content_type.search(url)
                        content_type = _.group(1) if _ else ''
                        _ = p_content_type_no.search(url)
                        content_type_no = _.group(1) if _ else ''
                        url = url.split()[0]
                        self.url_dict.append((url, severity, tag, status, content_type, content_type_no))
                        # print (url, severity, tag, status, content_type, content_type_no)
                infile.close()
        except Exception, e:
            self.logger.error('[Exception in InfoDisScanner._load_dict] %s' % e)

    def _http_request(self, url, timeout=10,protocal='http',path=None):
        conn=None
        try:
            if not path: path = '/'
            conn_fuc = httplib.HTTPSConnection if protocal == 'https' else httplib.HTTPConnection
            conn = conn_fuc(url, timeout=timeout)
            conn.request(method='GET', url=path)
                         # "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0"
                         # 'User-Agent': 'Mozilla/5.0 (Windows NT 5.2) AppleWebKit/534.30 (KHTML, like Gecko) Chrome/12.0.742.122 Safari/534.30'
            # )
            resp = conn.getresponse()
            resp_headers = dict(resp.getheaders())
            status = resp.status
            if resp_headers.get('content-type', '').find('text') >= 0 or resp_headers.get('content-type', '').find('html') >= 0 or \
                            int(resp_headers.get('content-length', '0')) <= 1048576:
                html_doc = self._decode_response_text(resp.read())
            else:
                html_doc = ''
            return status, resp_headers, html_doc
        except Exception, e:
            self.logger.error('[Exception in InfoDisScanner._http_request] %s %s', str(e), str(traceback.print_exc()))
            return -1, {}, ''
        finally:
            if conn is not None:
                conn.close()
                del conn

    def _enqueue(self, url,url_queue):
        for _ in self.url_dict:
            full_url = url.rstrip('/') + _[0]
            url_description = {'prefix': url.rstrip('/'), 'full_url': full_url}
            # url_description:{'prefix': 'qcpj.bnuz.edu.cn:80', 'full_url': 'qcpj.bnuz.edu.cn:80/backend/'}, severity:2, tag:, p_status:0, content_type:, content_type_no: path:/backend/
            item = (url_description, _[1], _[2], _[3], _[4], _[5], _[0])
            url_queue.put(item)


    @staticmethod
    def _decode_response_text(rtxt, charset=None):
        if charset:
            try:
                return rtxt.decode(charset)
            except:
                pass
        encodings = ['UTF-8', 'GB2312', 'GBK', 'iso-8859-1', 'big5']
        for _ in encodings:
            try:
                return rtxt.decode(_)
            except:
                pass
        try:
            return rtxt.decode('ascii', 'ignore')
        except:
            pass
        raise Exception('Fail to decode response Text')


    def _update_severity(self, severity):
        if severity > self.final_severity:
            self.final_severity = severity

    def _scan_worker(self,url_queue,protocal,_status,has_404,ip,port):
        mail_msg = ''
        results={}

        print ("fuzzdetect::_scan_worker() url:%s, status:%d"%(str(url_queue), _status))
        while url_queue.qsize() > 0:
            try:
                item = url_queue.get(timeout=1.0)
            except:
                return None
            url=None
            try:
                url_description, severity, tag, p_status, content_type, content_type_no, path = item
                url = url_description['full_url']
                prefix = url_description['prefix']
            except Exception, e:
                self.logger.error('[InfoDisScanner._scan_worker][1] Exception: %s' % e)
                continue
            if not item or not url:
                break
            try:
                c_status, headers, html_doc = self._http_request(url=prefix,protocal=protocal,path=path)
                # if (c_status in [200, 301, 302, 303]) and (has_404 or c_status!=_status):
                if (c_status in [200]) and (has_404 or c_status !=_status):
                    if p_status and c_status != p_status:
                        continue
                    if not p_status or html_doc.find(str(p_status)) >= 0:
                        if content_type and headers.get('content-type', '').find(content_type) < 0 or \
                            content_type_no and headers.get('content-type', '').find(content_type_no) >=0:
                            continue
                        if results.get(prefix,None) is None:
                            results[prefix] = []
                            add_disclosure = {'status':c_status, 'url':'%s' % (url)}
                            if add_disclosure in results[prefix]:
                                continue
                            mail_msg += """<p>泄漏路径：%s</p>"""%url
                            results[prefix].append(add_disclosure)
                            self._update_severity(severity)

                if len(results) >= 30:
                    self.logger.warning('More than 30 vulnerabilities found for [%s], could be false positive.', url)
            except Exception, e:
                self.logger.error('[InfoDisScanner._scan_worker][2][%s] Exception %s' % (url, e))

        # return a dict, this disclosure detect will be used in pocdetect's keywords
        if len(results) >= 1:
            callbackfuzz.sendemail('http://' + prefix, mail_msg)
            return results

    def check_404(self,url,protocal):
        """
        check status 404 existence
        """
        _status=0
        has_404=False
        try:
            # status, resp_headers, html_doc
            _status, headers, html_doc = self._http_request(url=url,protocal=protocal,path='/A_NOT_EXISTED_URL_TO_CHECK_404_STATUS_EXISTENCE')
            has_404 = (_status == 404)
            if _status == -1:
                self.logger.error('[ERROR] Fail to connect to %s' , url)
                return -1, has_404
            return _status,has_404
        except Exception, e:
            return _status,has_404
      
    def scanvul(self,ip,protocal,port):
        if len(self.url_dict)==0:
            self._init_rules()
        self.final_severity = 0
        url = ip + ':' + str(port)
        status, has404 = self.check_404(url=url,protocal=protocal)           # check the existence of status 404

        if status != -1:
            tempqueue = Queue.Queue()
            self._enqueue(url, tempqueue)
            dataresult = self._scan_worker(url_queue=tempqueue,protocal=protocal,_status=status,has_404=has404,ip=ip,port=port)
            if dataresult is not None:
                callbackfuzz.storedata(ip=ip, port=port, disclosures=dataresult)
                self.logger.info('Fuzzey detect callbackfuzz: %s' , str(dataresult))
                pass
        else:
            pass


if __name__ == '__main__':
    a = InfoDisScanner()
    while True:
        print a.scanvul(ip='qcpj.bnuz.edu.cn',port='80',protocal='http')
        print a.scanvul(ip='www.bnuz.edu.cn', port='80', protocal='http')

#         if results:
#             for key in results.keys():
#                 for url in results[key]:
#                     print  '[+] [%s] %s' % (url['status'], url['url'])
