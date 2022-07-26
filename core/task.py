# 14.08.2019 Менеджер задач
import threading
import time


# Ошибки внутри влияют на поток, но не на переменную (acquire и release - вызываются всегда)
# Хотя в целях сохранения правильной работы программы ошибки стоит обрабатывать
# Пример работы
# x = Variable(0)
# ... где-то в потоке:
# with x:
#   x.value += 2
class SafeVariable:
    def __init__(self, value):
        self.value = value
        self._lock = threading.RLock()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


# Создает очередь объектов, управляя их уничтожением
# После использования обязательно вызвать stop()
class _TemporaryObjectManager:
    def __init__(self, name, fn_error=None):
        self._t = threading.Thread(name=name, target=self._update)
        self._q = SafeVariable(dict())
        self._fn_error = fn_error                # print при ошибке не завершает процесс
        self._exit = False
        self._t.start()

    def _get(self, key=0):
        with self._q:
            if self._q.value:
                if not key:
                    return self._q.value.pop(self._next())
                return self._q.value.pop(key)
        return None

    def _put(self, item):
        with self._q:
            if item[0] in self._q.value:
                self._q.value[item[0]] += [item[1]]
            else:
                self._q.value[item[0]] = [item[1]]

    def _next(self):
        with self._q:
            if self._q.value:
                return sorted(self._q.value.keys())[0]
        return None

    # cmp должно возвращать результат сравнения (True/False)
    # cmp(append_content, cmp_data) or !!without cmp_data!! if data is None
    def search(self, cmp, data=None, pop=False):
        with self._q:
            if not self._q.value:
                return None
            for key in self._q.value:   # key = call_time
                for obj in self._q.value[key]:
                    if (data is None and cmp(obj)) or (data is not None and cmp(obj, data)):
                        try:
                            if pop:
                                self._q.value[key].remove(obj)
                                if not len(self._q.value[key]):
                                    self._q.value.pop(key)
                        finally:
                            return key, obj
        return None

    def stop(self):
        self._exit = True

    def _pop(self, key):
        self._get(key)

    def _update(self):
        while not self._exit:
            try:
                key = self._next()
                if key is None or key-time.time() > 0:
                    time.sleep(1)
                    continue
                self._pop(key)
            except Exception as err:
                if self._fn_error is not None and self._fn_error(err):
                    return


class CooldownManager(_TemporaryObjectManager):
    def append(self, delta, data):
        self._put((int(time.time()+delta), data))

    def restore(self, obj):
        if obj and obj[0] > time.time():
            self._put(obj)

    def delete(self, obj):
        with self._q:
            if self._q.value:
                if obj[0] in self._q.value:
                    self._q.value.pop(obj[0])


class TaskManager(_TemporaryObjectManager):
    # fn не должна ничего возвращать
    def append(self, delta, fn, data=None):
        if int(delta) <= 0:
            self._call(fn, data)
        else:
            self._put((int(time.time() + delta), (fn, data)))

    # Поиск: self.search(cmp, (fn, data), pop)

    @staticmethod
    def _call(fn, data):
        if data is None:
            fn()
        else:
            fn(data)

    def _pop(self, key):
        for obj in self._get(key):
            self._call(obj[0], obj[1])
