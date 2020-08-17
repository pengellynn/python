import requests
import json
from multiprocessing import Pool


class DownLoader(object):
    def __init__(self):
        self.image_urls = []
        self.image_ids = []
        self.image_num = 0

    def get_page_info(self, server, url):
        try:
            header = requests.head(server, verify=False)
            header.raise_for_status()
            page_info = requests.get(url, header.text, verify=False)
            page_info.raise_for_status()
            return json.loads(page_info.text)
        except Exception as e:
            print("get_page_info异常")
            print(e)

    def get_download_params(self, data):
        size = len(data)
        self.image_num = size
        for k in range(size):
            image_url = data[k]['urls']['full']
            self.image_urls.append(image_url)
            image_id = data[k]['id']
            self.image_ids.append(image_id)

    def get_image(self,j):
        try:
            image = requests.get(self.image_urls[j], verify=False)
            image.raise_for_status()
            return image.content
        except Exception as e:
            print("get_image异常")
            print(e)

    def writer(self, path, name, data):
        with open(path+name+'.jpg', 'wb') as f:
            f.write(data)
            f.close()


def start_spider(i):
    server = "https://unsplash.com/"
    save_path = "D:\pythonDownload\images\\"
    url = server + 'napi/collections/1065976/photos?page=' + str(i) + '&per_page=10&order_by=latest'
    down = DownLoader()
    info = down.get_page_info(server, url)
    down.get_download_params(info)
    for j in range(down.image_num):
        image = down.get_image(j)
        down.writer(save_path, down.image_ids[j], image)
        print('第' + str(i) + '页第' + str(j + 1) + '图片下载成功！')


if __name__ == '__main__':
    pool = Pool(4)
    pool.map(start_spider, [x for x in range(5, 10)])
    pool.close()
    pool.join()
    print("所有下载完成！")