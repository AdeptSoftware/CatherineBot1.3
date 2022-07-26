# 19.01.2019
from core.instance import *
import application_data
import codecs
import time
import json
import core.yandex_api


_INI        = "app.json"
_USERDATA   = "userdata.json"


# ======== ========= ========= ========= ========= ========= ========= =========
# получение дефолтовых настроек
def get_default_option(section, param, default):
    if default is None:
        dd = application_data.get_default_storage_data(time.time())
        if "option" in dd and section in dd["option"] and param in dd["option"][section]:
            return dd["option"][section][param]
    return default


class _DataStorage:
    def __init__(self):
        # копия хранится в Яндекс диске
        self._data = None

    # поиск опции по ключу
    def get(self, section, param, default=None):
        try:
            return self._data["option"][section][param]
        except Exception as err:
            app().log("Параметр option."+str(section)+'.'+str(param)+" - не найден!", err)
            return get_default_option(section, param, default)

    # добавление / обновление пользователя
    def _update_user(self, user, nick, group_name):
        if user is not None:
            if user["id"] not in self._data["users"]:
                self._data["users"][user["id"]] = {"nick": None, "user": user}
            else:
                self._data["users"][user["id"]]["user"] = user
            self._data["users"][user["id"]]["next_update"] = int(time.time()) + self.get("updates", "user_profile")
            if nick is not None:
                if self._data["users"][user["id"]]["nick"] is None:
                    self._data["users"][user["id"]]["nick"] = {}
                if group_name not in self._data["users"][user["id"]]["nick"]:
                    self._data["users"][user["id"]]["nick"][group_name] = []
                for n in nick:
                    if n not in self._data["users"][user["id"]]["nick"][group_name]:
                        self._data["users"][user["id"]]["nick"][group_name] += [n]
                _list = []
                for nick in self._data["users"][user["id"]]["nick"][group_name]:
                    if nick not in _list:
                        _list += [nick]
                    else:
                        t = 0
                self._data["users"][user["id"]]["nick"][group_name] = _list
            return self._data["users"][user["id"]]
        return None


class _UserProfile:
    def __init__(self, profile):
        self._profile = profile

    def is_exist(self):
        return self._profile is not None

    def domain(self):
        if self._profile is None or "user" not in self._profile:
            return None
        return self._profile["user"]["domain"]

    def full_name(self):
        if self._profile is None or "user" not in self._profile:
            return "?"
        return self._profile["user"]["first_name"] + " " + self._profile["user"]["last_name"]

    def group(self, nickname, default=None):
        if self._profile:
            for key in self._profile["nick"]:
                if nickname in self._profile["nick"][key]:
                    return key
        return default

    def nick(self, group="Vainglory", _all=False, default="?"):
        if self._profile and self._profile["nick"] is not None:
            if not group:
                _list = []
                for key in self._profile["nick"]:
                    for name in self._profile["nick"][key]:
                        if name not in _list:
                            if not _all:
                                return name
                            _list += [name]
                return _list
            else:
                try:
                    if _all:
                        return self._profile["nick"][group]
                    return self._profile["nick"][group][0]
                except (KeyError, IndexError, TypeError):
                    default = "[id%d|%s]" % (self._profile["user"]["id"], self._profile["user"]["first_name"])
        if default is None:
            default = self.full_name() or "?"
        if _all:
            return [default]
        return default

    def key(self, k, default):
        try:
            return self._profile["user"][k]
        except (KeyError, TypeError):
            return default


class DataStorage(_DataStorage):
    def __init__(self, data):
        _DataStorage.__init__(self)
        self._data = data[0]
        self._userdata = data[1]

    # получить изображение пользователя (им же и установленное на бота)
    def get_userdata(self, user_id):
        if user_id in self._userdata:
            return self._userdata[user_id]
        return None

    # если мы ищем по user_id игрока, то групп можно указать потом в _UserProfile.nick
    def user_profile(self, value, group=None):
        if type(value) is int:
            if value > 0:
                flag = (value in self._data["users"])
                if not flag or time.time() > self._data["users"][value]["next_update"]:
                    res = app().vk.call("users.get", {"user_ids": value,
                                                      "fields": "domain,sex,online,can_write_private_message,city",
                                                      "name_case": "nom"})
                    self._update_user(res[0], None, None)
                    flag, value = True, res[0]["id"]
                if flag:
                    return _UserProfile(self._data["users"][value])
        else:
            for _id in self._data["users"]:
                if self._data["users"][_id]["nick"] is not None:
                    if group is None:
                        for key in self._data["users"][_id]["nick"]:
                            if value in self._data["users"][_id]["nick"][key]:
                                return _UserProfile(self._data["users"][_id])
                    elif group in self._data["users"][_id]["nick"] and value in self._data["users"][_id]["nick"][group]:
                        return _UserProfile(self._data["users"][_id])
        return _UserProfile(None)

    def user_profile_by_domain(self, domain):
        for _id in self._data["users"]:
            if "user" in self._data["users"][_id] and \
                    "domain" in self._data["users"][_id]["user"] and \
                    self._data["users"][_id]["user"]["domain"] == domain:
                return _UserProfile(self._data["users"][_id])
        return _UserProfile(None)

    def user_profile_by_nick(self, nick):
        for _id in self._data["users"]:
            if "user" in self._data["users"][_id] and \
                    "nick" in self._data["users"][_id]["user"] and \
                    self._data["users"][_id]["user"]["nick"]:
                for group in self._data["users"][_id]["user"]["nick"]:
                    if nick in self._data["users"][_id]["user"]["nick"][group]:
                        return _UserProfile(self._data["users"][_id])
        return _UserProfile(None)

    # загрузка ников
    def load_nicknames(self, users, group_name):
        offset = 0
        user_ids = ""
        for domain in users:
            if len(users[domain]) != 0:
                user_ids += ','+domain
                offset += 1
            if offset == 1000:
                self._load_nicknames(user_ids[1:], users, group_name)
                # обнулим
                user_ids = ""
                offset = 0
        if user_ids != "":
            self._load_nicknames(user_ids[1:], users, group_name)

    def _load_nicknames(self, user_ids, users, group_name):
        # отправим запрос
        try:
            res = app().vk.call("users.get", {"user_ids": user_ids,
                                              "fields": "domain,sex,online,can_write_private_message,city",
                                              "name_case": "nom"})
            if res is not None:
                for r in res:
                    if r["domain"] in users:
                        self._update_user(r, users[r["domain"]], group_name)
                        users.pop(r["domain"])
                #   else: страница пользователя удалена или заморожена
            else:
                raise RuntimeError("Список пользователей не удалось получить! (Обновление ников)")
        except Exception as err:
            app().log("Обновление ников завершено с ошибкой: "+str(err))
            return False
        return True

    # ===========================

    def s_get(self, user_id):
        if "stats" in self._data:
            if user_id in self._data["stats"]:
                return self._data["stats"][user_id]
        else:
            self._data["stats"] = {}
        # ====================================
        default = {"last": ["", 0, 0],
                   "word": [0, 0],
                   "symbol": 0,
                   "achievements": {},
                   "rank": 0}
        # ====================================
        self._data["stats"][user_id] = default
        return default


