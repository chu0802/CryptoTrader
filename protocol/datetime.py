import json
from datetime import datetime, timedelta
from typing import Union

import pytz


class FormattedDateTime:
    def __init__(
        self,
        time: Union[str, int, datetime],
        tz: str = "Asia/Taipei",
        datetime_format: str = "%Y-%m-%d %H:%M:%S",
    ):
        if isinstance(time, str):
            parsed_time = datetime.strptime(time, datetime_format)
            self.time = parsed_time.astimezone(pytz.timezone(tz))
        elif isinstance(time, int):
            self.time = datetime.fromtimestamp(time, tz=pytz.timezone(tz))
        elif isinstance(time, datetime):
            self.time = time.astimezone(pytz.timezone(tz))
        else:
            raise ValueError("Invalid datetime type")

        self.tz = tz
        self.datetime_format = datetime_format

    def __add__(self, other: Union["FormattedDateTime", datetime, int]):
        if isinstance(other, int):
            return FormattedDateTime(self.time + timedelta(seconds=other), tz=self.tz)
        elif isinstance(other, datetime):
            return FormattedDateTime(self.time + other, tz=self.tz)
        elif isinstance(other, FormattedDateTime):
            return FormattedDateTime(self.time + other.time, tz=self.tz)
        else:
            raise ValueError("Invalid datetime type")

    def __sub__(self, other: Union["FormattedDateTime", datetime, int]):
        if isinstance(other, int):
            return FormattedDateTime(self.time - timedelta(seconds=other), tz=self.tz)
        elif isinstance(other, datetime):
            return self.time - other
        elif isinstance(other, FormattedDateTime):
            return self.time - other.time
        else:
            raise ValueError("Invalid datetime type")

    def __gt__(self, other: "FormattedDateTime"):
        return self.time > other.time

    def __lt__(self, other: "FormattedDateTime"):
        return self.time < other.time

    def __eq__(self, other: "FormattedDateTime"):
        return self.time == other.time

    def __ge__(self, other: "FormattedDateTime"):
        return self.time >= other.time

    def __le__(self, other: "FormattedDateTime"):
        return self.time <= other.time

    def __ne__(self, other: "FormattedDateTime") -> bool:
        return self.time != other.time

    def __hash__(self):
        return hash(self.time)

    def __repr__(self):
        return self.time.__repr__()

    def __str__(self):
        return self.time.__str__()

    @property
    def timestamp(self):
        return int(self.time.timestamp())

    @property
    def string(self):
        return self.time.strftime(self.datetime_format)

    @property
    def datetime(self):
        return self.time


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
