import urllib
import itertools
import requests
import datetime
from bs4 import BeautifulSoup

import crawler_settings # crawlerの設定ファイル

HOME_URL = crawler_settings.HOME_URL
CALENDER_URL = crawler_settings.CALENDER_URL
MIN_DATE  = crawler_settings.MIN_DATE
MAX_DATE = crawler_settings.MAX_DATE

race_num = 0 # 総レース数count

# 1日のレース一覧ページを渡すと12R全てリンクを取得してくる
def race_list_day(race_program_url): #
    global race_num
    race_list = []
    msg =""
    race_day = datetime.date(year=1000, month=1, day=1)
    soup = BeautifulSoup(requests.get(race_program_url).content, 'html.parser')
    table = soup.find_all('table')
    for tab in table:
        table_class = tab.get('class')
        if table_class[0] == 'tb01c': # レースtable取得
            rows = tab.find_all('tr')
            for row in rows:
                for cell in row.findAll(['td', 'th']):
                    for a in cell.find_all('a'):
                        if 'race_info' in a.get('href'): # href=''リンク内に[race_info]があるURLのみ取得 レースの出走表
                            race_day = give_date(a.get('href')) # レース日取得
                            race_list.append(HOME_URL + a.get('href'))
    if race_day.year in [1000]: # リンクが取得できなかった場合
        msg = 'Could not get the link.'
    else:
        msg = 'Link acquisition completed.'
    race_num += len(race_list)
    print('|{} | Race：{:2}  {}'.format(race_day, len(race_list), msg))
    return race_list


# 半期のレースページを渡すと全ての日程のレースurlを取得してくる
def race_half_program_list(race_half_period_calendar_url): #
    race_program_list = []
    half_period = ""
    msg = ""
    msg2 = ""
    soup = BeautifulSoup(requests.get(race_half_period_calendar_url).content, 'html.parser')
    table = soup.find_all('table')
    for tab in table:
        table_class = tab.get('class')
        if table_class[0] == 'tb-calendar': # 月の開催日程table取得
            rows = tab.find_all('tr')
            for row in rows:
                for cell in row.findAll(['td', 'th']):
                    for a in cell.find_all('a'):
                        if 'program' in a.get('href'): # href=''リンク内に[program]があるURLのみ取得 当日レースのプログラム12R
                            race_day = give_date(a.get('href')) # レース日取得
                            if MIN_DATE <= race_day:                 # MIN_DATE以降のレース
                                if race_day <= MAX_DATE:            # MAX_DATE以前のレースをリストに入れる
                                    race_program_list.append(HOME_URL + a.get('href'))
                                else:
                                    msg = "\n取得最大指定日：{}までのリンクを取得しました。".format(MAX_DATE)
                            else:
                                msg2 = "\n取得開始指定日：{}からのリンクを取得しました。".format(MIN_DATE)
    if race_day.month in (4, 5, 6, 7, 8, 9):
        half_period = "前期(4～9月)"
    elif race_day.month in (1, 2, 3, 10, 11, 12):
        half_period = "後期(10～3月)"
    if race_day.month in (1, 2, 3):
        race_day = datetime.date(year=int(race_day.year)-1, month=int(race_day.month), day=int(race_day.day))
    print("{}年レース年間開催日程 {}から{}日分のリンクを取得しました。{}{}\n".format( race_day.year, half_period, str(len(race_program_list)), msg2, msg))
    return race_program_list


# urlからレース日を取得
def give_date(race_program_url):
    day = ""
    if 'program' in race_program_url:
        day = datetime.date(year=int(race_program_url[9:13]), month=int(race_program_url[13:15]), day=int(race_program_url[15:17]))
    elif 'race_info' in race_program_url:
        day = datetime.date(year=int(race_program_url[11:15]), month=int(race_program_url[15:17]), day=int(race_program_url[17:19]))
    return day


# [in]年間開催日程url　　[out] 全レースurl
def half_horse_race_list(race_list_helf_period):
    race_day_list = []
    race_program_url_list = race_half_program_list(race_list_helf_period) # 年間開催ページ(半期)を渡す
    for i in  range(len(race_program_url_list)): # 一日の出走表ページを渡す
        race_day_list.append(race_list_day(race_program_url_list[i]))         # [[url,url,url][url,url,url]...] 2次元配列
    print('現在合計{}レースのリンクを取得しました。'.format(race_num))
    print('----------------------------------------------------------------------------')
    return list(itertools.chain.from_iterable(race_day_list))                        # 2次元リストを1次元リストに平坦化


# 指定の日によって対応した半期のurlをリストに入れる
def half_year_calc():
    calendar_list = []
    calendar_msg = []
    year_interval = int(MAX_DATE.year) - int(MIN_DATE.year) + 1 # 何年分あるのか計算
    year = int(MIN_DATE.year)
    if MIN_DATE.month in (1, 2, 3) and year_interval != 1:
        year_interval += 1
        year -= 1
        if MAX_DATE.month in (1, 2, 3):
            year_interval -= 1
    elif  MIN_DATE.month in (1, 2, 3) and year_interval == 1 and MAX_DATE.month not in (1, 2, 3):
            year_interval += 1
            year -= 1
    elif  MIN_DATE.month in (1, 2, 3) and year_interval == 1 and MAX_DATE.month in (1, 2, 3):
            year -= 1
    for i in range(year_interval): # 年数分だけloop
        # 前期判定
        if i == 0:
            month = month_calc(MIN_DATE.month)
        else:
            month = '04'
        calendar_list.append(CALENDER_URL + str(year) + month + '.do')
        calendar_msg.append(str(year) + month_half_calc(month))
        # 後期表示判定
        max_month = month_calc(MAX_DATE.month)
        if i == 0 and month == '04' and year_interval == 1 and max_month == '04':
            msg = '半期のみ取得。'
        elif i == 0 and month == '04':
            calendar_list.append(CALENDER_URL + str(year) + '10' + '.do')
            calendar_msg.append(str(year) + month_half_calc('10'))
        elif i != 0 and  i != (year_interval - 1):
            calendar_list.append(CALENDER_URL + str(year) + '10' + '.do')
            calendar_msg.append(str(year) + month_half_calc('10'))
        elif i != 0 and month != max_month:
            calendar_list.append(CALENDER_URL + str(year) + max_month + '.do')
            calendar_msg.append(str(year) + month_half_calc(max_month))
        year += 1
    print('----------------------------------------------------------------------------')
    print('--- データの取得期間 ---')
    print('----------------------------------------------------------------------------')
    print('※前期 4月～9月, 後期 10月～3月')
    [print(cld_msg) for cld_msg in calendar_msg]
    print('----------------------------------------------------------------------------')
    return calendar_list

# 上半期か下半期か判定
def month_calc(month):
    if month in (4, 5, 6, 7, 8, 9):
        result_month = '04'
    elif month in (1, 2, 3, 10, 11, 12):
        result_month = '10'
    return result_month

def month_half_calc(month):
    if month == '04':
        half = '年：前期'
    if month == '10':
        half = '年：後期'
    return half


def horse_race_list():
    race_day_list = []
    calendar_list = half_year_calc()
    print('--- 半期毎にリンク取得 ---')
    print('----------------------------------------------------------------------------')
    for i in  range(len(calendar_list)):
        race_day_list.append(half_horse_race_list(calendar_list[i]))
    return list(itertools.chain.from_iterable(race_day_list)) # # 2次元リストを1次元リストに平坦化


def main():
    horse_race_list()
    #half_year_calc()


if __name__ == '__main__':
    main()
