from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from hadouken_zone.scheduler import Scheduler
from hadouken_zone.storage import StateStore

TZ = ZoneInfo("Europe/Madrid")


class FakePipeline:
    def __init__(self):
        self.calls = []
        self.still_active = None

    def send_good_morning(self, day):
        self.calls.append(("good_morning", day.isoformat()))

    def run_scan(self):
        self.calls.append(("scan",))
        return 0


class Clock:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now


def build(settings, tmp_path, start):
    clock = Clock(start)
    pipeline = FakePipeline()
    sched = Scheduler(settings, pipeline, StateStore(tmp_path / "state.json"), clock=clock, sleep=lambda s: None)
    return sched, pipeline, clock


def test_nothing_before_good_morning(settings, tmp_path):
    sched, pipe, _ = build(settings, tmp_path, datetime(2026, 11, 2, 8, 59, tzinfo=TZ))
    assert sched.tick() == []
    assert pipe.calls == []


def test_good_morning_then_scan_every_30_minutes(settings, tmp_path):
    sched, pipe, clock = build(settings, tmp_path, datetime(2026, 11, 2, 9, 0, tzinfo=TZ))
    assert sched.tick() == ["good_morning", "scan"]

    clock.now += timedelta(minutes=10)
    assert sched.tick() == []                       # aún no han pasado 30 min

    clock.now += timedelta(minutes=20)
    assert sched.tick() == ["scan"]                 # 09:30

    clock.now += timedelta(minutes=30)
    assert sched.tick() == ["scan"]                 # 10:00
    assert pipe.calls.count(("scan",)) == 3
    assert pipe.calls.count(("good_morning", "2026-11-02")) == 1


def test_good_morning_only_once_per_day_even_after_restart(settings, tmp_path):
    sched, pipe, clock = build(settings, tmp_path, datetime(2026, 11, 2, 9, 5, tzinfo=TZ))
    sched.tick()
    # "reinicio": nuevo planificador con el mismo archivo de estado
    sched2, pipe2, _ = build(settings, tmp_path, datetime(2026, 11, 2, 9, 10, tzinfo=TZ))
    assert "good_morning" not in sched2.tick()


def test_no_good_morning_if_bot_starts_late(settings, tmp_path):
    sched, pipe, _ = build(settings, tmp_path, datetime(2026, 11, 2, 15, 0, tzinfo=TZ))
    assert sched.tick() == ["scan"]


def test_stops_at_night_and_restarts_next_day(settings, tmp_path):
    sched, pipe, clock = build(settings, tmp_path, datetime(2026, 11, 2, 23, 40, tzinfo=TZ))
    assert sched.tick() == []
    clock.now = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
    assert sched.tick() == ["good_morning", "scan"]


def test_pipeline_knows_when_to_stop(settings, tmp_path):
    sched, pipe, clock = build(settings, tmp_path, datetime(2026, 11, 2, 23, 0, tzinfo=TZ))
    assert pipe.still_active() is True
    clock.now = datetime(2026, 11, 2, 23, 31, tzinfo=TZ)
    assert pipe.still_active() is False
