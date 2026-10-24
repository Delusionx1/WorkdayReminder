#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作日提醒器 —— 中国大陆法定节假日 / 调休 / 周末「别联系客户」提醒

界面
  * 屏幕右上角一个半透明悬浮小窗，显示「现在能不能联系客户」
  * 左键拖动可移动位置；双击打开设置；右键菜单
  * 系统托盘图标（颜色随状态变化）用于弹出提醒和退出

功能
  * 按北京时间判断：工作日 / 周末 / 法定节假日 / 调休上班日，并结合工作时间、午休
  * 节前最后一个工作日下午提醒收尾；调休上班日、假期结束第一天早上提醒
  * 自定义日期（年假、客户公司特殊安排）
  * 内置 2025、2026 年国务院放假安排；联网时自动从 holiday-cn 获取后续年份
  * 开机自启（Windows 注册表 / macOS LaunchAgent / Linux autostart），打包后同样可用
  * 单实例：重复启动只会打开已运行实例的设置

依赖:  pip install -r requirements.txt
运行:  python main.py
打包:  python -m PyInstaller --noconfirm --onefile --windowed --name WorkdayReminder main.py
文档:  docs/user-guide.md（用户使用）  docs/deployment.md（部署）
"""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, QObject, QPoint, QSettings, Qt, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QGuiApplication, QIcon, QPainter,
                           QPainterPath, QPixmap, QTextCharFormat)
from PySide6.QtNetwork import (QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QCheckBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSystemTrayIcon,
    QTabWidget, QTimeEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

APP_NAME = "工作日提醒器"
APP_ID = "WorkdayReminder"
APP_DIR = Path.home() / ".workday_reminder"
BEIJING = timezone(timedelta(hours=8), "北京时间")  # 中国大陆无夏令时，固定 UTC+8
WEEKDAYS = "一二三四五六日"

# ---------------------------------------------------------------------------
# 内置数据：国务院办公厅放假安排通知（名称, 放假开始, 放假结束, [调休上班日]）
# ---------------------------------------------------------------------------
BUILTIN_HOLIDAYS: dict[int, list[tuple[str, str, str, list[str]]]] = {
    2025: [  # 国办发明电〔2024〕12号
        ("元旦", "2025-01-01", "2025-01-01", []),
        ("春节", "2025-01-28", "2025-02-04", ["2025-01-26", "2025-02-08"]),
        ("清明节", "2025-04-04", "2025-04-06", []),
        ("劳动节", "2025-05-01", "2025-05-05", ["2025-04-27"]),
        ("端午节", "2025-05-31", "2025-06-02", []),
        ("国庆节、中秋节", "2025-10-01", "2025-10-08", ["2025-09-28", "2025-10-11"]),
    ],
    2026: [  # 国务院办公厅 2025年11月4日 通知
        ("元旦", "2026-01-01", "2026-01-03", ["2026-01-04"]),
        ("春节", "2026-02-15", "2026-02-23", ["2026-02-14", "2026-02-28"]),
        ("清明节", "2026-04-04", "2026-04-06", []),
        ("劳动节", "2026-05-01", "2026-05-05", ["2026-05-09"]),
        ("端午节", "2026-06-19", "2026-06-21", []),
        ("中秋节", "2026-09-25", "2026-09-27", []),
        ("国庆节", "2026-10-01", "2026-10-07", ["2026-09-20", "2026-10-10"]),
    ],
}

# holiday-cn 项目（NateScarlet/holiday-cn）按年发布的 JSON，国务院公布后会自动更新
HOLIDAY_CN_URLS = [
    "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json",
    "https://fastly.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json",
    "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json",
]


def now_bj() -> datetime:
    return datetime.now(BEIJING).replace(tzinfo=None)


def md(d: date) -> str:
    return f"{d.month}月{d.day}日"


def md_w(d: date) -> str:
    return f"{d.month}月{d.day}日（周{WEEKDAYS[d.weekday()]}）"


def hm(t: time) -> str:
    return t.strftime("%H:%M")


# ---------------------------------------------------------------------------
# 日历数据与判断逻辑
# ---------------------------------------------------------------------------
@dataclass
class DayStatus:
    day: date
    is_workday: bool
    kind: str          # holiday / makeup / weekend / workday / custom_off / custom_work
    label: str
    data_known: bool   # 该年份官方安排是否已加载


@dataclass
class RestBlock:
    start: date
    end: date
    names: list[str] = field(default_factory=list)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def is_holiday(self) -> bool:
        return bool(self.names)


class HolidayCalendar:
    def __init__(self) -> None:
        self.days: dict[date, tuple[str, bool]] = {}     # 日期 -> (名称, 是否放假)
        self.custom: dict[date, tuple[str, bool]] = {}
        self.years: set[int] = set()
        self._load_builtin()
        self._load_cache()

    def _load_builtin(self) -> None:
        for year, items in BUILTIN_HOLIDAYS.items():
            for name, s, e, makeups in items:
                d, end = date.fromisoformat(s), date.fromisoformat(e)
                while d <= end:
                    self.days[d] = (name, True)
                    d += timedelta(days=1)
                for m in makeups:
                    self.days[date.fromisoformat(m)] = (f"{name}调休上班", False)
            self.years.add(year)

    def _load_cache(self) -> None:
        if not APP_DIR.exists():
            return
        for f in sorted(APP_DIR.glob("holiday_cn_*.json")):
            try:
                self.load_holiday_cn(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass

    def load_holiday_cn(self, data: dict) -> bool:
        """加载 holiday-cn 格式数据；当年尚未公布（days 为空）时返回 False。"""
        year = int(data["year"])
        items = data.get("days") or []
        if not items:
            return False
        self.days = {d: v for d, v in self.days.items() if d.year != year}
        for it in items:
            d = date.fromisoformat(it["date"])
            name = it.get("name", "节假日")
            self.days[d] = (name, True) if it["isOffDay"] else (f"{name}调休上班", False)
        self.years.add(year)
        return True

    def set_custom(self, entries: dict[date, tuple[str, bool]]) -> None:
        self.custom = entries

    def status(self, d: date) -> DayStatus:
        known = d.year in self.years
        if d in self.custom:
            name, off = self.custom[d]
            return DayStatus(d, not off, "custom_off" if off else "custom_work", name, True)
        if d in self.days:
            name, off = self.days[d]
            return DayStatus(d, not off, "holiday" if off else "makeup", name, known)
        if d.weekday() >= 5:
            return DayStatus(d, False, "weekend", f"周{WEEKDAYS[d.weekday()]}", known)
        return DayStatus(d, True, "workday", "工作日", known)

    def is_workday(self, d: date) -> bool:
        return self.status(d).is_workday

    def rest_block(self, d: date) -> RestBlock:
        """包含 d 的连续休息区间（d 必须是休息日）。"""
        start = end = d
        for _ in range(40):
            if self.is_workday(start - timedelta(days=1)):
                break
            start -= timedelta(days=1)
        for _ in range(40):
            if self.is_workday(end + timedelta(days=1)):
                break
            end += timedelta(days=1)
        names: list[str] = []
        cur = start
        while cur <= end:
            st = self.status(cur)
            if st.kind in ("holiday", "custom_off") and st.label not in names:
                names.append(st.label)
            cur += timedelta(days=1)
        return RestBlock(start, end, names)

    def next_workday(self, d: date) -> date:
        cur = d + timedelta(days=1)
        for _ in range(60):
            if self.is_workday(cur):
                return cur
            cur += timedelta(days=1)
        return cur

    def upcoming(self, start: date, horizon: int = 400) -> list[tuple]:
        """[('rest', RestBlock) | ('makeup', date, label)]，只列含节假日的休息段。"""
        out: list[tuple] = []
        d, last = start, start + timedelta(days=horizon)
        while d <= last:
            st = self.status(d)
            if not st.is_workday:
                blk = self.rest_block(d)
                if blk.is_holiday:
                    out.append(("rest", blk))
                d = blk.end + timedelta(days=1)
                continue
            if st.kind in ("makeup", "custom_work"):
                out.append(("makeup", d, st.label))
            d += timedelta(days=1)
        return out

    def next_holiday(self, today: date) -> RestBlock | None:
        for item in self.upcoming(today + timedelta(days=1), 400):
            if item[0] == "rest" and item[1].start > today:
                return item[1]
        return None


# ---------------------------------------------------------------------------
# 设置
# ---------------------------------------------------------------------------
class Prefs:
    DEFAULTS = {
        "work_start": "09:00", "work_end": "18:00",
        "lunch_enabled": True, "lunch_start": "12:00", "lunch_end": "13:30",
        "eve_time": "16:00", "remind_weekend_eve": False,
        "custom_days": "", "opacity": 85, "pos": "", "locked": False, "welcomed": False,
    }

    def __init__(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.q = QSettings(str(APP_DIR / "settings.ini"), QSettings.Format.IniFormat)

    def raw(self, key: str):
        return self.q.value(key, self.DEFAULTS[key])

    def get_bool(self, key: str) -> bool:
        v = self.raw(key)
        return v if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes")

    def get_int(self, key: str) -> int:
        try:
            return int(self.raw(key))
        except (TypeError, ValueError):
            return int(self.DEFAULTS[key])

    def get_time(self, key: str) -> time:
        try:
            return time.fromisoformat(str(self.raw(key)))
        except ValueError:
            return time.fromisoformat(self.DEFAULTS[key])

    def get_str(self, key: str) -> str:
        return str(self.raw(key) or "")

    def set(self, key: str, value) -> None:
        self.q.setValue(key, hm(value) if isinstance(value, time) else value)
        self.q.sync()


def parse_custom_days(text: str) -> tuple[dict[date, tuple[str, bool]], list[str]]:
    """每行：日期或日期范围 + 休/班 + 说明，例如
         2026-11-11 休 年假
         2026-12-24~2026-12-26 休 客户公司年会
         2026-11-14 班 项目上线
    """
    result: dict[date, tuple[str, bool]] = {}
    errors: list[str] = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=2)
        try:
            if len(parts) < 2 or parts[1] not in ("休", "班"):
                raise ValueError
            s, _, e = parts[0].replace("～", "~").partition("~")
            d1 = date.fromisoformat(s)
            d2 = date.fromisoformat(e) if e else d1
            if d2 < d1 or (d2 - d1).days > 60:
                raise ValueError
            off = parts[1] == "休"
            note = parts[2] if len(parts) > 2 else ("自定义休息" if off else "自定义上班")
            cur = d1
            while cur <= d2:
                result[cur] = (note, off)
                cur += timedelta(days=1)
        except ValueError:
            errors.append(f"第{n}行无法识别：{line}")
    return result, errors


# ---------------------------------------------------------------------------
# 开机自启
# ---------------------------------------------------------------------------
class AutoStart:
    """打包后（PyInstaller，sys.frozen）注册 exe 本身；源码运行时注册 pythonw + 脚本。"""
    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    MAC_PLIST = Path.home() / "Library/LaunchAgents/com.workday.reminder.plist"
    LINUX_DESKTOP = Path.home() / ".config/autostart/workday-reminder.desktop"

    @staticmethod
    def command() -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable]
        exe = Path(sys.executable)
        if sys.platform == "win32":
            pyw = exe.with_name("pythonw.exe")
            exe = pyw if pyw.exists() else exe
        return [str(exe), str(Path(__file__).resolve())]

    @classmethod
    def is_enabled(cls) -> bool:
        if sys.platform == "win32":
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH) as k:
                    winreg.QueryValueEx(k, APP_ID)
                return True
            except OSError:
                return False
        if sys.platform == "darwin":
            return cls.MAC_PLIST.exists()
        return cls.LINUX_DESKTOP.exists()

    @classmethod
    def set_enabled(cls, on: bool) -> None:
        cmd = cls.command()
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_SET_VALUE) as k:
                if on:
                    winreg.SetValueEx(k, APP_ID, 0, winreg.REG_SZ, subprocess.list2cmdline(cmd))
                else:
                    try:
                        winreg.DeleteValue(k, APP_ID)
                    except FileNotFoundError:
                        pass
        elif sys.platform == "darwin":
            if on:
                cls.MAC_PLIST.parent.mkdir(parents=True, exist_ok=True)
                with open(cls.MAC_PLIST, "wb") as f:
                    plistlib.dump({"Label": "com.workday.reminder", "ProgramArguments": cmd,
                                   "RunAtLoad": True}, f)
            elif cls.MAC_PLIST.exists():
                cls.MAC_PLIST.unlink()
        else:
            if on:
                cls.LINUX_DESKTOP.parent.mkdir(parents=True, exist_ok=True)
                exec_line = " ".join(f'"{c}"' for c in cmd)
                cls.LINUX_DESKTOP.write_text(
                    f"[Desktop Entry]\nType=Application\nName={APP_NAME}\nExec={exec_line}\n"
                    f"X-GNOME-Autostart-enabled=true\n", encoding="utf-8")
            elif cls.LINUX_DESKTOP.exists():
                cls.LINUX_DESKTOP.unlink()

    @classmethod
    def refresh_path(cls) -> None:
        """程序被移动过时，自动把启动项更新为当前路径。"""
        try:
            if cls.is_enabled():
                cls.set_enabled(True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 「现在能联系客户吗」
# ---------------------------------------------------------------------------
@dataclass
class Verdict:
    level: str    # ok / warn / stop
    short: str    # 悬浮窗主文字
    sub: str      # 悬浮窗第二行
    extra: str    # 悬浮窗第三行（可为空）
    detail: str   # 完整说明（提示框 / 菜单）


def advise(cal: HolidayCalendar, prefs: Prefs, now: datetime) -> Verdict:
    today, t = now.date(), now.time()
    st = cal.status(today)
    ws, we = prefs.get_time("work_start"), prefs.get_time("work_end")
    wd = f"周{WEEKDAYS[today.weekday()]}"

    # 第三行：节前收尾 > 数据缺失 > 下一个假期倒计时
    extra = ""
    tomorrow = today + timedelta(days=1)
    if st.is_workday and not cal.is_workday(tomorrow) and cal.rest_block(tomorrow).is_holiday:
        blk = cal.rest_block(tomorrow)
        extra = f"明天起{'、'.join(blk.names)} {blk.days} 天，今天收尾"
    elif not st.data_known:
        extra = f"⚠ {today.year} 年放假安排未加载"
    else:
        nh = cal.next_holiday(today)
        if nh:
            extra = f"距{nh.names[0]}还有 {(nh.start - today).days} 天"
        elif today.year + 1 not in cal.years:
            extra = f"{today.year + 1} 年放假安排尚未公布"

    if not st.is_workday:
        blk = cal.rest_block(today)
        back = cal.next_workday(today)
        back_wd = f"周{WEEKDAYS[back.weekday()]}"
        back_txt = md(back) if blk.is_holiday or (back - today).days > 6 else back_wd
        if blk.is_holiday:
            extra = f"连休 {md(blk.start)}–{md(blk.end)}，共 {blk.days} 天"
        detail = (f"今天休息（{st.label}），不要联系客户。\n本次休息 {md(blk.start)}–{md(blk.end)}，"
                  f"共 {blk.days} 天；{md_w(back)} 恢复上班。")
        return Verdict("stop", "别联系客户", f"{st.label}休息 · {back_txt}上班", extra, detail)

    tag = f"{st.label} · " if st.kind in ("makeup", "custom_work") else f"{wd} · "
    if t < ws:
        return Verdict("warn", "还没上班", f"{tag}{hm(ws)} 后再联系", extra,
                       f"今天是工作日，{hm(ws)} 以后再联系客户。")
    if t >= we:
        nxt = cal.next_workday(today)
        nxt_txt = "明天" if nxt == tomorrow else f"周{WEEKDAYS[nxt.weekday()]}"
        return Verdict("warn", "已下班", f"下次：{nxt_txt} {hm(ws)} 后", extra,
                       f"已经下班了，别打扰客户。下次可联系：{md_w(nxt)} {hm(ws)} 以后。")
    if prefs.get_bool("lunch_enabled"):
        ls, le = prefs.get_time("lunch_start"), prefs.get_time("lunch_end")
        if ls <= t < le:
            return Verdict("warn", "午休中", f"{tag}{hm(le)} 后再联系", extra,
                           f"午休时间，尽量别打扰，{hm(le)} 以后再联系。")
    return Verdict("ok", "可以联系客户", f"{tag}{hm(ws)}–{hm(we)}", extra,
                   f"今天是{st.label}，工作时间 {hm(ws)}–{hm(we)}，可以联系客户。")


# ---------------------------------------------------------------------------
# 联网更新 holiday-cn 数据
# ---------------------------------------------------------------------------
class HolidayUpdater(QObject):
    finished = Signal(list, list)   # (结果描述, 新获取到的年份)

    def __init__(self, cal: HolidayCalendar, parent=None) -> None:
        super().__init__(parent)
        self.cal = cal
        self.nam = QNetworkAccessManager(self)
        self.busy = False

    def update(self, years: list[int]) -> None:
        if self.busy:
            return
        self.busy = True
        self.queue = list(years)
        self.messages: list[str] = []
        self.new_years: list[int] = []
        self._next()

    def _next(self) -> None:
        if not self.queue:
            self.busy = False
            self.finished.emit(self.messages, self.new_years)
            return
        self._fetch(self.queue.pop(0), 0)

    def _fetch(self, year: int, idx: int) -> None:
        if idx >= len(HOLIDAY_CN_URLS):
            self.messages.append(f"{year} 年：网络获取失败（继续使用已有数据）")
            self._next()
            return
        req = QNetworkRequest(QUrl(HOLIDAY_CN_URLS[idx].format(year=year)))
        req.setTransferTimeout(8000)
        reply = self.nam.get(req)
        reply.finished.connect(lambda r=reply, y=year, i=idx: self._done(r, y, i))

    def _done(self, reply: QNetworkReply, year: int, idx: int) -> None:
        reply.deleteLater()
        code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            if code == 404:
                self.messages.append(f"{year} 年：官方安排尚未公布")
                self._next()
            else:
                self._fetch(year, idx + 1)
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            was_known = year in self.cal.years
            if self.cal.load_holiday_cn(data):
                (APP_DIR / f"holiday_cn_{year}.json").write_text(
                    json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                self.messages.append(f"{year} 年：已更新")
                if not was_known:
                    self.new_years.append(year)
            else:
                self.messages.append(f"{year} 年：官方安排尚未公布")
        except Exception as exc:
            self.messages.append(f"{year} 年：数据解析失败（{exc}）")
        self._next()


# ---------------------------------------------------------------------------
# 悬浮窗
# ---------------------------------------------------------------------------
ACCENT = {"ok": "#3ecf72", "warn": "#f5a623", "stop": "#ff5a52"}
TRAY_CHAR = {"ok": "班", "warn": "等", "stop": "休"}
KIND_FMT = {   # 日历格子：背景, 文字
    "holiday":     ("#fbd5d3", "#9b2c2a"),
    "custom_off":  ("#e6dcf5", "#5b3a8c"),
    "makeup":      ("#ffe2b8", "#8a5600"),
    "custom_work": ("#d6ecfb", "#1f5f8b"),
    "weekend":     (None, "#9a9a9a"),
    "workday":     (None, "#222222"),
}


def make_icon(color: str, text: str) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(2, 2, 60, 60)
    f = QFont()
    f.setPixelSize(36)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(pm)


class FloatWidget(QWidget):
    doubleClicked = Signal()
    menuRequested = Signal(QPoint)
    moved = Signal(QPoint)

    WIDTH = 236
    MARGIN = 16

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(self.WIDTH)
        self.accent = QColor(ACCENT["ok"])
        self.locked = False
        self.base_opacity = 0.85
        self._drag_offset: QPoint | None = None
        self._dragged = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 10, 14, 11)
        lay.setSpacing(2)
        self.lbl_title = QLabel()
        self.lbl_sub = QLabel()
        self.lbl_extra = QLabel()
        self.lbl_title.setStyleSheet("color:#ffffff; font-size:16px; font-weight:600;")
        self.lbl_sub.setStyleSheet("color:#d6d6d6; font-size:12px;")
        self.lbl_extra.setStyleSheet("color:#a9a9a9; font-size:12px;")
        for w in (self.lbl_title, self.lbl_sub, self.lbl_extra):
            lay.addWidget(w)

    # ---- 显示内容 ----
    def set_verdict(self, v: Verdict) -> None:
        self.accent = QColor(ACCENT[v.level])
        self.lbl_title.setText(v.short)
        self.lbl_sub.setText(v.sub)
        self.lbl_extra.setText(v.extra)
        self.lbl_extra.setVisible(bool(v.extra))
        warn_extra = v.extra.startswith(("明天起", "⚠"))
        self.lbl_extra.setStyleSheet(f"color:{'#ffc864' if warn_extra else '#a9a9a9'}; font-size:12px;")
        self.setToolTip(v.detail + "\n\n双击：设置　右键：菜单")
        self.adjustSize()
        self.update()

    def set_opacity(self, percent: int) -> None:
        self.base_opacity = max(0.3, min(1.0, percent / 100))
        self.setWindowOpacity(self.base_opacity)

    def default_pos(self) -> QPoint:
        geo = QGuiApplication.primaryScreen().availableGeometry()
        return QPoint(geo.right() - self.WIDTH - self.MARGIN + 1, geo.top() + self.MARGIN)

    def place(self, saved: str) -> None:
        pos = None
        try:
            x, y = (int(v) for v in saved.split(","))
            if any(s.availableGeometry().contains(QPoint(x + 20, y + 20)) for s in QGuiApplication.screens()):
                pos = QPoint(x, y)
        except ValueError:
            pass
        self.move(pos or self.default_pos())

    # ---- 绘制 ----
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.fillPath(path, QColor(24, 26, 30, 205))
        p.setPen(QColor(255, 255, 255, 28))
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.accent)
        cy = self.lbl_title.geometry().center().y()
        p.drawEllipse(QPoint(14, cy), 5, 5)

    # ---- 鼠标 ----
    def enterEvent(self, event) -> None:
        self.setWindowOpacity(1.0)

    def leaveEvent(self, event) -> None:
        self.setWindowOpacity(self.base_opacity)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and not self.locked:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False
        elif e.button() == Qt.MouseButton.RightButton:
            self.menuRequested.emit(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e) -> None:
        if self._drag_offset is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            self._dragged = True

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_offset is not None and self._dragged:
            self.moved.emit(self.pos())
        self._drag_offset = None

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()


# ---------------------------------------------------------------------------
# 设置对话框（双击悬浮窗打开）
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    saved = Signal()
    updateRequested = Signal()

    def __init__(self, cal: HolidayCalendar, prefs: Prefs, float_widget: FloatWidget) -> None:
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.cal, self.prefs, self.fw = cal, prefs, float_widget
        self.setWindowTitle(f"{APP_NAME} · 设置")
        self.resize(560, 520)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "常规")
        tabs.addTab(self._tab_custom(), "自定义日期")
        tabs.addTab(self._tab_calendar(), "放假日历")
        root.addWidget(tabs, 1)

        self.lbl_data = QLabel()
        self.lbl_data.setStyleSheet("color:#777;")
        self.lbl_data.setWordWrap(True)
        root.addWidget(self.lbl_data)

        btns = QHBoxLayout()
        self.b_update = QPushButton("更新节假日数据")
        self.b_update.clicked.connect(self._request_update)
        b_cancel = QPushButton("取消")
        b_cancel.clicked.connect(self.reject)
        b_save = QPushButton("保存")
        b_save.setDefault(True)
        b_save.clicked.connect(self.save)
        btns.addWidget(self.b_update)
        btns.addStretch()
        btns.addWidget(b_cancel)
        btns.addWidget(b_save)
        root.addLayout(btns)

    # ---- 构建 ----
    def _time_edit(self, key: str) -> QTimeEdit:
        e = QTimeEdit()
        e.setDisplayFormat("HH:mm")
        return e

    @staticmethod
    def _row(*widgets) -> QHBoxLayout:
        h = QHBoxLayout()
        for w in widgets:
            h.addWidget(QLabel(w) if isinstance(w, str) else w)
        h.addStretch()
        return h

    def _tab_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setVerticalSpacing(12)
        self.ed_ws, self.ed_we = self._time_edit("work_start"), self._time_edit("work_end")
        form.addRow("客户工作时间", self._row(self.ed_ws, "至", self.ed_we))

        self.cb_lunch = QCheckBox("提醒")
        self.ed_ls, self.ed_le = self._time_edit("lunch_start"), self._time_edit("lunch_end")
        form.addRow("午休", self._row(self.cb_lunch, self.ed_ls, "至", self.ed_le))

        self.ed_eve = self._time_edit("eve_time")
        form.addRow("节前收尾提醒", self._row(self.ed_eve, "（放假前最后一个工作日）"))
        self.cb_weekend_eve = QCheckBox("普通周五也提醒")
        form.addRow("", self.cb_weekend_eve)

        self.sl_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sl_opacity.setRange(30, 100)
        self.lbl_opacity = QLabel()
        self.sl_opacity.valueChanged.connect(self._preview_opacity)
        form.addRow("悬浮窗透明度", self._row(self.sl_opacity, self.lbl_opacity))
        self.cb_locked = QCheckBox("锁定位置（防止误拖动）")
        b_reset = QPushButton("回到右上角")
        b_reset.clicked.connect(self._reset_pos)
        form.addRow("", self._row(self.cb_locked, b_reset))

        self.cb_autostart = QCheckBox("开机自动启动")
        form.addRow("启动", self.cb_autostart)
        return w

    def _tab_custom(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("自己请假、客户公司的特殊放假或加班安排，每行一条："))
        self.ed_custom = QPlainTextEdit()
        self.ed_custom.setPlaceholderText(
            "2026-11-11 休 年假\n2026-12-24~2026-12-26 休 客户公司年会\n2026-11-14 班 项目上线，客户加班")
        lay.addWidget(self.ed_custom, 1)
        self.lbl_custom_err = QLabel()
        self.lbl_custom_err.setStyleSheet("color:#c0392b;")
        self.lbl_custom_err.setWordWrap(True)
        lay.addWidget(self.lbl_custom_err)
        return w

    def _tab_calendar(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setLocale(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.currentPageChanged.connect(lambda y, m: self._paint_calendar())
        self.calendar.selectionChanged.connect(self._show_day)
        top.addWidget(self.calendar, 3)
        self.lbl_day = QLabel()
        self.lbl_day.setWordWrap(True)
        self.lbl_day.setAlignment(Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.lbl_day, 2)
        lay.addLayout(top, 3)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["日期", "天数", "说明"])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tree, 2)
        return w

    # ---- 数据进出 ----
    def load(self) -> None:
        p = self.prefs
        for edit, key in ((self.ed_ws, "work_start"), (self.ed_we, "work_end"), (self.ed_ls, "lunch_start"),
                          (self.ed_le, "lunch_end"), (self.ed_eve, "eve_time")):
            t = p.get_time(key)
            edit.setTime(QTime(t.hour, t.minute))
        self.cb_lunch.setChecked(p.get_bool("lunch_enabled"))
        self.cb_weekend_eve.setChecked(p.get_bool("remind_weekend_eve"))
        self.sl_opacity.setValue(p.get_int("opacity"))
        self.cb_locked.setChecked(p.get_bool("locked"))
        try:
            self.cb_autostart.setChecked(AutoStart.is_enabled())
        except Exception:
            self.cb_autostart.setChecked(False)
        self.ed_custom.setPlainText(p.get_str("custom_days"))
        self.lbl_custom_err.clear()
        self.refresh_data()
        self.calendar.setSelectedDate(QDate.currentDate())

    def refresh_data(self) -> None:
        yrs = "、".join(str(y) for y in sorted(self.cal.years))
        self.lbl_data.setText(f"已加载官方放假安排：{yrs} 年　·　数据目录：{APP_DIR}")
        self._paint_calendar()
        self._show_day()
        self._fill_list()

    def save(self) -> None:
        entries, errors = parse_custom_days(self.ed_custom.toPlainText())
        if errors:
            self.lbl_custom_err.setText("\n".join(errors))
            QMessageBox.warning(self, APP_NAME, "「自定义日期」有无法识别的行，请修改后再保存。")
            return
        p = self.prefs
        for edit, key in ((self.ed_ws, "work_start"), (self.ed_we, "work_end"), (self.ed_ls, "lunch_start"),
                          (self.ed_le, "lunch_end"), (self.ed_eve, "eve_time")):
            p.set(key, edit.time().toString("HH:mm"))
        p.set("lunch_enabled", self.cb_lunch.isChecked())
        p.set("remind_weekend_eve", self.cb_weekend_eve.isChecked())
        p.set("opacity", self.sl_opacity.value())
        p.set("locked", self.cb_locked.isChecked())
        p.set("custom_days", self.ed_custom.toPlainText())
        self.cal.set_custom(entries)
        try:
            if self.cb_autostart.isChecked() != AutoStart.is_enabled():
                AutoStart.set_enabled(self.cb_autostart.isChecked())
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"开机自启设置失败：{exc}")
        self.saved.emit()
        self.accept()

    def reject(self) -> None:   # 取消时恢复透明度预览
        self.fw.set_opacity(self.prefs.get_int("opacity"))
        super().reject()

    def _preview_opacity(self, v: int) -> None:
        self.lbl_opacity.setText(f"{v}%")
        self.fw.set_opacity(v)

    def _reset_pos(self) -> None:
        self.fw.move(self.fw.default_pos())
        self.prefs.set("pos", "")

    def _request_update(self) -> None:
        self.b_update.setEnabled(False)
        self.b_update.setText("正在更新…")
        self.updateRequested.emit()

    def update_done(self, messages: list) -> None:
        self.b_update.setEnabled(True)
        self.b_update.setText("更新节假日数据")
        self.refresh_data()
        if self.isVisible() and messages:
            QMessageBox.information(self, APP_NAME, "\n".join(messages))

    # ---- 日历 ----
    def _paint_calendar(self) -> None:
        cw = self.calendar
        cw.setDateTextFormat(QDate(), QTextCharFormat())
        first = date(cw.yearShown(), cw.monthShown(), 1)
        today = now_bj().date()
        for i in range(-10, 45):
            d = first + timedelta(days=i)
            bg, fg = KIND_FMT[self.cal.status(d).kind]
            f = QTextCharFormat()
            f.setForeground(QBrush(QColor(fg)))
            if bg:
                f.setBackground(QBrush(QColor(bg)))
            if d == today:
                f.setFontWeight(QFont.Weight.Bold)
                f.setFontUnderline(True)
            cw.setDateTextFormat(QDate(d.year, d.month, d.day), f)

    def _show_day(self) -> None:
        qd = self.calendar.selectedDate()
        d = date(qd.year(), qd.month(), qd.day())
        st = self.cal.status(d)
        lines = [f"<b>{md(d)} 周{WEEKDAYS[d.weekday()]}</b>", st.label]
        if st.is_workday:
            lines.append("<span style='color:#1e8a4c'>✔ 客户上班，可以联系</span>")
        else:
            blk = self.cal.rest_block(d)
            lines.append("<span style='color:#c0392b'>✘ 休息日，别联系客户</span>")
            lines.append(f"连休 {md(blk.start)}–{md(blk.end)}<br>共 {blk.days} 天")
        if not st.data_known:
            lines.append(f"<span style='color:#d98a00'>⚠ {d.year} 年安排未加载</span>")
        lines.append("<br><span style='color:#c0392b'>■</span> 节假日　<span style='color:#e0a040'>■</span> 调休上班")
        self.lbl_day.setText("<br>".join(lines))

    def _fill_list(self) -> None:
        self.tree.clear()
        today = now_bj().date()
        start = date(today.year, 1, 1)
        target = None
        for item in self.cal.upcoming(start, (date(today.year + 1, 12, 31) - start).days):
            if item[0] == "rest":
                blk = item[1]
                last = blk.end
                row = QTreeWidgetItem([f"{blk.start.year}年 {md(blk.start)}–{md(blk.end)}",
                                       f"{blk.days} 天", "、".join(blk.names)])
                color = "#9b2c2a"
            else:
                _, last, label = item
                row = QTreeWidgetItem([f"{last.year}年 {md_w(last)}", "上班", label])
                color = "#8a5600"
            if last < today:
                color = "#aaaaaa"
            elif target is None:
                target = row
            for c in range(3):
                row.setForeground(c, QBrush(QColor(color)))
            self.tree.addTopLevelItem(row)
        if today.year + 1 not in self.cal.years:
            row = QTreeWidgetItem([f"{today.year + 1} 年", "", "放假安排尚未公布（通常 11 月前后），公布后自动获取"])
            row.setForeground(2, QBrush(QColor("#d98a00")))
            self.tree.addTopLevelItem(row)
            target = target or row
        if target:   # 等列表显示出来再滚动到「下一个」放假安排
            QTimer.singleShot(0, lambda: self.tree.scrollToItem(target, QTreeWidget.ScrollHint.PositionAtTop))


# ---------------------------------------------------------------------------
# 主控制器
# ---------------------------------------------------------------------------
class ReminderApp(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.prefs = Prefs()
        self.cal = HolidayCalendar()
        self.cal.set_custom(parse_custom_days(self.prefs.get_str("custom_days"))[0])
        self._fired: set[str] = set()
        self._last_day: date | None = None
        self._manual_update = False

        self.fw = FloatWidget()
        self.fw.locked = self.prefs.get_bool("locked")
        self.fw.set_opacity(self.prefs.get_int("opacity"))
        self.fw.doubleClicked.connect(self.open_settings)
        self.fw.menuRequested.connect(lambda pos: self.menu.exec(pos))
        self.fw.moved.connect(lambda p: self.prefs.set("pos", f"{p.x()},{p.y()}"))

        self.dialog: SettingsDialog | None = None
        self._build_menu_and_tray()

        self.updater = HolidayUpdater(self.cal, self)
        self.updater.finished.connect(self._on_update_finished)

        self.tick()
        self.fw.place(self.prefs.get_str("pos"))
        self.fw.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30_000)
        QTimer.singleShot(2000, lambda: self.start_update(manual=False))
        AutoStart.refresh_path()

        if not self.prefs.get_bool("welcomed"):
            self.prefs.set("welcomed", True)
            QTimer.singleShot(1200, lambda: self.notify(
                APP_NAME, "已在屏幕右上角显示。双击悬浮窗可以设置（含开机自启），拖动可移动位置。", "ok"))

    def _build_menu_and_tray(self) -> None:
        self.menu = QMenu()
        self.act_status = QAction("", self.menu)
        self.act_status.setEnabled(False)
        self.menu.addAction(self.act_status)
        self.menu.addSeparator()
        a_settings = QAction("设置…", self.menu)
        a_settings.triggered.connect(self.open_settings)
        self.act_toggle = QAction("隐藏悬浮窗", self.menu)
        self.act_toggle.triggered.connect(self.toggle_float)
        a_quit = QAction("退出", self.menu)
        a_quit.triggered.connect(self.app.quit)
        self.menu.addAction(a_settings)
        self.menu.addAction(self.act_toggle)
        self.menu.addSeparator()
        self.menu.addAction(a_quit)

        self.tray: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(make_icon(ACCENT["ok"], "班"), self)
            self.tray.setContextMenu(self.menu)
            self.tray.activated.connect(self._on_tray_activated)
            self.tray.show()

    # ---- 周期刷新 ----
    def tick(self) -> None:
        now = now_bj()
        if self._last_day != now.date():
            first = self._last_day is None
            self._last_day = now.date()
            self._fired = {k for k in self._fired if k.startswith(str(now.date()))}
            if not first:
                self.start_update(manual=False)
        self.refresh(now)
        self._check_notifications(now)

    def refresh(self, now: datetime | None = None) -> None:
        v = advise(self.cal, self.prefs, now or now_bj())
        self.fw.set_verdict(v)
        self.act_status.setText(v.detail.splitlines()[0])
        icon = make_icon(ACCENT[v.level], TRAY_CHAR[v.level])
        self.app.setWindowIcon(icon)
        if self.tray:
            self.tray.setIcon(icon)
            self.tray.setToolTip(f"{APP_NAME}\n{v.short} · {v.sub}")

    # ---- 提醒 ----
    def notify(self, title: str, msg: str, level: str = "stop") -> None:
        if self.tray and self.tray.supportsMessages():
            icon = (QSystemTrayIcon.MessageIcon.Information if level == "ok"
                    else QSystemTrayIcon.MessageIcon.Warning)
            self.tray.showMessage(title, msg, icon, 15_000)
        else:   # 没有系统托盘时用非模态对话框，避免阻塞计时器
            box = QMessageBox(QMessageBox.Icon.Information, title, msg)
            box.setModal(False)
            box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            box.show()

    def _once(self, key: str) -> bool:
        if key in self._fired:
            return False
        self._fired.add(key)
        return True

    def _check_notifications(self, now: datetime) -> None:
        today, t = now.date(), now.time()
        st = self.cal.status(today)
        if not st.is_workday:
            blk = self.cal.rest_block(today)
            if blk.is_holiday and self._once(f"{today}-rest"):
                self.notify(f"今天休息（{st.label}）",
                            f"不要联系客户。{md_w(self.cal.next_workday(today))} 恢复上班。")
            return

        if t >= self.prefs.get_time("work_start") and self._once(f"{today}-morning"):
            prev = today - timedelta(days=1)
            if st.kind in ("makeup", "custom_work"):
                self.notify(f"今天{st.label}", "别当成周末——客户今天正常上班，可以联系。", "ok")
            elif not self.cal.is_workday(prev) and self.cal.rest_block(prev).is_holiday:
                self.notify("假期结束，客户恢复上班", "可以跟进假期前没处理完的事项了。", "ok")

        tomorrow = today + timedelta(days=1)
        if t >= self.prefs.get_time("eve_time") and not self.cal.is_workday(tomorrow):
            blk = self.cal.rest_block(tomorrow)
            if (blk.is_holiday or self.prefs.get_bool("remind_weekend_eve")) and self._once(f"{today}-eve"):
                name = "、".join(blk.names) if blk.names else "周末"
                self.notify(f"明天起放假：{name}",
                            f"{md(blk.start)}–{md(blk.end)} 共 {blk.days} 天。"
                            f"需要客户确认 / 回复的事，今天下班前处理完。", "warn")

    # ---- 交互 ----
    def open_settings(self) -> None:
        if self.dialog is None:
            self.dialog = SettingsDialog(self.cal, self.prefs, self.fw)
            self.dialog.saved.connect(self._on_saved)
            self.dialog.updateRequested.connect(lambda: self.start_update(manual=True))
        if not self.dialog.isVisible():
            self.dialog.load()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _on_saved(self) -> None:
        self.fw.locked = self.prefs.get_bool("locked")
        self.fw.set_opacity(self.prefs.get_int("opacity"))
        self.refresh()

    def toggle_float(self) -> None:
        if self.fw.isVisible():
            self.fw.hide()
            self.act_toggle.setText("显示悬浮窗")
        else:
            self.fw.show()
            self.act_toggle.setText("隐藏悬浮窗")

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger and not self.fw.isVisible():
            self.toggle_float()

    # ---- 数据更新 ----
    def start_update(self, manual: bool) -> None:
        self._manual_update = manual
        y = now_bj().year
        self.updater.update([y, y + 1])

    def _on_update_finished(self, messages: list, new_years: list) -> None:
        self.refresh()
        if self.dialog:
            self.dialog.update_done(messages if self._manual_update else [])
        if new_years and not self._manual_update:
            self.notify("已获取新的放假安排", f"{'、'.join(map(str, new_years))} 年国务院放假安排已更新。", "ok")


# ---------------------------------------------------------------------------
# 单实例 + 入口
# ---------------------------------------------------------------------------
def server_name() -> str:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return f"{APP_ID}-{user}"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # 已经在运行：让旧实例打开设置，自己退出
    sock = QLocalSocket()
    sock.connectToServer(server_name())
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        return 0

    QLocalServer.removeServer(server_name())
    server = QLocalServer()
    server.listen(server_name())

    ctrl = ReminderApp(app)

    def on_conn() -> None:
        c = server.nextPendingConnection()
        if c:
            c.readyRead.connect(ctrl.open_settings)
            c.disconnected.connect(c.deleteLater)
    server.newConnection.connect(on_conn)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())