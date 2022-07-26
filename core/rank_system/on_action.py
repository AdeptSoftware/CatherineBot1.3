from core.instance import *
import core.strings


# обработка действий пользователя
def main(msg):
    if "action" not in msg.item:
        return False
    # {"type": "chat_title_update" "text": "R2D3"}
    # {'type': 'chat_pin_message', 'member_id': 481403141, 'conversation_message_id': 133, 'message': 'd'}
    # {'type': 'chat_unpin_message', 'member_id': 481403141, 'conversation_message_id': 133}
    # {'type': 'chat_kick_user', 'member_id': 481403141}
    if msg.item["action"]["type"] == "chat_kick_user":
        if msg.item["from_id"] == msg.item["action"]["member_id"]:
            app().vk.send_text(msg.pid, core.strings.rnd(core.strings.on_leave()) +
                               yourself_action(msg.pid, msg.item["from_id"], True, msg.is_men()))
        else:
            app().vk.send_text(msg.pid, core.strings.rnd(core.strings.on_kick()))
    # {'type': 'chat_invite_user', 'member_id': 481403141}
    elif msg.item["action"]["type"] == "chat_invite_user":
        if msg.item["from_id"] == msg.item["action"]["member_id"]:
            app().vk.send_text(msg.pid,
                               core.strings.rnd(core.strings.on_repeat_invite()) +
                               yourself_action(msg.pid, msg.item["from_id"], False, msg.is_men()))
        else:
            app().eventer.update_event_data("data_updater", "flag", True)
            app().vk.send_text(msg.pid,
                               core.strings.rnd(core.strings.on_invite()) +
                               yourself_action(msg.pid, msg.item["action"]["member_id"], False, msg.is_men()))
    return True


def yourself_action(pid, uid, is_leave, men):
    text = ""
    if pid == 2000000008:
        text = app().disk.user_profile(str(uid)).full_name()
        if text == '?':
            res = app().vk.call("users.get", {"user_ids": uid,
                                              "fields": "domain,sex,online,can_write_private_message,city",
                                              "name_case": "nom"})
            text = "[id" + str(uid) + "|" + res[0]["first_name"] + " " + res[0]["last_name"] + "]"
        if is_leave:
            text = "\nНас покинул" + "а"*int(not men) + ": " + text
        else:
            text = "\nОбнаружен пользователь: " + text
    return text
