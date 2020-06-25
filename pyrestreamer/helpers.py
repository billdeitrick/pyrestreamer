"""Helper classes."""

import os
import datetime
import logging
import time
import threading
import subprocess
import sys
import queue
import signal

from typing import List, Tuple, Dict
from enum import Enum

import pytz
import pytz.tzinfo
import pushover

log = logging.getLogger("pyrestreamer")

class Service():
    """Represents a church service or other event."""

    def __init__(self, dow: int, hr: int, min: int, buf: int, dur:int , tz: pytz.tzinfo):
        """
        Args:
            dow (int): Day of the week on which the service occurs. Monday is day 1.
            hr (int): The hour when the service starts.
            min (int): The minute the service starts.
            buf (int): The number of minutes before and after the service content should be active.
            dur (int): The duration of the service (minutes).
            tz (tzinfo): The PYTZ timezone object for the local timezone.
        """

        self.dow = dow
        self.hr = hr
        self.min = min
        self.buf = buf
        self.dur = dur
        self.tz = tz

    def is_active(self):
        """Is this service active now?
        
        Note:
            This currently does not support services which cross date
            boundaries, such as a service that starts at 11:00 pm on
            one day and finishes at 12:30 pm the next.

        Returns:
            (bool): True if service is active now, false if it is not.
        """

        now = datetime.datetime.now(self.tz)
        start_date = self._date_for_dow(now, self.dow)
        start_datetime = datetime.datetime(
            start_date.year,
            start_date.month,
            start_date.day,
            self.hr,
            self.min
        )
        start_datetime = self.tz.localize(start_datetime)
        buffered_start_datetime = start_datetime - datetime.timedelta(minutes=self.buf)
        buffered_end_datetime = start_datetime + datetime.timedelta(minutes=self.dur + self.buf)

        return buffered_start_datetime <= now <= buffered_end_datetime

    def _date_for_dow(self, check_date, dow):
        """Get the date corresponding to a given day of the week (service time aware).

        Args:
            (datetime.date): Date or datetime object corresponding to the current date.
            (int): The day of the week to find.
        
        Returns:
            (datetime.date): The next date corresponding to the given day of the week.
        """

        # Find the occurrence of next day of week
        while True:
            if check_date.isoweekday() == dow:
                return check_date.date()
            
            check_date += datetime.timedelta(days=1)

    def __eq__(self, other):
        return all([
            self.dow == other.dow,
            self.hr == other.hr,
            self.min == other.min,
            self.buf == other.buf,
            self.dur == other.dur,
            self.tz == other.tz
        ])

    def __str__(self):

        return f'<Service: DOW={self.dow}, HR={self.hr}, MIN={self.min}, BUF={self.buf}, DUR={self.dur}, TZ={self.tz}>'

