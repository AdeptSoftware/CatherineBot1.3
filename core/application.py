# 19.01.2019
import datetime
import threading
import core.vk.wrapper
import core.utils.convert
import core.yadisk_storage
from core.storage import set_topic_list
from core.event.eventer import Event, Manager
from core.cmd.manager import CommandManager
from core.cmd.message import *

from vk_api.bot_longpoll import VkBotEventType

DEFAULT_PID = 2000000001

# ======== ========= ========= ========= ========= ========= ========= =========
class Application:
    def __init__(self):
        self.cmd = CommandManager()
        self._debug = False
        self._ref_names = []            # имена аккаунта
        self._storage = {}              # не сохраняются при завершении программы, но необходимы для работы
        self._disk = None               # доступ к яндекс диску
        self.disk = None                # доступ к сохранкам на яндекс диске
        self.vk = None                  # доступ к аккаунту vk
        self.eventer = None             # менеджер событий
        self._info = [0, ""]            # информация об ошибках [cnt, last_err]

    # Создание и инициализация данных
    def create(self, root_directory, token, is_debug=False, ignore_data_update=False):
        if is_debug:
            print("Инициализация...")
        # Вернет True, если все создано успешно
        self.eventer = core.event.eventer.Manager()
        self._disk = core.yadisk_storage.StorageManager()
        self.disk = core.yadisk_storage.DataStorage(self._disk.data())
        self.vk = core.vk.wrapper.Wrapper()
        self._debug = is_debug

        # Инициализация яндекс диска и вк
        try:
            if not self._disk.create(token, root_directory):
                return False
            auth = self._disk.get("auth.json")
            if auth is None:
                app().log("Данные для входа не найдены!")
                return False
            if not self.vk.create(auth["token"], auth["id"]):
                return False
        except Exception as err:
            return self.log(str(err))
        # инициализируем диалоги:
        if is_debug:
            # auth["dialogs"]["debug"]["group"] = "Vainglory"
            self.cmd.add_chat(auth["dialogs"]["debug"])
        else:
            for key in auth["dialogs"]:
                if key != "debug":
                    self.cmd.add_chat(auth["dialogs"][key])
        # инициализируем события
        for name in auth["topics"]:
            set_topic_list(name, auth["topics"][name])
        self._initialize_events()
        self.eventer.start()
        # запускаем обновление ников
        if not ignore_data_update:
            self._disk.update_disk(True, True)
            self._disk.refresh_userdata()
            self.eventer.forcibly_update("data_updater")
        # Выведем информацию по поводу запуска
        # self.vg.start()
        self.vk.start()
        self.log("Бот активирован", use_print=True)
        return True

    # дебаг или не дебаг
    def debug(self):
        return self._debug

    # получить параметр из хранилища
    def get(self, param, default=None):
        if param in self._storage:
            return self._storage[param]
        return default

    # записать параметр в хранилище
    def set(self, param, value):
        print("Update storage: " + str(param) + " = " + str(value))
        self._storage[param] = value

    # Запись лога (в личку vk - себе)
    def console(self, text, obj=None):
        if obj is not None:
            text += '\n' + core.utils.convert.obj2str(obj)
        self.vk.console(text)

    # Запись лога (на Яндекс-диск)
    def log(self, text, obj=None, use_print=True, _time=True):
        if obj is not None:
            text += '\n' + core.utils.convert.obj2str(obj)
        if _time:
            text = "["+str(self.time())+"]: "+text
        if not self._debug:
            if use_print:
                print(text)
            try:
                self._disk.log(threading.currentThread().name, text)
            except Exception as err1:
                try:
                    text += "\n _disk: " + str(err1)
                    self.vk.console(text, True)
                except Exception as err2:
                    print(text + "\n vk: " + str(err2))
        else:
            print(text)
        return False

    # Получить текущее время
    def time(self):
        if not self._debug:
            h = self.disk.get("app", "timezone")
            if h is None:
                return datetime.datetime.now() + datetime.timedelta(days=-40*365)
        else:
            h = 1
        return datetime.datetime.now() + datetime.timedelta(hours=h)

    # Завершение работы
    def exit(self, cause, safe=False):
        self.log("Завершена работа по причине: "+cause, _time=not safe)
        self.eventer.stop()
        self.cmd.stop()
        self.vk.stop()
        try:
            if not self._debug:
                self._disk.update_disk(True)
        finally:
            exit(0)

    def _err(self, err, info=""):
        if not self._info[1] or self._info[1] != str(err.args[0]):
            text = "%s (cnt:%d)\n%s: " % (err, self._info[0], str(self.cmd.action))
            if info:
                text += info
            self.log(text)
            self._info[1] = str(err.args[0])
            self._info[0] = 1
        else:
            self._info[0] += 1

    def update_disk(self):
        self._disk.update_disk(True)

    def _read(self, item):
        ans = self.cmd.answer(Message(item, self.disk.user_profile(item["from_id"])))
        if ans is not None:
            if ans["action"] is not None:
                self.vk.send(item["peer_id"], ans)
            elif ans["text"]:
                self._err(ans["text"])

    # основной цикл сообщений
    def run(self):
        e = None
        self.cmd.run(self.log)
        lp = self.vk.get_long_poll()
        if self._debug:
            self.vk.send_text(DEFAULT_PID, "Ready!")
        while True:
            try:
                for e in lp.listen():
                    if e.type == VkBotEventType.MESSAGE_NEW:
                        self._read(e.obj["message"])
                    else:
                        print("New Bot Event Type ({0})".format(e.type))
            except Exception as err:
                self._err(err, "\nmsg=\"%s\"" % e.obj["text"])

    # ==== ========= ========= ========= ========= ========= ========= =========
    # Методы, которые нельзя вызывать

    # Инициализация событий
    def _initialize_events(self):
        import core.event.handlers.fn_update as _u
        # События чатов
        events = self._disk.get("events.json", "utf-8")
        if events:
            for i in range(len(events)):
                self.eventer.new(Event("timetable"+str(i), _u.update_timetable, events[i]))
        # Прочие события
        self.eventer.new(Event("data_updater", _u.update_data))
        self.eventer.new(Event("data_topics",  _u.update_topics))

    # вызывается редко и только админом
    def _admin_console(self, item):
        try:
            if "!refresh" in item["text"]:
                text = "обновление"
                if "userdata" in item["text"]:
                    text += " userdata"
                    self._disk.refresh_userdata()
                elif "nick" in item["text"]:
                    flag = False
                    text += " списка ников"
                    if "all" in item["text"]:
                        text += " (расширенное)"
                        flag = True
                    self.eventer.forcibly_update("data_updater", {"flag": True, "all": flag})
                self.vk.console("Успешно завершено! " + text)
        except Exception as err:
            self.log(str(err))
