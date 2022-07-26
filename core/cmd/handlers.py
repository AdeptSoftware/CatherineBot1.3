# Встроенные обработчики
# Возвращать должно либо str, либо {"text": smth, "attachment": [smth]}
import core.utils.calculator as _calc
import core.storage as storage
import core.rank_system.rs
import core.strings
import requests
import random
import re

# msg.list всегда имеет хотя бы 1 слово!


# вернёт один случайный ответ из списка
def x_rnd(_list):
    return _list[random.randint(0, len(_list)-1)]


def _cmp(msg, key_words, answers, q=False):
    for key in key_words:
        if key in msg.list and (not q or msg.item["text"][-1] == '?'):
            return x_rnd(answers)
    return None


def _cmp_phrase(msg, phrases):
    length = len(msg.list)
    for phrase in phrases:
        if phrase[0] in msg.list:
            index = msg.list.index(phrase[0])
            if 0 <= index < length-1 and msg.list[index+1] == phrase[1]:
                return True
    return False


def _rnd_pos(min_pos, max_pos):
    return random.randint(min_pos, max_pos-1)+random.random()


def _in(word, chars):
    for char in chars:
        if char in word:
            return True
    return False


def _find_nicks(msg, in_text=True, in_fwd=True, threshold=0, skip=0):
    if not in_text and not in_fwd:
        return None
    # Подготовка:
    _list = []
    msg.split(_list, msg.item["text"])
    if skip >= 0:
        while _list[0].lower() != msg.list[skip]:
            _list.pop(0)
        _list.pop(0)
    # Поиск
    res = {}
    if in_text:
        for string in _list:
            if string[0] == '@':    # domain
                domain = string[1:]     # либо id/domain
                if len(domain) > 2 and domain[:2] == "id" and domain[2:].isnumeric():
                    uid = int(domain[2:])
                    if uid < 0:
                        continue
                    domain = storage.profile(uid).domain()
                elif domain == "catherinebot":
                    continue
                if domain:
                    res[string[1:]] = (domain, storage.nick(domain, msg.chat["group"]))
                    continue
            elif not msg.is_word(string):
                continue
            res[string] = storage.domain(string, msg.chat["group"], threshold)
    if in_fwd:
        for item in msg.fwd:
            if item["from_id"] < 0:
                continue
            domain = storage.profile(item["from_id"]).domain()
            if domain and domain not in res:
                res[domain] = (domain, storage.nick(domain, msg.chat["group"]))
    return res      # type(res[0]) in (None, tuple, list)

# ========= ========= ========= ========= ========= ========= ========= =========


def abbreviation(msg):
    flag = len(msg.list) == 3 and msg.list[0] == "что" and msg.list[1] == "такое"
    if not ((len(msg.list) == 2 and msg.list[0] in ("аббревиатура", "расшифровка")) or flag):
        return None
    import urllib.request
    param = ""
    for byte in msg.list[1+int(flag)].encode("cp1251"):
        param += "%"+hex(byte)[2:]
    res = urllib.request.urlopen('http://www.korova.ru/humor/cyborg.php?acronym='+param)
    msg = "Будьте осторожны \"" + msg.list[1] + "\" неизвестный науке киборг!"
    if res.getcode() == 200:
        res = re.findall(r"<p>(.*)</p>\r\n<form action", res.read().decode("cp1251"))
        if res is not None and len(res) == 1 and res[0][:10] != "ВАСЯПУПКИН":
            msg = res[0]
    return msg


