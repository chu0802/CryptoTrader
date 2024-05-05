from collections import deque
from dataclasses import dataclass

from sortedcontainers import SortedList

from protocol.datetime import FormattedDateTime


@dataclass
class TimeValue:
    time: FormattedDateTime
    value: float

    def __init__(self, time, value):
        self.time = time
        self.value = value

    def __le__(self, other: "TimeValue"):
        return self.value <= other.value

    def __ge__(self, other: "TimeValue"):
        return self.value >= other.value

    def __eq__(self, other: "TimeValue"):
        return self.value == other.value

    def __lt__(self, other: "TimeValue"):
        return self.value < other.value

    def __gt__(self, other: "TimeValue"):
        return self.value > other.value

    def __ne__(self, other: "TimeValue"):
        return self.value != other.value

    def __hash__(self):
        return hash(self.time)

    def __sub__(self, other: "TimeValue"):
        return TimeValue(self.time, self.value - other.value)


class TimeValueQueue:
    def __init__(self, max_size):
        self.max_size = max_size
        self.sorted_values = SortedList()
        self.time_queue = deque()
        self.time_to_value = {}

    def append(self, time_value: TimeValue) -> None:
        # Check for max size and remove oldest entry if needed
        if len(self.time_queue) >= self.max_size:
            oldest_time = self.time_queue.popleft()
            oldest_value = self.time_to_value.pop(oldest_time)
            self.sorted_values.remove(oldest_value)

        # Insert new entry
        self.time_queue.append(time_value.time)
        self.time_to_value[time_value.time] = time_value
        self.sorted_values.add(time_value)

    def min(self) -> TimeValue:
        return self.sorted_values[0] if self.sorted_values else None

    def max(self) -> TimeValue:
        return self.sorted_values[-1] if self.sorted_values else None
