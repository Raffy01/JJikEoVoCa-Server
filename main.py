import json
import socket
import ssl
import threading
import logging

import handlers
import utils
from lib.db_manager import DatabaseManager
from config import Config
logger = logging.getLogger('Core')
shutdown_flag = False


def monitor_input():
    """
    별도 스레드에서 사용자 입력을 모니터링.
    사용자가 "shutdown"를 입력하면 shutdown_flag 설정, 서버 종료를 유도.
    """
    global shutdown_flag
    while True:
        cmd = input()  # blocking 호출 (별도 스레드이므로 메인 루프에 영향 없음)
        if cmd.strip().lower() == "shutdown":
            shutdown_flag = True
            print("[*] 서버 종료를 시작합니다.")
            break


def handle_client(conn, addr):
    """
    클라이언트 연결을 처리합니다.
    헤더를 읽은 후 해당하는 함수를 호출.
    """
    try:
        request_data = utils.recieve_json(conn)
        if not request_data:
            raise ValueError(f"No data received")
        intention = request_data.get('intention')
        payload = request_data.get('payload')
        if intention == 'Authentication':
            logger.info(f"{addr} Requesting Authentication")
            print(f"[*] {addr} Requesting Authentication")
            handlers.authentication(conn, addr, payload)
        elif intention == 'SearchUserByUid':
            logger.info(f"{addr} Requesting User Search")
            print(f"[*] {addr} Requesting User Search")
            handlers.search_user(conn, addr, payload)
        elif intention == 'Dictionary':
            logger.info(f"{addr} Requesting Dictionary With Image")
            print(f"[*] {addr} Requesting Dictionary With Image")
            handlers.dictionary_image(conn, addr, payload)
        elif intention == 'DictionaryText':
            logger.info(f"{addr} Requesting Dictionary With Text")
            print(f"[*] {addr} Requesting Dictionary With Text")
            handlers.dictionary_text(conn, addr, payload)
        elif intention == 'STT':
            logger.info(f"{addr} Requesting STT")
            print(f"[*] {addr} Requesting STT")
            handlers.pronunciation_test(conn, addr, payload)
        elif intention == 'SendBack':
            logger.info(f"{addr} Requesting STT Sendback")
            print(f"[*] {addr} Requesting STT Sendback")
            handlers.stt_sendback(conn, addr, payload)
        elif intention == 'Friend':
            logger.info(f"{addr} Requesting Friend List")
            print(f"[*] {addr} Requesting Friend List")
            handlers.friend_list(conn, addr, payload)
        elif intention == 'Request':
            logger.info(f"{addr} Requesting Friend Request")
            print(f"[*] {addr} Requesting Friend Request")
            handlers.request_friend(conn, addr, payload)
        elif intention == 'Accept':
            logger.info(f"{addr} Requesting Friend Accept")
            print(f"[*] {addr} Requesting Rating Accept")
            handlers.accept_friend(conn, addr, payload)
        elif intention == 'Reject':
            logger.info(f"{addr} Requesting Friend Reject")
            print(f"[*] {addr} Requesting Friend Reject")
            handlers.reject_friend(conn, addr, payload)
        elif intention == 'PendingRequests':
            logger.info(f"{addr} Requesting Pending Friend Requests")
            print(f"[*] {addr} Requesting Pending Friend Requests")
            handlers.pending_requests(conn, addr, payload)
        elif intention == 'DeleteFriend':
            logger.info(f"{addr} Requesting Friend Deletion")
            print(f"[*] {addr} Requesting Friend Deletion")
            handlers.delete_friend(conn, addr, payload)
        elif intention == 'Wordbook':
            logger.info(f"{addr} Requesting Wordbook Upload")
            print(f"[*] {addr} Requesting Wordbook Upload")
            handlers.wordbook_upload(conn, addr, payload)
        elif intention == 'GetWordbook':
            logger.info(f"{addr} Requesting Wordbook Pool")
            print(f"[*] {addr} Requesting Wordbook Pool")
            handlers.get_wordbook(conn, addr, payload)
        elif intention == 'GetRandomSubscribedWord':
            logger.info(f"{addr} Requesting Random Subscribed Word")
            print(f"[*] {addr} Requesting Random Subscribed Word")
            handlers.get_random_word(conn, addr, payload)
        elif intention == 'WordbookUpdate':
            logger.info(f"{addr} Requesting Wordbook Update")
            print(f"[*] {addr} Requesting Wordbook Update")
            handlers.wordbook_update(conn, addr, payload)
        elif intention == 'WordbookDelete':
            logger.info(f"{addr} Requesting Wordbook Delete")
            print(f"[*] {addr} Requesting Wordbook Delete")
            handlers.wordbook_delete(conn, addr, payload)
        elif intention == 'SearchWordbook':
            logger.info(f"{addr} Requesting Wordbook Search (AND)")
            print(f"[*] {addr} Requesting Wordbook Search (AND)")
            handlers.wordbook_search_and(conn, addr, payload)
        elif intention == 'SearchWordbookOr':
            logger.info(f"{addr} Requesting Wordbook Search (OR)")
            print(f"[*] {addr} Requesting Wordbook Search (OR)")
            handlers.wordbook_search_or(conn, addr, payload)
        elif intention == 'GetWordbookInfoWithID':
            logger.info(f"{addr} Requesting Wordbook Info With ID")
            print(f"[*] {addr} Requesting Wordbook Info With ID")
            handlers.get_wordbook_info_by_id(conn, addr, payload)
        elif intention == 'TagUpdate':
            logger.info(f"{addr} Requesting Tag Update")
            print(f"[*] {addr} Requesting Tag Update")
            handlers.update_tag(conn, addr, payload)
        elif intention == 'SearchTag':
            logger.info(f"{addr} Requesting Tag Search")
            print(f"[*] {addr} Requesting Tag Search")
            handlers.search_tag(conn, addr, payload)
        elif intention == 'Subscribe':
            logger.info(f"{addr} Requesting Subscription")
            print(f"[*] {addr} Requesting Subscription")
            handlers.subscribe(conn, addr, payload)
        elif intention == 'Cancel':
            logger.info(f"{addr} Requesting Subscription Cancle")
            print(f"[*] {addr} Requesting Subscription Cancle")
            handlers.cancle_subscription(conn, addr, payload)
        elif intention == 'GetSubscribedWordbooks':
            logger.info(f"{addr} Requesting Subscribed Wordbooks")
            print(f"[*] {addr} Requesting Subscribed Wordbooks")
            handlers.get_subscribed_wordbooks(conn, addr, payload)
        elif intention == 'LinkUserWord':
            logger.info(f"{addr} Requesting Link User, Word and Status")
            print(f"[*] {addr} Requesting Link User, Word and Status")
            handlers.link_user_word_status(conn, addr, payload)
        elif intention == 'UnlinkUserWord':
            logger.info(f"{addr} Requesting Unlink User, Word and Status")
            print(f"[*] {addr} Requesting Unlink User, Word and Status")
            handlers.unlink_user_word_status(conn, addr, payload)
        elif intention == 'GetLinkedWordOfUser':
            logger.info(f"{addr} Requesting Words With Status")
            print(f"[*] {addr} Requesting Words With Status")
            handlers.get_word_with_status(conn, addr, payload)
        elif intention == 'SessionStart':
            logger.info(f"{addr} Requesting Chat Start")
            print(f"[*] {addr} Requesting Chat Start")
            handlers.handle_chat_start(conn, addr, payload)
        elif intention == 'ChatInput':
            logger.info(f"{addr} Requesting Chat Input")
            print(f"[*] {addr} Requesting Chat Input")
            handlers.handle_chat_input(conn, addr, payload)
        elif intention == 'QuizSubmit':
            logger.info(f"{addr} Requesting Quiz Submit")
            print(f"[*] {addr} Requesting Quiz Submit")
            handlers.handle_quiz_submit(conn, addr, payload)
        elif intention == 'AnalyzeLearning':
            logger.info(f"{addr} Requesting Analyze Learning")
            print(f"[*] {addr} Requesting Analyze Learning")
            handlers.handle_learning_analyze(conn, addr, payload)
        elif intention == 'TodayReview':
            logger.info(f"{addr} Requesting Today Review")
            print(f"[*] {addr} Requesting Today Review")
            handlers.handle_today_review(conn, addr, payload)
        elif intention == 'BusinessTalk':
            logger.info(f"{addr} Requesting Business Talk")
            print(f"[*] {addr} Requesting Business Talk")
            handlers.handle_business_talk(conn, addr, payload)
        elif intention == 'GenerateExample':
            logger.info(f"{addr} Requesting Generate Example")
            print(f"[*] {addr} Requesting Generate Example")
            handlers.handle_generate_example(conn, addr, payload)
        else:
            raise ValueError(f'Invalid intention : {intention}')

    # 클라이언트의 비정상적인 연결 종료 또는 타임아웃을 먼저 처리합니다.
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ssl.SSLEOFError, socket.timeout) as e:
        logger.warning(f"Client {addr} disconnected abruptly or timed out: {e}")
        print(f"\n[*] Client {addr} disconnected abruptly.: {e}")
        # 'pass'를 통해 'finally'로 점프, 연결을 닫습니다.
        pass

    # JSON 디코딩 오류나 ValueError 등 "서버가 처리해야 할" 오류들
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid request from {addr}: {e}")
        print(f"\n[!!] Invalid request from {addr}: {e}")

        if isinstance(e, json.JSONDecodeError):
            reply = {
                "status": "REJECT",
                "code": "JSON_ERROR",
                "payload": {"message": str(e)}
            }
        else:  # ValueError (예: Invalid intention)
            reply = {
                "status": "REJECT",
                "code": "INVALID_REQUEST",
                "payload": {"message": str(e)}
            }
        try:
            utils.send_json(conn, reply)
        except (ConnectionResetError, BrokenPipeError, ssl.SSLEOFError):
            logger.warning(f"Tried to send REJECT to {addr}, but client was already gone.")
            print(f"[*] Tried to send REJECT to {addr}, but client disconnected. ")

    # 위에서 잡지 못한 그 외 모든 "예상치 못한 서버 내부 오류"
    except Exception as e:
        logger.error(f"Internal Server Error with {addr}: {e}", exc_info=True)  # exc_info=True로 트레이스백 로깅
        print(f"\n[!!] Internal Server Error with {addr}: {e}")
        reply = {
            "status": "ERROR",
            "code": "INTERNAL_SERVER_ERROR",
            "payload": {
                "message": "An unexpected error occurred on the server."
            }
        }
        try:
            utils.send_json(conn, reply)
        except (ConnectionResetError, BrokenPipeError, ssl.SSLEOFError):
            logger.warning(f"Tried to send ERROR to {addr}, but client was already gone.")
            print(f"[*] Tried to send ERROR to {addr}, but client disconnected.")

    finally:
        logger.info(f"{addr} closed")
        print(f"[*] {addr} closed")
        conn.shutdown(socket.SHUT_WR)
        conn.close()