class PushoverHandler(logging.Handler):
    """Emit logs directly to pushover."""

    def __init__(self, user_key, api_token, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.client = pushover.Client(user_key, api_token=api_token)

    def emit(self, record):
        log_entry = self.format(record)

        return self.client.send_message(log_entry, 'PyReStreamer')

class StreamingState(Enum):
    """Enum for possible streaming states."""

    IDLE = 0 #pylint: disable=unused-variable
    STREAMING = 1 #pylint: disable=unused-variable

class ReStreamer():
    def __init__(self, service_times: str, service_buffer: int, sleep_time: int, pytz_timezone: str, input_url: str, ffmpeg_params: str):
        self.service_times = service_times
        self.service_buffer = service_buffer
        self.sleep_time = sleep_time
        self.pytz_timezone = pytz_timezone
        self.input_url = input_url
        self.ffmpeg_params = ffmpeg_params

        self.services = load_services(self.service_times, int(self.service_buffer), self.pytz_timezone)

    @classmethod
    def output_reader(cls, proc: subprocess.Popen, queue: queue.Queue):
        for line in iter(proc.stdout.readline, b''):
            queue.put(line.decode('utf-8'))

    def event_loop(self):
        """The main PyReStreamer event loop."""

        current_state = StreamingState.IDLE

        comm_queue: queue.Queue = None
        reader_thread: threading.Thread = None
        proc: subprocess.Popen = None
        had_status_out: bool = None
        last_ts: int = 0
        ts_unchanged_count: int = 0
        no_status_out_intervals: int = 0

        log.warning("PyRestreamer has begun monitoring for active events.")

        while True:
            log.debug('Main loop start.')

            expected_state = StreamingState.STREAMING if list_has_active_service(self.services) else StreamingState.IDLE

            if expected_state is not current_state:
                log.info(f"We need to transition from {current_state} to {expected_state}")

                if current_state is StreamingState.IDLE:
                    log.debug("Starting streaming.")

                    proc = subprocess.Popen(
                        f"streamlink {self.input_url} best -O| ffmpeg -progress - -nostats -hide_banner -re -i - {self.ffmpeg_params}",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        preexec_fn=os.setsid
                    )

                    comm_queue = queue.Queue()
                    reader_thread = threading.Thread(target=ReStreamer.output_reader, args=(proc, comm_queue))
                    reader_thread.start()

                    current_state = StreamingState.STREAMING

                    log.warning("PyRestreamer has started streaming.")

                elif current_state is StreamingState.STREAMING:
                    log.debug("Service ended. We should stop streaming.")

                    # end process group for shell running ffmpeg
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

                    # make sure we gave ffmpeg enough time to quit
                    time.sleep(2)

                    # kill output reader thread
                    reader_thread.join()

                    if proc.poll() is None:
                        log.critical("Did not exit streaming state as expected (ffmpeg still running?); exiting to force container restart.")
                        sys.exit(1)

                    # Reset event loop loop variables
                    comm_queue = None
                    reader_thread = None
                    proc = None
                    had_status_out = False
                    last_ts = 0
                    ts_unchanged_count = 0
                    no_status_out_intervals = 0

                    current_state = StreamingState.IDLE

                    log.warning("PyRestreamer has stopped streaming.")

            elif current_state is StreamingState.STREAMING:
                log.debug("We are currently streaming. Checking for new output to verify state.")

                if proc.poll():
                    log.critical("ffmpeg has exited unexpectedly; exiting to force container restart.")
                    sys.exit(1)

                lines = []

                while True:
                    try:
                        lines.append(str(comm_queue.get(block=False)).strip())
                    except queue.Empty:
                        break

                standard_out, status_out = ReStreamer.parse_ffmpeg_output(lines)

                if had_status_out and standard_out:
                    segment_timeouts = [line for line in standard_out if line.startswith('[stream.dash][error] Failed to open segment')]

                    if segment_timeouts:
                        log.info(f"Segment timeouts: {'##'.join(segment_timeouts)}")

                    if [line for line in standard_out if line.startswith('[stream.ffmpegmux][error] Pipe copy aborted:')]:
                        log.critical(f"Pipe died. Forcing container restart: {'##'.join(standard_out)}")
                        sys.exit(1)

                    standard_out = [line for line in standard_out if not line.startswith('[stream.dash][error] Failed to open segment')]

                    if standard_out:
                        log.warning(f"Unexpected output from ffmpeg proc: {'##'.join(standard_out)}")

                elif standard_out:
                    log.info(f"FFMPEG proc output: {'##'.join(standard_out)}")

                if 'total_size' in status_out:
                    had_status_out = True
                    total_size = int(status_out['total_size'])
                    
                    log.debug(f"Total output size: {total_size}")

                    if total_size > last_ts:
                        last_ts = total_size
                        ts_unchanged_count = 0
                    else:
                        ts_unchanged_count += 1

                if last_ts == 0 and not had_status_out:
                    no_status_out_intervals += 1

                if ts_unchanged_count == 3 or no_status_out_intervals == 3:
                    log.critical("Ffmpeg seems to be stuck; output size not increasing or no status output. Forcing container restart.")
                    sys.exit(1)

            log.debug(f"Main loop end. Sleep for {self.sleep_time} seconds.")

            time.sleep(int(self.sleep_time))

    @classmethod
    def parse_ffmpeg_output(cls, ffmpeg_output: List[str]) -> Tuple[List[str], Dict[str, str]]:
        """Parse ffmpeg output.

        Splits output into a list of standard outputs and status outputs. For status outputs,
        there can be multiples of the same key depending on polling intervals. This function
        will return only the most recent status output for a given key.

        Args:
            ffmpeg_output (List[int]): List of lines from ffmpeg output.

        Returns:
            Tuple(List[Str], Dict): List of standard outputs, dict of status outputs.
        """

        standard_output = []
        status_output = {}

        for row in ffmpeg_output:
            if "=" in row:
                split = [item for item in row.split('=') if len(item) > 0]

                if len(split) == 2:
                    status_output[split[0].strip()] = split[1].strip()
                else:
                    standard_output.append(row)
            else:
                standard_output.append(row)

        return standard_output, status_output

def list_has_active_service(services: List[Service]) -> bool:
    """Check whether or not we have a currently active service.

    Args:
        list[Service]: A list of service objects.

    Returns:
        bool: True if we have an active service, false if we do not.
    """

    return any(service.is_active() for service in services)

def load_services(services_string, service_buffer, timezone):
    """Return array of service objects from environment variable.
    
    Args:
        services_string (str): String representing service times.
        service_buffer (int): Buffer time to start streaming before service.
        timezone (str): The PYTZ-compatible timezone string.

    Returns:
        [Service]: Array of service objects.
    """

    services_string = services_string.split(',')

    service_objs = []

    for service in services_string:
        split = service.split('|')
        
        service_objs.append(
            Service(
                int(split[0]),
                int(split[1].split(':')[0]),
                int(split[1].split(':')[1]),
                int(service_buffer),
                int(split[2]),
                pytz.timezone(timezone)
            )
        )

    return service_objs
