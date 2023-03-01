# --- Do not remove these libs ---
import talib.abstract as ta
from pandas import DataFrame

# --------------------------------
from freqtrade.strategy.interface_mod import IStrategyMod
from freqtrade.strategy.strategy_helper import merge_informative_pair


class CherrySonicDragon(IStrategyMod):
    """

    author@: Hieu Le
    When H4 theo sonic va nam ngoai dragon thi tiep tuc long/short khung nho khi cham ema

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
    startup_candle_count: int = 610

    DEFAULT_RSI_PERIOD = 14
    MEDIUM_RSI = 50
    OVER_BOUGHT_RSI = 75
    OVER_SOLD_RSI = 25

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()

        tf_4h = [(pair, '4h') for pair in pairs]
        tf_1h = [(pair, '1h') for pair in pairs]

        return tf_4h + tf_1h

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.dp:
            return dataframe

        # EMA for 4h
        tf_4h = '4h'
        informative_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=tf_4h)
        informative_4h['ema34'] = ta.EMA(informative_4h, 34)
        informative_4h['ema34_high'] = ta.EMA(informative_4h, timeperiod=34, price='high')
        informative_4h['ema34_low'] = ta.EMA(informative_4h, timeperiod=34, price='low')
        informative_4h['ema89'] = ta.EMA(informative_4h, 89)
        informative_4h['ema200'] = ta.EMA(informative_4h, 200)
        informative_4h['rsi'] = ta.RSI(informative_4h, timeperiod=self.DEFAULT_RSI_PERIOD)

        dataframe = merge_informative_pair(dataframe, informative_4h, self.timeframe, tf_4h, ffill=True)

        # EMA for 1h
        tf_1h = '1h'
        informative_1h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=tf_1h)
        informative_1h['ema34'] = ta.EMA(informative_1h, 34)
        informative_1h['ema89'] = ta.EMA(informative_1h, 89)
        informative_1h['ema200'] = ta.EMA(informative_1h, 200)
        informative_1h['ema610'] = ta.EMA(informative_1h, 610)

        dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, tf_1h, ffill=True)

        # 30m
        dataframe['ema34'] = ta.EMA(dataframe, 34)
        dataframe['ema89'] = ta.EMA(dataframe, 89)
        dataframe['ema200'] = ta.EMA(dataframe, 200)
        dataframe['ema610'] = ta.EMA(dataframe, 610)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # long
        dataframe.loc[
            (
                (self.trend_sonic_buy(dataframe, '_4h') | self.check_if_trend_sonic_soft_buy(dataframe, '_4h')) &
                # price above dragon
                # (dataframe['close_4h'] > dataframe['ema34_high_4h']) &
                (dataframe['close_4h'] > dataframe['ema34_4h']) &
                (dataframe['rsi_4h'] > self.MEDIUM_RSI) &
                (dataframe['rsi_4h'] < self.OVER_BOUGHT_RSI) &
                (
                    # 1h
                    (
                        (
                            (
                                self.touch_ema_buy(dataframe, '_1h') &
                                self.bullish_candle(dataframe, '_1h')
                            ) |
                            (
                                self.touch_ema_buy(dataframe.shift(1), '_1h') &
                                self.closed_above_prev_candle(dataframe, '_1h') &
                                self.closed_above_middle_candle(dataframe, '_1h')
                            )
                        ) &
                        (self.trend_sonic_buy(dataframe, '_1h') | self.trend_sonic_revert_soon_buy(dataframe, '_1h'))
                    ) |
                    # 30m
                    (
                        (
                            (
                                self.touch_ema_buy(dataframe) &
                                self.bullish_candle(dataframe)
                            ) |
                            (
                                self.touch_ema_buy(dataframe.shift(1)) &
                                self.closed_above_prev_candle(dataframe) &
                                self.closed_above_middle_candle(dataframe)
                            )
                        ) &
                        (self.trend_sonic_buy(dataframe) | self.trend_sonic_revert_soon_buy(dataframe))
                    )
                )

             )

            , 'enter_long'] = 1

        # short
        dataframe.loc[
            (
                (self.trend_sonic_sell(dataframe, '_4h') | self.check_if_trend_sonic_soft_sell(dataframe, '_4h')) &
                # price below dragon
                # (dataframe['close_4h'] < dataframe['ema34_low_4h']) &
                (dataframe['close_4h'] < dataframe['ema34_4h']) &
                (dataframe['rsi_4h'] < self.MEDIUM_RSI) &
                (dataframe['rsi_4h'] > self.OVER_SOLD_RSI) &
                (
                    # 1h
                    (
                        (
                            (
                                self.touch_ema_sell(dataframe, '_1h') &
                                self.bearish_candle(dataframe, '_1h')
                            ) |
                            (
                                self.touch_ema_sell(dataframe.shift(1), '_1h') &
                                self.closed_below_prev_candle(dataframe, '_1h') &
                                self.closed_below_middle_candle(dataframe, '_1h')
                            )
                        ) &
                        (self.trend_sonic_sell(dataframe, '_1h') | self.trend_sonic_revert_soon_sell(dataframe, '_1h'))
                    ) |
                    # 30m
                    (
                        (
                            (
                                self.touch_ema_sell(dataframe) &
                                self.bearish_candle(dataframe)
                            ) |
                            (
                                self.touch_ema_sell(dataframe.shift(1)) &
                                self.closed_below_prev_candle(dataframe) &
                                self.closed_below_middle_candle(dataframe)
                            )
                        ) &
                        (self.trend_sonic_sell(dataframe) | self.trend_sonic_revert_soon_sell(dataframe))
                    )
                )
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

