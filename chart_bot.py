# -*- coding: utf-8 -*- 

import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from mplfinance.original_flavor import candlestick_ohlc
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import datetime, re
from pymongo import MongoClient
import pymongo, ssl
import requests

token = os.environ["BOT_TOKEN"]
token_name_list : list = os.environ["TOKEN_NAME"].split(" ")
max_length : int = int(os.environ["MAX_LENGTH"])
chat_id_list : list = os.environ["CHAT_ID_LIST"].split(" ")
fig_scale : int = int(os.environ["FIG_SCALE"])
except_list : list = os.environ["EXCEPT_LIST"].split(" ")
ks_asset_name_list : list = os.environ["KS_ASSET_NAME_LIST"].split(" ")
ks_asset_url_list : list = os.environ["KS_ASSET_URL_LIST"].split(" ")

mongoDB_connect_info : dict = {
    "host" : os.environ["mongoDB_HOST"],
    "username" : os.environ["USER_ID"],
    "password" : os.environ["USER_PASSWORD"]
    }

price_db = None
time_list : list = []
ks_asset_url_dict : dict = {}
close_prices_dict : dict = {"klay":[]}
prices_candle_dict : dict = {"klay":[]}
candle_time_db_dict : dict = {"m" : None, "5":None, "15":None, "1":None, "4":None, "d":None}

for k in token_name_list:
    close_prices_dict[k] = []
    prices_candle_dict[k] = []

for i in range(len(ks_asset_name_list)):
    ks_asset_url_dict[ks_asset_name_list[i]] = ks_asset_url_list[i]

config_plot = dict( ## 키워드 인자
    color='#7CFC00', # 선 색깔
    linestyle='solid', # 선 스타일
    linewidth=3, # 선 두께 
    # marker='o', # 마커 모양
    # markersize=5 # 마커 사이즈
)

bbox = dict( ## 텍스트 박스 스타일 지정
    boxstyle='square', # 박스 모양
    facecolor='white', # 박스 배경색
)

def load_ks_json(url):
    result : dict = {}
    try:
        for key, value in ks_asset_url_dict.items():
            r = requests.get(value).json()
            result[key] = r[len(r)-1]
        return True, result
    except Exception as e:
        print(f"{datetime.datetime.now().strftime('%m/%d %H:%M')} : {e}")
        return False, {}

def draw_ratio_chart(ax, prices, data_time, ratio_list:list):
    ax.clear()
    c_val = prices[ratio_list[0]]
    c_val1 = prices[ratio_list[1]]

    data_number = min(len(data_time), len(c_val), len(c_val1))
    if data_number < max_length:
        result_data_time = data_time[-data_number:]
        result_c_val = c_val[-data_number:]
        result_c_val1 = c_val1[-data_number:]
    else:
        result_data_time = data_time[-max_length:]
        result_c_val = c_val[-max_length:]
        result_c_val1 = c_val1[-max_length:]
    
    x = np.arange(len(result_data_time))
    ohlc = result_c_val
    ohlc1 = result_c_val1
    dohlc = np.hstack((np.reshape(x, (-1, 1)), ohlc))
    dohlc1 = np.hstack((np.reshape(x, (-1, 1)), ohlc1))
    
    ratio_data_list : list = []

    for j in range(len(dohlc)):
        ratio_data_list.append(round(dohlc[j][4]/dohlc1[j][4],5))

    max_value = max(ratio_data_list)
    min_value = min(ratio_data_list)
    
    config_plot1 = dict( ## 키워드 인자
    color='#0000ff', # 선 색깔
    linestyle='solid', # 선 스타일
    linewidth=3, # 선 두께 
    # marker='o', # 마커 모양
    # markersize=5 # 마커 사이즈
    )

    ax.plot(ratio_data_list, **config_plot1)

    yticks = list(ax.get_yticks()) ## y축 눈금을 가져온다.
    xticks = list(ax.get_xticks()) ## x축 눈금을 가져온다.

    for y in yticks:
        ax.axhline(y,linestyle=(0,(5,2)),color='grey',alpha=0.5) ## 눈금선 생성

    ax.text(xticks[len(xticks)-2], yticks[len(yticks)-1],f'{ratio_data_list[len(ratio_data_list)-1]}',fontsize=20, ha='center', bbox=bbox) ## 선 그래프 텍스트
    ax.text(0, yticks[len(yticks)-1],f'H : {max_value}\nL : {min_value}',fontsize=18, ha='left', bbox=bbox) ## 선 그래프 텍스트

    for time_j in range(len(result_data_time)):
        if time_j % 6 != 0:
            result_data_time[time_j] = ""

    ax.spines['right'].set_visible(False) ## 오른쪽 축 숨김
    ax.spines['top'].set_visible(False) ## 위쪽 축 숨김
    ax.set_xticks(x)
    ax.set_xticklabels(result_data_time, rotation=45)
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax.set_title(f"{ratio_list[0]}/{ratio_list[1]} ratio",fontsize=20)

    return ax