def server_on():
    """
    서버를 실행합니다.
    별도 스레드에서 사용자 입력을 모니터링하며, shutdown_flag가 설정되면 서버를 종료합니다.
    """
    purpose = ssl.Purpose.CLIENT_AUTH
    context = ssl.create_default_context(purpose)
    context.load_cert_chain(certfile=Config.SSL_CERT_PATH, keyfile=Config.SSL_KEY_PATH)

    HOST = Config.HOST
    PORT = Config.PORT

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.settimeout(1.0)  # 주기적으로 shutdown_flag 확인을 위해 타임아웃 설정
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.listen(Config.THREADS)
    print(f"[*] 서버 시작: {HOST}:{PORT}")
    logger.info(f"Server Started: {HOST}:{PORT}")

    # 사용자 입력 모니터링 스레드 시작
    input_thread = threading.Thread(target=monitor_input, daemon=True)
    input_thread.start()

    global shutdown_flag
    while not shutdown_flag:
        conn = None  # try 블록 밖에서 conn을 None으로 초기화
        tls_conn = None  # tls_conn도 초기화

        try:
            # 1. 소켓 수락
            conn, addr = server_socket.accept()
            print(f"[*] {addr}에서 연결됨")
            logger.info(f"Connection from {addr}")

            # 2. TLS 핸드셰이크
            tls_conn = context.wrap_socket(conn, server_side=True)
            # 중요: 핸드셰이크 성공 시, 소켓 'conn'의 소유권은 'tls_conn'으로 넘어감
            # 이제부터 'tls_conn'을 관리해야 함.
            # 만약의 경우를 대비해 conn은 None으로 설정 (실수 방지)
            conn = None

            # 3. 스레드 생성 및 시작
            client_thread = threading.Thread(target=handle_client, args=(tls_conn, addr))
            client_thread.start()

            # 중요: 스레드 시작 성공 시, 'tls_conn'의 소유권은 'handle_client' 함수로 넘어감
            # 따라서 여기서부턴 이 루프가 소켓을 닫으면 안 됨.
            tls_conn = None  # 소유권이 넘어갔으므로 None으로 설정+

        except socket.timeout:
            continue  # 타임아웃은 정상, 그냥 루프 계속

        except (ConnectionResetError, ConnectionAbortedError) as e:
            # 핸드셰이크 중 클라이언트가 연결을 강제로 끊음
            print(f"[!!] Connection Error from {addr if 'addr' in locals() else 'Unknown'}: {e}")
            logger.warning(f"Connection Error from {addr if 'addr' in locals() else 'Unknown'}: {e}")

            # conn만 생성되었을 수도, tls_conn까지 생성되었을 수도 있음
            # 아래 finally 블록에서 둘 다 처리하므로 여기서는 pass
            pass

        except ssl.SSLError as e:
            # 핸드셰이크 명백히 실패 (프로토콜 오류 등)
            print(f"[!!] Error During TLS Handshake from {addr if 'addr' in locals() else 'Unknown'}: {e}")
            logger.error(f"Error During TLS Handshake from {addr if 'addr' in locals() else 'Unknown'}: {e}")
            # 마찬가지로 finally에서 리소스 정리
            pass

        except Exception as e:
            # 예: 스레드 생성 실패 (Resources temporarily unavailable) 등
            logger.error(f"Unexpected Error in accept loop: {e}")
            print(f"[!!] Unexpected Error: {e}")
            # 마찬가지로 finally에서 리소스 정리
            pass

        finally:
            # --- 리소스 정리 ---
            # 이 블록은 스레드 시작(3)까지 성공적으로 완료되지 못했을 때
            # 남겨진 소켓을 정리하기 위해 존재함.

            if tls_conn:
                # 2번(wrap_socket)은 성공했으나 3번(스레드 시작)이 실패한 경우
                tls_conn.close()
                logger.info(
                    f"Closed tls_conn for {addr if 'addr' in locals() else 'Unknown'} due to accept loop error.")

            elif conn:
                # 1번(accept)은 성공했으나 2번(wrap_socket)이 실패한 경우
                conn.close()
                logger.info(f"Closed raw conn for {addr if 'addr' in locals() else 'Unknown'} due to handshake error.")

    server_socket.close()
    print("[*] 서버가 종료되었습니다.")
    logger.info(f"Server Terminated")


if __name__ == "__main__":
    utils.setup_logging()
    db = DatabaseManager.get_instance()
    db.initialize_databases()
    handlers.initialize_chat_service(Config.GEMINI_API_KEY)
    server_on()
    db.close_all_connections()
