import os
import logging
import logging.config
import datetime
import hashlib

import yaml
import freezegun

from pyrestreamer.helpers import \
    load_services, list_has_active_service, StreamingState, ReStreamer

log = logging.getLogger("pyrestreamer")
with open(str(os.getenv('LOG_CONFIG')), 'r') as fh:
    logging.config.dictConfig(yaml.load(fh, Loader=yaml.FullLoader))

log.info('PyRestreamer app is initializing.')

DEBUG_MODE = os.getenv("DEBUG")
log.info(f'Debug mode: {DEBUG_MODE}')

DEBUG_DATETIME = os.getenv("DEBUG_DATETIME")
log.info(f'Debug datetime: {DEBUG_DATETIME}')

DEBUG_TZ_OFFSET = os.getenv("DEBUG_TZ_OFFSET")
log.info(f'Debug TZ offset: {DEBUG_TZ_OFFSET}')

SERVICE_TIMES = os.getenv("SERVICE_TIMES")
log.info(f'Service times: {SERVICE_TIMES}')

INPUT_URL = os.getenv("INPUT_URL")
log.info(f"Input URL SHA256: {hashlib.sha256(str(INPUT_URL).encode('UTF-8')).hexdigest()}")

FFMPEG_PARAMS = os.getenv("FFMPEG_PARAMS")
log.info(f"FFMPEG params SHA256:{hashlib.sha256(str(FFMPEG_PARAMS).encode('UTF-8')).hexdigest()}")

SERVICE_BUFFER = os.getenv("SERVICE_BUFFER")
log.info(f'Service buffer: {SERVICE_BUFFER}')

PYTZ_TIMEZONE = os.getenv("PYTZ_TIMEZONE")
log.info(f'Timezone: {PYTZ_TIMEZONE}')

SLEEP_TIME = os.getenv("SLEEP_TIME")
log.info(f'Sleep Time: {SLEEP_TIME}')

LOG_CONFIG = os.getenv("LOG_CONFIG")
log.info(f'Logging Path: {LOG_CONFIG}')

def run():
    rs = ReStreamer(SERVICE_TIMES, SERVICE_BUFFER, SLEEP_TIME, PYTZ_TIMEZONE, INPUT_URL, FFMPEG_PARAMS)

    if str(os.getenv('DEBUG')).lower() == 'true':
        with freezegun.freeze_time(DEBUG_DATETIME, tz_offset=int(DEBUG_TZ_OFFSET)):
            rs.event_loop()
    else:
        try:
            rs.event_loop()
        except Exception as e:
            log.critical(f'Fatal error running app: {e}')

if __name__ == '__main__':
    run()