def total_chart(time, prices, user_name, list_coins, title, ratio_chart : bool = False, ratio_list : list = None):
    checker = False
    if "kscoinbase" in list_coins:
        checker, ks_price_data_dict = load_ks_json(ks_asset_url_dict)        

    result_str : str = ""
    if ratio_chart and ratio_list is not None:
        n_rows = len(list_coins) + len(ratio_list)
    else:
        n_rows = len(list_coins)
    fig, axes = plt.subplots(n_rows, 1, figsize=(4*fig_scale, n_rows*fig_scale), dpi=150)
    if n_rows != 1:
        axes = axes.flatten()
    else:
        axes = [axes]

    data_time = time
    
    for i, ax in enumerate(axes):
        ax.clear()
        if ratio_chart and i >= len(list_coins):
            ax = draw_ratio_chart(axes[i], prices, data_time, ratio_list[i-len(list_coins)])
            plt.tight_layout()
            continue
        
        cid = list_coins[i]
        c_val = prices[cid]

        tmp_list = [candle_price for candle_prices in c_val for candle_price in candle_prices]
        max_value = max(tmp_list)
        min_value = min(tmp_list)

        data_number = min(len(data_time), len(c_val))
        if data_number < max_length:
            result_data_time = data_time[-data_number:]
            result_c_val = c_val[-data_number:]
        else:
            result_data_time = data_time[-max_length:]
            result_c_val = c_val[-max_length:]
        
        x = np.arange(len(result_data_time))
        ohlc = result_c_val
        dohlc = np.hstack((np.reshape(x, (-1, 1)), ohlc))

        ax.plot(close_prices_dict[cid.lower()], **config_plot)
        ax2 = ax.twinx()     

        candlestick_ohlc(ax2, dohlc, width=0.5, colorup='r', colordown='b')

        yticks = list(ax2.get_yticks()) ## y축 눈금을 가져온다.
        xticks = list(ax2.get_xticks()) ## x축 눈금을 가져온다.
        coint_premium : str = ""

        if checker and cid in ks_asset_url_dict.keys():
            oracle_price = round(float(ks_price_data_dict[cid]["oraclePrice"]), 3)
            cal_premium = round((float(ohlc[len(ohlc)-1][3])/oracle_price-1)*100, 3)
            if cal_premium >= 0:
                coint_premium = f"\n- oracle : ${oracle_price} (+{cal_premium}%)"
            else:
                coint_premium = f"\n- oracle : ${oracle_price} ({cal_premium}%)"

        result_str += f"{cid.upper()} : ${ohlc[len(ohlc)-1][3]} {coint_premium}\n"

        for y in yticks:
            ax2.axhline(y,linestyle=(0,(5,2)),color='grey',alpha=0.5) ## 눈금선 생성

        ax2.text(xticks[len(xticks)-2], yticks[len(yticks)-1],f'{dohlc[len(dohlc)-1][4]}',fontsize=20, ha='center', bbox=bbox) ## 선 그래프 텍스트
        ax2.text(0, yticks[len(yticks)-1],f'H : {max_value}\nL : {min_value}',fontsize=18, ha='left', bbox=bbox) ## 선 그래프 텍스트
        
        for time_i in range(len(result_data_time)):
            if time_i % 6 != 0:
                result_data_time[time_i] = ""

        ax2.spines['right'].set_visible(False) ## 오른쪽 축 숨김
        ax2.spines['top'].set_visible(False) ## 위쪽 축 숨김
        # ax2.set_xticks(x)
        # ax2.set_xticklabels(result_data_time, rotation=45)
        ax2.yaxis.set_label_position('left')
        ax2.yaxis.set_ticks_position('left')
        ax2.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        ax2.axes.xaxis.set_visible(False)
        ax2.axes.yaxis.set_visible(False)
        ax2.set_title(f'{cid.upper()}/USDT ({title})',fontsize=20)

        ax.spines['right'].set_visible(False) ## 오른쪽 축 숨김
        ax.spines['top'].set_visible(False) ## 위쪽 축 숨김
        ax.set_ylim(ax2.get_ylim())
        ax.set_xticks(x)
        ax.set_xticklabels(result_data_time, rotation=45)
        ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        plt.tight_layout()

    plt.savefig(f"result_{user_name}.png")
    fig.clf()
    plt.close()

    return result_str

