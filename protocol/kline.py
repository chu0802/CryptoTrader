from dataclasses import dataclass


@dataclass
class KLine:
    open: float
    high: float
    low: float
    close: float

    def to_dict(self):
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
