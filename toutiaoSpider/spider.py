# -*- coding: utf-8 -*-
'''
抓取今日头条图片 存储到mongdb
'''
import threading
import sys
import getopt
import os
import requests
from requests.exceptions import RequestException
import json
import re
from bs4 import BeautifulSoup
import pymongo
from time import sleep

from hashlib import md5

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36'
}

def getPagehtml(url = '',header={},param = None):
    try:
        res = requests.get(url = url,params= param,headers=header)
        if res.status_code == 200:
            return res.text
        print('\033[1;31m 请求页面失败 status_code =%s  url = %s  \033[1;0m'%(str(res.status_code),res.url))
        return None
    except RequestException as e:
        print('\033[1;31m 请求页面失败  %s\033[1;0m'%(e))
        return None

def parsePageIndex(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data['data']:
            if 'source_url'  in item.keys():
                yield 'https://www.toutiao.com'+item['source_url']
    else:
        print(' \033[1;31m 引导页无有效数据\033[1;0m')
        return None

"""
title 
imagelist  = JSOR.parse("")
"""
def parsePageImageFomat(html):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')
    titleContent = ''
    if len(title) > 0 :
        titleContent = title[0].get_text()
    else:
        return None
    pattern1 = re.compile('BASE_DATA\.galleryInfo.*?(\{.*?)</script>',re.S)
    g = re.search(pattern1,html)
    pattern2 = re.compile('JSON\.parse\("(.*?)"\),',re.S)
    if g != None:
        g2 = re.search(pattern2,g.group(1))
        if g2 !=None:
            find = g2.group(1).replace('\\','')
            try:
                datalDict = json.loads(find)
                if 'sub_images' in datalDict.keys():
                    return {'title':titleContent,'images':[item.get('url') for item in datalDict.get('sub_images')]}
            except Exception as e:
                print('\033[1;31m 解析图片地址错误 %s \033[1;0m'%(e))
                return None

"""
content = articleInfo {
}
"""
def parsePageArticleFomat(html):
    pattern = re.compile('articleInfo:.*?title:(.*?)content:(.*?)groupId', re.S)
    result = re.search(pattern,html)
    pattern2 =  re.compile('img src.*?(http://.*?)&quot')

    if result != None:
        title = result.group(1)
        title = title.replace('\'',"")
        imageUrlList = re.findall(pattern2,result.group(2))
        if len(imageUrlList)  == 0 :
            return None
        return {'title': title.strip(), 'images': imageUrlList}

    return None
def parsePageGeneral(html):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')
    titleContent = ''
    if len(title) > 0 :
        titleContent = title[0].get_text()
    else:
        return None
    images = soup.select('img')
    if len(images) == 0 :
        return None
    imagesList = []
    for item in images :
        if 'src' in item.attrs.keys():
            imagesList.append(item['src'])
    return {'title': titleContent, 'images': imagesList}


def parsePageDetail(html):
    '''
    imagedict = parsePageGeneral(html)
    if imagedict != None:
        return imagedict
    '''
    imagedict = parsePageImageFomat(html)
    if imagedict != None:
        return imagedict
    imagedict = parsePageArticleFomat(html)
    if imagedict != None:
         return imagedict

    return None

def url_complete(url):
    if url[-3:] == 'htm':
        url = url+'l'
    return url

def getToutiaoPageIndex(offset = 0,kw=''):
    params = {
        'offset': str(offset),
        'format': 'json',
        'keyword': kw,
        'autoload': 'true',
        'count': '20',
        'cur_tab': '1',
        'from': 'search_tab',
    }
    url = 'https://www.toutiao.com/search_content/'
    #获得搜索结果引导页
    html = getPagehtml(url,headers,params)
    if html == None :
        print(' \033[1;31m 搜索失败 !\033[1;0m\n')
        return None
    #解析引导页面中的文章地址
    urls  = parsePageIndex(html)
    if urls == None:
        print(' \033[1;31m 解析引导页列表失败 !\033[1;0m\n')
        return None
    for url  in  urls:
        url = url_complete(url)
        yield  url

def dowonload_image(url=''):
    try:
        res = requests.get(url=url,headers = headers)
        if res.status_code == 200:
            # 防止 被网站屏蔽
            sleep(3)
            return res.content
        print('\033[1;31m 下载图片失败 status_code =%s  url = %s  \033[1;0m' % (str(res.status_code), res.url))
        return None
    except RequestException as e:
        print('\033[1;31m 下载图片失败  %s \033[1;0m  ' % (e))
        return None

def save_image(content,idir):
    file_path = idir +'/'+ md5(content).hexdigest()+'.jpg'
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()


def write2FileFromUrl(imageUrlList,imageDir):
    for item in imageUrlList:
        content = dowonload_image(item)
        if content != None:
            save_image(content,imageDir)


def threadTask(offset,kw,imageDir,dbcoll):
    print(threading.current_thread(),'start')
    urls = getToutiaoPageIndex(offset, kw=kw)
    if urls == None:
        print(' \033[1;31m 获得引导页地址列表失败 ! \033[1;0m \n')
        return None

    for url in urls:
        #print(url)
        htmlPageSource = getPagehtml(url=url, header=headers, param=None)
        if htmlPageSource == None:
            print(' \033[1;31m 获得文章页面失败 !\033[1;0m \n')
            continue
        imageDict = parsePageDetail(htmlPageSource)
        if imageDict != None:
            imageDict['url'] = url
            # writedb
            if dbcoll.find_one({'title':imageDict['title']})  == None:
                dbcoll.insert_one(imageDict)
                write2FileFromUrl(imageDict['images'],imageDir)




def initMongoDB(kw):
    mongo_url = "127.0.0.1:27017"
    client = pymongo.MongoClient(mongo_url)
    DATABASE = "spider-头条"
    db = client[DATABASE]
    COLLECTION = kw
    db_coll = db[COLLECTION]
    return db_coll

def spider(threadcount = 1,kw= '美女'):
    imageDir = os.getcwd().replace('\\','/') + '/'+kw
    print(imageDir)
    if not os.path.exists(imageDir):
        os.mkdir(imageDir)
    taskList = []
    dbcoll = initMongoDB(kw)
    for i in range(threadcount):
        task = threading.Thread(target=threadTask,args=(20*i,kw,imageDir,dbcoll,))
        taskList.append(task)
    for task in taskList:
        task.start()





def optInit(argv):
    kw = '美女'
    number = 1
    print(argv)
    try:
        opts, args = getopt.getopt(argv, "hk:n:", [ "key=",'number='])
    except getopt.GetoptError:
        print('spider.py  -k <find image name >  -n <1 = 20 index html> ')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('spider.py  -k <find image name >  -n <1 = 20 index html> ')
            sys.exit()
        elif opt in ("-k", "--key"):
            kw = arg
        elif opt in ("-n", "--number"):
            number = arg
    return kw,int(number)



if __name__ == '__main__':
    kw,number = optInit(sys.argv[1:])
    print('start key = %s threadcount = %d '%(kw,number))
    spider(number, kw)