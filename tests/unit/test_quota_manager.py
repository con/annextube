"""Unit tests for YouTube API quota manager."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from annextube.lib.quota_manager import QuotaExceededError, QuotaManager


class TestCalculateNextQuotaReset:
    """Tests for calculate_next_quota_reset method."""

    def test_reset_before_midnight_pst(self):
        """Test calculation when current time is before midnight PST."""
        manager = QuotaManager()

        # 2026-02-07 22:30 UTC = 2026-02-07 14:30 PST
        now = datetime(2026, 2, 7, 22, 30, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-02-08 00:00 PST = 2026-02-08 08:00 UTC
        expected = datetime(2026, 2, 8, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

    def test_reset_after_midnight_pst(self):
        """Test calculation when current time is after midnight PST."""
        manager = QuotaManager()

        # 2026-02-08 09:00 UTC = 2026-02-08 01:00 PST
        now = datetime(2026, 2, 8, 9, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-02-09 00:00 PST = 2026-02-09 08:00 UTC
        expected = datetime(2026, 2, 9, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

    def test_reset_during_pdt(self):
        """Test calculation during Pacific Daylight Time (summer)."""
        manager = QuotaManager()

        # 2026-07-15 20:00 UTC = 2026-07-15 13:00 PDT (UTC-7)
        now = datetime(2026, 7, 15, 20, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-07-16 00:00 PDT = 2026-07-16 07:00 UTC
        expected = datetime(2026, 7, 16, 7, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

    def test_reset_exactly_at_midnight_pst(self):
        """Test calculation when current time is exactly midnight PST."""
        manager = QuotaManager()

        # 2026-02-08 08:00 UTC = 2026-02-08 00:00 PST
        now = datetime(2026, 2, 8, 8, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return next midnight: 2026-02-09 00:00 PST = 2026-02-09 08:00 UTC
        expected = datetime(2026, 2, 9, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

    def test_reset_one_hour_before_midnight(self):
        """Test calculation when quota exceeded at 11 PM PT (only 1 hour wait)."""
        manager = QuotaManager()

        # 2026-02-08 07:00 UTC = 2026-02-07 23:00 PST
        now = datetime(2026, 2, 8, 7, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-02-08 00:00 PST = 2026-02-08 08:00 UTC
        expected = datetime(2026, 2, 8, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

        # Verify only 1 hour wait
        wait_seconds = (next_reset - now).total_seconds()
        assert wait_seconds == 3600  # 1 hour

    def test_reset_one_hour_after_midnight(self):
        """Test calculation when quota exceeded at 1 AM PT (23 hour wait)."""
        manager = QuotaManager()

        # 2026-02-08 09:00 UTC = 2026-02-08 01:00 PST
        now = datetime(2026, 2, 8, 9, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-02-09 00:00 PST = 2026-02-09 08:00 UTC
        expected = datetime(2026, 2, 9, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

        # Verify 23 hour wait
        wait_seconds = (next_reset - now).total_seconds()
        assert wait_seconds == 23 * 3600  # 23 hours

    def test_dst_transition_spring_forward(self):
        """Test calculation around DST transition (spring forward)."""
        manager = QuotaManager()

        # 2026 DST transition: March 8, 2:00 AM PST -> 3:00 AM PDT
        # Before transition: 2026-03-08 09:00 UTC = 2026-03-08 01:00 PST
        now = datetime(2026, 3, 8, 9, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-03-09 00:00 PDT = 2026-03-09 07:00 UTC
        expected = datetime(2026, 3, 9, 7, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected

    def test_dst_transition_fall_back(self):
        """Test calculation around DST transition (fall back)."""
        manager = QuotaManager()

        # 2026 DST transition: November 1, 2:00 AM PDT -> 1:00 AM PST
        # After transition: 2026-11-01 09:00 UTC = 2026-11-01 01:00 PST
        now = datetime(2026, 11, 1, 9, 0, 0, tzinfo=timezone.utc)
        next_reset = manager.calculate_next_quota_reset(now)

        # Should return 2026-11-02 00:00 PST = 2026-11-02 08:00 UTC
        expected = datetime(2026, 11, 2, 8, 0, 0, tzinfo=timezone.utc)
        assert next_reset == expected


class TestFormatDuration:
    """Tests for format_duration method."""

    def test_format_hours_and_minutes(self):
        """Test formatting duration with hours and minutes."""
        manager = QuotaManager()
        assert manager.format_duration(3600) == "1h 0m"
        assert manager.format_duration(5430) == "1h 30m"
        assert manager.format_duration(23 * 3600 + 900) == "23h 15m"

    def test_format_minutes_only(self):
        """Test formatting duration with only minutes."""
        manager = QuotaManager()
        assert manager.format_duration(60) == "1m"
        assert manager.format_duration(1800) == "30m"
        assert manager.format_duration(3540) == "59m"

    def test_format_zero(self):
        """Test formatting zero duration."""
        manager = QuotaManager()
        assert manager.format_duration(0) == "0m"

    def test_format_rounds_down(self):
        """Test that formatting rounds down seconds."""
        manager = QuotaManager()
        assert manager.format_duration(90) == "1m"  # 1m 30s -> rounds to 1m
        assert manager.format_duration(3659) == "1h 0m"  # 1h 0m 59s -> rounds to 1h 0m


class TestSleepWithProgress:
    """Tests for sleep_with_progress method."""

    @patch('time.sleep')
    @patch('time.time')
    def test_sleep_full_duration(self, mock_time, mock_sleep):
        """Test sleeping for full duration without interruption."""
        manager = QuotaManager(check_interval_seconds=10)

        # Simulate realistic time progression
        # Each call to time.time() returns current time, which advances after sleep
        current_time = [100.0]  # Use list for mutability

        def time_side_effect():
            return current_time[0]

        def sleep_side_effect(seconds):
            current_time[0] += seconds

        mock_time.side_effect = time_side_effect
        mock_sleep.side_effect = sleep_side_effect

        manager.sleep_with_progress(30, check_interval=10)

        # Should sleep 3 times (10s each)
        assert mock_sleep.call_count == 3

    @patch('time.sleep')
    @patch('time.time')
    def test_sleep_with_callback_success(self, mock_time, mock_sleep):
        """Test early exit when callback returns True."""
        manager = QuotaManager(check_interval_seconds=10)

        # Simulate realistic time progression
        current_time = [100.0]  # Use list for mutability

        def time_side_effect():
            return current_time[0]

        def sleep_side_effect(seconds):
            current_time[0] += seconds

        mock_time.side_effect = time_side_effect
        mock_sleep.side_effect = sleep_side_effect

        # Callback succeeds on second check
        callback = MagicMock(side_effect=[False, True])

        manager.sleep_with_progress(60, check_interval=10, check_callback=callback)

        # Should only sleep twice (exits early)
        assert mock_sleep.call_count == 2
        assert callback.call_count == 2

    @patch('time.sleep', side_effect=KeyboardInterrupt)
    @patch('time.time', return_value=100)
    def test_sleep_keyboard_interrupt(self, mock_time, mock_sleep):
        """Test that KeyboardInterrupt is propagated."""
        manager = QuotaManager(check_interval_seconds=10)

        with pytest.raises(KeyboardInterrupt):
            manager.sleep_with_progress(30, check_interval=10)


class TestHandleQuotaExceeded:
    """Tests for handle_quota_exceeded method."""

    def test_disabled_raises_immediately(self):
        """Test that disabled quota manager raises immediately."""
        manager = QuotaManager(enabled=False)

        with pytest.raises(QuotaExceededError, match="Quota resets at midnight Pacific Time"):
            manager.handle_quota_exceeded("Test quota error")

    def test_excessive_wait_time_raises(self):
        """Test that excessive wait time raises error."""
        manager = QuotaManager(enabled=True, max_wait_hours=1)

        # Mock time 2 AM PT (22 hours until next reset)
        now = datetime(2026, 2, 8, 10, 0, 0, tzinfo=timezone.utc)
        next_reset = now + timedelta(hours=22)

        with patch('annextube.lib.quota_manager.datetime') as mock_dt:
            mock_dt.now.return_value = now

            with patch.object(manager, 'calculate_next_quota_reset', return_value=next_reset):
                with pytest.raises(QuotaExceededError, match="22.0 hours away"):
                    manager.handle_quota_exceeded("Test quota error")

    @patch.object(QuotaManager, 'sleep_with_progress')
    def test_successful_wait(self, mock_sleep):
        """Test successful wait until quota reset."""
        manager = QuotaManager(enabled=True, max_wait_hours=24)

        # Mock time 11 PM PT (1 hour until reset)
        with patch.object(manager, 'calculate_next_quota_reset') as mock_calc:
            now = datetime(2026, 2, 8, 7, 0, 0, tzinfo=timezone.utc)
            next_reset = datetime(2026, 2, 8, 8, 0, 0, tzinfo=timezone.utc)
            mock_calc.return_value = next_reset

            with patch('annextube.lib.quota_manager.datetime') as mock_dt:
                mock_dt.now.return_value = now

                manager.handle_quota_exceeded("Test quota error")

                # Verify sleep was called with ~1 hour
                mock_sleep.assert_called_once()
                wait_seconds = mock_sleep.call_args[0][0]
                assert 3500 < wait_seconds < 3700  # ~1 hour (allowing for timing variance)

    @patch.object(QuotaManager, 'sleep_with_progress', side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt_propagated(self, mock_sleep):
        """Test that KeyboardInterrupt during wait is propagated."""
        manager = QuotaManager(enabled=True)

        with patch.object(manager, 'calculate_next_quota_reset') as mock_calc:
            now = datetime(2026, 2, 8, 7, 0, 0, tzinfo=timezone.utc)
            next_reset = datetime(2026, 2, 8, 8, 0, 0, tzinfo=timezone.utc)
            mock_calc.return_value = next_reset

            with patch('annextube.lib.quota_manager.datetime') as mock_dt:
                mock_dt.now.return_value = now

                with pytest.raises(KeyboardInterrupt):
                    manager.handle_quota_exceeded("Test quota error")


class TestQuotaManagerConfiguration:
    """Tests for QuotaManager configuration options."""

    def test_default_configuration(self):
        """Test default configuration values."""
        manager = QuotaManager()
        assert manager.enabled is True
        assert manager.max_wait_hours == 48
        assert manager.check_interval_seconds == 1800

    def test_custom_configuration(self):
        """Test custom configuration values."""
        manager = QuotaManager(
            enabled=False,
            max_wait_hours=12,
            check_interval_seconds=600
        )
        assert manager.enabled is False
        assert manager.max_wait_hours == 12
        assert manager.check_interval_seconds == 600
