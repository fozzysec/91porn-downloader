#!/usr/bin/env python3
from gevent import monkey
monkey.patch_all()
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import gevent
from queue import Queue
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
import sys
import lxml.html
import re
import os
import json
from binascii import crc32

#alternative "http://www.91porn999.com"
SITE_DOMAIN = "http://www.91porn888.com"
LOGIN_URL = "{0}/denglu.html"
INDEX_URL = "{0}/lm/1-3-2-1-{1}.html"
VALIDATION = "www.wuyuexiang.com"
DOWNLOAD_DIR = "videos"
UA = 'Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'
_video_player_re = re.compile(r'videourl:\s*\"(.*)\"', re.MULTILINE)
VISIT_RECORD = "_91_record.dat"
VISIT_RECORD_TMP = "_91_record.tmp"
TIMEOUT = 30
FETCH_RETRY = 5
DOWNLOAD_RETRY = 5
INDEX_THREAD = 2
ACCESS_THREAD = 5
DOWNLOAD_THREAD = 5

def get_player_video(session, queue, url, title, retries = 3):
    response = session.get(url, allow_redirects=False, timeout=TIMEOUT)
    if response.status_code is not 200:
        print("[Fetcher][Error]Insuffcient balance")
        return
    doc = lxml.html.fromstring(response.text)
    try:
        player_config = doc.xpath('//script[2]/text()')[0]
    except IndexError:
        print("[Fetcher][Error]Error when get player page")
        return
    match = _video_player_re.search(player_config)
    video_url = match.group(1)
    url_validator = urlparse(video_url)
    if not all([
        url_validator.scheme,
        url_validator.netloc,
        url_validator.path
        ]):
        if(retries > 0):
            print("[Fetcher][Error]Broken URL found, retries = %d" % retries)
            get_player_video(session, queue, url, title, retries - 1)
            return
    else:
        print("[Fetcher][Info]%s: %s" % (title, video_url))
        queue.put((video_url, title,))

def process_video_urls(queue, download_queue, access):
    if os.path.isfile(VISIT_RECORD):
        visit_record = open(VISIT_RECORD, 'r')
        visited_list = json.loads(visit_record.read())
        visit_record.close()
    else:
        visited_list = []
    while(True):
        url = queue.get(block=True)
        if url is 'STOP':
            break
        result, updated_visited_list = check_video_url(visited_list, url)
        if result:
            visited_list = updated_visited_list
            access['pool'].submit(
                    visit_video,
                    access['session'],
                    download_queue,
                    ''.join([SITE_DOMAIN, url])
                    )
        else:
            print("[Fetcher][Info]Duplicated video, discard it.")
    access['pool'].shutdown()
    download_queue.put(('STOP',None,))
    tmp_visit_record = open(VISIT_RECORD_TMP, 'w')
    tmp_visit_record.write(json.dumps(visited_list))
    tmp_visit_record.close()

def check_video_url(visited_list, url):
    checksum = crc32(url.encode('ascii'))
    if checksum not in visited_list:
        visited_list.append(checksum)
        return True, visited_list
    else:
        return False, None

def visit_video(session, queue, url):
    response = session.get(url, allow_redirects=False, timeout=TIMEOUT)
    if response.status_code is 302:
        print("[visit_video][Error]Insufficient account credit balance.")
        queue.put(('STOP', None,))
        return
    doc = lxml.html.fromstring(response.text)
    
    try:
        title = doc.xpath('//div[@class="page-header"]/h1/text()')[0].rstrip()
        player_url = doc.xpath('//iframe[@id="player"]/@src')[0]
    except IndexError:
        print("[visit_video][Error]Error when get video page")
        return
    title = re.sub('[\n\s]', '', title)
    player_url = ''.join([SITE_DOMAIN, player_url])
    get_player_video(session, queue, player_url, title)

