import logging

from config import Config
import utils
from lib.db_manager import DatabaseManager
logger = logging.getLogger(__name__)


def authentication(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        email = payload.get('email')
        nickname = payload.get('nickname')
        image = payload.get('image')
        oneline = payload.get('oneline')
        if not all([email, nickname, image]):
            raise ValueError("Missing required fields in payload")

        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_email(email)
        if user_data is None:
            code = "NEW_USER"
            print(f"[!] UID not found. Allocating new UID")
            logger.warning(f"UID not found. Allocating new UID")
            uid = db.add_user(email, nickname, image, oneline)
            for wordbook_id in Config.DEFAULT_WORDBOOKS:
                db.link_subscriber_to_wordbook(wordbook_id, uid)
        else:
            code = "EXISTING_USER"
            uid = user_data['uid']
            old_nickname = user_data['nickname']
            old_image = user_data['image']
            old_oneline = user_data['oneline']
            if nickname != old_nickname:
                code = "EXISTING_USER_UPDATED"
                db.update_nickname(uid, nickname)
                print(f"[*] {uid}'s nickname updated: {old_nickname} -> {nickname}")
                logger.info(f"{uid}'s nickname updated: {old_nickname} -> {nickname}")
            if image != old_image:
                code = "EXISTING_USER_UPDATED"
                db.update_image(uid, image)
                print(f"[*] {uid}'s image updated: {old_image} -> {image}")
                logger.info(f"{uid}'s image updated: {old_image} -> {image}")
            if oneline != old_oneline:
                code = "EXISTING_USER_UPDATED"
                db.update_oneline(uid, oneline)
                print(f"[*] {uid}'s image updated: {old_oneline} -> {oneline}")
                logger.info(f"{uid}'s image updated: {old_oneline} -> {oneline}")
        print(f"[*] uid of {email}, {nickname}, {oneline} : {uid}")
        logger.info(f"uid of {email}, {nickname}, {oneline} : {uid}")
        reply = {
            "status": "ACCEPT",
            "code": code,
            "payload": {
                "uid": str(uid),
                "nickname": nickname,
                "email": email,
                "image": image,
                "oneline": oneline
            }
        }
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def search_user(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        uid = payload.get('uid')
        if not uid:
            raise ValueError("Missing required fields in payload")

        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(uid)
        if user_data is None:
            raise ValueError(f"Requesting Info Of Non-Existing User")
        else:
            uid = user_data['uid']
            nickname = user_data['nickname']
            image = user_data['image']
            oneline = user_data['oneline']
            print(f"[*] {uid}'s info : {nickname}, {image}")
            logger.info(f"{uid}'s info : {nickname}, {image}")
        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "uid": str(uid),
                "nickname": nickname,
                "image": image,
                "oneline": oneline
            }
        }
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)
