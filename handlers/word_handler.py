import logging
import json

import utils
from lib.db_manager import DatabaseManager
logger = logging.getLogger(__name__)


def link_user_word_status(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        invalid_entries = []
        uid = payload.get('uid')
        word_ids = payload.get('word_ids')
        status = payload.get('status')
        if not all([uid, word_ids, status]):
            raise ValueError(f"Missing required fields in payload")
        if status not in ('liked', 'wrong', 'review'):
            raise ValueError(f"Error: Invalid status '{status}'")
        if status == "wrong":
            raise ValueError(f"The incorrect word recording task has been transferred to QuizSubmit.")
        db = DatabaseManager.get_instance()
        if not db.get_user_by_uid(uid):
            raise ValueError(f"UID {uid} Not Found")

        with db.transaction() as cursor:
            for word_id in word_ids:
                # word_id 유효성 검증
                word_data = db.get_word_by_id(word_id, cursor)
                if not word_data:
                    print(f"Skipping invalid entry: {word_id}")
                    invalid_entries.append(word_id)
                    continue

                # 통합된 테이블에 상태 업데이트 (UPSERT)
                db.link_word_user_status(word_id, uid, status, cursor=cursor)

        reply = {
            "status": "ACCEPT",
            "code": "OK" if not invalid_entries else "INVALID_ENTRY_FOUND",
            "payload": {
                "message": "User And Word Status Linked",
                "invalid_entries": invalid_entries
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        utils.send_json(conn, reply)
        utils.send_json(conn, reply)


def unlink_user_word_status(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "Server Error"}
    }
    try:
        invalid_entries = []
        uid = payload.get('uid')
        word_ids = payload.get('word_ids')
        status = payload.get('status')

        if not all([uid, word_ids, status]):
            raise ValueError(f"Missing required fields")
        if status not in ('liked', 'wrong', 'review'):
            raise ValueError(f"Invalid status '{status}'")
        db = DatabaseManager.get_instance()
        if not db.get_user_by_uid(uid):
            raise ValueError(f"UID {uid} Not Found")

        with db.transaction() as cursor:
            for word_id in word_ids:
                word_data = db.get_word_by_id(word_id, cursor)
                if not word_data:
                    invalid_entries.append(word_id)
                    continue

                # 통합된 테이블에서 상태 해제 (Update Flags)
                db.unlink_word_user_status(word_id, uid, status, cursor=cursor)

        reply = {
            "status": "ACCEPT",
            "code": "OK" if not invalid_entries else "INVALID_ENTRY_FOUND",
            "payload": {
                "message": "User And Word Status Unlinked",
                "invalid_entries": invalid_entries
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        utils.send_json(conn, reply)


def get_word_with_status(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "Server Error"}
    }
    parsed_data = []
    try:
        uid = payload.get('uid')
        status = payload.get('status')

        if not all([uid, status]):
            raise ValueError(f"Missing required fields")
        if status not in ('liked', 'wrong', 'review'):
            raise ValueError(f"Invalid status '{status}'")

        db = DatabaseManager.get_instance()
        if not db.get_user_by_uid(uid):
            raise ValueError(f"UID {uid} Not Found")

        # 통합된 테이블에서 조건에 맞는 word_id 목록 조회
        word_rows = db.get_word_user_status(uid, status)

        for row in word_rows:
            # get_word_user_status가 row 팩토리를 반환하므로 딕셔너리처럼 접근
            word_id = row['master_word_id']
            word_data = db.get_word_by_id(word_id)

            if not word_data:
                continue

            # JSON 파싱 (안전하게 처리)
            try:
                meanings_list = json.loads(word_data['meanings']) if word_data['meanings'] else []
            except (json.JSONDecodeError, TypeError):
                meanings_list = []

            try:
                distractors_list = json.loads(word_data['distractors']) if word_data['distractors'] else []
            except (json.JSONDecodeError, TypeError):
                distractors_list = []

            parsed_data.append({
                "word_id": word_data['master_word_id'],
                "word": word_data['term'],
                "meanings": meanings_list,
                "distractors": distractors_list,
                "example": word_data['example_sentence']
            })

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": parsed_data
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        utils.send_json(conn, reply)


def get_random_word(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {
            "message": "An unexpected error occurred on the server."
        }
    }
    try:
        uid = payload.get('uid')
        if not uid:
            raise ValueError(f"Missing required fields in payload")

        db = DatabaseManager.get_instance()
        # uid 검증
        if not db.get_user_by_uid(uid):
            raise ValueError(f"UID {uid} Not Found")

        selected_words = db.get_random_word_for_user(uid)
        data = []
        for selected_word in selected_words:
            try:
                meanings_list = json.loads(selected_word['meanings'])
            except (json.JSONDecodeError, TypeError):
                meanings_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리

            try:
                distractors_list = json.loads(selected_word['distractors'])
            except (json.JSONDecodeError, TypeError):
                distractors_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리

            data.append({
                "word_id": selected_word['master_word_id'],
                "word": selected_word['term'],
                "meanings": meanings_list,
                "distractors": distractors_list,
                "example": selected_word['example_sentence']
            })

        reply = {
            "status": "ACCEPT",
            "code": "OK" if data else "NO_WORD_FOUND",
            "payload": {
                "data": data
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
