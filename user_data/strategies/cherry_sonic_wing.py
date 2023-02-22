# --- Do not remove these libs ---
import talib.abstract as ta
from pandas import DataFrame

# --------------------------------
from freqtrade.strategy import merge_informative_pair
from freqtrade.strategy.interface_mod import IStrategyMod


class CherrySonicWing(IStrategyMod):
    """

    author@: Hieu Le

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
    timeframe = '4h'

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 610

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()

        tf_1d = [(pair, '1d') for pair in pairs]

        return tf_1d

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.dp:
            return dataframe

        # EMA for 1d
        tf_1d = '1d'
        informative_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=tf_1d)
        informative_1d['ema34'] = ta.EMA(informative_1d, 34)
        informative_1d['ema89'] = ta.EMA(informative_1d, 89)
        informative_1d['ema200'] = ta.EMA(informative_1d, 200)

        dataframe = merge_informative_pair(dataframe, informative_1d, self.timeframe, tf_1d, ffill=True)

        dataframe['ema34'] = ta.EMA(dataframe, 34)
        dataframe['ema89'] = ta.EMA(dataframe, 89)
        dataframe['ema200'] = ta.EMA(dataframe, 200)
        dataframe['ema610'] = ta.EMA(dataframe, 610)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # long
        dataframe.loc[
            (
                (self.trend_sonic_buy(dataframe) | self.trend_sonic_revert_soon_buy(dataframe) | self.trend_sonic_buy(dataframe, '_1d')) &
                self.touch_ema_buy(dataframe) &
                self.bullish_candle(dataframe)
             )

            , 'enter_long'] = 1

        # short
        dataframe.loc[
            (
                (self.trend_sonic_sell(dataframe) | self.trend_sonic_revert_soon_sell(dataframe) | self.trend_sonic_sell(dataframe, '_1d')) &
                self.touch_ema_sell(dataframe) &
                self.bearish_candle(dataframe)
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

    @staticmethod
    def touch_ema_buy(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (
                        (dataframe['close' + tf_suffix] > dataframe['ema34' + tf_suffix]) &
                        (dataframe['low' + tf_suffix] <= dataframe['ema34' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] > dataframe['ema89' + tf_suffix]) &
                        (dataframe['low' + tf_suffix] <= dataframe['ema89' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] > dataframe['ema200' + tf_suffix]) &
                        (dataframe['low' + tf_suffix] <= dataframe['ema200' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] > dataframe['ema610' + tf_suffix]) &
                        (dataframe['low' + tf_suffix] <= dataframe['ema610' + tf_suffix])
                )
        )

    @staticmethod
    def touch_ema_sell(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (
                        (dataframe['close' + tf_suffix] < dataframe['ema34' + tf_suffix]) &
                        (dataframe['high' + tf_suffix] >= dataframe['ema34' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] < dataframe['ema89' + tf_suffix]) &
                        (dataframe['high' + tf_suffix] >= dataframe['ema89' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] < dataframe['ema200' + tf_suffix]) &
                        (dataframe['high' + tf_suffix] >= dataframe['ema200' + tf_suffix])
                ) |
                (
                        (dataframe['close' + tf_suffix] < dataframe['ema610' + tf_suffix]) &
                        (dataframe['high' + tf_suffix] >= dataframe['ema610' + tf_suffix])
                )
        )

