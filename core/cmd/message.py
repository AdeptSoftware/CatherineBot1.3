import core.storage as _storage
import core.strings
import re
_re_word = re.compile(r"(?:(?:\w+|\d+)-\w+|[_\w\d]+|\[id\d+\|.+?\]|@[_\w\d]+)")
_refs = core.strings.std_catherine_refs()


class Message:
    def __init__(self, item, profile):
        self.item = item
        self.chat = None
        self._profile = profile
        self.pid = self.item["peer_id"]
        self.uid = self.item["from_id"]

        self.fwd = []
        if "fwd_messages" in self.item:
            self.fwd += self.item.pop("fwd_messages")
        if "reply_message" in self.item:
            self.fwd += [self.item.pop("reply_message")]

        self.list = []
        self.prefix = ""
        self.ref = True
        
        self._prepare()
        self.parasite = []      # слово-паразит, идущее первым и портящее распознавание: "ну", "вообщем", ...
        while (self.list and self.list[0] in ("ну", "вообщем", 'и', 'а', "но")):
            self.parasite += [self.list.pop(0)]

    # Добавляет символы между слов
    @staticmethod
    def _sym(_list, text, span0, span1):
        data = text[span0:span1]
        data = ''.join(data.split(' '))
        if data:
            _list += [data]

    def split(self, _list, text):
        _list.clear()
        last_span = 0
        for obj in _re_word.finditer(text):
            span = obj.span()
            if span[0] - last_span > 0:
                self._sym(_list, text, last_span, span[0])
            _list += [text[span[0]:span[1]]]
            last_span = span[1]
        length = len(text)
        if last_span < length:
            self._sym(_list, text, last_span, length)

    def _prepare(self):
        self.list.clear()
        self.split(self.list, self.item["text"].lower().replace('ё', 'е'))
        if self.list and not self.is_word(self.list[0]):
            self.prefix = self.list.pop(0)
        if self.list:
            index = -1
            length = len(self.list)
            if not self.is_word(self.list[index]) and length > 1:
                index = -2
            if self.list[0] in _refs:
                self.list.pop(0)
                if length > 1 and not self.is_word(self.list[0]):
                    self.list.pop(0)
                return
            if self.list[index] in _refs:
                self.list.pop(index)
                if length > -index and not self.is_word(self.list[index]):
                    self.list.pop(index)
                return
        self.ref = False

    def get(self, start=0, end=None):
        res = ""
        for text in self.list[start:(end or len(self.list))]:
            if res and (self.is_word(text) or text == '-' or text.isdigit()):
                res += ' '
            res += text
        return res

    @staticmethod
    def is_word(text):
        for c in text:
            if ('a' <= c <= 'я') or ('А' <= c <= 'Я') or ('a' <= c <= 'z') or ('A' <= c <= 'Z') or \
                    c == 'ё' or c == 'Ё':
                return True
        return False

    def reference(self, get_nick=False, add_link=False, default=None, full=False):
        res = None
        if self._profile.is_exist():
            if get_nick:
                domain = self._profile.key("domain", None)
                if domain:
                    result = _storage.nick(domain, self.chat["group"])
                    if result:
                        res = result[0]
            if res is None:
                if full:
                    res = self._profile.full_name() or default
                else:
                    res = self._profile.key("first_name", default)
        if res is None:
            if default is None:
                return "@id" + str(self.uid)
            res = str(default)
        if add_link:
            return "[id{0}|{1}]".format(self.uid, res)
        return res

    def domain(self):
        return self._profile.domain()

    def is_men(self):
        return not self._profile.is_exist() or self._profile.key("sex", 2) == 2

    # case X 2 nom (До конца не доделано)
    # case: текущий падеж name
    # именительный – nom, родительный – gen, [дательный – dat], [винительный – acc], творительный – ins, предложный – abl
    @staticmethod
    def transform(name, case="acc"):
        lo = name.lower()
        if lo == "":
            return "он(а)"
        elif lo in ("себя", "себе", "собой"):
            return "ты"
        elif lo in ("всех", "всем"):
            return "все"
        # Женские имена оканч. на тв.согл.
        elif lo in ("катрин", "элизабет", "ирен"):
            return lo.capitalize()
        elif lo in ("ассоль", "айгюль"):
            return lo.capitalize()
        # Заимственные имена
        elif lo in ("ромео", "рене", "луи", "бруно", "лео", "пьеро", "гиви"):
            return lo.capitalize()
        elif case == "dat":
            if lo == "игорю":
                return "Игорь"
            if lo == "павлу":
                return "Павел"
            if lo == "ваде":
                return "Вадя"
        elif case == "acc":
            if lo == "павла":
                return "Павел"
            if lo == "игоря":
                return "Игорь"
        # Женские имена в 3-м склонении (оканчивающиеся на -ь): Любовь, Адель, Жизель, ...
        if case != "ins" and lo[:-1] in ("адел", "жизел", "любов", "нинел"):
            return (lo[:-1]+'ь').capitalize()
        if case == "ins" and lo[:-1] in ("адель", "жизель", "любовь", "нинель"):
            return (lo[:-1]).capitalize()
        # Мужские и женские имена, оканчивающиеся на -я, -ья, -ия, -ея
        if (case in ("gen", "dat", "abl") and lo[-2:] == "ии") or \
           (case in ("dat", "abl") and lo[-2:] == "ье") or \
           (case == "gen" and lo[-2:] == "ьи") or \
           (case == "acc" and lo[-2:] == "ью"):
            return (lo[:-1]+'я').capitalize()
        if (case == "ins" and lo[-3:] in ("ьей", "ией")):
            return (lo[:-2]+'я').capitalize()
        # Мужские и женские имена, оканчивающиеся на -а
        if (case in ("acc", "abl") and lo[-1] == 'у') or \
           (case == "ins" and lo[-2:] == "ой") or \
           (case == "gen" and lo[-1] == 'ы') or \
           (case == "dat" and lo[-1] == 'е'):
            return (lo[:-1]+'а').capitalize()
        # Мужские имена, оканчивающиеся на согласный и на –й:
        if (case in ("gen", "acc") and lo[-1] in ('я', 'a')) or \
           (case == "ins" and lo[-2:] in ("ем", "ом")) or \
           (case == "dat" and lo[-1] == 'ю') or \
           (case == "abl" and lo[-1] == 'е'):
            return (lo[:-1]+'й').capitalize()
        # Прочее
        sym = {}
        if case == "acc":
            sym = {'а': '', 'ю': 'я'}
        if case == "dat":
            sym = {'у': '', 'е': 'я', 'я': 'ь'}
        for key in sym:
            if key == lo[-1]:
                return (lo[:-1]+sym[key]).capitalize()

        # return lo.capitalize()  # Не нашли
