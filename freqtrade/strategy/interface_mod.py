from abc import ABC
from datetime import datetime

import pytz
from pandas import DataFrame
import pandas as pd

from freqtrade.constants import DATE_STORAGE_FORMAT
from freqtrade.enums.rpcmessagetype import RPCMessageType
from freqtrade.persistence.signal_tracking import SignalTracking
from freqtrade.rpc import RPCManager
from freqtrade.strategy.interface import IStrategy


class IStrategyMod(IStrategy, ABC):
    INTERFACE_VERSION = 3

    BUY: str = 'BUY'
    SELL: str = 'SELL'
    rpc_manager: RPCManager = None
    TIME_ZONE = pytz.timezone('Asia/Saigon')

    def send_notification(self, pair: str, signal: str):
        if self.rpc_manager is None:
            return

        self.rpc_manager.send_msg({
            'type': RPCMessageType.SIGNAL,
            'status': f"{pair} - {signal} - {self.timeframe} - {self.__class__.__name__}"
        })

    def check_and_notify_signal(self, buy: bool, sell: bool, pair: str):
        if buy and not self.check_already_tracked(signal=self.BUY, pair=pair):
            self.send_notification(pair, self.BUY)
            self.track_signal(signal=self.BUY, pair=pair)

        if sell and not self.check_already_tracked(signal=self.SELL, pair=pair):
            self.send_notification(pair, self.SELL)
            self.track_signal(signal=self.SELL, pair=pair)

    def track_signal(self, signal: str, pair: str):
        now = datetime.now(self.TIME_ZONE)
        signal = SignalTracking(pair=pair,
                                timeframe=self.timeframe,
                                signal=signal,
                                strategy=self.__class__.__name__,
                                created_time=now,
                                created_date=int(now.strftime(DATE_STORAGE_FORMAT)))
        SignalTracking.query.session.add(signal)
        SignalTracking.query.session.commit()

    def check_already_tracked(self, signal: str, pair: str):
        signals = SignalTracking.query_signals(
                                pair=pair,
                                timeframe=self.timeframe,
                                signal=signal,
                                strategy=self.__class__.__name__,
                                date=int(datetime.now(self.TIME_ZONE).strftime(DATE_STORAGE_FORMAT))).all()
        return len(signals) > 0

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float, time_in_force: str,
                            current_time: datetime, **kwargs) -> bool:
        if self.config['runmode'].value == 'dry_run' and self.config.get('notification_only', False):
            # skip all trades, only in dry-run mode
            return False

    @staticmethod
    def volume_increasing_buy(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (
                (dataframe['volume' + tf_suffix].shift(1) < dataframe['volume' + tf_suffix]) &
                (dataframe['close' + tf_suffix] > dataframe['open' + tf_suffix])
            ) |
            (
                    (dataframe['volume' + tf_suffix].shift(1) > dataframe['volume' + tf_suffix]) &
                    (dataframe['close' + tf_suffix] < dataframe['open' + tf_suffix])
            ) |
            (
                    (dataframe['volume' + tf_suffix].shift(1) < dataframe['volume' + tf_suffix]) &
                    (dataframe['close' + tf_suffix] < dataframe['open' + tf_suffix]) &
                    (dataframe['close' + tf_suffix] > (dataframe['high' + tf_suffix] - ((dataframe['high' + tf_suffix] - dataframe['low' + tf_suffix]) / 2)))
            )

        )

    @staticmethod
    def volume_increasing_sell(dataframe: DataFrame, tf_suffix: str = ''):
        return (
                (
                        (dataframe['volume' + tf_suffix].shift(1) > dataframe['volume' + tf_suffix]) &
                        (dataframe['close' + tf_suffix] > dataframe['open' + tf_suffix])
                ) |
                (
                        (dataframe['volume' + tf_suffix].shift(1) < dataframe['volume' + tf_suffix]) &
                        (dataframe['close' + tf_suffix] < dataframe['open' + tf_suffix])
                ) |
                (
                        (dataframe['volume' + tf_suffix].shift(1) < dataframe['volume' + tf_suffix]) &
                        (dataframe['close' + tf_suffix] > dataframe['open' + tf_suffix]) &
                        (dataframe['close' + tf_suffix] < (dataframe['high' + tf_suffix] - ((dataframe['high' + tf_suffix] - dataframe['low' + tf_suffix]) / 2)))
                )

        )

    @staticmethod
    def volume_higher_prev(dataframe: DataFrame, tf_suffix: str = ''):
        return dataframe['volume' + tf_suffix].shift(1) < dataframe['volume' + tf_suffix]

    @staticmethod
    def volume_higher_mean(dataframe: DataFrame, tf_suffix: str = ''):
        return dataframe['volume' + tf_suffix] > dataframe['volume' + tf_suffix].tail(5).mean()

    @staticmethod
    def touch_buy(self, dataframe: DataFrame, support: pd.Series, tf_suffix: str = ''):
        return (
                (dataframe['close' + tf_suffix] > support) &
                (dataframe['low' + tf_suffix] <= support) &
                self.closed_above_middle_candle(dataframe)
        )

    @staticmethod
    def touch_sell(self, dataframe: DataFrame, resistance: pd.Series, tf_suffix: str = ''):
        return (
                (dataframe['close' + tf_suffix] < resistance) &
                (dataframe['high' + tf_suffix] >= resistance) &
                self.closed_below_middle_candle(dataframe)
        )

    @staticmethod
    def green_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] > dataframe['open' + tf_suffix])
        )

    @staticmethod
    def red_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] < dataframe['open' + tf_suffix])
        )

    @staticmethod
    def closed_above_prev_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] > dataframe['close' + tf_suffix].shift(1))
        )

    @staticmethod
    def closed_below_prev_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] < dataframe['close' + tf_suffix].shift(1))
        )

    @staticmethod
    def closed_above_middle_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] > (dataframe['high' + tf_suffix] - ((dataframe['high' + tf_suffix] - dataframe['low' + tf_suffix]) / 2)))
        )

    @staticmethod
    def closed_below_middle_candle(dataframe: DataFrame, tf_suffix: str = ''):
        return (
            (dataframe['close' + tf_suffix] < (dataframe['high' + tf_suffix] - ((dataframe['high' + tf_suffix] - dataframe['low' + tf_suffix]) / 2)))
        )