def achievements(msg):
    if msg.list[0] not in ("ачивки", "достижения", "достяги", "achievements"):
        return None
    _err_msg = "Нет информации о {0} в \"знакомствах\"!\n" \
               "Возможно не удалось вычленить ник или происходит обновление данных."
    ans, _id = "", None
    length = len(msg.list)
    _all = (msg.list[-1] == '+')
    if length == 1 or (length == 2 and _all):
        if msg.fwd:
            _id = msg.fwd[0]["from_id"]
            profile = storage.profile(_id)
            ans = profile.full_name() or "?"
        else:
            _id = msg.uid
            ans = msg.reference(full=True)
    elif length >= 2:
        user = _find_nicks(msg)
        if user:
            key = list(user.keys())[0]
            if not user[key]:
                return _err_msg.format(key)
            profile = storage.profile(user[key][0], True)
            ans = profile.full_name() or user[key][1][0]
            _id = profile.key("id", None)
        else:
            return _err_msg.format(msg.list[1])
    if _id is None or _id <= 0:
        return "К сожалению, об этом пользователе данных нет :("
    s = storage.statistics(_id)
    # Выведем информацию по рангу
    if _all:
        ans += ": %s (%d ранг: %d/%d)\n" % (core.rank_system.rs.rank_list[s["rank"]][0], s["rank"], s["word"][0],
                                            core.rank_system.rs.rank_list[s["rank"] + 1][1])
    else:
        ans += ": %s (%d ранг)\n" % (core.rank_system.rs.rank_list[s["rank"]][0], s["rank"])
    if _all and s["last"][2] != 0 and msg.item["date"] - s["last"][2] >= 5:
        ans += "Последняя замеченная активность: %s назад\n" % storage.print_time(msg.item["date"]-s["last"][2])
    msg_a = ""
    i, count = 0, 0
    for a in s["achievements"]:
        if type(s["achievements"][a]) is int:
            res = core.rank_system.rs.print_achievement(msg, int(a), s["achievements"][a], _all)
        else:
            res = core.rank_system.rs.print_achievement(msg, int(a), s["achievements"][a][int(_all)], _all)
        if res != "":
            count += 1
            if _all or i < 4:
                msg_a += res
                i += 1
    if not _all and i < count:
        msg_a += "Скрыто достижений: %d\n" % (count - i)
    if msg_a != "":
        ans += "\n[Достижения]\n" + msg_a + '\n'
    return ans


def announcement(msg):
    if not (len(msg.list) > 3 and msg.list[0] == "объявление" and msg.list[1].isnumeric() and msg.list[2].isnumeric()):
        return None
    lst = msg.item["text"].split('\n')
    if len(lst) < 2:
        return None
    text = "\n".join(lst[1:])
    interval = int(msg.list[1])*60
    name = "Announcement " + str(random.randint(0, 999999))
    storage.event(name, storage.h_ann, {"interval": interval, "count": int(msg.list[2]), "msg": text,
                                        "peer_id": msg.pid, "name": name}, interval)
    return x_rnd(("Сделаю!", "Будет сделано!"))


def calc(msg):
    mul = ('x', 'х')
    chars = ('+', '-', '*', '/', '^', '%', '÷', ':', '×')
    for obj in msg.list:
        if obj in chars or _in(obj, mul):
            answer = ""
            res = _calc.main(msg.item["text"])
            if res is not None:
                for r in res:
                    try:
                        if r["result"][0] != '!':
                            answer += r["formula"] + '=' + r["result"] + '\n'
                    except Exception as err:
                        return "Я отказываюсь это вычислять!\n"+str(err)
                if answer != "":
                    return answer
    return None


def date(msg):
    if msg.list[0] in ("сколько", "дай", "какая", "какое", "какой"):
        _list = ("время", "времени", "дата", "день")
        if (len(msg.list) >= 2 and msg.list[1] in _list) or \
           (len(msg.list) >= 3 and msg.list[2] in _list):
            return storage.time().strftime("Текущее время в Москве (+3):\n%d.%m.%Y %H:%M")
    return None


def find_player(msg):
    if msg.list[0] not in ("найти", "найди"):
        return None
    if len(msg.list) > 1 and msg.list[1] == "меня":
        res = {msg.uid: (msg.domain(), [msg.reference(True)], 0)}
    else:
        threshold = 3           # поиск "аb" в ["aa", "ab", "ac"]
        if msg.chat["group"] != "Vainglory":
            threshold = -1      # поиск "ab" в "abcd"
        res = _find_nicks(msg, threshold=threshold)
    # Анализируем
    p = 1
    end_msg = ""
    not_found, probably, found, att = [], "", [], []
    for key in res:
        if res[key] is None:                # нет никаких данных о нике
            not_found += [key]
        elif type(res[key][0]) is tuple:       # возможные ники
            if len(res[key]) == 1:
                val = res[key][0][1].replace('\n', ' ')
                text = "{0}. {1} → {3} vk.com/{2}\n".format(p, key, res[key][0][0], val)
            else:
                text = "{0}. {1}:\n".format(p, key)
                for obj in res[key]:
                    val = obj[1].replace('\n', ' ')
                    f = len(key)/len(obj[1])
                    if f > 1:
                        f = 1/f
                    text += "→ {0} vk.com/{1} ({2:.1f}%)\n".format(val, obj[0], f*100)
            probably += text
            p += 1
        elif res[key][1] is not None:           # Нашли ник
            _list = tuple(val.replace('\n', ' ') for val in res[key][1])
            if type(res[key][0]) is int:
                found += ["[id{0}|{1}]".format(res[key][0], "||".join(_list))]
            else:
                found += ["[{0}|{1}]".format(res[key][0], "||".join(_list))]
            profile = storage.profile(res[key][0], True)
            uid = profile.key("id", None)
            if uid:
                userdata = storage.userdata(str(uid))
                if userdata is not None:
                    att += userdata[0]
                    if userdata[1] is not None:
                        end_msg = '\n' + userdata[1] + "\n"
    if len(not_found) == len(probably) == len(found) == 0:
        if len(msg.list) > 1:
            return None
        return {"text": "Я не знаю кто это...", "attachment": []}
    text = ""
    if found:
        text = "Вы искали: " + ", ".join(found) + "\n\n"
    if probably:
        text += "Может быть, Вы искали:\n" + probably + '\n'
    if not_found:
        text += "Не найдены: " + ", ".join(not_found) + '\n'
    return {"text": text+end_msg, "attachment": att}


