import requests
from bs4 import BeautifulSoup


class DownLoader(object):
    def __init__(self):
        self.server = 'https://www.biquke.com/bq/67/67199/'
        self.url = 'https://www.biquke.com/bq/67/67199/'
        self.titles = []  #章节名
        self.urls = []    #章节地址
        self.num = 0      #章节数

    def get_chapter_info(self):
        rep = requests.get(self.url)
        rep.encoding ='utf-8'
        div_bf = BeautifulSoup(rep.text, 'lxml')
        div = div_bf.find_all('div', id='list')
        a_bf = BeautifulSoup(str(div[0]), 'lxml')
        a = a_bf.find_all('a')
        self.num = len(a)
        for each in a:
            print("----------each.text-----------")
            print(each.text)
            self.titles.append(each.text)
            self.urls.append(self.server+each.get('href'))

    def get_content(self, target):
        rep = requests.get(target)
        rep.encoding = 'utf-8'
        bf = BeautifulSoup(rep.text, 'lxml')
        div = bf.find_all('div', id='content')
        text = div[0].text.replace('\xa0'*4, '\n\n')
        return text

    def writer(self, path,  title, text):
        with open(path, 'a', encoding='utf-8') as f:
            # f.write(title + '\n')
            f.writelines(text)
            f.write('\n\n')
            f.close()


if __name__ == '__main__':
    dl = DownLoader()
    dl.get_chapter_info()
    print("开始下载...")
    for i in range(dl.num):
        content = dl.get_content(dl.urls[i])
        dl.writer('D:\pythonDownload\都市超级修仙人\\'+dl.titles[i]+'.txt', dl.titles[i], content)
        print(("  已下载:%.3f%%" % float(i / dl.num) + '\r'))
    print('下载完成!')
