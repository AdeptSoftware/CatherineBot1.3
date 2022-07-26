# 24.10.2020 Парсер обсуждений с никами
from core.task import SafeVariable
from core.cmp_string import String
import requests
import re


# Ники с патча 1.3x больше не хранятся на ядиске, а загружаются только из обсуждений
class TopicManager:
    def __init__(self):
        self._topic = SafeVariable(list())
        self._data = {}

    def add(self, short_name, topic_id, fn_parser_id, ignore_domain, offset=0):
        parser = (_vg_parser, _interstellar_parser)
        with self._topic:
            result = (parser[fn_parser_id], topic_id, ignore_domain, offset)
            if short_name not in self._data:
                self._data[short_name] = { "index": len(self._topic.value),
                                           "out":   [result]}
                self._topic.value += [{}]
            else:
                self._data[short_name]["out"] += [result]

    def parse(self, short_name=None):
        with self._topic:
            for key in self._data:
                if not short_name or short_name == key:
                    self._topic.value[self._data[key]["index"]] = {}
                    for obj in self._data[key]["out"]:
                        res = _load(obj[0], obj[1], obj[2], obj[3])
                        for id in res:
                            if id not in self._topic.value[self._data[key]["index"]]:
                                self._topic.value[self._data[key]["index"]][id] = res[id]
                            else:
                                for value in res[id]:
                                    if value not in self._topic.value[self._data[key]["index"]][id]:
                                        self._topic.value[self._data[key]["index"]][id] += [value]
                cnt = len(self._topic.value[self._data[key]["index"]])
                print("Обновлен список «{0}». Найдено элементов: {1}".format(key, cnt))

    def content(self, domain, short_name):
        if short_name not in self._data:
            return None
        index = self._data[short_name]["index"]
        with self._topic:
            if domain in self._topic.value[index]:
                return self._topic.value[index][domain]
        return None

    def domain(self, content, short_name, threshold=0, cnt=5):
        if short_name not in self._data:
            return None
        result = []
        f = String(content.lower())
        abs_threshold = abs(threshold)
        index = self._data[short_name]["index"]
        with self._topic:
            for domain in self._topic.value[index]:
                if content in self._topic.value[index][domain]:
                    return domain, self._topic.value[index][domain]
                if threshold != 0:
                    for text in self._topic.value[index][domain]:
                        k = f.cmp_damerau_levenshtein(text.lower())
                        if k <= abs_threshold:
                            result += [(domain, text, k)]
                if threshold < 0:
                    for text in self._topic.value[index][domain]:
                        if f in text.lower():
                            result += [(domain, text, abs(len(text)-len(f)))]
        if result:
            if threshold < 0 and len(result) > 1:
                index, _list = [], []
                for i in range(0, len(result)):
                    val = (result[i][0], result[i][1])
                    if val in _list:
                        index += [i]
                    _list += [val]
                index.reverse()
                for i in index:
                    result.pop(i)
            return sorted(result, key=lambda kv: kv[2])[:cnt]
        return None


# ========= ========= ========= ========= ========= ========= ========= =========
_nick = re.compile(r"\b[A-Za-z0-9_]{3,80}\b")
_domain = re.compile(r"\"pi_author\" href=\"/(.+)[\"\'] rel")
_comment = re.compile(r"<div class=\"pi_text\">(.+)</div>")
_ex = ("f50", "catherine", "vainglory", "http", "https", "com", "dragons", "drag0ns", "wallchia", "blood",
       "3x3", "5x5", "3v3", "5v5", "html", "css", "php", "quot", "amp", "uncharted", "fantastic", "fifty",
       "joseph", "heros", "evolved", "heroes", "storm", "guild", "girl", "mobile", "legend", "legends")


def replace_codes(text):
    return text.replace('&quot;', '?').replace('&amp;', '&').replace('&#33;', '!').\
        replace('&#036;', '$').replace('&#092;', '\\').replace('&gt;', '>').\
        replace('&lt;', '<').replace('<br/>', '\n').replace('</a>', '').replace('&#39;', '\'')


def delete_image(text):
    while "<img" in text:
        s0 = text.find("<img")
        s1 = text.find(">", s0)
        if s1 < 0:
            text = text[:s0]
        else:
            text = text[:s0]+text[s1+1:]
    return text

# def xfn(s): return [s]

def _load(fn, topic_id, ignore_domain, offset=0):
    _dict = {}
    while True:
        res = requests.get("https://vk.com/"+topic_id, params={"offset": offset})
        if res.status_code == 200:
            domains = _domain.findall(res.text)
            comments = _comment.findall(res.text)
            if len(domains) != len(comments): # сообщение содержащее стикер/изображение
                print("Length domains({0}) != messages({1}). Offset: {2}".format(len(domains), len(comments), offset))
                offset += 20
                continue
            if len(domains) == 0:
                break
            for i in range(0, len(comments)):
                if domains[i] == ignore_domain:
                    continue
                comments[i] = replace_codes(comments[i])
                comments[i] = delete_image(comments[i])
                result = fn(comments[i])
                if result:
                    if domains[i] not in _dict:
                        _dict[domains[i]] = []
                    for r in result:
                        if r not in _dict[domains[i]]:
                            _dict[domains[i]] += [r]
            offset += 20
        else:
            break
    return _dict


def _vg_parser(comment):
    return _nick.findall(comment)


def _interstellar_parser(comment):
    while "<a href" in comment:
        s_index = comment.index("<a href")
        e_index = comment.index('>', s_index)
        if e_index != -1:
            comment = comment[:s_index]+comment[e_index+1:]
        else:
            break
    nicks = []
    for nick in _nick.findall(comment):
        if nick.lower() not in _ex and not nick.isnumeric():
            nicks += [nick]
    return nicks or [comment]