# ======== ========= ========= ========= ========= ========= ========= =========

class StorageManager(_DataStorage):
    def __init__(self):
        super().__init__()
        self._data = application_data.get_default_storage_data(time.time())
        self._userdata = {}
        self._disk = core.yandex_api.Wrapper()
        self._root = None
        self._is_init = False

    def data(self):
        return [self._data, self._userdata]

    def get(self, filename, encoding="utf-8"):
        try:
            string = self._disk.download(self._root + '/' + filename, encoding)
            return json.loads(string.encode(encoding))
        except Exception as err:
            app().log("Loading file: " + filename + '\n' + str(err))
        return None

    def is_init(self):
        return self._is_init

    # создание
    def create(self, token, root_directory: str):
        self._root = root_directory + self._data["version"]
        if self._disk.create(token):
            try:
                if not self._disk.exists(self._root):
                    self._disk.mkdir(self._root)
                if not self._disk.exists(self._root+"/logs"):
                    self._disk.mkdir(self._root+"/logs")
            except Exception as err:
                app().log(str(err))
                return False
            return True
        return False

    def log(self, thread_name, text):
        if thread_name == "MainThread":
            thread_name = "main"
        path = self._root+"/logs/thread_"+str(thread_name)+'.txt'
        self._disk.upload(path, self._disk.download(path) + '\n' + text)

    # обновление данных
    def update_disk(self, forcibly=False, load=False):
        try:
            if not forcibly and self._data["last_update"]+int(time.time()) < self.get("updates", "disk"):
                return False
            if load:
                vg = self.get("backup/nicknames/Vainglory.json")
                dr = self.get("backup/nicknames/DragonRaja.json")
                string = self._disk.download(self._root + '/' + _INI)
                if string != "":
                    res = json.loads(string)
                    if res["version"] == self._data["version"]:
                        self._data["last_update"] = int(time.time())
                        for key in res:
                            if key in self._data:
                                if key not in ["users", "stats"]:
                                    self._data[key] = res[key]
                                elif key == "users":
                                    for id in res[key]:
                                        if "nick" in res[key][id]:
                                            res[key][id]["nick"] = {}
                                            if id in vg:
                                                res[key][id]["nick"]["Vainglory"] = vg[id]
                                            if id in dr:
                                                res[key][id]["nick"]["DragonRaja"] = dr[id]
                                        self._data[key][int(id)] = res[key][id]
                                else:
                                    for _id in res[key]:
                                        __id = int(_id)
                                        self._data[key][__id] = {}
                                        for k in res[key][_id]:
                                            if k == "achievements":
                                                self._data[key][__id][k] = {}
                                                for a in res[key][_id][k]:
                                                    self._data[key][__id][k][int(a)] = res[key][_id][k][a]
                                            else:
                                                self._data[key][__id][k] = res[key][_id][k]
                    print("Disk loaded!")

            else:
                if not app().debug():
                    data = self._data.copy()
                    if "duel" in data:
                        data.pop("duel")
                    self._disk.upload(self._root + '/' + _INI, json.dumps(data))
                    print("Disk updated!")
        except Exception as err:
            app().log(str(err))
            return False
        self._is_init = True
        return True

    # обновление списка картинок
    def refresh_userdata(self):
        # загрузим пикчи
        string = self._disk.download(self._root + '/' + _USERDATA)
        if string != "":
            obj = json.loads(string)
            self._userdata.clear()
            for nick in obj:
                self._userdata[nick] = obj[nick]

    # добавление в вывод по нику картинок и прочего
    def update_userdata(self, nickname, attachments):
        att = []
        audio = []
        for key in attachments:
            if attachments[key] is not None:
                a = key+str(attachments[key]["owner_id"])+'_'+str(attachments[key]["id"])
                if key == "audio":
                    audio += [a]
                else:
                    att += [a]
        att += audio
        if nickname not in self._userdata or self._userdata[nickname] != att:
            if attachments["photo"] is not None:
                app().vk.call("photos.copy", {"owner_id": attachments["photo"]["owner_id"],
                                              "photo_id": attachments["photo"]["id"]})
            self._userdata[nickname] = att
            try:
                self._disk.upload(self._root + '/' + _USERDATA, json.dumps(self._userdata))
                return len(self._userdata[nickname])
            except Exception as err:
                app().log(str(err))
        return 0
