from datetime import datetime, time
from app.core.logger import logger

def get_current_datetime_info() -> dict:
    """获取当前日期、时间、星期、节日等信息"""
    now = datetime.now()
    info = {
        "current_time": now.strftime("%H:%M"),
        "current_date": now.strftime("%Y年%m月%d日"),
        "weekday": _get_weekday_cn(now.weekday()),
        "holiday": _get_holiday(now),
        "time_period": _get_time_period(now.time())
    }
    logger.debug(f"当前时间信息：{info}")
    return info

def _get_weekday_cn(weekday: int) -> str:
    days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return days[weekday]

def _get_holiday(now: datetime) -> str:
    """简单的节日判断（可扩展）"""
    month, day = now.month, now.day
    holidays = {
        (1, 1): "元旦",
        (2, 14): "情人节",
        (5, 1): "劳动节",
        (6, 1): "儿童节",
        (10, 1): "国庆节",
        (12, 25): "圣诞节",
    }
    return holidays.get((month, day), "")

def _get_time_period(t: time) -> str:
    """根据当前时间判断时段"""
    if time(0, 0) <= t < time(6, 0):
        return "凌晨"
    elif time(6, 0) <= t < time(9, 0):
        return "早晨"
    elif time(9, 0) <= t < time(12, 0):
        return "上午"
    elif time(12, 0) <= t < time(14, 0):
        return "中午"
    elif time(14, 0) <= t < time(18, 0):
        return "下午"
    elif time(18, 0) <= t < time(22, 0):
        return "晚上"
    else:
        return "深夜"

def is_sleeping(role_schedule: dict) -> bool:
    """
    根据角色作息表判断当前是否在睡觉时间
    role_schedule 格式：{"sleep": "23:00-07:00", "work": "09:00-18:00"}
    """
    if not role_schedule or "sleep" not in role_schedule:
        return False

    now = datetime.now().time()
    sleep_start, sleep_end = role_schedule["sleep"].split("-")
    start_h, start_m = map(int, sleep_start.split(":"))
    end_h, end_m = map(int, sleep_end.split(":"))

    sleep_start_time = time(start_h, start_m)
    sleep_end_time = time(end_h, end_m)

    if sleep_start_time <= sleep_end_time:
        return sleep_start_time <= now <= sleep_end_time
    else:
        # 跨午夜的情况，如 23:00-07:00
        return now >= sleep_start_time or now <= sleep_end_time