def draw_chart(db, user_name, coin_name, title, ratio_chart : bool = False, ratio_list : list = None):
    global time_list
    global prices_candle_dict
    global close_prices_dict
    
    price_documents = list(db.find().sort([("_id",-1)]).limit(min(max_length, db.count_documents({}))))
    result_documents = list(reversed(price_documents))
    if len(result_documents) >= 2:
        for data in result_documents:
            time_list.append(data["Time"])
            for k in data.keys():
                if k != "_id" and k != "Time" and k in ['klay'] + token_name_list:
                    prices_candle_dict[k].append(data[k][0])
                    
                    close_prices_dict[k].append(data[k][0][3])
        # try:
        if "total" not in coin_name:
            list_coins = coin_name
        else:
            list_coins = ['klay'] + [c for c in token_name_list]
            for coin_name in except_list:
                list_coins.remove(coin_name)
        
        price_data_str = total_chart(time_list, prices_candle_dict, user_name, list_coins, title, ratio_chart, ratio_list)
        # except:
        #     return False, f"에러 발생..."
    else:
        return False, f"데이터 수집중..."
    
    time_list = []
    for k in prices_candle_dict.keys():
        prices_candle_dict[k] = []
        close_prices_dict[k] = []

    return True, price_data_str

def input_checker(input_msg, db_dict):
    user_name : str = ""
    result_db = None
    interval_time : str = ""
    input_msg_list : list = []
    
    user_name = input_msg.from_user["username"]
    input_msg_list = input_msg.text.split(" ")

    if len(input_msg_list) > 1:
        if input_msg_list[1] not in db_dict.keys():
            return False,  user_name, result_db, interval_time
        result_db = db_dict[input_msg_list[1]][0]
        interval_time = db_dict[input_msg_list[1]][1]
    else:
        result_db = db_dict["5"][0]
        interval_time = db_dict["5"][1]
    
    return True,  user_name, result_db, interval_time

def display_price_ratio(msg : str, a_token_name, b_token_name):
    result : str = ""
    cal_ratio = msg.split("\n")
    price_ratio : float = 0.0
    price_dict : dict = {a_token_name : None, b_token_name: None}
    for price_value in cal_ratio:
        if price_value.find(f"{a_token_name.upper()} : $") != -1 and price_value[0] == a_token_name.upper()[0]:
            price_dict[a_token_name] = price_value[price_value.find("$")+1:]
        if price_value.find(f"{b_token_name.upper()} : $") != -1 and price_value[0] == b_token_name.upper()[0]:
            price_dict[b_token_name] = price_value[price_value.find("$")+1:]
    try:
        price_ratio = round(float(price_dict[a_token_name])/float(price_dict[b_token_name]), 5)
        result = f"{msg}\n1 {a_token_name} ≈ {price_ratio} {b_token_name}"
    except ZeroDivisionError:
        price_ratio = 0.0
        result = f"{msg}\n{b_token_name}의 가격은 \"$0.00\"입니다."
   
    return result

def show_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["total"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_klay_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "aklay", "ksp", "korc", "kbelt"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "Klay", "aKlay")
    result_msg = display_price_ratio(result_msg, "ksp", "Klay")
    result_msg = display_price_ratio(result_msg, "Klay", "kOrc")
    result_msg = display_price_ratio(result_msg, "Klay", "kBelt")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_aklay_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "aklay"], interval_str, ratio_chart=True, ratio_list=[["klay", "aklay"]])

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "aKlay")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_ksp_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "ksp"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "Klay", "Ksp")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_skai_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["skai", "vkai", "akai", "kai"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "sKai", "vKai")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_kfi_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "kfi", "ksta"], interval_str, ratio_chart=True, ratio_list=[["klay", "kfi"], ["kfi", "ksta"]])

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Kfi")
    result_msg = display_price_ratio(result_msg, "Klay", "Ksta")
    result_msg = display_price_ratio(result_msg, "Kfi", "Ksta")
                                                               

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_house_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""
                
    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "aklay", "house", "wood", "kokoa", "ksd"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "House")
    result_msg = display_price_ratio(result_msg, "aKlay", "House")
    result_msg = display_price_ratio(result_msg, "Wood", "House")
    result_msg = display_price_ratio(result_msg, "Klay", "Kokoa")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
            
    return