def goodbye(msg):
    return _cmp(msg, ("досвидания", "goodbye", "покеда"),
                ("Пока", "До скорой встречи :)"))


# Можно добавить ответ в виде стикера
def hello(msg):
    return _cmp(msg, ("привет", "дратути", "здрасти", "здравствуй", "приветик",
                      "здравствуйте", "здарова", "hello", "hey", 'хаюшки'),
                ("Привет", "Здравствуй", "Приветик"))


def hit(msg):
    ni = 0      # next index
    case = "acc"
    if msg.list[0] in ("шлепок", "отшлепай", "шлепнуть", "шлепни", "подзатыльник"):
        ni = 1
    elif len(msg.list) >= 3 and msg.list[0] in ("дай", "бей") and msg.list[1] == "по" and msg.list[2] in ("попе", "жопе"):
        case = "dat"
        ni = 3
    if ni:
        ans = x_rnd(("{0}, Вам был выдан шлепок! Дай пять. Хорошая работа!",
                     "Шлепок совершён! {0}, Вы счастливы? :)",
                     "{0}, вот Ваш шлепок. Получите и распишитесь)",
                     "*Шлепок* {0}, в этот чудесный день Вам было приятно? ;)"))
        if len(msg.list) > ni:
            if msg.list[ni] in ("все", "всех", "себя") or msg.list[ni] in core.strings.std_catherine_refs():
                return "Может лучше уж тебя шлёпнуть?"
            if msg.list[ni] == "меня":
                return "Вы отшлёпаны! Приятного дня)))"
            return ans.format(msg.transform(msg.list[ni], case))
        if len(msg.fwd) == 1:
            return ans.format(storage.profile(msg.fwd[0]["from_id"]).key("first_name", "Эй"))
        return "Может определишься уже кого шлёпнуть?!\nЧур не меня))"
    return None


def how_much(msg):
    if msg.list:
        if msg.list[0] in ("сколько", "насколько", "восколько") or \
        (len(msg.list) > 1 and msg.list[0] in ("на", "во") and msg.list[1] == "сколько"):
            return str(random.randint(1, 100))
        if msg.list[0] == "как" and len(msg.list) >= 2:
            if msg.list[1] == "много":
                return str(random.randint(1, 50))
            if msg.list[1] == "долго":
                _list = storage.print_time(random.randint(300, 86400)).split()
                if _list:
                    return _list[0]
                return "Бесконечно)"
            if msg.list[1] == "часто":
                return str(random.randint(1, 8)) + " раз"
    return None


def is_true(msg):
    return _cmp(msg, ("точно", "правда"),
                ("Это ложь!", "Внутреннее чутьё мне подсказывает, что это ложь)))",
                 "Чистая правда!", "Может быть..."), True)


def repeat_text(msg):
    if msg.list and msg.list[0] in ("скажи", "повтори"):
        if random.random() <= 0.35:
            return x_rnd(("Неа", "Я тебе не попугай!", "Ты что меня за попугая держишь?", "Не хочу!",
                          "Не скажу", "Не буду!", "Я не буду это говорить", "Могу только язык показать :P",
                          "Нет!", "Отказываюсь", "Могу только сказать: \"нет\"", "Зачем?"))
        length = len(msg.list)
        if length > 1:
            if msg.list[1] in ("\"", ":\""):
                i = 2
                while msg.list[i] != "\"" and i < length:
                    i += 1
                return msg.get(2, i)
            return msg.get(1)
    return None


