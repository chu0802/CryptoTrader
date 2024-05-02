import json
from datetime import datetime
from typing import Union

import pytz


class FormattedDateTime:
    def __init__(
        self,
        time: Union[str, int, datetime],
        tz: str = "Asia/Taipei",
        datetime_format: str = "%Y-%m-%d %H:%M:%S",
    ):
        self._ms_timestamp = self.extract_timestamp_from_various_type(
            time, datetime_format, tz
        )
        self._datetime = datetime.fromtimestamp(
            self._ms_timestamp // 1000, tz=pytz.timezone(tz)
        )

        self.datetime_format = datetime_format
        self.tz = tz

    def extract_timestamp_from_various_type(
        self, time: Union[str, int, datetime], datetime_format: str, tz: str
    ):
        if isinstance(time, str):
            parsed_time = datetime.strptime(time, datetime_format)
            return int(parsed_time.astimezone(pytz.timezone(tz)).timestamp()) * 1000
        elif isinstance(time, int):
            if len(str(time)) == 10:
                return time * 1000
            elif len(str(time)) == 13:
                return time
            else:
                raise ValueError("Invalid time range")
        elif isinstance(time, datetime):
            return int(time.astimezone(pytz.timezone(tz)).timestamp()) * 1000
        else:
            raise ValueError("Invalid datetime type")

    def __add__(self, other: Union["FormattedDateTime", datetime, int]):
        if isinstance(other, int):
            return FormattedDateTime(self._ms_timestamp + other * 1000, tz=self.tz)
        elif isinstance(other, datetime):
            return FormattedDateTime(self._datetime + other, tz=self.tz)
        elif isinstance(other, FormattedDateTime):
            return FormattedDateTime(
                self._ms_timestamp + other._ms_timestamp, tz=self.tz
            )
        else:
            raise ValueError("Invalid datetime type")

    def __sub__(self, other: Union["FormattedDateTime", datetime, int]):
        if isinstance(other, int):
            return FormattedDateTime(self._ms_timestamp - other * 1000, tz=self.tz)
        elif isinstance(other, datetime):
            return (self._datetime - other).total_seconds()
        elif isinstance(other, FormattedDateTime):
            return (self._ms_timestamp - other._ms_timestamp) / 1000
        else:
            raise ValueError("Invalid datetime type")

    def __gt__(self, other: "FormattedDateTime"):
        return self._ms_timestamp > other._ms_timestamp

    def __lt__(self, other: "FormattedDateTime"):
        return self._ms_timestamp < other._ms_timestamp

    def __eq__(self, other: "FormattedDateTime"):
        return self._ms_timestamp == other._ms_timestamp

    def __ge__(self, other: "FormattedDateTime"):
        return self._ms_timestamp >= other._ms_timestamp

    def __le__(self, other: "FormattedDateTime"):
        return self._ms_timestamp <= other._ms_timestamp

    def __ne__(self, other: "FormattedDateTime") -> bool:
        return self._ms_timestamp != other._ms_timestamp

    def __hash__(self):
        return hash(self._ms_timestamp)

    def __repr__(self):
        return self._datetime.__repr__()

    def __str__(self):
        return self._datetime.__str__()

    @property
    def timestamp(self):
        return int(self._ms_timestamp // 1000)

    @property
    def ms_timestamp(self):
        return int(self._ms_timestamp)

    @property
    def string(self):
        return self._datetime.strftime(self.datetime_format)

    @property
    def datetime(self):
        return self._datetime


class DatetimeJsonEncoder(json.JSONEncoder):
    def preprocess_date(self, o):
        return o.string if isinstance(o, FormattedDateTime) else o

    def default(self, z):
        if isinstance(z, FormattedDateTime):
            return z.string
        else:
            return json.JSONEncoder().default(z)

    def iterencode(self, o, **kwargs):
        if isinstance(o, dict):
            o = {self.preprocess_date(k): v for k, v in o.items()}
        elif isinstance(o, list):
            o = [self.preprocess_date(v) for v in o]
        return super().iterencode(o, **kwargs)


class DateTimeJsonDecoder:
    def __init__(self, datetime_format="%Y-%m-%d %H:%M:%S"):
        self.datetime_format = datetime_format

    def is_datetime_string(self, str):
        try:
            datetime.strptime(str, self.datetime_format)
            return True
        except ValueError:
            return False

    def to_datetime(self, o):
        return FormattedDateTime(o) if self.is_datetime_string(o) else o

    def __call__(self, obj):
        if isinstance(obj, dict):
            return {self.to_datetime(k): v for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.to_datetime(v) for v in obj]
        else:
            return self.to_datetime(obj)
