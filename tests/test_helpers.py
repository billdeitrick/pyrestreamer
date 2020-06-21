import unittest
import datetime
import os

import pytest
import pytz
from freezegun import freeze_time

from pyrestreamer.helpers import Service, load_services, list_has_active_service, ReStreamer

class TestService():
    """Verify Service class function as expected."""

    def test_is_active(self):
        """Verify service is correctly reported active."""

        service = Service(6, 18, 00, 2, 90, pytz.timezone('US/Eastern'))

        # Inactive
        #region
        with freeze_time("2020-01-04 17:57:59", tz_offset=5):
            assert False == service.is_active()

        with freeze_time("2020-01-04 19:33:00", tz_offset=5):
            assert False == service.is_active()

        with freeze_time("2020-01-04 16:00:00", tz_offset=5):
            assert False == service.is_active()

        with freeze_time("2020-01-04 20:00:00", tz_offset=5):
            assert False == service.is_active()

        with freeze_time("2020-01-05 10:45:00", tz_offset=5):
            assert False == service.is_active()
        #endregion

        # Active
        #region
        with freeze_time("2020-01-04 17:58:00", tz_offset=5):
            assert True == service.is_active()

        with freeze_time("2020-01-04 18:00:00", tz_offset=5):
            assert True == service.is_active()

        with freeze_time("2020-01-04 19:00:00", tz_offset=5):
            assert True == service.is_active()

        with freeze_time("2020-01-04 19:30:00", tz_offset=5):
            assert True == service.is_active()

        with freeze_time("2020-01-04 19:32:00", tz_offset=5):
            assert True == service.is_active()
        #endregion

    @freeze_time("2020-01-04 19:32:00", tz_offset=5)
    def test_date_for_dow(self):
        """Test getting the next date for a given day of the week."""

        # Test without crossing date boundary
        service = Service(6, 18, 00, 2, 90, pytz.timezone('US/Eastern'))
        now = datetime.datetime.now(pytz.timezone('US/Eastern'))

        assert datetime.date(2020, 1, 6) == service._date_for_dow(now, 1)
        assert datetime.date(2020, 1, 7) == service._date_for_dow(now, 2)
        assert datetime.date(2020, 1, 8) == service._date_for_dow(now, 3)
        assert datetime.date(2020, 1, 9) == service._date_for_dow(now, 4)
        assert datetime.date(2020, 1, 10) == service._date_for_dow(now, 5)
        assert datetime.date(2020, 1, 4) == service._date_for_dow(now, 6)
        assert datetime.date(2020, 1, 5) == service._date_for_dow(now, 7)

    def test_eq(self):
        """Test function checking equality of two Service objects."""

        s1 = Service(7, 9, 0, 2, 90, pytz.timezone('US/Eastern'))
        s2 = Service(7, 9, 0, 2, 90, pytz.timezone('US/Eastern'))
        s3 = Service(7, 10, 45, 2, 90, pytz.timezone('US/Eastern'))

        assert s1 == s2
        assert s1 != s3

class TestHelperFunctions():
    """Verify load services function is working as expected."""

    def test_load_service(self):
        """Test loading services from string vars."""

        service_string = "6|18:00|88,7|09:00|88,7|10:45|88,7|18:00|88"

        services = load_services(service_string, 2, 'US/Eastern')

        expected_services = [

            Service(
                6,
                18,
                0,
                2,
                88,
                pytz.timezone('US/Eastern')
            ),

            Service(
                7,
                9,
                0,
                2,
                88,
                pytz.timezone('US/Eastern')
            ),

            Service(
                7,
                10,
                45,
                2,
                88,
                pytz.timezone('US/Eastern')
            ),

            Service(
                7,
                18,
                00,
                2,
                88,
                pytz.timezone('US/Eastern')
            ),

        ]

        assert expected_services == services

    @pytest.mark.freeze_time("2020-01-04 18:00:00", tz_offset=5)
    def test_list_has_active_service(self):
        """Test whether or not a give list or service contains an active service."""

        s1 = Service(
            6,
            18,
            0,
            2,
            88,
            pytz.timezone('US/Eastern')
        )

        s2 = Service(
            7,
            9,
            0,
            2,
            88,
            pytz.timezone('US/Eastern')
        )

        s3 = Service(
            7,
            10,
            45,
            88,
            2,
            pytz.timezone('US/Eastern')
        )


        l1 = [s1, s2, s3]
        l2 = [s2, s3]

        assert True == list_has_active_service(l1)

        assert False == list_has_active_service(l2)

class TestRestreamer():
    """Test various functions of the restreamer class."""

    def test_parse_ffmpeg_output(self):
        """Test the ffmpeg output parsing function."""

        fn_input = [
            "[cli][info] Available streams: 144p (worst), 270p, 360p, 540p, 720p, 1080p (best)",
            "[cli][info] Opening stream: 1080p (dash)",
            "Input #0, matroska,webm, from 'pipe:':",
            "Metadata:",
            "COMPATIBLE_BRANDS: iso6mp41",
            "MAJOR_BRAND     : iso5",
            "MINOR_VERSION   : 512",
            "ENCODER         : Lavf58.20.100",
            "Duration: N/A, start: 264.256000, bitrate: N/A",
            "bitrate= 715.7kbits/s",
            "total_size=45802",
            "out_time_us=512000",
            "out_time_ms=512000",
        ]

        exp_output = (
            [
                "[cli][info] Available streams: 144p (worst), 270p, 360p, 540p, 720p, 1080p (best)",
                "[cli][info] Opening stream: 1080p (dash)",
                "Input #0, matroska,webm, from 'pipe:':",
                "Metadata:",
                "COMPATIBLE_BRANDS: iso6mp41",
                "MAJOR_BRAND     : iso5",
                "MINOR_VERSION   : 512",
                "ENCODER         : Lavf58.20.100",
                "Duration: N/A, start: 264.256000, bitrate: N/A",
            ],
            {
                'bitrate': '715.7kbits/s',
                'total_size': '45802',
                'out_time_us': '512000',
                'out_time_ms': '512000',
            }
        )

        assert exp_output == ReStreamer.parse_ffmpeg_output(fn_input)

    def test_parse_ffmpeg_output_unexpected(self):
        """Test the ffmpeg output parsing function."""

        fn_input = [
            "[cli][info] Available streams: 144p (worst), 270p, 360p, 540p, 720p, 1080p (best)",
            "[cli][info] Opening stream: 1080p (dash)",
            "Input #0, matroska,webm, from 'pipe:':",
            "unexpected=",
            "=unexpected",
            "unexpected=unexpected=unexpected",
            "out_time_ms=512000",
        ]

        exp_output = (
            [
                "[cli][info] Available streams: 144p (worst), 270p, 360p, 540p, 720p, 1080p (best)",
                "[cli][info] Opening stream: 1080p (dash)",
                "Input #0, matroska,webm, from 'pipe:':",
                "unexpected=",
                "=unexpected",
                "unexpected=unexpected=unexpected",
            ],
            {
                'out_time_ms': '512000',
            }
        )

        assert exp_output == ReStreamer.parse_ffmpeg_output(fn_input)