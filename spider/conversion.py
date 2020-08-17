import os


def ts_walker(path):
    ts_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            ts_list.append(os.path.join(root, file))
    ts_list = sorted(ts_list, key=lambda fn: int(fn.lstrip(root).rstrip('.ts')))
    return ts_list


def merge_ts(path, name, ts_list):
    file = path + name + '.ts'
    if(os.path.isfile(file)):
       os.remove(file)
    with open(file, 'ab') as fw:
        for ts in ts_list:
            with open(ts, 'rb') as fr:
                content = fr.read()
                fw.write(content)


def ts_to_mp4(ts_path):
    str = 'D:\\ffmpeg-4.2-win64-static\\bin\\ffmpeg -i ' + ts_path +' '+ts_path.replace('.ts', '.mp4')
    print(str)
    os.system(str)


if __name__ == '__main__':
    path = "D:\pythonDownload\\video\\"
    ts_list = ts_walker(path)
    print(ts_list)
    name = "天行九歌-第80集"
    merge_ts(path, name, ts_list)
    ts_to_mp4(path+name+'.ts')
