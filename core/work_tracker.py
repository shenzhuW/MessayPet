# core/work_tracker.py
"""工作记录器 - 跟踪前台窗口使用时间"""
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from PySide6.QtCore import QTimer

from core.event_bus import EventType


class WindowRecord:
    """单条窗口记录"""
    def __init__(self, title: str, start_time: float, end_time: float = None, group_key: str = ""):
        self.title = title
        self.start_time = start_time
        self.end_time = end_time or time.time()
        self.group_key = group_key

    @property
    def duration(self) -> int:
        return int(self.end_time - self.start_time)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "group_key": self.group_key,
            "start": int(self.start_time),
            "end": int(self.end_time),
            "duration": self.duration
        }

    @staticmethod
    def from_dict(data: dict):
        return WindowRecord(
            title=data["title"],
            start_time=data["start"],
            end_time=data.get("end", data["start"] + data["duration"]),
            group_key=data.get("group_key", "")
        )


class WorkTracker:
    """工作记录器 - 监控并记录前台窗口使用时间"""

    # 数据保留天数
    RETENTION_DAYS = 30

    def __init__(self, config_manager, event_bus=None):
        self.config_manager = config_manager
        self.event_bus = event_bus

        # 当前记录状态
        self._current_record: Optional[WindowRecord] = None
        self._today_records: List[WindowRecord] = []

        # 是否正在运行
        self._is_running = False

        # 订阅 token
        self._subscribe_token: Optional[str] = None

        # 定时保存（5分钟）
        self._save_timer = QTimer()
        self._save_timer.timeout.connect(self._save_today_records)
        self._save_timer.start(5 * 60 * 1000)  # 5分钟

    def start(self):
        """开始监控"""
        if self._is_running:
            return

        self._is_running = True

        # 订阅窗口变化事件（复用 WindowMonitor 的事件）
        if self.event_bus:
            self._subscribe_token = self.event_bus.subscribe(
                EventType.WINDOW_CHANGED,
                self._on_window_changed
            )

        # 加载今日记录
        self._load_today_records()

    def stop(self):
        """停止监控并保存记录"""
        if not self._is_running:
            return

        self._is_running = False

        # 取消订阅
        if self.event_bus and self._subscribe_token:
            self.event_bus.unsubscribe(EventType.WINDOW_CHANGED, self._subscribe_token)
            self._subscribe_token = None

        # 结束当前记录
        if self._current_record:
            self._current_record.end_time = time.time()
            self._today_records.append(self._current_record)
            self._current_record = None

        # 保存记录
        self._save_today_records()

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def _on_window_changed(self, data: dict):
        """窗口变化事件回调 - 实时捕获"""
        # 优先使用 display_name（有项目名则显示项目-窗口名）
        display_name = data.get("display_name", "")
        title = data.get("title", "")
        group_key = data.get("group_key", "")
        if not display_name and not title:
            return

        now = time.time()

        # 结束上一条记录
        if self._current_record:
            self._current_record.end_time = now
            self._today_records.append(self._current_record)

        # 使用 display_name 记录（包含项目信息）
        record_title = display_name if display_name else title
        self._current_record = WindowRecord(
            title=record_title,
            start_time=now,
            group_key=group_key
        )

    def _load_today_records(self):
        """加载今日记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        all_records = self.config_manager.load_work_records()
        self._today_records = []
        for record_data in all_records.get(today, []):
            self._today_records.append(WindowRecord.from_dict(record_data))

    def _save_today_records(self):
        """保存今日记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        all_records = self.config_manager.load_work_records()

        # 清理超过30天的数据
        cutoff_date = (datetime.now() - timedelta(days=self.RETENTION_DAYS)).strftime("%Y-%m-%d")
        all_records = {k: v for k, v in all_records.items() if k >= cutoff_date}

        # 更新今日记录
        records_to_save = [r.to_dict() for r in self._today_records]
        all_records[today] = records_to_save

        self.config_manager.save_work_records(all_records)

    def get_records(self, date: datetime = None) -> List[Dict[str, Any]]:
        """获取指定日期的记录"""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        all_records = self.config_manager.load_work_records()
        return all_records.get(date_str, [])

    def get_weekly_records(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取本周记录（周一到周日）"""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        all_records = self.config_manager.load_work_records()
        weekly = {}

        for i in range(7):
            day = monday + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            weekly[date_str] = all_records.get(date_str, [])

        return weekly

    def get_monthly_records(self, year: int = None, month: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取指定月份的记录"""
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month

        all_records = self.config_manager.load_work_records()
        monthly = {}

        for date_str, records in all_records.items():
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                if d.year == year and d.month == month:
                    monthly[date_str] = records
            except ValueError:
                continue

        return monthly