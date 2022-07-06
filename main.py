import requests
import pandas as pd
import time
from ast import literal_eval
import json

import upbit


def market_code():
    url = "https://api.upbit.com/v1/market/all"
    querystring = {"isDetails": "false"}
    response = requests.request("GET", url, params=querystring)

    # 코인이름 - 마켓코드 매핑
    r_str = response.text
    r_str = r_str.lstrip('[')  # 첫 문자 제거
    r_str = r_str.rstrip(']')  # 마지막 문자 제거
    r_list = r_str.split("}")  # str를 }기준으로 쪼개어 리스트로 변환

    name_to_code = {}
    code_list = []

    for i in range(len(r_list) - 1):
        r_list[i] += "}"
        if i != 0:
            r_list[i] = r_list[i].lstrip(',')
        r_dict = literal_eval(r_list[i])  # element to dict
        if r_dict["market"][0] == 'K':  # 원화거래 상품만 추출
            temp_dict = {r_dict["market"]: r_dict["korean_name"]}
            code_list.append(r_dict["market"])  # 코드 리스트
            # name_to_code.update(temp_dict)  # 코인이름 - 코드 매핑(딕셔너리)
    return code_list

def rsi(ohlc: pd.DataFrame, period: int = 14):
    ohlc["trade_price"] = ohlc["trade_price"]
    delta = ohlc["trade_price"].diff()
    gains, declines = delta.copy(), delta.copy()
    gains[gains < 0] = 0
    declines[declines > 0] = 0

    _gain = gains.ewm(com=(period - 1), min_periods=period).mean()
    _loss = declines.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    return pd.Series(100 - (100 / (1 + RS)), name="RSI")


def sendAlert(token, channel, lowCoinDataSet):
    print('sendAlert')
    text = '[CCI Alert] 일봉' + '\n'
    x = {'name': 'John', 'age': 36}
    for coin in lowCoinDataSet:
        text += coin['market'] + ' ' + coin['rsi'] + "\n"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'channel': channel,
        'text': text
    }
    r = requests.post('https://slack.com/api/chat.postMessage',
                      headers=headers,
                      data=json.dumps(payload)
                      )

    chat_data = pd.json_normalize(r.json()['message'])
    return chat_data.ts[0]


def deleteSlackMsg(token, channel, ts):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    }
    payload = {
        'channel': channel,
        'ts': ts
    }
    r = requests.post('https://slack.com/api/chat.delete',
                      headers=headers,
                      data=json.dumps(payload)
                      )
    print('deleteSlackMsg')


code_list = market_code()
print('code_list', code_list)
# code_list = ['KRW-BTC', 'KRW-SBD']
ts = 0

while True:
    # url = "https://api.upbit.com/v1/candles/minutes/60"
    url = "https://api.upbit.com/v1/candles/days"
    lowCoinDataSet = []

    for market in code_list:
        querystring = {"market": market, "count": "200"}
        response = requests.request("GET", url, params=querystring)
        data = response.json()
        time.sleep(1)
        cci2 = upbit.get_cci(data)
        # cci2 = upbit.get_rsi(data)
        # cci2 = cci[0]['CCI']

        if ((cci2 > -200 and cci2 < -95) and market != 'KRW-BTC'):
        # if ((cci2 < 30) and market != 'KRW-BTC'):
            print(market, cci2)
            lowcoin = {'market': market, 'rsi': str(cci2)}
            lowCoinDataSet.append(lowcoin)
        elif (market == 'KRW-BTC'):
            mainCoin = {'market': market, 'rsi': str(cci2)}

    sorted_lowCoinDataSet = sorted(lowCoinDataSet, key=lambda k: k['rsi'])
    sorted_lowCoinDataSet.insert(0, mainCoin)
    print(sorted_lowCoinDataSet)

    if len(sorted_lowCoinDataSet) > 0:
        if(ts != 0):
            deleteSlackMsg('your token id', 'your channel id', ts)
            # time.sleep(0.3)
        ts = sendAlert('your token id', '#your-channel-name', sorted_lowCoinDataSet)
    time.sleep(180)

