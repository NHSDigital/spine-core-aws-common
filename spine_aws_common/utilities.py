"""
Common utilities used in lambda application classes
"""
from datetime import datetime, timedelta


class StopWatch:
    """
    Class to support timing points in the code
    """

    def __init__(self):
        self.start_time = None

    def start_the_clock(self):
        """
        Start the clock
        """
        self.start_time = datetime.now()

    def stop_the_clock(self):
        """
        Stop the clock automatically resets and restarts the clock
        Use split the clock if want to keep a parent timer running
        """
        step_duration_seconds = self.split_the_clock()
        self.start_time = datetime.now()
        return step_duration_seconds

    def split_the_clock(self):
        """
        Split the clock, keeping the parent timer running
        """
        step_duration = datetime.now() - self.start_time
        step_duration_seconds = round(
            float(step_duration.seconds) + float(step_duration.microseconds) / 1000000,
            3,
        )
        if step_duration_seconds < 0.0005:
            step_duration_seconds = 0.000

        return step_duration_seconds

    def reset_the_clock(self, seed_time):
        """
        Reset the clock assuming a new seed time, to be used when time has
        been passed as message by string Assumed format of time is:
        %Y%m%dT%H%M%S.%3N
        """
        date_split = seed_time.split(".")
        self.start_time = datetime.strptime(date_split[0], "%Y%m%dT%H%M%S")
        self.start_time += timedelta(milliseconds=int(date_split[1]))


def human_readable_bytes(num):
    """Size in human readable format for logs"""
    if abs(num) < 1024:
        return f"{num}B"
    num /= 1024.0
    for unit in ["Ki", "Mi", "Gi", "Ti"]:
        if abs(num) < 1024.0:
            return f"{num:.1f}{unit}B"
        num /= 1024.0
    return f"{num:.1f}PiB"
