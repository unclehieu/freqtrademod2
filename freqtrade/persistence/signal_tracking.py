from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Query

from freqtrade.constants import DATETIME_PRINT_FORMAT
from freqtrade.persistence.base import _DECL_BASE


class SignalTracking(_DECL_BASE):
    """
    Signal database model.
    """
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True)

    pair = Column(String(25), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=False)
    signal = Column(String(10), nullable=False, index=False)
    strategy = Column(String(255), nullable=True)
    created_time = Column(DateTime, nullable=False)
    created_date = Column(Integer, nullable=False, index=True)

    def __repr__(self):
        return (f'SignalTracking(id={self.id}, pair={self.pair}, timeframe={self.timeframe}, '
                f'signal={self.signal}, date={self.created_date})')

    @staticmethod
    def query_signals(pair: Optional[str], timeframe: Optional[str], signal: Optional[str], strategy: Optional[str],
                      date: int) -> Query:
        """
        Get all signals for this pair by date
        """

        filters = [SignalTracking.created_date == date, ]
        if pair:
            filters.append(SignalTracking.pair == pair)

        if timeframe:
            filters.append(SignalTracking.timeframe == timeframe)

        if signal:
            filters.append(SignalTracking.signal == signal)

        if strategy:
            filters.append(SignalTracking.strategy == strategy)

        return SignalTracking.query.filter(
            *filters
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'pair': self.pair,
            'created_time': self.created_time.strftime(DATETIME_PRINT_FORMAT),
            'timeframe': self.timeframe,
            'signal': self.signal,
            'strategy': self.strategy
        }