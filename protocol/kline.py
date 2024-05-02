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

    @classmethod
    def from_api(cls, data):
        return cls(float(data[1]), float(data[2]), float(data[3]), float(data[4]))
