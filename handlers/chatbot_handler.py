import logging
import json

import utils
from lib.db_manager import DatabaseManager
from lib.ai_client import GeminiClient
from lib.vector_store import VectorStore
from lib.service import VocabularyService

# from lib.models import MistakeRecord # DTO를 직접 사용하지 않고 딕셔너리로 처리 예정

logger = logging.getLogger(__name__)

# 챗봇 서비스 싱글톤 인스턴스 저장소
_service_instance: VocabularyService


def initialize_chat_service(api_key: str):
    """서버 시작 시 VocabularyService 객체를 초기화하고 저장합니다."""
    global _service_instance
    db = DatabaseManager.get_instance()
    ai = GeminiClient(api_key)
    vector_store = VectorStore()

    # VocabularyService는 Repository 객체를 인자로 받도록 설계되었으나,
    # 기존 서버 구조는 DatabaseManager가 Repository 역할을 겸하므로,
    # 임시로 VocabularyService의 첫 번째 인자에 DatabaseManager 인스턴스를 전달하고,
    # VocabularyService 내부 코드를 수정하여 DatabaseManager 메소드를 직접 호출하도록 합니다.
    # (이는 Step 4에서 VocabularyService 내부를 수정할 때 반영됩니다.)
    _service_instance = VocabularyService(db, ai, vector_store)
    print("[*] VocabularyService initialized with DB, AI, and VectorStore.")
    logger.info("VocabularyService initialized.")


def get_chat_service() -> VocabularyService:
    """초기화된 VocabularyService 인스턴스를 반환합니다."""
    if _service_instance is None:
        raise Exception("Chat service not initialized. Call initialize_chat_service first.")
    return _service_instance