def variants(msg):
    if "или" not in msg.list:
        return None
    start = 0
    length = len(msg.list)
    if length > 2:
        if msg.list[0] in ("кто", "что", "че", "чо"):
            start = 2
        i = 0
        part = []
        while i <= length:
            if i == length or (not msg.is_word(msg.list[i]) and not msg.list[i].isnumeric() and msg.list[i] != '-'):
                part += [msg.get(start, i)]
                break
            if msg.list[i] == "или":
                part += [msg.get(start, i)]
                start = i+1
            i += 1
        part = tuple(filter(None, part))    # исключаем пустые элементы
        if len(part) > 1:
            ans = x_rnd(part)
            if ans in core.strings.std_catherine_refs() or ans == 'я':
                ans = "ты"
            return ans.capitalize()
    return None


def rnd(msg, _max=50000):
    if len(msg.list) == 8 and ''.join(msg.list[:2])+msg.list[3]+msg.list[5]+msg.list[7] == "rand(.%,)":
        if msg.list[2].isnumeric() and msg.list[4].isnumeric() and msg.list[6].isnumeric():
            p = float(''.join(msg.list[2:5]))
            cnt = int(msg.list[6]) or _max
            if p > 0.0:
                x = []
                i = 0
                while i < cnt and i < _max:
                    rand = random.random()*100
                    if rand <= p:
                        x += [i+1]
                    i += 1
                if x:
                    values = ', '.join(str(v) for v in x[:10])
                    if len(x) > 10:
                        values += ", ..."
                    return "Выпало {0}/{1} на итерациях:\n{2}".format(len(x), i, values)
            return "Так ничего и не выпало :("
    return None


def sleep(msg):
    if _cmp_phrase(msg, (("спокойной", "ночи"), ("сладких", "снов"))):
        return x_rnd(("Спокойной ночи)", "И вам сладких снов"))
    return None


def where_am(msg):
    if msg.list[0] != "где":
        return None
    i = 0
    r = None
    res = None
    _r = re.compile(r"null,\[\\\"([^\\]+?)\\\"\],\[\[")
    while i < 10:
        string = "https://www.google.com/maps/@{0:6f},{1:6f}z?hl=ru".format(_rnd_pos(-56, 78), _rnd_pos(-180, 180))
        r = requests.get(string)
        if r is None:
            i += 1
            continue
        # storage.core.instance.app().log("StatusCode: %d" % (r.status_code))
        if r.status_code == 429:
            return msg.reference(False) + ", " + core.strings.rnd(core.strings.on_unknown_location())
        if r.status_code == 200:
            xx = r.content.decode('utf-8', 'backslashreplace')
            res = _r.findall(xx)
            # storage.core.instance.app().log("Text: %s\nResult:%s\n\n\n" % (str(xx), str(res)))
            if res is not None and len(res) != 0:
                result = res[0].lower()
                skip = False
                for water in ("океан", "море", "залив", "пролив", "озеро", "река", "зал", "sea", "ocean", "проход"):
                    if water in result:
                        skip = True
                        res = None
                        break
                if not skip:
                    break
        i += 1
    if res is not None and r is not None:
        return msg.reference(False) + ', ' + res[0] + '?' + ('\n' + r.request.url[8:])*int(msg.list[-1] in ('+', '?+'))
    return core.strings.rnd(core.strings.on_unknown_location())


def who_am(msg):    # Застенчивый некромант из Чертаново, который ищет крестражи путина.
    return None


"""
if msg.list and msg.list[0] == "кто":
    x0 = ("застенчивый", "раскрепощенный", "пьяный", "разговорчивый", "быстрый", "медленный", "глупый",
          "задорный", "смешной", "нелепый", "красивый", "алчный", "корыстный", "вежливый", "пошлый",
          "развратный", "умный", "молчаливый", "болтливый", "смелый", "крикливый", "рыжий", "опухший")
    x1 = ("тащер", "повелитель мертвых", "самурай", "садовник", "повелитеь мух", "таракан", "индеец",
          "авторитет", "диктатор", "паладин", "жнец душ", "победитель по жизни", "кролик", "абориген",
          "чародей", "фантазёр", "сферический конь в вакууме", "богач", "пельмень", "тень", "скиталец",
          "троглодит", "бабник", "грифон", "орк", "стажёр", "артист", "шахтёр", "батюшка", "баран",
          "вурдалак", "ловец", "еврей", "меломан", "иллюзия", "старый хрящ", "кожаный мешок", "некромант",
          "оборотень", "лодырь", "святой", "ученый")
    x2 = ("крестражи", "посох", "молот", "угли", "")
"""
