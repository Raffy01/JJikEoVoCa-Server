import logging
import json

import utils
from lib.db_manager import DatabaseManager
logger = logging.getLogger(__name__)


def handle_upload(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        title = payload.get('title')
        tags = payload.get('tags')  # tags는 리스트 형태
        owner_uid = payload.get('owner_uid')
        data = payload.get('data')
        if not all([title, owner_uid, data]):
            raise ValueError("Missing required fields in payload")

        # 해시 계산
        data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
        file_hash = utils.calcaulate_md5(data_string.encode('utf-8'))  # 문자열을 바이트로 인코딩

        db = DatabaseManager.get_instance()

        # 데이터베이스 트랜잭션 시작
        with db.transaction() as cursor:

            # owner_uid 검증
            owner = db.get_user_by_uid(owner_uid, cursor=cursor)
            if not owner:
                raise ValueError(f'Invalid Owner Uid : {owner_uid}')

            # Wordbooks 테이블에 단어장 정보 저장
            wid = db.add_wordbook(title, owner_uid, file_hash, cursor=cursor)
            # Word 정보 저장 밑 Wordbook과 연결
            for word_data in data:
                term = word_data.get('word')
                meanings = word_data.get('meanings', [])
                distractors = word_data.get('distractors', [])
                example = word_data.get('example')
                if not all([term, meanings, distractors, example]):
                    logger.warning(f"Skipping Invalid Word Entry: {term}")
                    print(f'[!] Skipping Invalid Word Entry: {term}')
                    continue

                meanings_json = json.dumps(meanings, ensure_ascii=False)
                distractors_json = json.dumps(distractors, ensure_ascii=False)

                db.add_word_to_wordbook(wid, term, meanings_json, distractors_json, example, cursor)
            # 태그 처리 및 링크 생성
            for tag_name in tags:
                # 태그 이름 정규화 (예: 소문자 변환, 공백 제거)
                normalized_tag = tag_name.strip().lower()
                if not normalized_tag:
                    continue

                # 기존 태그 확인
                tag_data = db.get_tag_by_name(normalized_tag, cursor=cursor)
                if tag_data:
                    tid = tag_data['tid']
                else:
                    # 새 태그 생성
                    tid = db.add_tag(normalized_tag, cursor=cursor)

                # 단어장과 태그 연결
                db.link_tag_to_wordbook(wid, tid, cursor=cursor)

            # 생성자는 자동으로 구독자 테이블에 연결
            db.link_subscriber_to_wordbook(wid, owner_uid, cursor=cursor)
        logger.info(f"Wordbook '{title}' and {len(tags)} tags successfully saved for {addr}.")
        print(f"[*] 단어장 '{title}' 저장 완료")

        reply = {
            "status": "ACCEPT",
            "code": "WORDBOOK_CREATED",
            "payload": {"wid": wid, "title": title}
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        print(f"[!] Request Rejected {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook upload for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def handle_update(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    is_updated = False
    try:
        wid = payload.get('wid')
        title = payload.get('title')
        tags = payload.get('tags')  # tags는 리스트 형태
        owner_uid = payload.get('owner_uid')
        data = payload.get('data')

        if not all([wid, title, tags, owner_uid, data]):
            raise ValueError("Missing required fields in payload")

        # 해시 계산
        data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
        new_hash = utils.calcaulate_md5(data_string.encode('utf-8'))  # 문자열을 바이트로 인코딩

        db = DatabaseManager.get_instance()
        # 데이터베이스 트랜잭션 시작
        with db.transaction() as cursor:
            old_wordbook = db.get_wordbook_by_id(wid)
            owner = db.get_user_by_uid(owner_uid, cursor=cursor)
            # owner_uid 검증
            if not owner:
                raise ValueError(f'Invalid Owner Uid : {owner_uid}')
            # 단어장 존재 여부 검증
            if old_wordbook is None:
                raise ValueError(f'Requesting Update for Non-existing wordbook')
            # owner_uid 일치 여부 검증
            if old_wordbook['owner_uid'] != int(owner_uid):
                raise PermissionError(f'Owner Id Mismatch')

            # Wordbook의 해시 값을 비교, 단어장 값의 변화 판정
            old_hash = old_wordbook['hash']
            if not utils.compare_hash(old_hash, new_hash):
                is_updated = True
                # Wordbooks 테이블에 단어장 정보 저장
                db.update_wordbook(wid, new_hash, cursor=cursor)

                existing_word_rows = db.get_words_by_wordbook(wid, cursor=cursor)
                existing_master_ids = {row['master_word_id'] for row in existing_word_rows}

                current_master_ids = set()

                for word_data in data:
                    term = word_data.get('word')
                    meanings = word_data.get('meanings', [])
                    distractors = word_data.get('distractors', [])
                    example = word_data.get('example')

                    if not all([term, meanings, distractors, example]):
                        logger.warning(f"Skipping invalid word entry during update: {term}")
                        print(f'[!] Skipping invalid word entry during update: {term}')
                        continue

                    meanings_json = json.dumps(meanings, ensure_ascii=False)
                    distractors_json = json.dumps(distractors, ensure_ascii=False)

                    master_word_id = db.add_word_to_wordbook(wid, term, meanings_json, distractors_json,
                                                             example, cursor=cursor)
                    current_master_ids.add(master_word_id)

                    ids_to_remove = existing_master_ids - current_master_ids

                    for target in ids_to_remove:
                        db.remove_word_from_wordbook(wid, target, cursor=cursor)

            db.delete_all_tags_for_wordbook(wid, cursor=cursor)
            # 태그 처리 및 링크 생성
            for tag_name in tags:
                # 태그 이름 정규화 (예: 소문자 변환, 공백 제거)
                normalized_tag = tag_name.strip().lower()
                if not normalized_tag:
                    continue

                # 기존 태그 확인
                tag_data = db.get_tag_by_name(normalized_tag, cursor=cursor)
                if tag_data:
                    tid = tag_data['tid']
                else:
                    # 새 태그 생성
                    tid = db.add_tag(normalized_tag, cursor=cursor)
                # 단어장과 태그 연결
                db.link_tag_to_wordbook(wid, tid, cursor=cursor)

        logger.info(f"Wordbook '{title}' and {len(tags)} tags successfully updated for {addr}.")
        print(f"[*] 단어장 '{title}' 수정 완료")

        reply = {
            "status": "ACCEPT",
            "code": "WORDBOOK_UPDATED" if is_updated else "NOT_MODIFIED",
            "payload": {"wid": wid, "title": title}
        }
        utils.send_json(conn, reply)
    except PermissionError as e:
        logger.warning(f"Permission error from {addr}: {e}")
        print(f"[!] Request Rejected {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        print(f"[!] Request Rejected {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook upload for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def handle_delete(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        wid = payload.get('wid')
        owner_uid = payload.get('owner_uid')
        if not all([wid, owner_uid]):
            raise ValueError("Missing required fields in payload")

        db = DatabaseManager.get_instance()

        old_wordbook = db.get_wordbook_by_id(wid)
        owner = db.get_user_by_uid(owner_uid)
        # owner_uid 검증
        if not owner:
            raise ValueError(f'Invalid Owner Uid : {owner_uid}')
        # 단어장 존재 여부 검증
        if old_wordbook is None:
            raise ValueError(f'Requesting Deletion for Non-existing wordbook')
        # owner_uid 일치 여부 검증
        if old_wordbook['owner_uid'] != int(owner_uid):
            raise PermissionError(f'Owner Uid Mismatch')

        # 단어장 DB 삭제
        db.delete_wordbook(wid)

        logger.info(f"Wordbook '{wid}' successfully deleted for {addr}.")
        print(f"[*] 단어장 '{wid}' 삭제 완료")

        reply = {
            "status": "ACCEPT",
            "code": "WORDBOOK_DELETED",
            "payload": {"wid": wid}
        }
        utils.send_json(conn, reply)
    except PermissionError as e:
        logger.warning(f"Permission error from {addr}: {e}")
        print(f"[!] Request Rejected {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        print(f"[!] Request Rejected {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook upload for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def get_wordbook(conn, addr, payload):
    reply = {
            "status": "ERROR",
            "code": "INTERNAL_SERVER_ERROR",
            "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        wid = payload.get('wid')
        if not wid:
            raise ValueError("Missing required fields in payload")
        db = DatabaseManager.get_instance()
        wordbook = db.get_wordbook_by_id(wid)
        if wordbook is None:
            raise ValueError(f"Requesting Non-Existing Wordbook")
        word_rows = db.get_words_by_wordbook(wid)
        parsed_data = []
        for row in word_rows:
            try:
                meanings_list = json.loads(row['meanings'])
            except (json.JSONDecodeError, TypeError):
                meanings_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리

            try:
                distractors_list = json.loads(row['distractors'])
            except (json.JSONDecodeError, TypeError):
                distractors_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리

            parsed_data.append({
                "word_id": row['master_word_id'],
                "word": row['term'],
                "meanings": meanings_list,
                "distractors": distractors_list,
                "example": row['example_sentence']
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
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def link_subscriber(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        wid = payload.get('wid')
        subscriber = payload.get('subscriber')
        if not all([wid, subscriber]):
            raise ValueError("Missing required fields in payload")
        db = DatabaseManager.get_instance()
        user_info = db.get_user_by_uid(subscriber)
        wordbook = db.get_wordbook_by_id(wid)
        # subscriber 존재 여부 검증
        if user_info is None:
            raise ValueError(f'Subscriber Not Exist')
        # 단어장 존재 여부 검증
        if wordbook is None:
            raise ValueError(f'Requesting Subscribtion for Non-existing wordbook')
        # 이미 구독중인지 여부 검증
        subscriber_rows = db.get_subscriber_for_wordbook(wid)
        is_subscribed = any(row['subscriber'] == subscriber for row in subscriber_rows)

        # 구독중이지 않다면, wordbook_subscriber table에 추가
        if not is_subscribed:
            db.link_subscriber_to_wordbook(wid, subscriber)

        logger.info(f"Subscriber '{subscriber}' successfully subscribed {wid}.")
        print(f"[*] 유저 {subscriber} 이/가 성공적으로 {wid}을/를 구독함.")
        reply = {
            "status": "ACCEPT",
            "code": "OK" if not is_subscribed else "ALREADY_SUBSCRIBED",
            "payload": {"message": "Subscription Done." if not is_subscribed else "You already subscribed this wordbook"}
        }
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling subscription for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def cancle_subscription(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        wid = payload.get('wid')
        subscriber = payload.get('subscriber')
        if not all([wid, subscriber]):
            raise ValueError("Missing required fields in payload")
        db = DatabaseManager.get_instance()
        user_info = db.get_user_by_uid(subscriber)
        wordbook = db.get_wordbook_by_id(wid)
        # subscriber 존재 여부 검증
        if user_info is None:
            raise ValueError(f'Subscriber Not Exist')
        # 단어장 존재 여부 검증
        if wordbook is None:
            raise ValueError(f'Requesting Subscriber Deletion for Non-existing wordbook')

        # 단어장의 소유자인지 여부 검증
        if subscriber is wordbook['owner_uid']:
            raise ValueError(f'Owner Cannot Cancle Subscription')

        # 이미 구독중인지 여부 검증
        subscriber_rows = db.get_subscriber_for_wordbook(wid)
        is_subscribed = any(row['subscriber'] == subscriber for row in subscriber_rows)
        # 구독중이지 않다면, Value Error
        if not is_subscribed:
            raise ValueError(f'You Are Not Subscribing {wid}')

        # Wordbook_Subscriber table에서 튜플 제거
        db.delete_subscriber_to_wordbook(wid, subscriber)

        logger.info(f"Subscriber '{subscriber}' successfully cancled subscription {wid}.")
        print(f"[*] 유저 {subscriber} 이/가 성공적으로 {wid}을/를 구독을 해제함.")

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {"message": "Subscription Successfully Cancled."}
        }
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling subscription cancle for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def get_subscribed_wordbooks(conn, addr, payload):
    """
    특정 uid가 가지고 있는 모든 단어장의 목록(wid, title, tag) 리턴
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occured on the server."}
    }
    try:
        uid = payload.get('uid')
        if not uid:
            raise ValueError("Missing required fields in payload")
        db = DatabaseManager.get_instance()

        # uid 유효성 검증
        user = db.get_user_by_uid(uid)
        if not user:
            raise ValueError("Invalid User ID")

        subscribed_rows = db.get_wordbook_for_subscriber(uid)
        wordbook_list = []

        for row in subscribed_rows:
            wid = row['wordbook_id']

            wordbook = db.get_wordbook_by_id(wid)
            if not wordbook:
                logger.warning(f"Found subscription for non-existent wid {wid} for user {uid}")
                continue  # orphaned record 스킵

            title = wordbook['title']
            tag_rows = db.get_tags_for_wordbook(wid)
            tags = [tag['name'] for tag in tag_rows]

            wordbook_list.append({
                "wid": wid,
                "title": title,
                "tags": tags
            })
        logger.info(f"User {uid} from {addr} requested subscribed wordbooks. Found {len(wordbook_list)}.")
        print(f"[*] {uid}의 구독 단어장 목록 전송 완료")
        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": wordbook_list  # 완성된 리스트를 payload에 담아 전송
            }
        }
        utils.send_json(conn, reply)
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling subscription list for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def wordbook_search_and(conn, addr, payload):
    """
    태그 ID 리스트(tids)를 받아, 모든 태그를 포함하는(AND 조건)
    단어장의 목록(wid, title, tag)을 반환합니다.
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occured on the server."}
    }
    try:
        tids = payload.get('tids')
        if not tids or not isinstance(tids, list):
            raise ValueError("Missing or invalid 'tids' list in payload")

        db = DatabaseManager.get_instance()

        # AND 조건으로 단어장 검색
        wordbook_rows = db.search_wordbooks_by_tags_and(tids)

        wordbook_list = []
        for row in wordbook_rows:
            wid = row['wid']
            subscription_count = row['subscription_count']
            wordbook = db.get_wordbook_by_id(wid)
            if not wordbook:
                logger.warning(f"Found search result for non-existent wid {wid}")
                continue  # orphaned 데이터 스킵

            title = wordbook['title']
            tag_rows = db.get_tags_for_wordbook(wid)
            tags = [tag['name'] for tag in tag_rows]

            wordbook_list.append({
                "wid": wid,
                "title": title,
                "tags": tags,
                "subscription_count": subscription_count
            })

        logger.info(f"Tag search from {addr} for tids {tids}. Found {len(wordbook_list)}.")
        print(f"[*] 태그 검색 완료 (tids: {tids}). {len(wordbook_list)}개 결과 전송.")

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": wordbook_list  # 완성된 리스트를 payload에 담아 전송
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook search for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def wordbook_search_or(conn, addr, payload):
    """
    태그 ID 리스트(tids)를 받아, 일부 태그를 포함하는(OR 조건)
    단어장의 목록(wid, title, tag)을 반환합니다.
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occured on the server."}
    }
    try:
        tids = payload.get('tids')
        if not tids or not isinstance(tids, list):
            raise ValueError("Missing or invalid 'tids' list in payload")

        db = DatabaseManager.get_instance()

        # AND 조건으로 단어장 검색
        wordbook_rows = db.search_wordbooks_by_tags_or(tids)

        wordbook_list = []
        for row in wordbook_rows:
            wid = row['wid']
            subscription_count = row['subscription_count']
            wordbook = db.get_wordbook_by_id(wid)
            if not wordbook:
                logger.warning(f"Found search result for non-existent wid {wid}")
                print(f'[!] Found search result for non-existent wid {wid}')
                continue  # orphaned 데이터 스킵

            title = wordbook['title']
            tag_rows = db.get_tags_for_wordbook(wid)
            tags = [tag['name'] for tag in tag_rows]

            wordbook_list.append({
                "wid": wid,
                "title": title,
                "tags": tags,
                "subscription_count": subscription_count
            })

        logger.info(f"Tag search from {addr} for tids {tids}. Found {len(wordbook_list)}.")
        print(f"[*] 태그 검색 완료 (tids: {tids}). {len(wordbook_list)}개 결과 전송.")

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": wordbook_list  # 완성된 리스트를 payload에 담아 전송
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook search for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def get_wordbook_info_by_id(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occured on the server."}
    }
    try:
        wid = payload.get('wid')
        if not wid:
            raise ValueError("Missing required fields in payload")

        db = DatabaseManager.get_instance()
        wordbook = db.get_wordbook_by_id(wid)

        if not wordbook:
            logger.warning(f"Wordbook {wid} Not Found")
            print(f"[!] Wordbook {wid} Not Found")
            raise ValueError(f"Wordbook {wid} Not Found")

        title = wordbook['title']
        tag_rows = db.get_tags_for_wordbook(wid)
        tags = [tag['name'] for tag in tag_rows]
        data = {
            "wid": wid,
            "title": title,
            "tags": tags
        }

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": data
            }
        }

        logger.info(f"Wordbook Meta from {addr} for {wid}.")
        print(f"[*] 단어장 메타데이터 전송 완료 (wid: {wid})")
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        print(f"[!] Request Rejected {addr}: {e}")
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook search for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)