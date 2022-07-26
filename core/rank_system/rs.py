import re
import core.rank_system.any_cond as _c
from core.instance import app as _app


# измеряется в словах
rank_list = [["Неизвестный", 0],                                    # 0
             ["Тень", 50],                                          # 1
             ["Усердный", 400],                                     # 2
             ["Исследователь", 1000],                               # 3
             ["Печатная машинка", 2000],                            # 4
             ["Словарь", 4000],                                     # 5
             ["Эрудит", 8000],                                      # 6
             ["Библиотекарь", 13500],                               # 7
             ["Оратор", 20000],                                     # 8
             ["Эксперт", 25000],                                    # 9
             ["Хранитель мудрости", 37500],                         # 10
             ["Великий жрец", 50000],                               # 11
             ["Владыка", 70000],                                    # 12
             ["Легенда чата", 100000],                              # 13
             ["Сверхразум", 1000000],                               # 14
             ["Сама бесконечность", 1000000000]]


def print_achievement(msg, index, current_value, _all=False):
    key, value = 0, None
    for a_key in _c.achievement_list[index][1]:
        if a_key <= current_value:
            key = a_key
        else:
            if _all:
                value = [current_value, a_key]
            break
    if key == 0:
        return ""
    if not value and _all:
        value = [current_value, list(_c.achievement_list[index][1].keys())[-1]]
    return _c.print_achievement(msg, index, key, value, False, True)


def _length(_list, max_count, _ex):
    for e in _list:
        if not e.isnumeric() and e not in _ex and len(e) > max_count:
            print(e)
            return False
    return True


def main(msg, spam_count=5, spam_time=60):
    if msg.uid in [18157007]:
        return None
    msg.s = _app().disk.s_get(msg.uid)
    # Если повторяется текст, то не учитываем
    if msg.s["last"][0] == msg.item["text"] and _c.is_type(msg, "audio_message") is None:
        msg.s["last"][1] += 1
        if msg.s["last"][1] == spam_count and msg.s["last"][2] < spam_time:
            _app().vk.send_text("тебе не кажется, что это уже спам?!")
        msg.s["last"][2] = msg.item["date"]
        return None
    # Построим частоту употребления слов
    f = {}
    for w in msg.list:
        if msg.is_word(w):
            if w in f:
                f[w] += 1
            else:
                f[w] = 1
    text = ""
    if len(f) != 0:
        x = sorted(f.items(), key=lambda kv: kv[1])
        x.reverse()
        for k in x:
            if len(k[0]) >= 3 and f[k[0]] > 3:
                # msg += "→ Знаешь.. В этом сообщении слово «" + k[0] + "» встречается " + str(k[1]) + " раз(-а)?\n"
                break
    r0 = re.compile(r"\s+")
    r1 = re.compile(r"[a-z]")
    r2 = re.compile(r"[аеёиоуыэюя]")
    r3 = re.compile(r"[бвгджзйклмнпрстфхчцшщ]")
    count = len(msg.list)
    word_count = 0
    for i in range(0, count):
        if not msg.is_word(msg.list[i]):
            continue
        length = len(msg.list[i])
        if r1.search(msg.list[i]) is not None or \
           not _length(r0.split(r2.sub(' ', msg.list[i]).strip()), 3, ["ств", "нстр", "встр", "льств", "йств",
                                                                       "нств", "тств", "вств", "взгл", "рств",
                                                                       "ссср", "мств"]) or \
           not _length(r0.split(r3.sub(' ', msg.list[i]).strip()), 2, []) or \
           (f[msg.list[i]] <= 3 and (length < 3 or length > 12)):
            continue
        msg.s["symbol"] += length
        word_count += 1
    msg.s["word"][0] += word_count
    # Обновим статы и проверим выполняются ли достижения
    pos = -1
    try:
        for pos in range(0, len(_c.achievement_list)):
            if _c.achievement_list[pos][0] is not None:
                if callable(_c.achievement_list[pos][0]):
                    msg_x = _c.achievement_list[pos][0](msg)
                    if msg_x != "":
                        text += "→ " + msg_x
    except Exception as err:
        return pos
    # Теперь ранги
    if msg.s["rank"]+1 < len(rank_list) and msg.s["word"][0] >= rank_list[msg.s["rank"] + 1][1]:
        msg.s["rank"] += 1
        _s = ""
        if not msg.is_men():
            _s = 'а'
        text += "→ " + msg.reference(True) + " получил" + _s + " новый ранг «" + rank_list[msg.s["rank"]][0] + "»\n"
    # всегда должно быть в конце:
    msg.s["last"] = [msg.item["text"], 1, msg.item["date"]]
    if text != "":
        _app().vk.send_text(msg.pid, text)
    return None
