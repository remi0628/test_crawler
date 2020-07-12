import re
import datetime
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs4
from urllib.request import urlopen, urljoin, urlparse

HOME_URL = 'https://www.nankankeiba.com'
#### https://www.nankankeiba.com/race_info/
URL = 'https://www.nankankeiba.com/race_info/2020071020060501.do'
BLANK_URL = 'https://www.nankankeiba.com/uma_info/2017100322.do'


def main():
    race_top, condition, race_len, race_date = result_data(URL) # レース当日データ取得
    print('#レース当日データ#\n', '日付：{}, レース距離：{}, 土の状態：{}, 1位馬番：{}'.format(race_date, race_len, condition, race_date))
    blank_link_list = horse_page_link(URL)
    for i in range(len(blank_link_list)):
        print(blank_link_list[i])
    soup = url_to_soup(BLANK_URL)
    print(horse_data(BLANK_URL))


def url_to_soup(url): # レース情報ページ取得
    req = requests.get(url)
    return bs4(req.content, 'html.parser') # 'lmxl'より処理が速い

def horse_page_link(url): # 各馬の過去情報URLリスト取得
    soup = url_to_soup(url)
    link_list = [HOME_URL + x.get('href') for x in soup.find_all('a', class_='tx-mid tx-low') ] # サイト内リンクから過去情報リンクのみ取得
    return link_list

# lamda
tag_to_text = lambda x: x.split('\n')
split_tr = lambda x: str(x).split('</tr>')

def get_previous_race_row(soup): # 競走馬詳細データから出走履歴取得
    race_table = soup.find_all('table', class_='tb01 w100pr bg-over stripe al-center')[2] # 競走馬詳細データサイト内には表が3つ　その内3つめの出走履歴を取得
    return [tag_to_text(x) for x in split_tr(race_table)]

def horse_data(url): # 出走履歴からデータ作成
    soup = url_to_soup(url)
    blank_race_data = get_previous_race_row(soup) # 過去のレースデータ
    print('出走履歴1番目の日付：', re.split('[<>]' ,blank_race_data[1:2][0][2])[2])
    print(len(blank_race_data))
    #blank_race_day_calc(blank_race_data)
    #print(re.split('[<>]' ,blank_race_data))
    df =  pd.DataFrame(blank_race_data)[1:][[2,3,10,11,13,14,15,19,23]].dropna().rename(columns={
        2:'date', 3:'place', 10:'len', 11:'wether', 13:'popularity', 14:'rank', 15:'time',19:'weight',23:'money'})
    return df

def blank_race_day_calc(blank_race_data): # 出走履歴何番目を取得するかレース当日と日付計算判定
    data_len = blank_race_data[1:] # len(data_len)-1 : 出走履歴数
    for i in range((len(data_len)-1)):
        day = re.split('[<>]' ,data_len[i][2])[2].split('/')
        year = '20' + day[0]
        race_day = datetime.date(year=int(year), month=int(day[1]), day=int(day[2])) # datetime.datetimeオブジェクト y-m-d
        print(race_day)


# 当日データ取得
def result_data(url): # レース結果取得 return[1着馬, 土の状態, レースの長さ, レース日]
    soup = url_to_soup(url)
    condition = soup.find(id="race-data02").get_text().replace('\n','').split('　')[2][0:1] # 土の状態
    race_len = int(soup.find(id="race-data01-a").get_text().replace('\n','').split('　')[3].replace(',','')[1:5]) # レースの長さ
    race_top = soup.find('td', class_='bg-3 al-center').get_text() # 1位
    race_date = race_day(soup) # レース日付
    return race_top, condition, race_len, race_date

def race_day(soup): # レース日 datetimeオブジェクトに変換 return datetime.date[y-m-d]
    today = soup.find('span', class_='tx-small').text.strip()
    today = re.split('[年月日]', today)
    del today[-1]
    race_day = datetime.date(year=int(today[0]), month=int(today[1]), day=int(today[2]))
    return race_day


if __name__ == '__main__':
    main()
