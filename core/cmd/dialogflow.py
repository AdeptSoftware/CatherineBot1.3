# https://cloud.google.com/dialogflow/docs/quick/api
# Если будет ошибка "Token must be a short-lived token" - синхронизировать время на ПК с нужным часовым поясом
from dialogflow_v2.proto.session_pb2 import TextInput, QueryInput, QueryParameters
import dialogflow_v2

import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google.json"


# В зависимости от настроек агента в DialogFlow
# AUTOMATIC SPELL CORRECTION = On | Threshold = 0.2
# Позволяет задавать пороги распознавания текста и выдавать ответы
# В самом агенте можно изменять вопросы и ответы без перезагрузки бота
class Agent:
    def __init__(self):
        self._session = dialogflow_v2.SessionsClient()
        self._path = self._session.session_path("catherine-cilind", "Catherine")

    @staticmethod
    def make(action, text, score=1.0):
        return {"text": text, "score":  score, "action": action}

    def answer(self, text):
        try:
            t_input = TextInput(text=text, language_code="ru")
            q_input = QueryInput(text=t_input)
            q_params = QueryParameters(time_zone="Europe/Moscow")  # "Asia/Dubai"
            res = self._session.detect_intent(session=self._path, query_input=q_input, query_params=q_params)
            if not res.query_result.action:
                return None
            return {"text": res.query_result.fulfillment_text,
                    "score":  res.query_result.intent_detection_confidence,
                    "action": res.query_result.action}
        except Exception as err:
            return self.make(None, str(err))
