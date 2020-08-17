import requests
from bs4 import BeautifulSoup
import os
import time
from multiprocessing.dummy import Pool as ThreadPool


class Downloader(object):
    def __init__(self, url, path, name):
        self.url = "https://jx.618g.com?url=" + url
        self.path = path
        self.name = name
        self.temp_path = os.path.join(self.path, 'temp')
        self.head = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"}
        if not os.path.exists(self.temp_path):
            os.mkdir(self.temp_path)

    def request(self, url):
        try:
            requests.packages.urllib3.disable_warnings()
            response = requests.get(url, headers=self.head, verify=False)
            response.raise_for_status()
            return response
        except Exception as e:
            print("HttpError happened......")
            print(e)

    def get_m3u8_url(self, url):
        res = self.request(url)
        soup = BeautifulSoup(res.text, 'lxml')
        src = soup.find('iframe').attrs['src']
        url = src.split('=')[1]
        return url

    def get_real_m3u8_url(self, m3u8_url):
        res = self.request(m3u8_url)
        real_url = m3u8_url.rstrip('index.m3u8')+res.text.split('\n')[2]
        return real_url

    def down_video_m3u8(self, path, real_url):
        res = self.request(real_url)
        content = res.content
        with open(path, 'wb') as f:
            f.write(content)
            f.close()

    def get_ts_urls(self, path, base_url):
        urls = []
        with open(path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if(line.endswith(".ts\n")):
                    url =base_url+line.rstrip('\n')
                    urls.append(url)
            f.close()
        return urls

    def down_ts(self, list):
        res = self.request(list[1])
        content = res.content
        ts_dir = os.path.join(self.temp_path, 'ts')
        if not os.path.exists(ts_dir):
            os.mkdir(ts_dir)
        ts_path = os.path.join(ts_dir, str(list[0]) + '.ts')
        with open(ts_path, 'wb') as f:
            f.write(content)
            f.close()

    def ts_walker(self, path):
        ts_list =[]
        for root, dirs, files in os.walk(path):
            for file in files:
                ts_list.append(os.path.join(root, file))
        ts_list = sorted(ts_list,key=lambda fn: int(fn.lstrip(root).rstrip('.ts')))
        return ts_list

    def merge_ts(self, ts_list):
        path = os.path.join(self.path, self.name+'.ts')
        with open(path, 'ab') as fw:
            for ts in ts_list:
                with open(ts, 'rb') as fr:
                    content = fr.read()
                    fr.close()
                    fw.write(content)
            fw.close()

    def start_spider(self):
        m3u8_url = self.get_m3u8_url(self.url)
        print(m3u8_url)
        real_url = self.get_real_m3u8_url(m3u8_url)
        print(real_url)
        m3u8_path = os.path.join(self.temp_path, self.name+'.m3u8')
        print("正在下载m3u8文件......")
        self.down_video_m3u8(m3u8_path, real_url)
        print("下载m3u8文件完成！")
        base_url = real_url.rstrip(self.name + 'index.m3u8')
        ts_urls = self.get_ts_urls(m3u8_path, base_url)
        print(ts_urls)
        print("正在下载ts文件......")
        time1 = time.time()
        pool = ThreadPool(10)
        pool.map(self.down_ts, [[i, ts_urls[i]]for i in range(len(ts_urls))])
        pool.close()
        pool.join()
        time2 = time.time()
        print("下载ts文件完成！耗费时间:"+str(time2-time1))
        print("正在合并ts文件......")
        time3 = time.time()
        ts_dir = os.path.join(self.temp_path, 'ts')
        ts_list = self.ts_walker(ts_dir)
        self.merge_ts(ts_list)
        time4 = time.time()
        print("合并ts文件完成！耗费时间:"+str(time4-time3))
        print("下载完成！")


if __name__ == '__main__':
    url = "https://v.qq.com/x/page/v0032kxv040.html?ptag=10525"
    path = "D:\\pythonDownload\\video\\"
    name = "天行九歌-第82集"
    downloader = Downloader(url, path, name)
    downloader.start_spider()