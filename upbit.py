import time
import logging
import requests
import uuid
import hashlib
import math
import os
import pandas as pd
import numpy

from urllib.parse import urlencode
from decimal import Decimal
server_url = 'https://api.upbit.com'

# 상수 설정
min_order_amt = 5000

def get_rsi(candle_data):
    try:
        df = pd.DataFrame(candle_data)
        df = df.reindex(index=df.index[::-1]).reset_index()

        df['close'] = df["trade_price"]

        # RSI 계산
        def rsi(ohlc: pd.DataFrame, period: int = 14):
            ohlc["close"] = ohlc["close"]
            delta = ohlc["close"].diff()

            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0

            _gain = up.ewm(com=(period - 1), min_periods=period).mean()
            _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()

            RS = _gain / _loss
            return pd.Series(100 - (100 / (1 + RS)), name="RSI")

        rsi = round(rsi(df, 14).iloc[-1], 4)

        return rsi


    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def get_cci(candle_data):
    try:

        # CCI 데이터 리턴용
        #cci_list = []

        # 오름차순 정렬
        df = pd.DataFrame(candle_data)
        ordered_df = df.sort_values(by=['candle_date_time_kst'], ascending=[True])

        # 계산식 : (Typical Price - Simple Moving Average) / (0.015 * Mean absolute Deviation)
        ordered_df['TP'] = (ordered_df['high_price'] + ordered_df['low_price'] + ordered_df['trade_price']) / 3
        ordered_df['SMA'] = ordered_df['TP'].rolling(window=20).mean()
        ordered_df['MAD'] = ordered_df['TP'].rolling(window=20).apply(lambda x: pd.Series(x).mad())
        ordered_df['CCI'] = (ordered_df['TP'] - ordered_df['SMA']) / (0.015 * ordered_df['MAD'])

        # 개수만큼 조립
        #for i in range(0, loop_cnt):
        #    cci_list.append({"CCI": round(ordered_df['CCI'].loc[i], 4)})
        cci = round(ordered_df['CCI'].loc[0], 4)

        return cci

    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def send_request(reqType, reqUrl, reqParam, reqHeader):
    try:

        # 요청 가능회수 확보를 위해 기다리는 시간(초)
        err_sleep_time = 0.3

        # 요청에 대한 응답을 받을 때까지 반복 수행
        while True:

            # 요청 처리
            response = requests.request(reqType, reqUrl, params=reqParam, headers=reqHeader)

            # 요청 가능회수 추출
            if 'Remaining-Req' in response.headers:

                hearder_info = response.headers['Remaining-Req']
                start_idx = hearder_info.find("sec=")
                end_idx = len(hearder_info)
                remain_sec = hearder_info[int(start_idx):int(end_idx)].replace('sec=', '')
            else:
                logging.error("헤더 정보 이상")
                logging.error(response.headers)
                break

            # 요청 가능회수가 3개 미만이면 요청 가능회수 확보를 위해 일정시간 대기
            if int(remain_sec) < 3:
                logging.debug("요청 가능회수 한도 도달! 남은횟수:" + str(remain_sec))
                time.sleep(err_sleep_time)

            # 정상 응답
            if response.status_code == 200 or response.status_code == 201:
                break
            # 요청 가능회수 초과인 경우
            elif response.status_code == 429:
                logging.error("요청 가능회수 초과!:" + str(response.status_code))
                time.sleep(err_sleep_time)
            # 그 외 오류
            else:
                logging.error("기타 에러:" + str(response.status_code))
                logging.error(response.status_code)
                break

            # 요청 가능회수 초과 에러 발생시에는 다시 요청
            logging.info("[restRequest] 요청 재처리중...")

        return response

    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise

def get_candle(target_item, tick_kind, inq_range):
    try:

        # ----------------------------------------
        # Tick 별 호출 URL 설정
        # ----------------------------------------
        # 분붕
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        # 일봉
        elif tick_kind == "D":
            target_url = "days"
        # 주봉
        elif tick_kind == "W":
            target_url = "weeks"
        # 월봉
        elif tick_kind == "M":
            target_url = "months"
        # 잘못된 입력
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))

        logging.debug(target_url)

        # ----------------------------------------
        # Tick 조회
        # ----------------------------------------
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", server_url + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()

        logging.debug(candle_data)

        return candle_data

    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise