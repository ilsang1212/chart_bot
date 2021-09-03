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

token = os.environ["BOT_TOKEN"]
token_name_list : list = os.environ["TOKEN_NAME"].split(" ")
token_hash_list : list = os.environ["TOKEN_HASH"].split(" ")
max_length : int = int(os.environ["MAX_LENGTH"])
chat_id_list : list = os.environ["CHAT_ID_LIST"].split(" ")

mongoDB_connect_info : dict = {
    "host" : os.environ["mongoDB_HOST"],
    "username" : os.environ["USER_ID"],
    "password" : os.environ["USER_PASSWORD"]
    }

price_db = None
kwlps : dict = {}
time_list : list = []
close_prices_dict : dict = {"klay":[]}
prices_candle_dict : dict = {"klay":[]}
candle_time_db_dict : dict = {"5":None, "15":None, "1":None, "4":None}

for i, name in enumerate(token_name_list):
    kwlps[name] = token_hash_list[i]

for k in kwlps.keys():
    close_prices_dict[k] = []
    prices_candle_dict[k] = []

# Figure 크기 이상하면 여기 수치 조정하세요.
fig_scale = 3

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

def total_chart(time, prices, user_name, list_coins, title):
    result_str : str = ""
    n_rows = len(list_coins)
    fig, axes = plt.subplots(n_rows, 1, figsize=(4*fig_scale, n_rows*fig_scale), dpi=50)
    if n_rows != 1:
        axes = axes.flatten()
    else:
        axes = [axes]

    data_time = time
    
    for i, ax in enumerate(axes):
        cid = list_coins[i]
        ax.clear()

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
        result_str += f"{cid.upper()} : ${ohlc[len(ohlc)-1][3]}\n"

        for y in yticks:
            ax2.axhline(y,linestyle=(0,(5,2)),color='grey',alpha=0.5) ## 눈금선 생성

        ax2.text(xticks[len(xticks)-2], yticks[len(yticks)-1],f'{dohlc[len(dohlc)-1][4]}',fontsize=15, ha='center', bbox=bbox) ## 선 그래프 텍스트
        ax2.text(0, yticks[len(yticks)-1],f'H : {max_value}\nL : {min_value}',fontsize=12, ha='left', bbox=bbox) ## 선 그래프 텍스트
        
        for i in range(len(result_data_time)):
            if i % 6 != 0:
                result_data_time[i] = ""

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

def draw_chart(db, user_name, coin_name, title):
    global time_list
    global prices_candle_dict
    global close_prices_dict
    
    price_documents = list(db.find().sort([("_id",-1)]).limit(min(max_length, db.count_documents({}))))
    result_documents = list(reversed(price_documents))
    if len(result_documents) >= 2:
        for data in result_documents:
            time_list.append(data["Time"])
            for k in data.keys():
                if k != "_id" and k != "Time":
                    prices_candle_dict[k].append(data[k][0])
                    close_prices_dict[k].append(data[k][0][3])
        try:
            if "total" not in coin_name:
                list_coins = coin_name
            else:
                list_coins = ['klay'] + [c for c in kwlps.keys()]
                remove_coin_list = ["orca", "vkai", "kdai", "kai"]
                for coin_name in remove_coin_list:
                    list_coins.remove(coin_name)
            
            price_data_str = total_chart(time_list, prices_candle_dict, user_name, list_coins, title)
        except:
            return False, f"에러 발생..."
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
    price_list : list = []
    for price_value in cal_ratio:
        if price_value.find("$") != -1:
            price_list.append(price_value[price_value.find("$")+1:])
    price_ratio = round(float(price_list[0])/float(price_list[1]), 5)

    result = f"{msg}\n1 {a_token_name} ≈ {price_ratio} {b_token_name}"
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

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "aklay", "ksp"], interval_str)

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "aklay"], interval_str)

    result_msg = display_price_ratio(result_msg, "Klay", "aKlay")

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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
    
    result_msg = display_price_ratio(result_msg, "Klay", "Ksp")

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    data_checker, result_msg = draw_chart(data_db, user_name, ["skai", "vkai", "kai"], interval_str)

    result_msg = display_price_ratio(result_msg, "sKai", "vKai")

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "kfi"], interval_str)

    result_msg = display_price_ratio(result_msg, "Klay", "Kfi")

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    data_checker, result_msg = draw_chart(data_db, user_name, ["klay", "house"], interval_str)

    result_msg = display_price_ratio(result_msg, "Klay", "House")

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
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

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def spon_link(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text="1클파이도 감사히 받습니다!\n받은 후원금은 서버 운영비 및 개발자 치킨 사먹는데 쓰입니다.")  
    ctx.bot.send_message(chat_id=update.message.chat_id, text="0x5657CeC0a50089Ac4cb698c71319DC56ab5C866a")    

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

    candle_time_db_dict = {"5":[price_db.coin.price, "5m"], "15":[price_db.coin.price_fifteen, "15m"], "1":[price_db.coin.price_hour, "1h"], "4":[price_db.coin.price_four_hour, "4h"]}

    updater = Updater(token)
    dp = updater.dispatcher
    print("Bot Started")

    dp.add_handler(CommandHandler(["c", "C", "chart", "Chart", "CHART"], show_chart))
    dp.add_handler(CommandHandler(["k", "K", "klay", "Klay", "KLAY"], show_klay_chart))
    dp.add_handler(CommandHandler(["a", "A", "aklay", "Aklay", "AKLAY"], show_aklay_chart))
    dp.add_handler(CommandHandler(["p", "P", "ksp", "Ksp", "KSP"], show_ksp_chart))
    dp.add_handler(CommandHandler(["s", "S", "skai", "Skai", "SKAI", "sKai"], show_skai_chart))
    dp.add_handler(CommandHandler(["f", "F", "kfi", "Kfi", "KFI"], show_kfi_chart))
    dp.add_handler(CommandHandler(["h", "H", "house", "House", "HOUSE"], show_house_chart))
    dp.add_handler(CommandHandler(["o", "O", "orca", "Orca", "ORCA"], show_orca_chart))
    dp.add_handler(CommandHandler(["spon", "sp"], spon_link))
    # dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
    
