# 19.09.2020 Менеджер команд (DialogFlow)
import core.task
import core.cmd.handlers as _h
import core.cmd.dialogflow

import core.rank_system.rs as _rs
import core.rank_system.on_action as _act

# Через обращение:
# [Announcement], [Search], [Abbreviation], Chaos, MeaningLife, WhatsUp, Mood, Bad,
# Thx, DoNotAfraid, DoNotTired, LetsGo, ReachAgreement, Again, [Hit], [DateTime],
# [Variants], [Calc], [Rnd], [WhereAmI], MiniGame, There, Love, Marry, WhatULike,
# Beautiful, UPurpose, [Timetable], [Save], IHateU, Lies, [RepeatText], KnockKnock

# Просто так: [IsTrue], [Achievements], [FindPlayer], [Goodbye], {Sleep, Hello}

# Похерены будут: F50Links, WhatCharacter

# Константы типа команды
_ALL         = 0
_EVERYONE    = 1
_ADMIN       = 2
# Константы типа доступности
_BREAK       = 0
_AVAILABLE   = 1
_COOLDOWN    = 2


def _cmd(obj, data):     # data = (cmd, uid)
    return not obj[0] and obj[1] == data[0] and obj[2] == data[1]


def _user(obj, uid):
    return obj[0] and obj[1] == uid


