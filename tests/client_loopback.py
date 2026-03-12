import socket
import os
import ssl
import json
import struct

# 서버 설정
SERVER_IP = '127.0.0.1'  # 서버 IP 주소
PORT = 2121
FILE_PATH = './fixtures/test_voices/test_voice.wav'  # 전송할 파일 경로
SENDBACK_FILE_PATH = './fixtures/test_voices/never_gonna_give_you_up.wav'
BUFFER_SIZE = 65536  # 64KB
TEST_STRING = "cherry"
NULL = "null"


def recieve_json(conn):
    """
    연결된 소켓으로부터 JSON 데이터를 안정적으로 수신합니다.
    [4바이트 길이 정보] + [JSON 데이터] 형식으로 수신합니다.
    """
    # 1. 데이터 길이(4바이트)를 먼저 받습니다.
    len_bytes = conn.recv(4)
    if not len_bytes:
        return None
    # 받은 4바이트를 정수로 변환합니다.
    data_length = struct.unpack('>I', len_bytes)[0]

    # 2. 위에서 얻은 길이만큼의 데이터를 모두 수신합니다.
    data = b''
    while len(data) < data_length:
        packet = conn.recv(data_length - len(data))
        if not packet:
            return None
        data += packet

    # 3. 수신한 데이터를 JSON으로 디코딩하여 반환합니다.
    return json.loads(data.decode('utf-8'))


