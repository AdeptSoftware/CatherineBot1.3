# 21.07.2019
import core.instance


def _phrase(msg, phrases):
    for phrase in phrases:
        if phrase[0] in msg.list:
            i = msg.list.index(phrase[0])
            if i+len(phrase)-1 < len(msg.list):
                for k in range(i+1, len(msg.list)):
                    if phrase[k-i] != msg.list[k]:
                        return False
                return True
    return False


def print_achievement(msg, index, key, value=None, description=True, only_name=False):
    if key in achievement_list[index][1]:
        _s = ""
        if not msg.is_men():
            _s = 'а'
        text = ""
        if not only_name:
            text += "{0} получил{1} достижение ".format(msg.reference(True), _s)
        text += "«" + achievement_list[index][1][key][0] + "» ("
        if value is not None:
            text += str(value[0]) + '/' + str(value[1])
        else:
            text += str(key)
        text += ')'
        if description and achievement_list[index][1][key][1] is not None:
            import random
            i = random.randint(0, len(achievement_list[index][1][key][1])-1)
            text += "\n„"+achievement_list[index][1][key][1][i]+'“'
        return text + '\n'
    return ""


def inc(msg, index, upd=True):
    if index in msg.s["achievements"]:
        msg.s["achievements"][index] += 1
        return print_achievement(msg, index, msg.s["achievements"][index])
    else:
        msg.s["achievements"][index] = 1
    if upd:
        core.instance.app().eventer.update_event_data("data_updater", "flag", True)
    return ""


def inc_s(msg, index, value):
    save_key = 0
    progress = None
    keys = tuple(achievement_list[index][1].keys())
    for i in range(0, len(keys)):
        if keys[i] <= value:
            save_key = keys[i]
            if i+1 == len(keys):
                progress = None
            else:
                progress = [value, keys[i+1]]
        else:
            break
    if save_key != 0:
        if index not in msg.s["achievements"] or msg.s["achievements"][index][0] < save_key:
            msg.s["achievements"][index] = [save_key, value]
            return print_achievement(msg, index, save_key, progress)
        else:
            if msg.s["achievements"][index][1] < value:
                msg.s["achievements"][index][1] = value
        core.instance.app().eventer.update_event_data("data_updater", "flag", True)
    return ""


def _cond_ego(msg):
    for w in ("я", "меня", "мне"):
        if w in msg.list:
            return inc(msg, 0)
    return ""


def _cond_find(msg):
    if len(msg.list) > 1 and ("найти" == msg.list[0] or "найди" == msg.list[0]) and '?' not in msg.list[-1]:
        return inc(msg, 1)
    return ""


def _cond_where_am(msg):
    if len(msg.list) >= 2 and msg.list[0] == "где" and msg.list[1] == 'я':
        return inc(msg, 2)
    return ""


def _cond_call_play(msg):
    if _phrase(msg, (("кто", "играть"), ("кто", "катать"))):
        return inc(msg, 5)
    return ""


def _cond_agent(msg):
    if msg.item["date"]-msg.s["last"][2] >= 604800:   # Больше недели
        return inc(msg, 6)
    return ""


def _cond_fast_msg(msg):
    if msg.item["date"]-msg.s["last"][2] <= 3:
        return inc_s(msg, 7, len(msg.item["text"]))
    return ""


def _cond_bracket(msg):
    length = len(msg.list)
    flag = (')' in msg.prefix or (length != 0 and ')' in msg.list[length-1]))
    if not flag:
        for w in msg.list:
            if ')' in w:
                flag = True
                break
    if flag:
        return inc(msg, 9)
    return ""


def __cond_att(msg, _id, _type, ext=None):
    for a in msg.item["attachments"]:
        if "type" in a and a["type"] == _type:
            if ext is None or a[_type]["ext"] == ext:
                return inc(msg, _id)
    return ""


def _cond_eat(msg):
    for w in ("ем", "пожру", "покушаю", "жрать", "кушать", "еда", "пища", "еду", "пищу"):
        if w in msg.list:
            return inc(msg, 10)
    return ""


def _cond_stickers(msg):
    return __cond_att(msg, 11, "sticker")