class CommandManager:
    def __init__(self):
        self._agent = core.cmd.dialogflow.Agent()
        self._used_cmd = None
        self._chats = {}
        
        self.action = None              # Текущее действие (команда)
        # Константы
        self._remember_time = 30        # Время запоминания, сек
        self._setting()
        
    def add_chat(self, data):
        # data.keys() = [ "id", "handlers", "admins", "group", "blocked_users", "blocked_cmd" ]
        self._chats[data["id"]] = data

    def run(self, fn_error):
        self._used_cmd = core.task.CooldownManager("UsedCommand", fn_error)

    def stop(self):
        self._used_cmd.stop()

    def answer(self, msg):
        if msg.pid not in self._chats or msg.uid in self._chats[msg.pid]["blocked_users"]:
            return None
        msg.chat = self._chats[msg.pid]         # Не перемещать ниже. Иначе будет трудно уловимая ошибка!
        if self._handlers(msg) or not msg.list or not msg.item["text"]:
            return None
        # Проверим пользователь уже ведет диалог с нами или нет?
        last = self._used_cmd.search(_user, msg.uid, False)
        if not msg.ref and last:
            msg.ref = True
        # Ищем подходящий ответ
        self.action = self._built_in_commands(msg) or self._dialogflow(msg)
        if self.action:
            if self.action["action"] is None:
                return self.action  # Ошибка при обращении к dialogflow
            if self.action["score"] >= 0.86:
                status = self._available(self.action["action"], msg.uid, self._chats[msg.pid]["admins"])
                self._remember(msg.uid, last)
                if status == _AVAILABLE:
                    return self._unique(self.action["action"], str(msg.uid)) or self.action
                elif status == _COOLDOWN:
                    return self._agent.make("RepeatCommand", self.repeat_cmd)
                return None
        return self._build_in_questions(msg, last)

    def _remember(self, uid, last):   # Запомним время последнего обращения к нам
        if last:
            self._used_cmd.delete(last)
        self._used_cmd.append(self._remember_time, (True, uid))

    def _built_in_commands(self, msg):
        for cmd in self.handlers:
            if cmd in self._chats[msg.pid]["blocked_cmd"]:
                continue
            if not msg.ref and cmd not in self.unref:
                continue
            self.action = self.handlers[cmd](msg)
            if self.action:
                if type(self.action) is str:
                    return self._agent.make(cmd, self.action)
                answer = self._agent.make(cmd, None)
                for key in self.action:
                    answer[key] = self.action[key]
                return answer
        return None

    def _build_in_questions(self, msg, last):
        if not msg.ref:
            return None
        for q in self.question:
            if q[0] == msg.list[0]:
                self._remember(msg.uid, last)
                return self._rnd("SimpleQuestion", q[1])
        if msg.list[-1] == '?':
            return self._rnd("SimpleQuestion", self.last_q)
        return None

    def _dialogflow(self, msg):
        if msg.ref:
            return self._agent.answer(msg.get())
        return None

    # Проверка доступна ли команда
    def _available(self, cmd, uid, admins):
        p = self.default
        if cmd in self.params:
            p = self.params[cmd]
        if p[0] == _ADMIN and uid not in admins:
            return _BREAK
        if p[2] <= 0:
            return _AVAILABLE
        # Получим информацию о текущем статусе команды
        if p[0] == _ALL:
            uid = None
        count = p[1]
        if p[1] <= 0:                   # Неограниченное количество ответов + кд между ответами
            status = self._used_cmd.search(_cmd, (cmd, uid), False)
            if not status:              # Запомним ответ
                self._used_cmd.append(p[2]*60, (False, cmd, uid))
                return _AVAILABLE
        else:                           # Ограниченное количество ответов (кд после исчерпания лимита)
            status = self._used_cmd.search(_cmd, (cmd, uid), True)
            if status:
                count = status[1][3]    # Оставшееся количество ответов
            count -= 1
            data = (False, cmd, uid, count)
            if count >= 0:
                self._used_cmd.append(p[2]*60, data)
                return _AVAILABLE
            self._used_cmd.restore((status[0], data))
        if count == -1:
            return _COOLDOWN
        return _BREAK

    # Проверка на необходимость уникального ответа
    def _unique(self, cmd, uid):
        if uid in self.unique and cmd in self.unique[uid]:
            return self._rnd(cmd, self.unique[uid][cmd])
        return None

    def _rnd(self, cmd, answers):
        return self._agent.make(cmd, _h.x_rnd(answers))

    def _handlers(self, msg):
        if "user_actions" in self._chats[msg.pid]["handlers"]:   # Добавлен/Удален пользователь
            if _act.main(msg):
                return True
        if "achievements" in self._chats[msg.pid]["handlers"]:  # Ачивки и т.д
            self.action = self._agent.make("rs", "")
            self.action = _rs.main(msg)
            if self.action is not None:
                self.action = "rs[%d]" % self.action
                raise "Error in RankSystem"
        return False

    # ========= ========= ========= ========= ========= ========= ========= =========
    def _setting(self):
        self.default = (_ALL, 0, 0)
        self.params = {
            #       name            type   cnt cd      # cd - cooldown, min
            "Announcement":     (_ADMIN,    0, 0),
            "Bad":              (_EVERYONE, 1, 60),
            "Goodbye":          (_EVERYONE, 1, 1),
            "Hello":            (_EVERYONE, 1, 1),
            "IHateU":           (_EVERYONE, 1, 60),
            "Lies":             (_EVERYONE, 1, 60),
            "Love":             (_EVERYONE, 2, 5),
            "Marry":            (_EVERYONE, 1, 5),
            "MeaningLife":      (_ALL,      1, 5),
            "Mood":             (_ALL,      1, 5),
            "ReachAgreement":   (_EVERYONE, 1, 5),
            "Sleep":            (_EVERYONE, 1, 1),
            "Timetable":        (_ADMIN,    0, 0),
            "WhatsUp":          (_ALL,      1, 5),
            "WhoAmI":           (_EVERYONE, 3, 5),
            "UPurpose":         (_EVERYONE, 1, 5)
        }
        # команды, запускаемые без обращения:
        self.unref = ("IsTrue", "Achievements", "FindPlayer", "KnockKnock", "Sleep", "Hello", "Goodbye")
        # команды с общим обработчиком (не DialogFlow)
        self._q_why = ("Я не знаю", "Согласно пророчеству!", "Так исторически сложилось...", "Таков мой замысел!",
                       "Это выяснили британские ученые)", "Мне так подсказывает внутреннее чутьё)", "Просто поверь)",
                       "Во славу Сатане!", "Потому что это, возможно, бесплатно :)", "Тебе придется довериться мне)",
                       "Потому что каждый год около 200 человек умирают от нападения диких муравьёв :(")
        self.question = (
            ("где", ("Где-то рядом))", "Здесь", "Я не знаю :(", "В Мексике", "Где-то в Азии...", "В океане")),
            ("почему", self._q_why),
            ("зачем", self._q_why),
            ("кто", ("Божество?", "Тащер?", "Повелитель мертвых?", "Самурай?", "Сырный король?", "Повелитеь мух?",
                     "Авторитет?", "Диктатор?", "Мисс Вселенная?", "Паладин?", "Жнец душ?", "Победитель по жизни?",
                     "Великий маг и чародей?", "Фантазёр?", "Сферический конь в вакууме?", "Герой?", "Пельмень?",
                     "Хм, может быть ужас летящий на крыльях ночи?", "Хм, вурдалак?", "Белка-летяга?", "Еврей?",
                     "Джонни?", "Любитель рока?", "Меломан?", "Иллюзия?", "Старый хрящ?", "Кожаный мешок?")),
            ("какой", ("Не знаешь выбери то, что красивее", "Могу посоветовать только метод проб и ошибок)",
                       "Второй?", "Первый?", "Если бы я знала...", "Хм, сложный вопрос(")),
            ("кому", ("Тебе?", "Мне?", "Может быть Вадимке?", "Миожет быть Дмитрию?", "Я не в курсе.")),
            ("как", ("Никак(", "Это долгая история. Расскажу как-нибудь потом)", "Это долго объяснять...",
                     "Поговаривают, что для этого нужны прямые руки...", "Каком к кверху)", "Может админы знают?")))
        self.last_q = ("Да", "Да!", "Конечно)", "Вероятно, да)", "Нет", "Нет!", "Не", "Я не в курсе(")
        # команды с уникальным обработчиком (не DialogFlow)
        self.handlers = {
            "Abbreviation": _h.abbreviation,
            "Achievements": _h.achievements,
            "Announcement": _h.announcement,
            "Calc":         _h.calc,
            "DateTime":     _h.date,
            "FindPlayer":   _h.find_player,
            "Goodbye":      _h.goodbye,
            "Hello":        _h.hello,
            "Hit":          _h.hit,
            "HowMuch":      _h.how_much,
            "IsTrue":       _h.is_true,
            "RepeatText":   _h.repeat_text,
            "Rnd":          _h.rnd,
            "Sleep":        _h.sleep,   # "Timetable":    _h.timetable,
            "Variants":     _h.variants,
            "WhereAmI":     _h.where_am,
            "WhoAmI":       _h.who_am
        }
        # ответы при повторе
        self.repeat_cmd = ["&#128528;", "Не приставай", "Я же уже ответила...", "Может сменим тему?"]
        # уникальные ответы на некоторые команды
        self.unique = {
            "290168127": {
                "Hello": ["*молчание*", "Ну-ну", "А с тобой я не разговариваю!",
                          "Вот он.. вернулся. Ну вы поглядите на него!"],
                "Love": ["А я уже нет..", "Подлец! Как ты мог бросить меня тут?!", "Уйди с глаз долой."],
                "Marry": ["Нет!", "Еще чего!"]
            },
            "9752245": {
                "Hello": ["Привет Вадимка &#10084;&#65039;"],
                "Again": ["Прячь тут. Здесь и так много мертвых душ.", "А что в подсобке места уже нет?",
                          "Поговаривают, что лучше всего не прятать, а растворять в концентированной серной кислоте"]
            }
        }
