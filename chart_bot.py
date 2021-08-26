# -*- coding: utf-8 -*- 

import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from mplfinance.original_flavor import candlestick_ohlc
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import datetime, time
from pymongo import MongoClient
import pymongo, ssl

token = os.environ["BOT_TOKEN"]
token_name_list : list = os.environ["TOKEN_NAME"].split(" ")
token_hash_list : list = os.environ["TOKEN_HASH"].split(" ")
max_length : int = int(os.environ["MAX_LENGTH"])

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

def total_chart(time, prices, user_name, list_coins):
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
        ax2.text(-2, yticks[len(yticks)-1],f'H : {max_value}\nL : {min_value}',fontsize=12, ha='left', bbox=bbox) ## 선 그래프 텍스트
        
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
        ax2.set_title(f'{cid.upper()}/USDT',fontsize=20)

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

def draw_chart(user_name, coin_name):
    global price_db
    global time_list
    global prices_candle_dict
    global close_prices_dict
    
    price_documents = list(price_db.coin.price.find().sort([("_id",-1)]).limit(min(max_length, price_db.coin.price.count_documents({}))))
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
                list_coins.remove("ksp")
            
            price_data_str = total_chart(time_list, prices_candle_dict, user_name, list_coins)
        except:
            return False, f"에러 발생..."
    else:
        return False, f"데이터 수집중..."
    
    time_list = []
    for k in prices_candle_dict.keys():
        prices_candle_dict[k] = []
        close_prices_dict[k] = []

    return True, price_data_str

def show_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]
    input_msg = update.message.text.split(" ")
    if len(input_msg) > 1:
        coin_name = input_msg[1]
    else:
        coin_name = "total"

    data_checker, result_msg = draw_chart(user_name, [coin_name])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def show_klay_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]

    data_checker, result_msg = draw_chart(user_name, ["klay", "aklay"])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def show_ksp_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]

    data_checker, result_msg = draw_chart(user_name, ["klay", "ksp"])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def show_skai_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]

    data_checker, result_msg = draw_chart(user_name, ["skai"])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def show_kfi_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]

    data_checker, result_msg = draw_chart(user_name, ["kfi"])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def show_house_chart(update, ctx):
    data_checker : bool = True
    result_msg : str = ""
    user_name = update.message.from_user["username"]

    data_checker, result_msg = draw_chart(user_name, ["house"])

    if data_checker:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)
        ctx.bot.send_photo(chat_id=update.message.chat_id, photo=open(f'result_{user_name}.png', 'rb'))
    else:
        ctx.bot.send_message(chat_id=update.message.chat_id, text=result_msg)    
    return

def spon_link(update, ctx):
    ctx.bot.send_message(chat_id=update.message.chat_id, text="1파이도 감사히 받습니다!\n받은 후원금은 서버 운영비 및 개발자 치킨 사먹는데 쓰입니다.")  
    ctx.bot.send_message(chat_id=update.message.chat_id, text="0x5657CeC0a50089Ac4cb698c71319DC56ab5C866a")    

def main():
    global price_db
    global time_list
    global prices_candle_dict

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

    updater = Updater(token)
    dp = updater.dispatcher
    print("Bot Started")

    dp.add_handler(CommandHandler(["c", "C", "chart", "Chart", "CHART"], show_chart))
    dp.add_handler(CommandHandler(["k", "K", "klay", "Klay", "KLAY"], show_klay_chart))
    dp.add_handler(CommandHandler(["p", "P", "ksp", "Ksp", "KSP"], show_ksp_chart))
    dp.add_handler(CommandHandler(["s", "S", "skai", "Skai", "SKAI", "sKai"], show_skai_chart))
    dp.add_handler(CommandHandler(["f", "F", "kfi", "Kfi", "KFI"], show_kfi_chart))
    dp.add_handler(CommandHandler(["h", "H", "house", "House", "HOUSE"], show_house_chart))
    dp.add_handler(CommandHandler(["spon", "sp"], spon_link))
    # dp.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
    