def _cond_butthurt(msg):
    if msg.list and msg.item["text"].isupper():
        return inc(msg, 12)
    for w in ("горю", "горит", "пылаю", "бомблю", "пылает", "дымит"):
        if w in msg.list:
            return inc(msg, 12)
    return ""


def _cond_repost(msg):
    return __cond_att(msg, 13, "wall")


def _cond_inform_me(msg):
    if _phrase(msg, (("зачем", "сказал"), ("держи", "в", "курсе"))):
        return inc(msg, 14)
    return ""


def _cond_symbol(msg):
    return inc_s(msg, 15, msg.s["symbol"])


def cond_duel_wins(wins, a):
    if wins in achievement_list[8][1] and (8 not in a or a[8] < wins):
        a[8] = wins
        core.instance.app().eventer.update_event_data("data_updater", "flag", True)
        return print_achievement(None, 8, wins)
    return ""


def _cond_smile(msg):
    for c in msg.item["text"]:
        if ord(c) > 8000:
            return inc(msg, 16)
    return ""


def _cond_gif(msg):
    return __cond_att(msg, 17, "doc", "gif")


def _cond_scream(msg):
    for text in ("ор", "ору"):
        if text in msg.list:
            return inc(msg, 18)
    return ""


def _cond_picture(msg):
    return __cond_att(msg, 19, "photo")


def _cond_swear(msg):
    for swear in ["еб", "бля", "хуй", "пизд", "сука", "суки", "хер", "чмо", "нахуя",
                  "даун", "дебил", "нахуй", "нахер", "лох", "мудак", "похер"]:
        for w in msg.list:
            if w[0:len(swear)] == swear:
                return inc(msg, 20)
    return ""


def _cond_dont_understand(msg):
    if "непонятно" in msg.list or _phrase(msg, (("не", "понял"), ("не", "поняла"), ("не", "понятно"))):
        return inc(msg, 21)
    return ""


def _cond_leave(msg):
    if "action" in msg.item and msg.item["action"]["type"] == "chat_kick_user":
        return inc(msg, 22, False)
    return ""


def _cond_bad_words(msg):
    for w in ("ихний", "отсюдова", "вообщем", "текет", "ложить"):
        if w in msg.list:
            return inc(msg, 23)
    return ""


def _cond_caller(msg):
    for w in msg.list:
        if "@all" in w or "@online" in w:
            return inc(msg, 24)
    return ""


def _cond_thx(msg):
    if "спасибо" in msg.list or _phrase(msg, (("не", "за", "что"), ("на", "здоровье"))):
        return inc(msg, 25)
    return ""


def _cond_audio(msg):
    return __cond_att(msg, 26, "audio")


def is_type(msg, _type):
    for a in msg.item["attachments"]:
        if "type" in a and a["type"] == _type:
            return a
    return None


def _cond_audio_message(msg):
    a = is_type(msg, "audio_message")
    if a is not None:
        if 27 not in msg.s["achievements"]:
            msg.s["achievements"][27] = [0, a["audio_message"]["duration"]]
        else:
            msg.s["achievements"][27][1] += a["audio_message"]["duration"]
        return inc_s(msg, 27, msg.s["achievements"][27][1])
    return ""


