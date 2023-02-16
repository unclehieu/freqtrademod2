
# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface_mod import IStrategyMod

# base on event of CCI/RSI/ADX/EMA to calculate indicators

class CherryEMA(IStrategyMod):
    """
    CherryEMA
    author@: Hieu Le

    """
    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "60":  0.01,
        "30":  0.03,
        "20":  0.04,
        "0":  0.05
    }

    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.10

    # Optimal timeframe for the strategy
    timeframe = '1h'
    startup_candle_count = 100
    # trailing stoploss
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # run "populate_indicators" only for new candle
    process_only_new_candles = False

    # Experimental settings (configuration will override these if set)
    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    # Optional order type mapping
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    CCI_SLOW = 14
    CCI_FAST = 6
    RSI_FAST = 6
    RSI_SLOW = 14
    INDI_TIME_PERIOD = 14
    RSI_MEDIUM = 50
    ADX_TREND = 25

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema34'] = ta.EMA(dataframe, timeperiod=34)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema89'] = ta.EMA(dataframe, timeperiod=89)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)

        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.INDI_TIME_PERIOD)

        dataframe['cci_slow'] = ta.CCI(dataframe, timeperiod=self.CCI_SLOW)
        dataframe['cci_fast'] = ta.CCI(dataframe, timeperiod=self.CCI_FAST)

        stoch = ta.STOCH(dataframe)
        dataframe['stochk'] = stoch['slowk']
        dataframe['stochd'] = stoch['slowd']

        stoch_rsi = ta.STOCHRSI(dataframe, timeperiod=self.INDI_TIME_PERIOD)
        dataframe['stochd_rsi'] = stoch_rsi['fastd']
        dataframe['stochk_rsi'] = stoch_rsi['fastk']

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.INDI_TIME_PERIOD)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=25)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=25)
        dataframe['mom'] = ta.MOM(dataframe, timeperiod=self.INDI_TIME_PERIOD)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (
                    (
                        # inverse trend ema20 cross ema50
                        qtpylib.crossed_above(dataframe['ema20'], dataframe['ema50']) |
                        (
                            (dataframe['close'] > dataframe['ema34']) &
                            (dataframe['close'] > dataframe['ema89']) &
                            (
                                (dataframe['close'].rolling(window=12).mean().shift(1) < dataframe['ema34']) |
                                (dataframe['close'].rolling(window=12).mean().shift(1) < dataframe['ema89'])
                            ) &
                            (dataframe['volume'].shift(1) < dataframe['volume'])
                        )
                    ) &
                    ((dataframe['rsi'] > self.RSI_MEDIUM) | self.check_adx(dataframe, True)) &
                    (dataframe['cci_slow'] > 0) &
                    (dataframe['close'] > dataframe['ema20']) &
                    (dataframe['open'] < dataframe['close'])  # green bar
                 ) |

                (
                        # continue way based on CCI events CCI > 0 & CCI > -100
                        ((qtpylib.crossed_above(dataframe['cci_slow'], -100) & dataframe['cci_slow'].rolling(
                            window=self.CCI_FAST).mean().shift(1) < -100)
                         | (qtpylib.crossed_above(dataframe['cci_slow'], 0) & dataframe['cci_slow'].rolling(
                                    window=self.CCI_FAST).mean().shift(1) < 0)) &
                        (self.check_stoch_macd(dataframe, True) | self.check_adx(dataframe, True))

                ) |
                (
                        # strong trend way based on crossing CCI > 100 & CCI < 200
                        qtpylib.crossed_above(dataframe['cci_slow'], 100) & (dataframe['cci_slow'] < 200) &
                        (dataframe['cci_slow'].rolling(window=self.CCI_FAST).mean().shift(1) < 100) &
                        self.check_stoch_macd(dataframe, True) &
                        ((dataframe['rsi'] > self.RSI_MEDIUM) | self.check_adx(dataframe, True))

                ) |
                (
                        # inverse way confirmed by green bar and CCI > -100 and RSI < 50
                        (dataframe['open'] < dataframe['close']) &  # green bar
                        (dataframe['close'] > dataframe['ema10']) &
                        (dataframe['cci_slow'] > -100) & (dataframe['cci_slow'] < 200) &
                        self.check_stoch_macd(dataframe, True) &
                        (dataframe['rsi'] < self.RSI_MEDIUM) & (dataframe['adx'] > self.ADX_TREND)

                ) |
                (
                    # RSI cross above 50
                    qtpylib.crossed_above(dataframe['rsi'], self.RSI_MEDIUM) &
                    (
                            (
                                (dataframe['rsi'].shift(1).tail(self.RSI_FAST).max() < self.RSI_MEDIUM) &
                                (dataframe['cci_slow'] > 0) &
                                self.check_stoch_macd(dataframe, True)
                            ) |
                            self.check_adx(dataframe, True)
                     )
                ) |
                (
                    # MACD cross above zero line
                    qtpylib.crossed_above(dataframe['macd'], 0) &
                    (dataframe['cci_slow'] < 100)
                ) |
                (
                    # ADX cross above 25
                    qtpylib.crossed_above(dataframe['adx'], self.ADX_TREND) & self.check_adx(dataframe, True)
                ) |
                (
                    # DI+ cross above DI-
                    qtpylib.crossed_above(dataframe['plus_di'], dataframe['minus_di']) & self.check_adx(dataframe, True)
                )

            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (
                    (
                        qtpylib.crossed_below(dataframe['ema20'], dataframe['ema50']) |
                        (
                                (dataframe['close'] < dataframe['ema34']) &
                                (dataframe['close'] < dataframe['ema89']) &
                                (
                                        (dataframe['close'].rolling(window=12).mean().shift(1) > dataframe['ema34']) |
                                        (dataframe['close'].rolling(window=12).mean().shift(1) > dataframe['ema89'])
                                ) &
                                (dataframe['volume'].shift(1) < dataframe['volume'])
                        )
                     ) &
                    ((dataframe['rsi'] < self.RSI_MEDIUM) | self.check_adx(dataframe, False)) &
                    (dataframe['cci_slow'] < 0) &
                    (dataframe['close'] < dataframe['ema20']) &
                    (dataframe['open'] > dataframe['close'])  # red bar
                ) |

                (
                        # continue way based on CCI events CCI < 0 & CCI < 100
                        ((qtpylib.crossed_below(dataframe['cci_slow'], 100) & dataframe['cci_slow'].rolling(
                            window=self.CCI_FAST).mean().shift(1) > 100)
                         | (qtpylib.crossed_below(dataframe['cci_slow'], 0) & dataframe['cci_slow'].rolling(
                                    window=self.CCI_FAST).mean().shift(1) > 0)) &
                        (self.check_stoch_macd(dataframe, False) | self.check_adx(dataframe, False))

                ) |
                (
                        # strong trend way based on crossing CCI < -100 & CCI > -200
                        qtpylib.crossed_below(dataframe['cci_slow'], -100) & (dataframe['cci_slow'] > -200) &
                        (dataframe['cci_slow'].rolling(window=self.CCI_FAST).mean().shift(1) > -100) &
                        self.check_stoch_macd(dataframe, False) &
                        ((dataframe['rsi'] < self.RSI_MEDIUM) | self.check_adx(dataframe, False))

                ) |
                (
                        # inverse way confirmed by green bar and CCI > -100 and RSI < 50
                        (dataframe['open'] > dataframe['close']) &  # red bar
                        (dataframe['close'] < dataframe['ema10']) &
                        (dataframe['cci_slow'] < 0) & (dataframe['cci_slow'] > -200) &
                        self.check_stoch_macd(dataframe, False) &
                        (dataframe['rsi'] > self.RSI_MEDIUM) & (dataframe['adx'] > self.ADX_TREND)

                ) |
                (
                        # RSI cross below 50
                        qtpylib.crossed_below(dataframe['rsi'], self.RSI_MEDIUM) &
                        (
                            (
                                    (dataframe['rsi'].shift(1).tail(self.RSI_FAST).min() > self.RSI_MEDIUM) &
                                    (dataframe['cci_slow'] < 0) &
                                    self.check_stoch_macd(dataframe, False)
                            ) |
                            self.check_adx(dataframe, False)
                        )
                ) |
                (
                    # MACD cross below zero line
                    qtpylib.crossed_below(dataframe['macd'], 0) &
                    (dataframe['cci_slow'] > -100)
                ) |
                (
                    # ADX cross below 25
                    qtpylib.crossed_below(dataframe['adx'], self.ADX_TREND) & self.check_adx(dataframe, False)
                ) |
                (
                    # DI+ cross below DI-
                    qtpylib.crossed_below(dataframe['plus_di'], dataframe['minus_di']) & self.check_adx(dataframe, False)
                )
            ),
            'sell'] = 1
        return dataframe

    def check_stoch_macd(self, dataframe: DataFrame, buy: bool):
        if buy:
            return (
                    (dataframe['cci_fast'] > dataframe['cci_slow']) &
                    ((dataframe['stochd'] > dataframe['stochk']) | (dataframe['stochd_rsi'] > dataframe['stochk_rsi'])) &
                    ((dataframe['macd'] > dataframe['macdsignal']) | (dataframe['macdhist'] > dataframe['macdhist'].shift(1)))
            )

        else:
            return (
                    (dataframe['cci_fast'] < dataframe['cci_slow']) &
                    ((dataframe['stochd'] < dataframe['stochk']) | (dataframe['stochd_rsi'] < dataframe['stochk_rsi'])) &
                    ((dataframe['macd'] < dataframe['macdsignal']) | (dataframe['macdhist'] < dataframe['macdhist'].shift(1)))
            )

    def check_stoch_macd_ema(self, dataframe: DataFrame, buy: bool):
        result = self.check_stoch_macd(dataframe, buy)
        if buy:
            return (
                    result &
                    (
                            ((dataframe['close'] > dataframe['ema34']) & (dataframe['close'] > dataframe['ema89'])) |
                            (dataframe['close'] > dataframe['ema200'])
                    )
            )

        else:
            return (
                    result &
                    (
                        ((dataframe['close'] < dataframe['ema34']) & (dataframe['close'] < dataframe['ema89'])) |
                        (dataframe['close'] < dataframe['ema200'])
                    )
            )

    def check_adx(self, dataframe: DataFrame, buy: bool):
        if buy:
            return (
                    (dataframe['adx'] > self.ADX_TREND) &
                    (dataframe['mom'] > 0) &
                    (dataframe['plus_di'] > self.ADX_TREND) &
                    (dataframe['plus_di'] > dataframe['minus_di'])

            )

        else:
            return (
                    (dataframe['adx'] > self.ADX_TREND) &
                    (dataframe['mom'] < 0) &
                    (dataframe['minus_di'] > self.ADX_TREND) &
                    (dataframe['plus_di'] < dataframe['minus_di'])
            )
