# 28.02.2019
from core import instance
import core.storage
import datetime


# нужно сделать чтобы было просто обращаться к содержимому ивента
# нужно сделать чтобы легко сохранялось отовсюду и обновлялось
# не требовало бы сложных действий

def update_topics(e):
    core.storage.update_topics()
    e.set_next_time(instance.app().disk.get("event", "topics_update", 9000))
    return True

def update_data(e):
    instance.app().update_disk()
    e.set_next_time(instance.app().disk.get("event", "data_update", 900))
    return True

def update_timetable(e):
    table = e.get("table")
    if table is None:
        return False
    if table["cur"] is not None:
        instance.app().vk.send_text(table["pid"], table["cur"])
    # Определим когда следующее сообщение будет
    i = 0
    t = instance.app().time()
    while i < 8:    # Неделя+1
        for msg in table["lst"]:
            z = datetime.datetime(t.year, t.month, t.day, msg[0], msg[1])
            z += datetime.timedelta(days=i)
            if msg[2] is None or z.isoweekday() in msg[2]:
                if t > z:
                    continue
                table["cur"] = msg[3]
                e.set_next_time((z-t).total_seconds())
                return True
        i += 1
    return False