def show_orca_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["orca"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_ks_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""
                
    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return
    
    ks_list = ks_asset_name_list + ["kai"]

    data_checker, result_msg = draw_chart(data_db, user_name, ks_list, interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    for ks_name in ks_asset_name_list:
        result_msg = display_price_ratio(result_msg, ks_name, "kai")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
            
    return

def show_bw_chart(update, ctx):
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""
                
    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "sbwpm", "clam"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
            
    return

def show_wm_chart(update, ctx):
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""
                
    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "wemix"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
            
    return

def show_jun_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["juns", "junc", "jun"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Juns", "Jun")
    result_msg = display_price_ratio(result_msg, "Junc", "Jun")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_mix_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "mix"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Mix")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_don_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "kdon"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "kdon")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["wiken", "mnr", "isr", "redi"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco1_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["bbc", "krush", "kicx", "kqbt"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco2_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["pib", "hibs", "khandy", "per"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco3_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["pics", "bora", "kcyclub"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco4_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["bype", "kmts", "kpax"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_jabco5_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["kpace", "ins", "com"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_biot_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["kbiot", "kdotr"], interval_str, ratio_chart=True, ratio_list=[["kbiot", "kdotr"]])

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "kbiot", "kdotr")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_bus_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "bus"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Bus")
    
    result_msg += f"\n※ 주의) 비율은 정확하지 않을 수 있습니다."
    
    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_meta_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "meta", "mudol"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Meta")
    result_msg = display_price_ratio(result_msg, "Klay", "Mudol")
        
    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_krno_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return
    
    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "krno", "kredit", "hook"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "Klay", "Krno")
    result_msg = display_price_ratio(result_msg, "Klay", "Hook")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_cla_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "cla"], interval_str, ratio_chart=True, ratio_list=[["klay", "cla"]])

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "klay", "cla")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_mon_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "mon"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Mon")
        
    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_punk_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "punk"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return

    result_msg = display_price_ratio(result_msg, "Klay", "Punk")
        
    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_kleva_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return
    
    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "kleva"], interval_str)

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "Klay", "Kleva")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def show_mkc_chart(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"사용할 수 없습니다.\n엔피스에 오셔서 확인하세요!\n[엔피스 바로가기](https://t.me/Npiece)", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    db_checker : bool = True
    data_checker : bool = True
    result_msg : str = ""
    interval_str : str = ""

    db_checker, user_name, data_db, interval_str = input_checker(update.message, candle_time_db_dict)

    if not db_checker:
        return

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "mkc"], interval_str, ratio_chart=True, ratio_list=[["klay", "mkc"]])

    if not data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        return
    
    result_msg = display_price_ratio(result_msg, "klay", "mkc")

    ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
    ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))

    return

def help(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text=("실시간 차트확인\n"
"http://tothem.pro/\n\n"
"[명령어] - /c, /chart 다가능"
"/c  : klay, aklay, skai, kfi, house, orca\n"
"      - 로딩시간 좀 걸림\n"
"/k : klay, aklay, ksp, korc, kbelt 차트\n"
"/a : klay, aklay 차트\n"
"/p : klay, ksp 차트\n"
"/s : skai, vkai, kai 차트\n"
"/f : klay, kfi 차트\n"
"/h : klay, aklay, house, wood, kokoa, ksd 차트\n"
"/o : orca 차트\n"
"/ks : 카이프로토콜 합성자산\n"
"      - 로딩시간 좀 걸림\n"
"/j : juns, jun 차트\n"
"/b : klay, sbwpm, clam 차트\n"
"/w : klay, wemix 차트\n"
"/m : klay, mix 차트\n"
"/d : klay, don 차트\n"
"/me : klay, meta, mudol 차트\n"
"/33 : klay, krno, kredit, hook 차트\n"
"/mo : klay, mon 차트\n"
"/kl : klay, kleva 차트\n"
"/jc : wiken, mnr, isr, redi 차트\n"
"/jc1 : bbc, krush, kicx, kqbt  차트\n"
"/jc2 : pib, hibs, khandy, per  차트\n"
"/jc3 : pics, bora, kcyclub 차트\n"
"/jc4 : bype, kmts, kpax 차트\n"
"/jc5 : kpace, ins 차트\n"
"/bi : kbiot, kdotr 차트\n"
"/cl : klay, cla 차트\n"
"/pu : klay, punk 차트\n"
"/mkc : klay, mkc 차트\n"
"/bus : klay, bus 차트\n\n"
"!! 모든 명령어뒤에 한칸띄고 숫자 m, 15, 1, 4, d를 붙이면(ex:/c 15)각각 1분봉, 15분봉, 1시간봉, 4시간봉 일봉 확인가능(기본값 5분봉)\n"
"!! 차트 데이터는 오차가 있을수 있으며 실시간으로 값이 반영되지 않을수 있습니다. 참고하시고 사용해주세요!\n\n"
"후원은 감사히 받습니다.\n"
"/꿀복\n"
"/spon, /sp\n"
"Tothemoon :\n"
"0x33d536f24523135D788AFeE67C8bd694c51D9283"))

