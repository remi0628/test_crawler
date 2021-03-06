import glob
import datetime
import time
import datetime
import numpy as np
import pandas as pd
import os
import re
import traceback
from concurrent import futures
import crawler_settings


def read_csv(race, date):
    print(os.path.basename(race))
    horses = glob.glob(race + "/*.csv")
    # horses = [i for i in horses if os.path.basename(i) != "refund.csv"]
    horses = sorted(horses[0:-1], key=lambda x: int(re.findall("\d+", os.path.basename(x))[0]))

    moneys = pd.read_csv(race + "/refund.csv", encoding="cp932").loc[0]
    race_horse = []
    rankings = np.zeros(16)
    for i in range(16):
        if len(horses) > i:

            birth = [int(x) for x in re.findall("\d+", horses[i])[-3:]]
            df = pd.read_csv(horses[i], encoding="cp932")
            df, ranking = make_race_data(df, date, birth, 10)

            if ranking != 0:  # 欠場等でないなら
                if rankings[ranking - 1] == 0:  # 同着の場合来た順に次に、本来払い戻し等どう処理されるか調べる必要性あり
                    rankings[ranking - 1] = int(re.findall("\d+", os.path.basename(horses[i]))[0])
                else:
                    rankings[ranking] = int(re.findall("\d+", os.path.basename(horses[i]))[0])

            race_horse.append(df[:10].values)
        else:
            race_horse.append(np.zeros((10, 20)))

    return race_horse, rankings, moneys


def make_npy():
    races = glob.glob("data/race/*")

    future_list = []
    with futures.ProcessPoolExecutor(max_workers=None) as executor:
        for i in range(len(races)):
            year, month, day, roundNumber, length, roadState, top = os.path.basename(races[i]).split("-")
            #  下級レースの除外
            if int(roundNumber) <= crawler_settings.EXCLUDE_LOWER_RACE:
                continue
            future = executor.submit(fn=read_csv, race=races[i], date=[year, month, day])
            future_list.append(future)
        _ = futures.as_completed(fs=future_list)

    X = [future.result()[0] for future in future_list]
    Y = [future.result()[1] for future in future_list]
    P = [future.result()[2] for future in future_list]

    X = np.array(X)
    Y = np.array(Y)
    P = np.array(P)
    X = X.astype("float")
    name = "2010-01-01-2020-04-01"
    np.save(f"data/X{name}.npy", X)
    np.save(f"data/Y{name}.npy", Y)
    np.save(f"data/P{name}.npy", P)


def inZeroOne(num):
    if num > 1:
        return 1
    elif num < 0:
        return 0
    else:
        return num


