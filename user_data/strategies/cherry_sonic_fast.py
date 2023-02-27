# --- Do not remove these libs ---
import talib.abstract as ta
from pandas import DataFrame

# --------------------------------
from freqtrade.strategy.interface_mod import IStrategyMod
from freqtrade.strategy.strategy_helper import merge_informative_pair


class CherrySonicFast(IStrategyMod):
    """

    author@: Hieu Le

    Khi 30m theo sonic thi pha dragon se vao lenh

    """
    can_short = False

    # Minimal ROI designed for the strategy.
    # adjust based on market conditions. We would recommend to keep it low for quick turn arounds
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "0": 0.1
    }

    # Optimal stoploss designed for the strategy
    stoploss = -0.1

    # Optimal timeframe for the strategy
    timeframe = '30m'

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 200

    DEFAULT_RSI_PERIOD = 14
    MEDIUM_RSI = 50
    OVER_BOUGHT_RSI = 75
    OVER_SOLD_RSI = 25

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()

        tf_1h = [(pair, '1h') for pair in pairs]

        return tf_1h

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.dp:
            return dataframe

        # EMA for 1h
        tf_1h = '1h'
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=tf_1h)
        informative_1h['ema34'] = ta.EMA(informative_1h, 34)
        informative_1h['ema89'] = ta.EMA(informative_1h, 89)
        informative_1h['ema200'] = ta.EMA(informative_1h, 200)

        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, tf_1h, ffill=True)

        # 30m
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.DEFAULT_RSI_PERIOD)
        dataframe['ema34'] = ta.EMA(dataframe, 34)
        dataframe['ema34_high'] = ta.EMA(dataframe, timeperiod=34, price='high')
        dataframe['ema34_low'] = ta.EMA(dataframe, timeperiod=34, price='low')
        dataframe['ema89'] = ta.EMA(dataframe, 89)
        dataframe['ema200'] = ta.EMA(dataframe, 200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # long
        dataframe.loc[
            (
                (self.trend_sonic_buy(dataframe) | self.trend_sonic_revert_soon_buy(dataframe)
                 | self.trend_sonic_keep_parent_buy(dataframe, '_1h')) &
                (dataframe['rsi'] > self.MEDIUM_RSI) &
                (dataframe['rsi'] < self.OVER_BOUGHT_RSI) &
                (dataframe['low'] <= dataframe['ema34']) &
                (dataframe['close'] > dataframe['ema34_high']) &
                self.closed_above_prev_candle(dataframe) &
                self.bullish_candle(dataframe) &
                self.volume_higher_mean(dataframe)

             )

            , 'enter_long'] = 1

        # short
        dataframe.loc[
            (
                (self.trend_sonic_sell(dataframe) | self.trend_sonic_revert_soon_sell(dataframe)
                 | self.trend_sonic_keep_parent_sell(dataframe, '_1h')) &
                (dataframe['rsi'] < self.MEDIUM_RSI) &
                (dataframe['rsi'] > self.OVER_SOLD_RSI) &
                (dataframe['high'] >= dataframe['ema34']) &
                (dataframe['close'] < dataframe['ema34_low']) &
                self.closed_below_prev_candle(dataframe) &
                self.bearish_candle(dataframe) &
                self.volume_higher_mean(dataframe)

            )

            , 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    @staticmethod
    def trend_sonic_buy(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (dataframe['ema34' + tf_suffix] >= dataframe['ema89' + tf_suffix]) &
                (dataframe['ema89' + tf_suffix] >= dataframe['ema200' + tf_suffix])
                # (dataframe['ema200' + tf_suffix] >= dataframe['ema610' + tf_suffix])
        )

    @staticmethod
    def trend_sonic_sell(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (dataframe['ema34' + tf_suffix] <= dataframe['ema89' + tf_suffix]) &
                (dataframe['ema89' + tf_suffix] <= dataframe['ema200' + tf_suffix])
                # (dataframe['ema200' + tf_suffix] <= dataframe['ema610' + tf_suffix])
        )

    @staticmethod
    def trend_sonic_revert_soon_buy(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (dataframe['ema34' + tf_suffix] >= dataframe['ema89' + tf_suffix]) &
                (dataframe['ema34' + tf_suffix] >= dataframe['ema200' + tf_suffix]) &
                (dataframe['ema89' + tf_suffix] <= dataframe['ema200' + tf_suffix])
        )

    @staticmethod
    def trend_sonic_revert_soon_sell(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (dataframe['ema34' + tf_suffix] <= dataframe['ema89' + tf_suffix]) &
                (dataframe['ema34' + tf_suffix] <= dataframe['ema200' + tf_suffix]) &
                (dataframe['ema89' + tf_suffix] >= dataframe['ema200' + tf_suffix])
        )