def spon_link(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text="1클파이도 감사히 받습니다!\n받은 후원금은 서버 운영비 및 개발자 치킨 사먹는데 쓰입니다.\n")
    ctx.bot.send_message(chat_id=update.message.chat_id, text="To the Moon! 후원주소\nhttps://tothem.pro")
    ctx.bot.send_message(chat_id=update.message.chat_id, text="0x33d536f24523135D788AFeE67C8bd694c51D9283")
    
def get_message(update, ctx):
    if str(update.message.chat_id) not in chat_id_list:
        ctx.bot.send_message(chat_id=update.message.chat_id, text="사용할 수 없습니다.")
        return
    if update.message.text == "/라미":
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"귀염뽀짝 사랑둥이")
    if update.message.text == "/용노" or update.message.text == "/yongno":
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'yongno.jpg', 'rb'))
    if update.message.text == "/라모" :
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'ramo.jpg', 'rb'))
    if update.message.text == "/농사를짓자" or update.message.text == "/농짓":
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"나도 어디든지 있다, 알겠냐")
    if update.message.text == "/상우" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"고양이 구원자. 천사")
    if update.message.text == "/꿀복" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"나는 어디든지 있다, 알겠냐")
    if update.message.text == "/바코드" or update.message.text == "/밬호드" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"멋진 오빠. 꺄아아아아악!")
    if update.message.text == "/노모" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"라모를 좋아하는 사랑꾼. 사랑해")
    if update.message.text == "/준게이" or update.message.text == "/게이준" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"에클 성애자.")
    if update.message.text == "/마오" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"KSP 팔지 마라, 알겠냐")
    if update.message.text == "/세모" :
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'semo.jpg', 'rb'))
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"구독해라, 알겠냐\nhttps://www.youtube.com/channel/UCOfnPeZklEOJWll_ajVhglQ")
    if update.message.text == "/고구마" :
        ctx.bot.send_message(chat_id=update.message.chat_id, text=f"자!숙!고!구!마!")
    
def test(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text=f"{update.message.chat_id}")

def hello_ment(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text=("📢 투더문에 오신 사랑스러운 유저님들\n\n"
"투더문은 트레이딩뷰, 오피스 모드등 다양한 기능을 제공하고있습니다.\n\n"
"혹시 건의사항이나 문의사항 있으면 우리 투더문 대표 라모, CM이 언제나 들어드립니다!!\n\n"
"개인적으로 궁금한 질문은 라모, 라미 또는 엠버서더들에게 문의 해주시면 빠르게 처리해드립니다.\n\n"
"* 매달 에어드랍, 수다 이벤트 진행중이 오니 많이 애용해주세요!\n\n"
"다들 들어와주셔서 감사합니다!\n\n"
"유저들을 위한 투더문이 되겠습니다.\n\n"
"- 제공 시바, 라미\n\n"
"📌 투더문 홈페이지\n"
"https://tothem.pro\n\n"
"📌투더문 후원 NFT 오픈씨 링크\n"
"https://opensea.io/ToTheMOONPenguin\n\n"
"📌 투더문 구글 플레이 스토어 어플 링크\n"
"https://play.google.com/store/apps/details?id=com.mino.eazydefi"))
    
