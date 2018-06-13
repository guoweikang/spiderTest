#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from requests.exceptions import  RequestException
import threading
import sys
import getopt
import json

class ZhiHuSpider():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'http://www.zhaopin.com/beijing/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Upgrade-Insecure-Requests': '1'
    }
    def __init__(self,keyword = 'python开发工程师',pageNumber = 1,file=''):
        self.kw = keyword
        self.file = open(file,'w',encoding='utf-8')
        self.pageNumber = pageNumber
        self.lock = threading.Lock()
        self.taskList = []
    def threadFunc(self,n):
        print('thread %s start\n'%(threading.current_thread()))
        indexCls = IndexParse(str(n),kw=self.kw)
        for one in indexCls.GetIndexData():
            self.lock.acquire()
            self.file.write(json.dumps(one,ensure_ascii=False) + '\n')
            self.lock.release()

    def startSpider(self):
        for i in range(self.pageNumber):
            task = threading.Thread(target  = self.threadFunc,args=(i,))
            self.taskList.append(task)
        for task in self.taskList:
            task.start()

class IndexParse():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'http://www.zhaopin.com/beijing/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Upgrade-Insecure-Requests': '1'
    }
    def __init__(self,pageIndex='1',kw = ''):
        self.pageIndex = pageIndex
        self.url = 'http://sou.zhaopin.com/jobs/searchresult.ashx'
        self.data = {
            'jl':'530',
            'kw':kw,
            'sm':'0',
            'p':pageIndex
        }
    def _getIndexHtml(self):
        try:
            res = requests.get(url=self.url,params=self.data,headers=self.headers)
            if res.status_code == 200:
                return res.text
            print('status_code = '+str(res.status_code))
            return  None
        except RequestException as e:
            print('status_code = ' + str(res.status_code))
            return None
#get ata : jobname ,反馈率,公司名称，职位月薪  工作地点 发布日期
    def _parsePageIndex(self):
        soup = BeautifulSoup(self.html,'lxml')
        jobList = soup.select('.newlist_list_content')
        for jobListItem in jobList:
            for jobOne in jobListItem.select('.newlist')[1:]:
                yield {
                    'name':jobOne.select('.zwmc')[0].get_text().strip(),
                    'respon':jobOne.select('.fk_lv')[0].get_text().strip(),
                    'confirmName':jobOne.select('.gsmc')[0].get_text().strip(),
                    'salary':jobOne.select('.zwyx')[0].get_text().strip(),
                    'address':jobOne.select('.gzdd')[0].get_text().strip(),
                    'date': jobOne.select('.gxsj')[0].get_text().strip(),
                    'url':jobOne.select('.zwmc a')[0].attrs['href'].strip()
                }
    def GetIndexData(self):
        html = self._getIndexHtml()
        if html == None:
            return None
        self.html = html
        for  one in self._parsePageIndex():
            yield  one

def main(file,kw,number):
    spi = ZhiHuSpider(keyword= kw, pageNumber=number,file=file)
    spi.startSpider()

def optInit(argv):
    file = 'data.txt'
    kw = 'python'
    number = 1
    print(argv)
    try:
        opts, args = getopt.getopt(argv, "hf:k:n:", ["file=", "key=",'pagenumber='])
    except getopt.GetoptError:
        print('zhilian.py  -k <jobname> -f <savefile>  -n <pagenumber> ')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('zhilian.py  -k <jobname> -f <savefile> ')
            sys.exit()
        elif opt in ("-f", "--file"):
            file = arg
        elif opt in ("-k", "--key"):
            kw = arg
        elif opt in ("-n", "--pagenumber"):
            number = arg
    return file,kw,number


if __name__ == '__main__':
    print('start\n')
    file,kw,number = optInit(sys.argv[1:])
    main(file,kw,int(number))