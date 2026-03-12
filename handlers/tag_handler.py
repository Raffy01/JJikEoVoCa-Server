import logging

import utils
from lib.db_manager import DatabaseManager
logger = logging.getLogger(__name__)


def handle_update_tag(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        wid = payload.get('wid')
        new_tags = payload.get('tags')  # ["새 태그1", "새 태그2"]

        if wid is None or new_tags is None:
            raise ValueError("Missing required fields in payload")

        db = DatabaseManager.get_instance()
        with db.transaction() as cursor:
            # 1. 기존 태그 연결 모두 삭제
            db.delete_all_tags_for_wordbook(wid, cursor=cursor)

            # 2. 새 태그 목록으로 다시 연결
            for tag_name in new_tags:
                normalized_tag = tag_name.strip().lower()
                if not normalized_tag:
                    continue

                tag_data = db.get_tag_by_name(normalized_tag, cursor=cursor)
                if tag_data:
                    tid = tag_data['tid']
                else:
                    tid = db.add_tag(normalized_tag, cursor=cursor)

                db.link_tag_to_wordbook(wid, tid, cursor=cursor)

        reply = {
            "status": "ACCEPT",
            "code": "TAGS_UPDATED",
            "payload": {"message": f"Wordbook {wid}'s tags updated successfully."}
        }
        utils.send_json(conn, reply)
        logger.info(f"Wordbook {wid}'s tags successfully updated for {addr}.")
        print(f"[*] 단어장 '{wid}'의 태그 업데이트 완료")
    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling wordbook upload for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def search_tag(conn, addr, payload):
    """
    검색어를 받아 'prefix'로 시작하는 태그 목록을
    참조 횟수(reference_count)와 함께 반환합니다.
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        query = payload.get('query')
        if not query:
            raise ValueError("Missing required fields in payload")

        '''
        # 검색어가 너무 짧으면 DB 부하를 줄이기 위해 차단
        if len(query.strip()) < 1:
            raise ValueError("Query term is too short")
        '''

        normalized_query = query.strip().lower()
        db = DatabaseManager.get_instance()

        # "query"로 시작하는 태그 검색
        # 결과 예: [{'name': '영어', 'reference_count': 5}, ...]
        tag_rows = db.search_tags_by_prefix(normalized_query)
        tags = [dict(row) for row in tag_rows]
        logger.info(f"Tag search for '{query}' from {addr}: Found {len(tags)} tags.")
        print(f"[*] '{query}' 태그 검색 요청: 태그 {len(tags)}개 반환")

        reply = {
            "status": "ACCEPT",
            "code": "OK",
            "payload": {
                "data": tags
            }  # 단어장 없이 태그 목록만 반환
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.warning(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error handling tag search for {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)
