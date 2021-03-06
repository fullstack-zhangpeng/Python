#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author : Jiaqiang


import requests
import json
import os


from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, APIC, TPE1, TIT2, TALB, error

# 歌曲信息编辑
class Meta(object):
    def __init__(self):
        super().__init__()


    def read_image(self,url):
        '''
        读取图片url为bytes
        :param url:
        :return:
        '''
        response = requests.get(url)
        data = bytes(response.content)
        return data

    def song_meta(self, path, songInfo):
        '''
        编辑歌曲信息
        :param path:
        :param songInfo:
        :return:
        '''
        try:
            audio = MP3(path, ID3=ID3)
        except HeaderNotFoundError:
            print('Can\'t sync to MPEG frame, not an validate MP3 file!')
            return

        if audio.tags is None:
            print('No ID3 tag, trying to add one!')
            try:
                audio.add_tags()
                audio.save()
            except error as e:
                print('Error occur when add tags:', str(e))
                return

                # Modify ID3 tags
        id3 = ID3(path)
        # Remove old 'APIC' frame
        # Because two 'APIC' may exist together with the different description
        # For more information visit: http://mutagen.readthedocs.io/en/latest/user/id3.html
        if id3.getall('APIC'):
            id3.delall('APIC')
        # add album cover
        id3.add(
            APIC(
                encoding=0,  # 3 is for UTF8, but here we use 0 (LATIN1) for 163, orz~~~
                mime='image/jpeg',  # image/jpeg or image/png
                type=3,  # 3 is for the cover(front) image
                data=self.read_image(songInfo['albumArt'])
            )
        )
        # add artist name
        id3.add(
            TPE1(
                encoding=3,
                text=songInfo['songer']
            )
        )
        # add song name
        id3.add(
            TIT2(
                encoding=3,
                text=songInfo['songName']
            )
        )
        # add album name
        id3.add(
            TALB(
                encoding=3,
                text=songInfo['albumName']
            )
        )
        id3.save(v2_version=3)


# 获取歌曲信息
def get_song(songId,album_id):
    url = 'http://www.kugou.com/yy/index.php?r=play/getdata&hash=%s&album_id=%s' % (songId,album_id)

    session = requests.session();
    result = session.get(url)
    response = json.loads(result.content.decode())

    # 专辑封面
    albumArt = response['data']['img']
    # 专辑名称
    albumName = response['data']['album_name']
    # 歌曲名称
    songName = response['data']['song_name']
    # 歌手
    songer = response['data']['author_name']
    # 歌曲Id
    songId = response['data']['play_url']

    songInfo = {
        'songName': songName,
        'songer': songer,
        'songId': songId,
        'albumName': albumName,
        'albumArt': albumArt
    }

    return songInfo


from bs4 import BeautifulSoup

# 获取列表
def get_list(url):
    session = requests.session();
    result = session.get(url)
    response = result.content.decode()

    # 获取script
    soup = BeautifulSoup(response,'html5lib')
    curl = soup.find_all('script')
    script = str(curl[0])
    # 获取songdata
    start = script.index('songsdata = ') + len('songsdata = ')
    end = script.index('</script>') - 2
    songdata = script[start:end]

    data = json.loads(songdata)


    list = []
    # 获取list
    for item in data:
        hash = item['hash']
        album_id = item['album_id']
        info = get_song(hash,album_id)
        list.append(info)

    return list


# 获取专辑
def get_album_list(url):
    session = requests.session();
    result = session.get(url)
    response = result.content.decode()

    # 获取歌曲数据
    response = str(response)
    start_song = response.index('//歌曲数据') + len('//歌曲数据')
    end_song = response.index('//分享的歌曲ID')
    script = response[start_song:end_song]

    # 获取songdata
    start = script.index('var data=') + len('var data=')
    end = script.index('];') + 1
    songdata = script[start:end]
    data = json.loads(songdata)

    list = []
    # 获取list
    for item in data:
        hash = item['hash']
        album_id = item['album_id']
        info = get_song(hash, album_id)
        list.append(info)

    return list



def get_data(page,o_parm):
    parm = [
        'listid=%s' % str(o_parm['listid']),
        'type=%s' % str(o_parm['type']),
        'uid=%s' % str(o_parm['uid']),
        'sign=%s' % str(o_parm['sign']),
        '_t=%s' % str(o_parm['_t']),
        'token=%s' % str(o_parm['token']),
        'pagesize=30',
        'page=%s' % str(page)
    ]
    url = "http://m.kugou.com/zlist/list?" + "&".join(parm)

    session = requests.session();
    result = session.get(url)
    response = result.content.decode()

    result = json.loads(response)
    return result



# 获取歌单
def get_playlist(url):

    wd = url.split('?')[-1].split('&')

    o_parm = {}
    for p in wd:
        o = p.split('=')
        o_parm[str(o[0])] = str(o[-1])


    page = 1
    result = get_data(page,o_parm)

    list = result['list']['info']

    # 计算页码
    totalPage = result['list']['count'] - page * 30

    while (totalPage > 0):
        page = page + 1
        result = get_data(page, o_parm)
        list.extend(result['list']['info'])
        totalPage = result['list']['count'] - page * 30



    print(len(list))

    playlist = []
    # 获取list
    for item in list:
        hash = item['hash']
        album_id = item['album_id']
        info = get_song(hash, album_id)
        playlist.append(info)

    return playlist



def downloader(items):
    # 创建下载文件夹
    if not os.path.exists("music"):  # 判断目录是否存在
        os.makedirs("music")  # 创建多级目录

    for item in items:
        songUrl = item['songId']
        if songUrl == None or songUrl == '':
            print("\033[1;31;0m【" + item['songName'] + "】无版权" + "，无法下载\033[0m")
        else:
            r = requests.get(songUrl, stream=True)
            file_name = "music/" + item['songName'] + ".mp3"
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)

            print("\033[1;32;0m【" + item['songName'] + "】 下载完成\033[0m")
            # 编辑歌曲信息
            meta = Meta()
            meta.song_meta(file_name,item)

# 获取专辑
# songs = get_album_list('http://www.kugou.com/yy/album/single/979856.html')

# 获取单曲
# songs = get_song('238B786A3F93C42E3D212953E1CE96C3','8149034')

# 获取歌单
songs = get_playlist('http://m.kugou.com/share/zlist.html?listid=2&type=0&uid=1054974589&token=ba3b430e97e91018c9744115a9de938ea45c0f6b7153cfd023bce0efc6899f0f&sign=13f8b955d242f9199436a9fdf861423d&_t=1529547092&chl=wechat&kugou_code=2987856&u=1054974589&h1=01f59fe8b7b2a03f5d38628c196872ec97cec0e0&from=singlemessage&isappinstalled=0')


print('共获取到【%s】首歌曲' % len(songs))
downloader(songs)