# достижения
# при добавлении достижения необходимо подправить кол-во их в yandex_disk.s_get
achievement_list = [[_cond_ego,                                                         # 0
                     {100: ["Эгоист",
                            ["Ваше «эго» никогда не было обделено вниманием",
                             "Любитель рассказать о себе",
                             "Эгоизм в крови"]]}],

                    [_cond_find,                                                         # 1
                     {10: ["Активный пользователь",
                           ["Найду несмотря ни на что"]],
                      25: ["Любопытный", None],
                      50: ["Поисковый отряд",
                           ["Всегда в поисках окаменелостей",
                            "Докапавшийся до истины"]],
                      100: ["Разведчик", None],
                      250: ["Агент спецслужб", None]}],

                    [_cond_where_am,                                                   # 2
                     {10: ["Амнезия",
                           ["Путешествия по миру не прошли зря...",
                            "В первые в этих дебрях"]],
                      25: ["Невезучий путешественник",
                           ["Откуда мне только не пришлось выбираться по несколько раз..."]],
                      50: ["Опытный путешественник", None],
                      100: ["Опытный путещественник II", None],
                      250: ["Вокруг света",
                            ["Куда только судьба Вас не закидывала..."]]}],

                    [None,                                                              # 3
                     {10: ["Рискованное дело",
                           ["Всегда готов к любым неожиданностям",
                            "Риск - дело благородное"]],
                      25: ["Отчаянный геймер",
                           ["Важны лишь прямые руки"]],
                      50: ["Отчаянный геймер II",
                           ["Всегда готов к любым неожиданностям"]],
                      200: ["Мастер на все руки", None],
                      500: ["Экстримал", None]}],

                    [None,                                                              # 4
                     {5: ["Дело чести",
                          ["Рискуешь окончить жизнь как Пушкин",
                           "Астрологи объявлили неделю дуэлей. Цена на гробы выросла",
                           "Сегодня на одного покойника станет больше",
                           "Пощечина. В нашем стане еще один краснолицый...",
                           "Честь береги смолоду"]],
                      25: ["Дуэлянт",
                           ["То самое чувство, когда везенье на твоей стороне",
                            "Закаленный боями",
                            "Самая быстрая рука на всём Диком Западе"]],
                      50: ["Преследователь", None],
                      75: ["Преследователь II", None],
                      100: ["Кровожадный",
                            ["Еще не застыла кровь на губах"]],
                      250: ["Most wanted!",
                            ["За тобой уже выехали",
                             "Ваш взгляд заставляет содрогнуться"]],
                      500: ["Серийный убийца", None],
                      1000: ["Маньяк",
                             ["Безумие - это не предел",
                              "Дуэль с Вами - это игра в ящик",
                              "Кто не спрятался, я не виноват!"]],
                      1666: ["Сатана", None],
                      2500: ["Вселенское зло", None]}],

                    [_cond_call_play,                                                   # 5
                     {3: ["Всегда готов", None],
                      10: ["Попытка не пытка", None],
                      15: ["Капкан", None],
                      30: ["Опытный охотник",
                           ["Охота на крупную дичь"]],
                      50: ["Командир отряда",
                           ["Вы знаете толк в командной игре",
                            "Без Вас тиммейты - никто"]],
                      100: ["Полководец", None],
                      250: ["Генерал", None],
                      500: ["Генералиссимус", None]}],

                    [_cond_agent,                                                       # 6
                     {7: ["Тайный агент",
                          ["Шпион, молчавший длительное время, найден!"]]}],

                    [_cond_fast_msg,                                                    # 7
                     {300: ["Неудержимый", None],
                      500: ["Быстрее ветра", None],
                      800: ["Молниеносный", None],
                      1000: ["Сверхзвуковой", None],
                      1500: ["Повелитель времени", None],
                      3000: ["К бесконечности", None]}],

                    [None,                                                              # 8
                     {2: ["Двухкратный чемпион", None],
                      5: ["Пятикратный чемпион", None],
                      10: ["Уворотливая мишень", None],
                      25: ["Бронированный", None],
                      50: ["Мертвец", None],
                      75: ["Призрак", None],
                      100: ["Дух Дуэлей", None]}],

                    [_cond_bracket,                                                     # 9
                     {10: ["Капелька веселья", None],
                      25: ["Веселый роджер", None],
                      50: ["Железнодорожная скоба",
                           ["Был ограблен небольшой склад))"]],
                      100: ["Вагон и маленькая тележка))",
                            ["Когда и вагона мало..."]],
                      150: ["Промышленный размах I", None],
                      200: ["Промышленный размах II", None],
                      250: ["Промышленный размах III",
                            ["Потребители довольны)"]],
                      500: ["Скобкофилия",
                            ["Уже как заболевание..."]],
                      1000: ["Болезнь прогрессирует))) I", None],
                      2500: ["Болезнь прогрессирует)) II", None],
                      5000: ["Болезнь прогрессирует) III", None],
                      10000: ["В масштабах вселенной", None]}],

                    [_cond_eat,                                                         # 10
                     {5: ["Кулинар",
                          ["Вы знаете толк в еде"]],
                      15: ["Гурман",
                           ["Тебе так просто не угодишь)"]]}],

                    [_cond_stickers,                                                    # 11
                     {13: ["Чертова дюжина стикеров", None],
                      50: ["Актёр",
                           ["Сменить маску как два пальца..."]],
                      150: ["Эмоциональный", None],
                      500: ["Человек «Стикер»",
                            ["Это уже болезнь...",
                             "Для тебя жизнь без стикеров невозможна"]],
                      1000: ["Стикероапокалипсис", None],
                      2500: ["Стикероапокалипсис II", None],
                      5000: ["Стикероапокалипсис III", None]}],

                    [_cond_butthurt,                                                    # 12
                     {1: ["С огоньком",
                          ["Дело пахнет жареным"]],
                      10: ["В лепёшку!",
                           ["Уже начала подгорать..."]],
                      25: ["Реактивная тяга",
                           ["Ещё чуть-чуть и оторвётся от земли..."]],
                      40: ["30-тикратный чемпион по бомбёжке",
                           ["Первая ступень отделилась..."]],
                      61: ["Космонавт",
                           ["Достигший первой космической скорости"]],
                      100: ["Эксперт магии Огня", None]}],

                    [_cond_repost,                                                      # 13
                     {5: ["Книжный червь", None]}],

                    [_cond_inform_me,                                                  # 14
                     {10: ["Молот справедливости", None]}],

                    [_cond_symbol,                                                      # 15
                     {666: ["Приспешник Дьявола", None],
                      5000: ["+5 к красноречию", None],
                      9000: ["Over 9000", None],
                      25000: ["Язык - друг мой, враг мой!", None],
                      50000: ["Находка для шпиона", None],
                      100500: ["100500", None],
                      500000: ["0,5 млн букв? Пф-ф-фигня!", None]}],

                    [_cond_smile,                                                       # 16
                     {25: ["Эмоции через край", None],
                      100: ["100 смайликов", None],
                      500: ["500 смайликов", None]}],

                    [_cond_gif,                                                         # 17
                     {15: ["GIF-Менеджер", None],
                      50: ["GIF-Мастер", None],
                      150: ["Властелин гифок", None]}],

                    [_cond_scream,                                                     # 18
                     {10: ["Орк", None],
                      100: ["Оральный хор", None]}],

                    [_cond_picture,                                                     # 19
                     {5: ["Художник", None],
                      50: ["Художественная выставка", None],
                      150: ["Третьяковская галерея", None]}],
                      
                    [_cond_swear,                                                       # 20
                     {75: ["Орк-Сквернослов", ["Я этого не одобряю!"]],
                      300: ["Орк-Матершинник", ["Остановись, окоянный!"]],
                      900: ["Орк-Сапожник", ["Хуже черной метки..."]]}],
                    
                    [_cond_dont_understand,                                             # 21
                     {10: ["Непонятливый", None]}],
                    
                    [_cond_leave,                                                       # 22
                     {2: ["Забвение", ["Он ушёл, но обещал вернутся...", "Ушёл в закат..."]],
                      15: ["Экзекуция", ["Бедный йорик!", "Сжечь ведьму!"]]}],
                    
                    [_cond_bad_words,                                                   # 23
                     {10: ["-10 к красноречию", None],
                      100: ["Неисправимый", ["Их или ихний? Да какая разница..."]]}],

                    [_cond_caller,                                                      # 24
                     {25: ["Рупор", None],
                      75: ["Агитатор", None],
                      150: ["Глас народа", None]}],

                    [_cond_thx,                                                         # 25
                     {20: ["Вежливый", None],
                      100: ["Само благородство", ["Найти таких людей сложно в наши дни..."]]}],

                    [_cond_audio,                                                       # 26
                     {7: ["Аудиофил", None],
                      50: ["Меломан", None],
                      150: ["Музыковед", None]}],

                    [_cond_audio_message,                                               # 27
                     {300: ["Болтун", ["5 минут голосовых сообщений? Пф. Ерунда!"]],
                      900: ["Длинный язык", ["Прошло только полчаса..."]],
                      1800: ["Долгий разговор", ["Ровно 1 час голосовых"]],
                      10800: ["Монстр общения", None]}]
                    
                    ]