def download_video(session, url, title):
    response = session.get(url, stream=True, timeout=TIMEOUT)
    if response.headers['Content-Type'] is 'text/html':
        print("[Downloader][Error]Invalid video {} found, skipping.".format(title))
        return
    if response.headers['content-length'] is 0:
        print("[Downloader][Error]Empty video {} found, skipping.".format(title))
        return
    if response.status_code is not 200:
        print("[Downloader][Error]Invalid video {} found, skipping.".format(title))
        return
    checksum = crc32(url.encode('ascii'))
    try:
        f = open("{}/{}-{:x}.mp4".format(DOWNLOAD_DIR, title, checksum), 'rb')
    except FileNotFoundError:
        print("[Downloader][Info]Starting download video {}-{:x}.mp4...".format(title, checksum))
        with open("{}/{}-{:x}.mp4".format(DOWNLOAD_DIR, title, checksum), 'wb') as f:
            for chunk in response.iter_content(chunk_size=4096):
                f.write(chunk)
        print("[Downloader][Info]Download video {}-{:x}.mp4 done.".format(title, checksum))

def download_videos(queue, download):
    while(True):
        (url, title) = queue.get(block=True)
        if url is 'STOP':
            break
        download['pool'].submit(
                download_video,
                download['session'],
                url,
                title
                )
    download['pool'].shutdown()

def visit_index(session, url, queue, fh):
    doc = lxml.html.fromstring(session.get(url, timeout=TIMEOUT).text)
    results = doc.xpath('//div[@class="col-sm-6 col-md-12 beijing img-rounded divcss32"]')
    for node in results:
        try:
            title = node.xpath('./div/h5/a/text()')[0]
            url = node.xpath('./div/h5/a/@href')[0]
            date = ' '.join([node.xpath('./div/div/div/div/ul/li[2]/a/text()')[0], node.xpath('./div/div/div/div/ul/li[3]/a/text()')[0].rstrip()])
        except IndexError:
            continue
        print("[Parser][Info]%s| %s| %s" % (url, date, title))
        fh.write("%s| %s| %s\n" % (url, date, title))
        queue.put(str(url))

def init(username, password, index_file):
    index_session = requests.Session()
    index_session.headers.update({'user-agent': UA})
    index_session.mount(SITE_DOMAIN, HTTPAdapter(max_retries=FETCH_RETRY))

    access_session = requests.Session()
    access_session.headers.update({'user-agent': UA})
    access_session.mount(SITE_DOMAIN, HTTPAdapter(max_retries=FETCH_RETRY))

    download_session = requests.Session()
    download_session.headers.update({'user-agent': UA})
    download_session.mount('http://', HTTPAdapter(max_retries=DOWNLOAD_RETRY))

    process_queue = Queue()
    download_queue = Queue()

    index_pool = ThreadPoolExecutor(max_workers=INDEX_THREAD)
    access_pool = ThreadPoolExecutor(max_workers=ACCESS_THREAD)
    download_pool = ThreadPoolExecutor(max_workers=DOWNLOAD_THREAD)

    fh = open(index_file, 'w', encoding='utf8')
    response = access_session.post(LOGIN_URL.format(SITE_DOMAIN), data={
        'ming': username,
        'mima': password,
        'wenti': VALIDATION
        })
    if response.status_code is 200:
        print("[Initializer][Info]Login succees.")
        return {'session': index_session, 'pool': index_pool}, {'session': access_session, 'pool': access_pool}, {'session': download_session, 'pool': download_pool}, process_queue, download_queue, fh
    else:
        print("[Initializer][Error]Login failed.")
        return None

def cleanup(fh):
    fh.close()
    os.rename(VISIT_RECORD_TMP, VISIT_RECORD)


username = sys.argv[1]
password = sys.argv[2]
index_file = sys.argv[3]
start_id = int(sys.argv[4])
end_id = int(sys.argv[5])

index, access, download, process_queue, download_queue, fh = init(username, password, index_file)

process_thread = Thread(
        target=process_video_urls,
        args=(process_queue, download_queue, access,)
        )
process_thread.start()
download_thread = Thread(
        target=download_videos,
        args=(download_queue, download,)
        )
download_thread.start()
urls = [INDEX_URL.format(SITE_DOMAIN, i) for i in range(start_id, end_id + 1)]
for url in urls:
    index['pool'].submit(
            visit_index,
            index['session'],
            url,
            process_queue,
            fh
            )

index['pool'].shutdown()
process_queue.put('STOP')

process_thread.join()
download_thread.join()
cleanup(fh)