def make_race_data(df, date, birth, l=10):
    df_ = pd.DataFrame(np.zeros((1, 20)), columns=["horse_cnt", "money", "result_rank", "len", "popularity", "weight",
                                                   "borden_weight", "sec", "diff_accident", "threeF", "birth_days",
                                                   "place_Urawa", "place_Funabashi",
                                                   "place_Ooi", "place_Kawasaki", "place_other", "soil_heavy",
                                                   "soil_s_heavy", "soil_good", "soil_bad"])
    weightLog = 0
    dropList = []
    check = False
    ranking = 0
    for idx, row in df.iterrows():
        check = True
        if str(row['着順']) == "nan" or str(row['人気']) == "nan" or str(row['タイム']) == "nan":
            dropList.append(idx)
            df_.loc[idx] = 0
            continue

        try:
            # 馬場状態
            df_.loc[idx, 'soil_heavy'] = 1 if row['天候馬場'][-2:] == '/重' else 0
            df_.loc[idx, 'soil_s_heavy'] = 1 if row['天候馬場'][-2:] == '稍重' else 0
            df_.loc[idx, 'soil_good'] = 1 if row['天候馬場'][-2:] == '/良' else 0
            df_.loc[idx, 'soil_bad'] = 1 if row['天候馬場'][-2:] == '不良' else 0

            df_.loc[idx, 'money'] = inZeroOne(float(str(row['獲得賞金（円）']).replace(',', '')) / 110000000)
            df_.loc[idx, 'horse_cnt'] = float(str(row['着順']).split('/')[1]) / 16
            df_.loc[idx, 'result_rank'] = float(row['着順'].split('/')[0]) / 16
            df_.loc[idx, 'len'] = inZeroOne((float(re.findall("\d+", str(row['距離']))[0]) - 800) / 3000)
            df_.loc[idx, 'popularity'] = float(row['人気']) / 16
            df_.loc[idx, 'borden_weight'] = inZeroOne((float(row['負担重量']) - 50) / 10)

            if row['体重'] == "計不":
                df_.loc[idx, 'weight'] = weightLog
                """
                if weightLog == 0:
                    dropList.append(idx)
                """
            else:
                df_.loc[idx, 'weight'] = inZeroOne((float(row['体重']) - 300) / 300)
                weightLog = inZeroOne((float(row['体重']) - 300) / 300)

            # 　競馬場
            df_.loc[idx, 'place_Urawa'] = 1 if row['競馬場'][:2] == "浦和" else 0
            df_.loc[idx, 'place_Funabashi'] = 1 if row['競馬場'][:2] == "船橋" else 0
            df_.loc[idx, 'place_Ooi'] = 1 if row['競馬場'][:2] == "大井" else 0
            df_.loc[idx, 'place_Kawasaki'] = 1 if row['競馬場'][:2] == "川崎" else 0
            if sum([df_.loc[idx, 'place_Urawa'], df_.loc[idx, 'place_Funabashi'], df_.loc[idx, 'place_Ooi'],
                    df_.loc[idx, 'place_Kawasaki']]) == 0:
                df_.loc[idx, 'place_other'] = 1
            else:
                df_.loc[idx, 'place_other'] = 0

            # タイム(秒)
            try:
                time = datetime.datetime.strptime(str(row['タイム']), '%M:%S.%f')
                df_.loc[idx, 'sec'] = inZeroOne(
                    (float(time.minute * 60 + time.second + time.microsecond / 1000000) - 40) / 250)
            except:
                time = datetime.datetime.strptime(str(row['タイム']), '%S.%f')
                df_.loc[idx, 'sec'] = inZeroOne((float(time.second + time.microsecond / 1000000) - 40) / 250)

            try:
                df_.loc[idx, 'threeF'] = inZeroOne((float(row['上3F']) - 30) / 30)
            except ValueError:
                df_.loc[idx, 'threeF'] = 0

            try:
                df_.loc[idx, 'diff_accident'] = inZeroOne(float(row['差/事故']) / 10)
            except ValueError:
                df_.loc[idx, 'diff_accident'] = 0

            # レース日
            raceDay = [int(x) for x in row['年月日'].split("/")]
            date = [int(x) for x in date]
            if raceDay[0] < 50:
                raceDay[0] += 2000
            elif raceDay[0] < 1900:
                raceDay[0] += 1900

            birthDate = datetime.date(raceDay[0], raceDay[1], raceDay[2]) - datetime.date(birth[0], birth[1], birth[2])
            df_.loc[idx, 'birth_days'] = inZeroOne((birthDate.days - 700) / 1000)

            if raceDay == date:  # 当日の場合不明なもの
                ranking = int(row['着順'].split('/')[0])
                df_.loc[idx, 'money'] = 0
                df_.loc[idx, 'result_rank'] = 0
                df_.loc[idx, 'popularity'] = 0
                df_.loc[idx, 'sec'] = 0
                df_.loc[idx, 'weight'] = 0
                df_.loc[idx, 'diff_accident'] = 0
                df_.loc[idx, 'threeF'] = 0

        except:  # エラーなら全部0
            traceback.print_exc()
            dropList.append(idx)
            df_.loc[idx] = 0

    for i in dropList:
        df_.drop(i, axis=0, inplace=True)
    if not check:
        df_.drop(0, axis=0, inplace=True)

    while len(df_) < l:
        df_.loc[len(df_) + len(dropList)] = 0

    return df_, ranking


def main():
    now = time.time()
    make_npy()
    print("レースデータ前処理時間　：", time.time() - now)


if __name__ == '__main__':
    main()