def main():
    global price_db
    global time_list
    global prices_candle_dict
    global candle_time_db_dict

    try:
        price_db = MongoClient(ssl=True, ssl_cert_reqs=ssl.CERT_NONE, **mongoDB_connect_info)
        price_db.admin.command("ismaster") # 연결 완료되었는지 체크
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\ndb 연결 완료. 아이디:{mongoDB_connect_info['username']}")
    except pymongo.errors.ServerSelectionTimeoutError:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\ndb 연결 실패! host 리스트를 확인할 것.")
    except pymongo.errors.OperationFailure:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\ndb 로그인 실패! username과 password를 확인할 것.")
    except:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\ndb 연결 실패! 오류 발생:")

    candle_time_db_dict = {"m":[price_db.coin.price_one, "1m"], "5":[price_db.coin.price_five, "5m"], "15":[price_db.coin.price_fifteen, "15m"], "1":[price_db.coin.price_hour, "1h"], "4":[price_db.coin.price_four_hour, "4h"], "d":[price_db.coin.price_day, "1Day"]}

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    print("Bot Started")
    
    message_handler = MessageHandler(Filters.text & (~Filters.command), get_message)

    dp.add_handler(message_handler)
    dp.add_handler(CommandHandler(["c", "C", "chart", "Chart", "CHART"], show_chart))
    dp.add_handler(CommandHandler(["k", "K", "klay", "Klay", "KLAY"], show_klay_chart))
    dp.add_handler(CommandHandler(["a", "A", "aklay", "Aklay", "AKLAY"], show_aklay_chart))
    dp.add_handler(CommandHandler(["p", "P", "ksp", "Ksp", "KSP"], show_ksp_chart))
    dp.add_handler(CommandHandler(["s", "S", "skai", "Skai", "SKAI", "sKai"], show_skai_chart))
    dp.add_handler(CommandHandler(["f", "F", "kfi", "Kfi", "KFI"], show_kfi_chart))
    dp.add_handler(CommandHandler(["h", "H", "house", "House", "HOUSE"], show_house_chart))
    dp.add_handler(CommandHandler(["o", "O", "orca", "Orca", "ORCA"], show_orca_chart))
    dp.add_handler(CommandHandler(["ks", "KS", "Ks", "kS"], show_ks_chart))
    dp.add_handler(CommandHandler(["j", "J", "jun", "Jun", "JUN"], show_jun_chart))
    dp.add_handler(CommandHandler(["b", "B"], show_bw_chart))
    dp.add_handler(CommandHandler(["w", "W"], show_wm_chart))
    dp.add_handler(CommandHandler(["m", "M", "mix", "MIX"], show_mix_chart))
    dp.add_handler(CommandHandler(["d", "D", "kdon", "KDON", "don", "DON"], show_don_chart))
    dp.add_handler(CommandHandler(["me", "ME", "meta", "META", "mu", "MU", "mudol", "MUDOL"], show_meta_chart))
    dp.add_handler(CommandHandler(["mo", "MO", "mon", "MON"], show_mon_chart))
    dp.add_handler(CommandHandler(["kl", "KL", "kleva", "KLEVA"], show_kleva_chart))
    dp.add_handler(CommandHandler(["33"], show_krno_chart))
    dp.add_handler(CommandHandler(["jc", "JC", "jab", "JAB"], show_jabco_chart))
    dp.add_handler(CommandHandler(["jc1", "JC1", "jab1", "JAB1"], show_jabco1_chart))
    dp.add_handler(CommandHandler(["jc2", "JC2", "jab2", "JAB2"], show_jabco2_chart))
    dp.add_handler(CommandHandler(["jc3", "JC3", "jab3", "JAB3"], show_jabco3_chart))
    dp.add_handler(CommandHandler(["jc4", "JC4", "jab4", "JAB4"], show_jabco4_chart))
    dp.add_handler(CommandHandler(["jc5", "JC5", "jab5", "JAB5"], show_jabco5_chart))
    dp.add_handler(CommandHandler(["bi", "BI"], show_biot_chart))
    dp.add_handler(CommandHandler(["mkc", "MKC", "MK", "mk"], show_mkc_chart))
    dp.add_handler(CommandHandler(["cl", "CL", "cla", "CLA"], show_cla_chart))
    dp.add_handler(CommandHandler(["bus"], show_bus_chart))
    dp.add_handler(CommandHandler(["pu", "PU", "punk", "PUNK"], show_punk_chart))
    dp.add_handler(CommandHandler(["spon", "sp"], spon_link))
    dp.add_handler(CommandHandler(["help"], help))
    dp.add_handler(CommandHandler(["call"], hello_ment))
    dp.add_handler(CommandHandler(["test"], test))
    # dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling(timeout=1, clean=True)
    updater.idle()

if __name__ == "__main__":
    main()
    
