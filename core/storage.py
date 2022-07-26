# Временная заглушка. В будущем будет переработано в полноценный класс
import core.instance

# Yandex Disk Storage (22.10.2020)
import datetime
import core.data.topic_manager as _tm

_tm = _tm.TopicManager()

# ========= ========= ========= ========= ========= ========= ========= =========


def print_time(sec):
    if sec <= 0:
        return "0 сек"
    h = int(sec/3600)
    m = int(sec/60) % 60
    return "{0}ч ".format(h)*(h > 0)+"{0}м ".format(m)*(m > 0)+"{0}сек".format(int(sec) % 60)


def time():
    h = core.instance.app().disk.get("app", "timezone", 3)
    return datetime.datetime.now()+datetime.timedelta(hours=h)


def statistics(uid):
    return core.instance.app().disk.s_get(uid)


def userdata(uid):
    return core.instance.app().disk.get_userdata(str(uid))

def set_topic_list(short_name, _list):
    for topic in _list:
        _tm.add(short_name, topic[0], topic[1], topic[2], topic[3])


def update_topics():
    _tm.parse()


# В тексте при поиске может быть: @domain, @id (конвертировать в domain), nick, domain, id
def nick(user_domain, group):
    res = profile(user_domain, is_domain=True).nick(group, True, None)
    if res:
        return res
    return _tm.content(user_domain, group)


def domain(nickname, group, threshold):
    # Без threshold и поиска ника в загруженных данных... Исправить!
    return _tm.domain(nickname, group, threshold)


# !!!!!!!!!! Удалить метод в будущем
def event(name, fn_update, data, next_activate_time=1):
    import core.event.eventer
    core.instance.app().eventer.new(core.event.eventer.Event(name, fn_update, data, next_activate_time))


# !!!!!!!!!!!!!!
def profile(value, is_domain=False):
    if is_domain:
        return core.instance.app().disk.user_profile_by_domain(value)
    return core.instance.app().disk.user_profile(value)


# !!!!!!!!!! Перенести метод в будущем
# запуск объявлений
def h_ann(e):
    count = e.get("count", 1)
    _list = {"text": e.get("msg", "Error!")}
    core.instance.app().vk.send(e.get("peer_id", 481403141), _list)
    count -= 1
    if count <= 0:
        return False
    else:
        e.set("count", count)
        e.set_next_time(e.get("interval", 1))
    return True


# !!!!!!!
def self_id():
    return core.instance.app().vk.id()