def send_file():
    if not os.path.exists(FILE_PATH):
        print("[!] 파일이 존재하지 않습니다.")
        return

    file_size = os.path.getsize(FILE_PATH)
    file_name = os.path.basename(FILE_PATH)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    # 의도 전송
    stt_request = {
        "intention": "STT",
        "payload": {
            "file_name": file_name,
            "file_size": file_size,
            "answer": TEST_STRING
        }
    }
    json_bytes = json.dumps(stt_request).encode('utf-8')
    len_bytes = struct.pack('>I', len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    sent_size = 0
    with open(FILE_PATH, "rb") as f:
        while sent_size < file_size:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            tls_socket.sendall(data)
            sent_size += len(data)

            # 진행률 출력
            percent = (sent_size / file_size) * 100
            print(f"\r[*] 전송 중... {percent:.2f}% 완료", end='', flush=True)

    print(f"\n[*] 파일 {file_name} 전송 완료")
    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def auth():
    email = "testestest@test.com"
    nickname = "테스터"
    image = "null"
    oneline = "테스트용 관리자 계정입니다."
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    auth_request = {
        "intention": "Authentication",
        "payload": {
            "email": email,
            "nickname": nickname,
            "image": image,
            "oneline": oneline
        }
    }
    json_bytes = json.dumps(auth_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    # json 패킷 길이 전송
    tls_socket.sendall(len_bytes)
    # json 패킷 전송
    tls_socket.sendall(json_bytes)
    uid = recieve_json(tls_socket)
    print(uid)


def friend_list():
    uid = 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    friend_request = {
        "intention": "Friend",
        "payload": {
            "uid": uid
        }
    }
    json_bytes = json.dumps(friend_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))

    # json 패킷 길이 전송
    tls_socket.sendall(len_bytes)
    # json 패킷 전송
    tls_socket.sendall(json_bytes)
    uid = recieve_json(tls_socket)
    print(uid)


def single_dict():
    image_path = './fixtures/test_images/img1.jpg'
    file_size = os.path.getsize(image_path)
    file_name = os.path.basename(image_path)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    single_request = {
        "intention": "Dictionary",
        "payload": {
            "cnt": "1",
            "file_name": [file_name, ],
            "file_size": [file_size, ]
        }
    }
    json_bytes = json.dumps(single_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    # json 패킷 길이 전송
    tls_socket.sendall(len_bytes)
    # json 패킷 전송
    tls_socket.sendall(json_bytes)
    # file 전송
    sent_size = 0
    with open(image_path, "rb") as f:
        while sent_size < file_size:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            tls_socket.sendall(data)
            sent_size += len(data)

            # 진행률 출력
            percent = (sent_size / file_size) * 100
            print(f"\r[*] 전송 중... {percent:.2f}% 완료", end='', flush=True)

    print(f"\n[*] 파일 {file_name} 전송 완료")
    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def multiple_dict():
    rep = 3

    image_path = {0: './fixtures/test_images/img2.jpg',
                  1: './fixtures/test_images/img3.jpg',
                  2: './fixtures/test_images/img4.jpg'}

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    file_size = []
    file_name = []
    for i in range(rep):
        file_size.append(os.path.getsize(image_path[i]))
        file_name.append(os.path.basename(image_path[i]))
    mult_request = {
        "intention": "Dictionary",
        "payload": {
            "cnt": "3",
            "file_name": file_name,
            "file_size": file_size
        }
    }
    json_bytes = json.dumps(mult_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))

    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    for i in range(rep):
        # file 전송
        sent_size = 0
        with open(image_path[i], "rb") as f:
            while sent_size < file_size[i]:
                data = f.read(BUFFER_SIZE)
                if not data:
                    break
                tls_socket.sendall(data)
                sent_size += len(data)

                # 진행률 출력
                percent = (sent_size / file_size[i]) * 100
                print(f"\r[*] 전송 중... {percent:.2f}% 완료", end='', flush=True)

        print(f"\n[*] 파일 {file_name[i]} 전송 완료")
    data = recieve_json(tls_socket)
    print(data)

    tls_socket.close()


def add_friend():
    requestor, requestie = 1, 5
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    add_request = {
        "intention": "Request",
        "payload": {
            "requester": requestor,
            "requestie": requestie
        }
    }
    json_bytes = json.dumps(add_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def accept_friend():
    requestor, requestie = 1, 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    accept_request = {
        "intention": "Accept",
        "payload": {
            "requester": requestor,
            "requestie": requestie
        }
    }
    # 의도 전송
    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def wordbook_register():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    accept_request = {
        "intention": "Wordbook",
        "payload": {
            "title": "토익영어장(800점)",
            "tags": ["영어", "토익", "토익800", "기본단어장"],
            "owner_uid": "1",
            "data": [{'word': 'account', 'meanings': ['계좌', '설명', '고려하다', ''], 'distractors': ['회계', '계산', '기록'], 'example': 'He gave a full account of the incident.'}, {'word': 'advance', 'meanings': ['진보', '사전의', '나아가다', ''], 'distractors': ['후퇴', '정체', '지연'], 'example': 'We made an advance in technology.'}, {'word': 'appeal', 'meanings': ['항소', '매력', '호소', ''], 'distractors': ['거부', '혐오', '외면'], 'example': 'The product has wide appeal.'}, {'word': 'approach', 'meanings': ['접근', '접근법', '다가가다', ''], 'distractors': ['회피', '후퇴', '탈출'], 'example': 'Take a different approach.'}, {'word': 'associate', 'meanings': ['연상하다', '동료', '관련시키다', ''], 'distractors': ['적', '반대자', '고립'], 'example': 'I associate him with honesty.'}, {'word': 'attract', 'meanings': ['끌다', '유인하다', '마음을 끌다', ''], 'distractors': ['밀어내다', '거부하다', '혐오하다'], 'example': 'The event will attract many.'}, {'word': 'authority', 'meanings': ['권위', '당국', '권한', ''], 'distractors': ['무력', '무능', '약함'], 'example': 'He has no authority here.'}, {'word': 'benefit', 'meanings': ['이익', '혜택', '이익을 얻다', ''], 'distractors': ['손해', '불이익', '피해'], 'example': 'Employees get full benefits.'}, {'word': 'claim', 'meanings': ['요구하다', '청구', '주장하다', ''], 'distractors': ['부인하다', '철회하다', '포기하다'], 'example': 'He claimed innocence.'}, {'word': 'clear', 'meanings': ['명확한', '치우다', '분명히 하다', ''], 'distractors': ['모호한', '흐릿한', '불분명한'], 'example': 'She gave a clear explanation.'}, {'word': 'concern', 'meanings': ['걱정', '관심사', '영향을 미치다', ''], 'distractors': ['무관심', '냉담', '무시'], 'example': 'There is concern about safety.'}, {'word': 'condition', 'meanings': ['조건', '상태', '조절하다', ''], 'distractors': ['자유', '불안정', '방해'], 'example': 'Under one condition.'}, {'word': 'consider', 'meanings': ['고려하다', '간주하다', '', ''], 'distractors': ['무시하다', '간과하다', '거부하다'], 'example': 'Please consider my offer.'}, {'word': 'credit', 'meanings': ['신용', '공로', '칭찬', ''], 'distractors': ['비난', '책망', '의심'], 'example': "Give credit where it's due."}, {'word': 'decline', 'meanings': ['감소하다', '거절하다', '쇠퇴', ''], 'distractors': ['증가하다', '상승하다', '개선되다'], 'example': 'Sales declined last year.'}, {'word': 'deliver', 'meanings': ['배달하다', '연설하다', '전달하다', ''], 'distractors': ['수취하다', '받다', '가로채다'], 'example': 'He will deliver the goods.'}, {'word': 'determine', 'meanings': ['결정하다', '판단하다', '결심하다', ''], 'distractors': ['불확실하게 하다', '혼란시키다', '의문을 제기하다'], 'example': 'We must determine the cause.'}, {'word': 'establish', 'meanings': ['설립하다', '입증하다', '', ''], 'distractors': ['폐지하다', '부정하다', '파괴하다'], 'example': 'They established the rule.'}, {'word': 'express', 'meanings': ['표현하다', '급행', '명시된', ''], 'distractors': ['숨기다', '억제하다', '침묵하다'], 'example': 'She expressed her opinion.'}, {'word': 'firm', 'meanings': ['회사', '확고한', '단단한', ''], 'distractors': ['흔들리는', '부드러운', '연약한'], 'example': 'They run a law firm.'}, {'word': 'forward', 'meanings': ['앞으로', '전달하다', '전방의', ''], 'distractors': ['뒤로', '후진하다', '역행하다'], 'example': 'Looking forward to it.'}, {'word': 'hold', 'meanings': ['잡다', '개최하다', '보류하다', ''], 'distractors': ['놓다', '던지다', '해제하다'], 'example': 'Please hold the line.'}, {'word': 'implement', 'meanings': ['이행하다', '도구', '', ''], 'distractors': ['무시하다', '지연시키다', '반대하다'], 'example': 'Implement the plan immediately.'}, {'word': 'observe', 'meanings': ['관찰하다', '준수하다', '말하다', ''], 'distractors': ['무시하다', '외면하다', '간과하다'], 'example': 'She observed the behavior.'}, {'word': 'operate', 'meanings': ['작동하다', '수술하다', '운영하다', ''], 'distractors': ['중단하다', '정지시키다', '파괴하다'], 'example': 'He operates heavy machinery.'}, {'word': 'organize', 'meanings': ['조직하다', '정리하다', '계획하다', ''], 'distractors': ['흩뜨리다', '무질서하게 하다', '혼란시키다'], 'example': 'He organized the files.'}, {'word': 'perform', 'meanings': ['수행하다', '공연하다', '작동하다', ''], 'distractors': ['실패하다', '중단하다', '망치다'], 'example': 'The team performed well.'}, {'word': 'present', 'meanings': ['제시하다', '현재의', '선물', '출석한'], 'distractors': ['숨기다', '없애다', '결석하다'], 'example': 'He presented the results.'}, {'word': 'prevent', 'meanings': ['막다', '예방하다', '', ''], 'distractors': ['조장하다', '촉진하다', '허용하다'], 'example': 'We must prevent disease.'}, {'word': 'process', 'meanings': ['과정', '처리하다', '절차', ''], 'distractors': ['방해하다', '중단시키다', '지연시키다'], 'example': 'The hiring process was fair.'}, {'word': 'produce', 'meanings': ['생산하다', '농산물', '제작하다', ''], 'distractors': ['소비하다', '파괴하다', '없애다'], 'example': 'They produce rice.'}, {'word': 'progress', 'meanings': ['진행', '진보', '발전하다', ''], 'distractors': ['퇴보하다', '후퇴하다', '정체하다'], 'example': 'Progress is steady.'}, {'word': 'raise', 'meanings': ['올리다', '기르다', '모금하다', ''], 'distractors': ['내리다', '떨어뜨리다', '낮추다'], 'example': 'They raised funds.'}, {'word': 'range', 'meanings': ['범위', '산맥', '정렬하다', ''], 'distractors': ['좁히다', '제한하다', '정렬하지 않다'], 'example': 'The price range is wide.'}, {'word': 'record', 'meanings': ['기록하다', '녹음하다', '기록', ''], 'distractors': ['잊다', '삭제하다', '무시하다'], 'example': 'He recorded the meeting.'}, {'word': 'reflect', 'meanings': ['반영하다', '반사하다', '생각하다', ''], 'distractors': ['무시하다', '간과하다', '반대하다'], 'example': 'Reflect on your actions.'}, {'word': 'relate', 'meanings': ['관련시키다', '말하다', '관계있다', ''], 'distractors': ['분리하다', '관계없다', '무관하다'], 'example': 'He related his experience.'}, {'word': 'release', 'meanings': ['출시하다', '석방하다', '발표', ''], 'distractors': ['구금하다', '억류하다', '유지하다'], 'example': 'They released the report.'}, {'word': 'represent', 'meanings': ['대표하다', '나타내다', '의미하다', ''], 'distractors': ['숨기다', '부인하다', '모호하게 하다'], 'example': 'The flag represents freedom.'}, {'word': 'reserve', 'meanings': ['예약하다', '보유하다', '예비의', ''], 'distractors': ['취소하다', '방출하다', '해제하다'], 'example': 'Reserve a table.'}, {'word': 'review', 'meanings': ['검토하다', '복습하다', '평가', ''], 'distractors': ['무시하다', '간과하다', '생략하다'], 'example': 'Review your notes.'}, {'word': 'support', 'meanings': ['지원하다', '지지하다', '부양하다', ''], 'distractors': ['반대하다', '지지하지 않다', '방해하다'], 'example': 'She supports her family.'}, {'word': 'submit', 'meanings': ['제출하다', '복종하다', '', ''], 'distractors': ['거부하다', '저항하다', '철회하다'], 'example': 'Please submit your application.'}, {'word': 'transfer', 'meanings': ['이체하다', '전근하다', '전송하다', ''], 'distractors': ['유지하다', '간직하다', '보관하다'], 'example': 'I want to transfer funds.'}, {'word': 'attach', 'meanings': ['첨부하다', '붙이다', '애착을 가지다', ''], 'distractors': ['떼어내다', '분리하다', '해제하다'], 'example': 'Please attach the file.'}, {'word': 'expand', 'meanings': ['확장하다', '늘리다', '확대되다', ''], 'distractors': ['축소하다', '줄이다', '수축되다'], 'example': 'They plan to expand the service.'}, {'word': 'confirm', 'meanings': ['확인하다', '확정하다', '입증하다', ''], 'distractors': ['취소하다', '부정하다', '불확실하게 하다'], 'example': 'Can you confirm your reservation?'}, {'word': 'analyze', 'meanings': ['분석하다', '검토하다', '', ''], 'distractors': ['종합하다', '조립하다', '결합하다'], 'example': 'We will analyze the results.'}, {'word': 'negotiate', 'meanings': ['협상하다', '교섭하다', '', ''], 'distractors': ['타협하지 않다', '거부하다', '협상을 거부하다'], 'example': 'They will negotiate the contract.'}, {'word': 'guarantee', 'meanings': ['보장하다', '보증서', '확약', ''], 'distractors': ['부정하다', '보장하지 않다', '취소하다'], 'example': 'We guarantee fast delivery.'}, {'word': 'arrange', 'meanings': ['정리하다', '배열하다', '준비하다', ''], 'distractors': ['흐트러뜨리다', '무질서하게 하다', '취소하다'], 'example': 'She arranged a meeting.'}]

        }
    }

    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def update_tag():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    accept_request = {
        "intention": "TagUpdate",
        "payload": {
            "wid": "1",
            "tags": ["영어", "커스텀", "업데이트_개발용"],
        }
    }

    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def update_wordbook():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    accept_request = {
        "intention": "WordbookUpdate",
        "payload": {
            "wid": "6",
            "title": "영어단어장1",
            "tags": ["영어", "커스텀", "개발용"],
            "owner_uid": "1",
            "data": [
                {
                    'word': 'compliment',
                    'meanings': ['칭찬하다', '칭찬', '', ''],
                    'distractors': ['비난하다', '요구하다', '모욕하다'],
                    'example': 'When the applause subsided, Zukerman complimented the artist.'},
                {
                    'word': 'summit',
                    'meanings': ['꼭대기', '정상', '', ''],
                    'distractors': ['기슭', '계곡', '평지'],
                    'example': 'I am the two hundred and ninth person to stand on the summit of Mount Everest.'
                },
                {
                    'word': 'deliver',
                    'meanings': ['배달하다', '전하다', '', ''],
                    'distractors': ['받다', '보관하다', '취소하다'],
                    'example': 'We want answers faster than they can be delivered.'
                },
                {
                    'word': 'alter',
                    'meanings': ['바꾸다', '변경하다', '', ''],
                    'distractors': ['유지하다', '고치다', '늘리다'],
                    'example': "Don't alter your sleep schedule suddenly."
                }
            ]
        }
    }
    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def delete_wordbook():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    accept_request = {
        "intention": "WordbookDelete",
        "payload": {
            "wid": "1",
            "owner_uid": "1",
        }
    }
    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def reject_friend():
    """1. 친구 요청 거부 테스트 (2번 유저가 1번 유저의 요청을 거부)"""
    requestor, requestie = 1, 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    reject_request = {
        "intention": "Reject",
        "payload": {
            "requester": requestor,  # 요청을 보낸 사람
            "requestie": requestie  # 요청을 거부하는 사람 (수신자)
        }
    }
    json_bytes = json.dumps(reject_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_sent_requests():
    """2. Pending 중인 보낸 친구 요청 목록 테스트 (1번 유저 기준)"""
    uid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    sent_request = {
        "intention": "PendingRequests",
        "payload": {
            "uid": uid,
            "type": "sent"
        }
    }
    json_bytes = json.dumps(sent_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_received_requests():
    """3. Pending 중인 받은 친구 요청 목록 테스트 (2번 유저 기준)"""
    uid = 2  # 1번 유저의 요청을 받은 2번 유저
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    received_request = {
        "intention": "PendingRequests",
        "payload": {
            "uid": uid,
            "type": "received"
        }
    }
    json_bytes = json.dumps(received_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def delete_friend():
    """4. 친구 삭제 테스트 (1번 유저가 2번 유저를 삭제)"""
    uid1, uid2 = 1, 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    delete_request = {
        "intention": "DeleteFriend",
        "payload": {
            "requester": uid1,  # 삭제를 요청하는 유저
            "requestie": uid2  # 삭제될 유저
        }
    }
    json_bytes = json.dumps(delete_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_user_info():
    """유저 정보 검색 테스트"""
    uid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "SearchUserByUid",
        "payload": {
            "uid": uid,  # 정보를 원하는 uid
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def subscribe_wordbook(wid, subscriber):
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "Subscribe",
        "payload": {
            "wid": wid,
            "subscriber": subscriber
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def cancle_subscription():
    wid = 4
    subscriber = 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "Cancel",
        "payload": {
            "wid": wid,
            "subscriber": subscriber
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_subscribed_wordbooks():
    uid = 2
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "GetSubscribedWordbooks",
        "payload": {
            "uid": uid
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_wordbook():
    wid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "GetWordbook",
        "payload": {
            "wid": wid
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def search_tag():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    query = "영"
    request = {
        "intention": "SearchTag",
        "payload": {
            "query": query
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def search_wordbook():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    tids = [1, 2, 3]
    request = {
        "intention": "SearchWordbook",
        "payload": {
            "tids": tids
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def dict_text():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    accept_request = {
        "intention": "DictionaryText",
        "payload": {
            "data": [
                {
                    'word': 'compliment',
                    'meanings': ['칭찬하다', '칭찬', '', ''],
                    'distractors': [],
                    'example': ''},
                {
                    'word': 'summit',
                    'meanings': ['꼭대기', '정상', '', ''],
                    'distractors': [],
                    'example': 'I am the two hundred and ninth person to stand on the summit of Mount Everest.'
                },
                {
                    'word': 'deliver',
                    'meanings': ['배달하다', '전하다', '', ''],
                    'distractors': ['받다', '', ''],
                    'example': 'We want answers faster than they can be delivered.'
                },
                {
                    'word': 'alter',
                    'meanings': ['바꾸다', '변경하다', '', ''],
                    'distractors': ['유지하다', '고치다', '늘리다'],
                    'example': ""
                }
            ]
        }
    }
    json_bytes = json.dumps(accept_request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)
    data = recieve_json(tls_socket)
    print(data)


def link_user_word_status():
    uid = 1
    word_ids = [1, 2, 3, 4, 5, 6]
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "LinkUserWord",
        "payload": {
            "uid": uid,
            "word_ids": word_ids,
            "status": "wrong"
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def unlink_user_word_status():
    uid = 1
    word_ids = [1, 2, 3, 4, 5, 6]
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "UnlinkUserWord",
        "payload": {
            "uid": uid,
            "word_ids": word_ids,
            "status": "wrong"
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_user_word_status():
    uid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "GetLinkedWordOfUser",
        "payload": {
            "uid": uid,
            "status": "liked"
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_random_word():
    owner_uid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "GetRandomSubscribedWord",
        "payload": {
            "uid": owner_uid,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def get_wordbook_info_by_id():
    wid = 1
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    request = {
        "intention": "GetWordbookInfoWithID",
        "payload": {
            "wid": wid,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def search_wordbook_or():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    tids = [1, 7]
    request = {
        "intention": "SearchWordbookOr",
        "payload": {
            "tids": tids
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def chatbot_start():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_name = "테스트 세션"
    request = {
        "intention": "SessionStart",
        "payload": {
            "uid": uid,
            "name": session_name
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def chatbot_input():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_id = "sess_a735ca57"
    message = "안녕하세요."
    request = {
        "intention": "ChatInput",
        "payload": {
            "uid": uid,
            "session_id": session_id,
            "message": message
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def quiz_submit():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    word_id = 1
    word_text = "compliment"
    question = "Choose the best meaning of this word."
    user_answer = "요구하다"
    correct_answer = "칭찬하다"
    request = {
        "intention": "QuizSubmit",
        "payload": {
            "uid": uid,
            "word_id": word_id,
            "word_text": word_text,
            "question": question,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def analyze_learnng():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_id = "sess_a735ca57"
    request = {
        "intention": "AnalyzeLearning",
        "payload": {
            "uid": uid,
            "session_id": session_id,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def today_learning():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_id = "sess_a735ca57"
    request = {
        "intention": "TodayReview",
        "payload": {
            "uid": uid,
            "session_id": session_id,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def business_talking():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_id = "sess_a735ca57"
    text = "hello what's the weather today"
    request = {
        "intention": "BusinessTalk",
        "payload": {
            "uid": uid,
            "session_id": session_id,
            "text": text
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def generate_example():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))
    uid = 1
    session_id = "sess_a735ca57"
    request = {
        "intention": "GenerateExample",
        "payload": {
            "uid": uid,
            "session_id": session_id,
        }
    }
    json_bytes = json.dumps(request).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


def sendback():
    if not os.path.exists(SENDBACK_FILE_PATH):
        print("[!] 파일이 존재하지 않습니다.")
        return

    file_size = 5000000
    # file_size = os.path.getsize(SENDBACK_FILE_PATH)
    file_name = os.path.basename(SENDBACK_FILE_PATH)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='./fixtures/cert/server.crt')
    tls_socket = context.wrap_socket(client_socket, server_hostname=SERVER_IP)
    tls_socket.connect((SERVER_IP, PORT))

    # 의도 전송
    stt_request = {
        "intention": "SendBack",
        "payload": {
            "file_name": file_name,
            "file_size": file_size,
        }
    }
    json_bytes = json.dumps(stt_request).encode('utf-8')
    len_bytes = struct.pack('>I', len(json_bytes))
    tls_socket.sendall(len_bytes)
    tls_socket.sendall(json_bytes)

    sent_size = 0
    with open(SENDBACK_FILE_PATH, "rb") as f:
        while sent_size < file_size:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            tls_socket.sendall(data)
            sent_size += len(data)

            # 진행률 출력
            percent = (sent_size / file_size) * 100
            print(f"\r[*] 전송 중... {percent:.2f}% 완료", end='', flush=True)

    print(f"\n[*] 파일 {file_name} 전송 완료")
    data = recieve_json(tls_socket)
    print(data)
    tls_socket.close()


if __name__ == "__main__":
    # auth()
    # friend_list()
    # add_friend()
    # accept_friend()
    # single_dict()
    # multiple_dict()
    # send_file()
    # wordbook_register()
    # update_wordbook()
    # delete_wordbook()
    # update_tag()
    # get_sent_requests()
    # get_received_requests()
    # reject_friend()
    # delete_friend()
    # get_user_info()
    # get_wordbook()
    dict_text()
    # search_tag()
    # search_wordbook()
    # subscribe_wordbook()
    # cancle_subscription()
    # get_subscribed_wordbooks()
    # link_user_word_status()
    # get_user_word_status()
    # unlink_user_word_status()
    # get_random_word()
    # get_wordbook_info_by_id()
    # search_wordbook_or()

    # chatbot_start()
    # chatbot_input()
    # quiz_submit()
    # analyze_learnng()
    # today_learning()
    # business_talking()
    # generate_example()
    # sendback()
    pass