# 세션 스타트
def handle_chat_start(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        # 클라이언트가 보낸 uid와 세션 이름(선택 사항)을 받습니다.
        owner_uid = payload.get('uid')
        session_name = payload.get('name', 'new_chat')  # 이름이 없으면 기본값 사용

        if not owner_uid:
            raise ValueError("Missing required fields: uid.")

        print(f"[*] Chat Start Request from {owner_uid}. Creating new session.")

        db = DatabaseManager.get_instance()

        # 1. DB Manager의 DAO 메소드를 호출하여 세션 생성
        # (이 기능은 이전에 챗봇 프로젝트의 repository에서 가져와 db_manager에 통합된 기능입니다.)
        new_session_id = db.create_session(int(owner_uid), session_name)

        # 2. 새로 생성된 세션 ID를 클라이언트에게 응답
        reply = {
            "status": "ACCEPT",
            "code": "SESSION_CREATED",
            "payload": {
                "session_id": new_session_id,
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during chat start: {e}")
        print(f"[!!] Error with {addr} during chat start: {e}")
        utils.send_json(conn, reply)


# ----------------------------------------------------
# A. 채팅 요청 처리
# ----------------------------------------------------
def handle_chat_input(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        owner_uid = payload.get('uid')
        session_id = payload.get('session_id')
        user_msg = payload.get('message')

        if not all([owner_uid, session_id, user_msg]):
            raise ValueError("Missing required fields: uid, session_id, or message.")
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(owner_uid)
        session_data = db.get_session_with_user(owner_uid, session_id)
        # 예외처리
        if not user_data:
            raise ValueError(f"User Not Exist")
        if not session_data:
            raise ValueError(f"Session Not Exist")

        print(f"[*] Chat Input from {owner_uid} in session {session_id}")
        logger.info(f"Chat Input from {owner_uid} in session {session_id}")

        service = get_chat_service()

        # 챗봇 응답 생성 및 로그 저장 (RAG 포함)
        ai_response = service.process_chat(
            owner_uid=int(owner_uid),
            session_id=session_id,
            user_msg=user_msg
        )

        reply = {
            "status": "ACCEPT",
            "code": "CHAT_RESPONSE",
            "payload": {
                "session_id": session_id,
                "response": ai_response
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during chat: {e}")
        print(f"[!!] Error with {addr} during chat: {e}")
        utils.send_json(conn, reply)


# ----------------------------------------------------
# B. 퀴즈 결과 제출 및 오답 기록
# ----------------------------------------------------

def handle_quiz_submit(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        uid = payload.get('uid')
        word_id = payload.get('word_id')
        word_text = payload.get('word_text')
        question = payload.get('question')
        user_answer = payload.get('user_answer')
        correct_answer = payload.get('correct_answer')
        if not all([uid, word_id, word_text, question, user_answer, correct_answer]):
            raise ValueError("Missing required fields for quiz submission.")

        # 예외 처리
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(uid)
        # 잘못된 uid
        if not user_data:
            raise ValueError("User Not Exist")
        word_data = db.get_word_by_id(word_id)
        # 잘못된 wid
        if not word_data:
            raise ValueError("Invalid Word ID")
        # 잘못된 단어와 id의 매치
        if word_data['term'] != word_text:
            raise ValueError("Word ID Mismatch")
        try:
            meanings_list = json.loads(word_data['meanings'])
        except (json.JSONDecodeError, TypeError):
            meanings_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리
        try:
            distractors_list = json.loads(word_data['distractors'])
        except (json.JSONDecodeError, TypeError):
            distractors_list = []  # DB 값이 null이거나 잘못된 JSON일 경우 빈 리스트 처리

        if user_answer not in set(meanings_list) | set(distractors_list):
            raise ValueError("Word ID Mismatch")
        if correct_answer not in meanings_list:
            raise ValueError("Word ID Mismatch")

        print(f"[*] Quiz Submit from {uid} for word_id {word_id}. Answer: {user_answer}")
        logger.info(f"Quiz Submit from {uid} for word_id {word_id}.")

        service = get_chat_service()

        if user_answer.strip().lower() == correct_answer.strip().lower():
            # 1. 정답인 경우: 통계 업데이트 ("correct" -> date_studied 갱신 포함)
            # service 호출 불필요 (정답은 '오답 노트'나 '기억'에 남길 필요 없음)
            db.link_word_user_status(word_id, uid, "correct")
            msg = "Correct answer recorded."
            code = "ANSWER_CORRECT"
        else:
            # 2. 오답인 경우: 서비스 계층 호출
            # 이 함수가 내부적으로 'record_mistake'를 불러서 DB(incorrect_count)와 Vector Store를 모두 업데이트함.
            # 따라서 별도로 db.link_word_user_status(..., "wrong")을 호출하면 안 됨 (중복 카운트 방지)
            service.submit_quiz_result(
                uid=int(uid),
                word_id=int(word_id),
                word_text=word_text,
                question=question,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
            msg = "Mistake recorded and learning memory updated."
            code = "MISTAKE_RECORDED"

        reply = {
            "status": "ACCEPT",
            "code": code,
            "payload": {
                "message": msg
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!] Error with {addr} during quiz submission: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during quiz submission: {e}")
        print(f"[!!] Error with {addr} during quiz submission: {e}")
        utils.send_json(conn, reply)


# ----------------------------------------------------
# C. 기타 분석 및 학습 기능
# ----------------------------------------------------

def handle_learning_analyze(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        owner_uid = payload.get('uid')
        session_id = payload.get('session_id')
        if not all([owner_uid, session_id]):
            raise ValueError("Missing required fields: uid or session_id.")
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(owner_uid)
        session_data = db.get_session_with_user(owner_uid, session_id)
        # 예외처리
        if not user_data:
            raise ValueError(f"User Not Exist")
        if not session_data:
            raise ValueError(f"Session Not Exist")

        print(f"[*] Analysis Request from {owner_uid}")
        logger.info(f"Analysis Request from {owner_uid}")

        service = get_chat_service()

        # 서비스 계층 호출
        analysis_report = service.analyze_learning_patterns(
            owner_uid=int(owner_uid),
            session_id=session_id
        )

        reply = {
            "status": "ACCEPT",
            "code": "ANALYSIS_REPORT",
            "payload": {
                "session_id": session_id,
                "response": analysis_report
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during analysis: {e}")
        print(f"[!!] Error with {addr} during analysis: {e}")
        utils.send_json(conn, reply)


def handle_today_review(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        owner_uid = payload.get('uid')
        session_id = payload.get('session_id')

        if not all([owner_uid, session_id]):
            raise ValueError("Missing required fields: uid or session_id.")
        # 예외처리
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(owner_uid)
        session_data = db.get_session_with_user(owner_uid, session_id)
        if not user_data:
            raise ValueError(f"User Not Exist")
        if not session_data:
            raise ValueError(f"Session Not Exist")

        print(f"[*] Today Review Request from {owner_uid}")
        logger.info(f"Today Review Request from {owner_uid}")

        service = get_chat_service()

        # 서비스 계층 호출
        review_content = service.review_todays_learning(
            owner_uid=int(owner_uid),
            session_id=session_id
        )

        reply = {
            "status": "ACCEPT",
            "code": "REVIEW_CONTENT",
            "payload": {
                "session_id": session_id,
                "response": review_content
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during review: {e}")
        print(f"[!!] Error with {addr} during review: {e}")
        utils.send_json(conn, reply)


def handle_business_talk(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        owner_uid = payload.get('uid')
        session_id = payload.get('session_id')
        user_text = payload.get('text')

        if not all([owner_uid, session_id, user_text]):
            raise ValueError("Missing required fields")
        # 예외처리
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(owner_uid)
        session_data = db.get_session_with_user(owner_uid, session_id)
        if not user_data:
            raise ValueError(f"User Not Exist")
        if not session_data:
            raise ValueError(f"Session Not Exist")

        service = get_chat_service()
        response_json = service.process_business_conversation(int(owner_uid), session_id, user_text)

        reply = {
            "status": "ACCEPT",
            "code": "CONVERSATION_RESPONSE",
            "payload": {
                "session_id": session_id,
                "response": json.loads(response_json)
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during review: {e}")
        print(f"[!!] Error with {addr} during review: {e}")
        utils.send_json(conn, reply)


def handle_generate_example(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        owner_uid = payload.get('uid')
        session_id = payload.get('session_id')

        if not all([owner_uid, session_id]):
            raise ValueError("Missing required fields: uid or session_id.")
        # 예외처리
        db = DatabaseManager.get_instance()
        user_data = db.get_user_by_uid(owner_uid)
        session_data = db.get_session_with_user(owner_uid, session_id)
        if not user_data:
            raise ValueError(f"User Not Exist")
        if not session_data:
            raise ValueError(f"Session Not Exist")

        service = get_chat_service()
        response_json = service.generate_examples_for_mistakes(int(owner_uid), session_id)

        reply = {
            "status": "ACCEPT",
            "code": "EXAMPLES_GENERATED",
            "payload": {
                "session_id": session_id,
                "response": response_json
            }
        }
        utils.send_json(conn, reply)

    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr} during review: {e}")
        print(f"[!!] Error with {addr} during review: {e}")
        utils.send_json(conn, reply)
