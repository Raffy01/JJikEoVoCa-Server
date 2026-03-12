import logging

import utils
from lib.db_manager import DatabaseManager
logger = logging.getLogger(__name__)


def friend_list(conn, addr, payload):
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
            raise ValueError("Missing required fields in payload")
        print(f"[*] {uid} Requesting Friend List")
        logger.info(f"{uid} Requesting Friend List")

        target_uids = []
        target_nicknames = []
        target_images = []
        target_onelines = []
        db = DatabaseManager.get_instance()
        tmp = db.get_friend_by_uid(uid)
        # uid 만큼 반복
        warn = False
        for friend_data in tmp:
            friend_uid = friend_data['uid2']
            user_data = db.get_user_by_uid(friend_uid)
            # db에서 데이터 load
            if user_data is None:
                warn = True
                user_uid = "null"
                user_nickname = "null"
                user_image = "0"
                user_oneline = "안녕하세요."
                logger.warning(f"UID {uid} Not Found")
                print(f"[!] UID {uid} Not Found")
            else:
                user_uid = str(user_data['uid']) if user_data['uid'] else "null"
                user_nickname = user_data['nickname'] if user_data['nickname'] else "null"
                user_image = user_data['image'] if user_data['image'] else "0"
                user_oneline = user_data['oneline'] if user_data['oneline'] else "안녕하세요."
            target_uids.append(user_uid)
            target_nicknames.append(user_nickname)
            target_images.append(user_image)
            target_onelines.append(user_oneline)
        # 데이터(들) 전송
        reply = {
            "status": "ACCEPT",
            "code": "OK" if not warn else "COMPLETED_WITH_WARNINGS",
            "payload": {
                "uids": target_uids,
                "nicknames": target_nicknames,
                "images": target_images,
                "onelines": target_onelines
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


def request_friend(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        requestor = payload.get('requester')
        requestie = payload.get('requestie')
        if not all([requestor, requestie]):
            raise ValueError("Missing required fields in payload")

        print(f"[*] Friend Request : {requestor} -> {requestie}")
        logger.info(f"Friend Request : {requestor} -> {requestie}")

        db = DatabaseManager.get_instance()

        # 1. 자기 자신에게 친구 요청을 보낸 경우
        if requestor == requestie:
            reply = {
                "status": "REJECT",
                "code": "SELF_REQUEST",
                "payload": {
                    "message": "You cannot send a friend request to yourself."
                }
            }
            logger.warning(f'Friend Request to himself : {requestor}')

        # 2. 이미 친구인 경우
        elif db.get_friend(requestor, requestie) is not None:
            reply = {
                "status": "REJECT",
                "code": "ALREADY_FRIENDS",
                "payload": {
                    "message": "You are already friend with this user."
                }
            }
            logger.warning(f'Requested But Already Friend : {requestor} -> {requestie}')

        # 3. 친구 요청 대상(requestie)이 존재하지 않는 경우
        elif db.get_user_by_uid(requestie) is None:
            reply = {
                "status": "REJECT",
                "code": "USER_NOT_FOUND",
                "payload": {
                    "message": "The user you are trying to add does not exist."
                }
            }
            logger.warning(f"requestie {requestie} Not Found")

        else:
            forward = db.get_request(requestor, requestie)
            backward = db.get_request(requestie, requestor)

            # 4. 중복된 친구 요청인 경우 (이미 보낸 요청)
            if forward is not None:
                reply = {
                    "status": "REJECT",
                    "code": "DUPLICATE_REQUEST",
                    "payload": {
                        "message": "A friend request has already been sent to this user."
                    }
                }
                logger.warning(f"Duplicated Friend Request : {requestor} -> {requestie}")

            # 5. 상대방의 요청이 있어 바로 친구가 되는 경우 (상호 요청)
            elif backward is not None:
                with db.transaction() as cursor:
                    db.update_request_status(requestie, requestor, 'ACCEPTED', cursor=cursor)
                    db.add_friend(requestor, requestie, cursor=cursor)
                    db.add_friend(requestie, requestor, cursor=cursor)
                reply = {
                    "status": "ACCEPT",
                    "code": "FRIENDSHIP_CREATED",
                    "payload": {
                        "message": "Mutual request found. You are now friends."
                    }
                }
                # Firebase Push Notification Logic (친구 수락)
                logger.info(f"Backward Checked. They are now friend")

            # 6. 새로운 친구 요청을 보내는 정상적인 경우
            else:
                db.add_request(requestor, requestie)
                reply = {
                    "status": "ACCEPT",
                    "code": "REQUEST_SENT",
                    "payload": {
                        "message": "Friend request sent successfully."
                    }
                }
                # Firebase Push Notification Logic (친구 요청)
                logger.info(f"Request Succeed, Now Pending")

        # 모든 로직 끝에서 최종적으로 한 번만 JSON을 전송합니다.
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


def accept_friend(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        requestor = payload.get('requester')
        requestie = payload.get('requestie')
        if not all([requestor, requestie]):
            raise ValueError("Missing required fields in payload")

        print(f"[*] uid {requestie} Accepting Friend Request : {requestor} -> {requestie}")
        logger.info(f"uid {requestie} Accepting Friend Request : {requestor} -> {requestie}")

        db = DatabaseManager.get_instance()

        # 1. 이미 친구 관계인 경우 (동시 요청 등으로 드물게 발생 가능)
        if db.get_friend(requestie, requestor) is not None:
            reply = {
                "status": "REJECT",
                "code": "ALREADY_FRIENDS",
                "payload": {
                    "message": "You are already friends with this user."
                }
            }
            # 남아있을 수 있는 친구 요청은 삭제 처리
            if db.get_request(requestor, requestie) is not None:
                db.delete_request(requestor, requestie)
            logger.warning(f'Accepted But Already Friend : {requestor} -> {requestie}')

        # 2. 친구 요청을 보낸 유저(requestor)가 존재하지 않는 경우 (탈퇴 등)
        elif db.get_user_by_uid(requestor) is None:
            reply = {
                "status": "REJECT",
                "code": "USER_NOT_FOUND",
                "payload": {
                    "message": "The user who sent the request no longer exists."
                }
            }
            # 존재하지 않는 유저의 친구 요청은 삭제 처리
            if db.get_request(requestor, requestie) is not None:
                db.delete_request(requestor, requestie)
            logger.error("Responding to a friend request from a deleted user")

        # 3. 수락하려는 친구 요청이 존재하지 않는 경우 (상대가 요청을 취소했거나 이미 처리된 경우)
        elif db.get_request(requestor, requestie) is None:
            reply = {
                "status": "REJECT",
                "code": "REQUEST_NOT_FOUND",
                "payload": {
                    "message": "This friend request does not exist. It may have been canceled."
                }
            }
            logger.warning(f'Responding to a void friend request from {requestor} to {requestie}')

        # 4. 정상적으로 친구 요청을 수락하는 경우
        else:
            with db.transaction() as cursor:
                db.update_request_status(requestor, requestie, 'ACCEPTED', cursor=cursor)
                db.add_friend(requestor, requestie, cursor=cursor)
                db.add_friend(requestie, requestor, cursor=cursor)

            reply = {
                "status": "ACCEPT",
                "code": "FRIENDSHIP_CREATED",
                "payload": {
                    "message": "Friend request accepted. You are now friends."
                }
            }
            # Firebase Push Notification Logic (친구 수락)
            logger.info(f"Friend Request {requestor} -> {requestie} Accepted")

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


def reject_friend(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        requestor = payload.get('requester')
        requestie = payload.get('requestie')  # 거부하는 유저 (수신자)
        if not all([requestor, requestie]):
            raise ValueError("Missing required fields in payload")

        print(f"[*] uid {requestie} Rejecting Friend Request : {requestor} -> {requestie}")
        logger.info(f"uid {requestie} Rejecting Friend Request : {requestor} -> {requestie}")

        db = DatabaseManager.get_instance()

        # 1. 수락/거부하려는 'PENDING' 상태 요청이 존재하는지 확인합니다.
        # 이 시점에서 requestie는 요청을 받은 사람이므로, 요청 레코드는 (requestor, requestie)로 존재해야 합니다.
        # 상태에 관계없이 요청 존재 여부만 확인 후 삭제해도 되지만, PENDING이 아니면 경고를 줍니다.
        current_request = db.get_request(requestor, requestie)

        if current_request is None or current_request['status'] != 'PENDING':
            reply = {
                "status": "REJECT",
                "code": "REQUEST_NOT_FOUND",
                "payload": {
                    "message": "This friend request does not exist or is not pending."
                }
            }
            logger.warning(f'Responding to a void or non-PENDING friend request from {requestor} to {requestie}')

        # 2. 정상적으로 친구 요청을 거부하는 경우: 레코드를 삭제
        else:
            db.delete_request(requestor, requestie)
            reply = {
                "status": "ACCEPT",
                "code": "REQUEST_REJECTED",
                "payload": {
                    "message": "Friend request rejected successfully."
                }
            }
            logger.info(f"Friend Request {requestor} -> {requestie} Deleted (Rejected)")

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


def delete_friend(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        uid1 = payload.get('requester')  # 삭제 요청자
        uid2 = payload.get('requestie')  # 삭제 대상
        if not all([uid1, uid2]):
            raise ValueError("Missing required fields in payload")

        print(f"[*] Friend Delete Request : {uid1} and {uid2}")
        logger.info(f"Friend Delete Request : {uid1} and {uid2}")

        db = DatabaseManager.get_instance()

        # 친구 관계 확인 (한쪽 방향만 확인해도 됨)
        if db.get_friend(uid1, uid2) is None:
            reply = {
                "status": "REJECT",
                "code": "NOT_FRIENDS",
                "payload": {
                    "message": "The two users are not friends."
                }
            }
            logger.warning(f'{uid1} tried to delete non-friend {uid2}')

        else:
            # Friends 테이블에서 양방향 레코드 모두 삭제
            db.delete_friend(uid1, uid2)
            reply = {
                "status": "ACCEPT",
                "code": "FRIENDSHIP_DELETED",
                "payload": {
                    "message": "Friend deleted successfully."
                }
            }
            logger.info(f"Friendship between {uid1} and {uid2} deleted")

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


def pending_requests(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        uid = payload.get('uid')
        request_type = payload.get('type')  # 'sent' or 'received'
        if not all([uid, request_type]):
            raise ValueError("Missing required fields in payload")

        if request_type not in ['sent', 'received']:
            raise ValueError("Invalid request type. Must be 'sent' or 'received'.")

        print(f"[*] {uid} Requesting Pending {request_type.capitalize()} Friend Requests")
        logger.info(f"{uid} Requesting Pending {request_type.capitalize()} Friend Requests")

        db = DatabaseManager.get_instance()
        target_uids = []
        target_nicknames = []
        target_images = []
        target_onelines = []
        requests_data = []

        if request_type == 'sent':
            # 2. pending중인 보낸 친구 요청 전송
            requests_data = db.get_sent_requests_by_uid(uid)
        elif request_type == 'received':
            # 3. pending중인 받은 친구 요청 전송
            requests_data = db.get_received_requests_by_uid(uid)

        code = 'OK'
        # 요청된 목록의 상대방 정보를 가져옵니다.
        for req_data in requests_data:
            # 'sent'의 경우 requestie, 'received'의 경우 requester의 정보를 가져와야 합니다.
            friend_uid = req_data['requestie'] if request_type == 'sent' else req_data['requester']
            user_data = db.get_user_by_uid(friend_uid)

            if user_data is None:
                code = "COMPLETED_WITH_WARNINGS"
                target_uids.append("null")
                target_nicknames.append("null")
                target_images.append("1")
                target_onelines.append("안녕하세요.")
                logger.warning(f"User for Request UID {friend_uid} Not Found")
                print(f"[!] User for Request UID {friend_uid} Not Found")
            else:
                target_uids.append(str(user_data['uid']) if user_data['uid'] else "null")
                target_nicknames.append(user_data['nickname'] if user_data['nickname'] else "null")
                target_images.append(user_data['image'] if user_data['image'] else "0")
                target_onelines.append(user_data['oneline'] if user_data['oneline'] else "안녕하세요.")
        if not requests_data:
            code = 'NO_REQUESTS_FOUND'
        reply = {
            "status": "ACCEPT",
            "code": code,
            "payload": {
                "uids": target_uids,
                "nicknames": target_nicknames,
                "images": target_images,
                "onelines": target_onelines,
                "type": request_type
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