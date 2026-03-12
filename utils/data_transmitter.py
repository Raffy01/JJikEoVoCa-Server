import socket
import os
import logging
import json
import struct
import io

from config import Config
logger = logging.getLogger(__name__)
BUFFER_SIZE = 65536  # 64KB


def receive_file(conn, raw_file_name, file_size_str):
    """
    클라이언트에서 파일을 전달 받음.
    받은 후 파일 경로를 리턴
    """
    conn.settimeout(Config.TIMEOUT_TIME)  # 타임아웃 설정
    safe_file_name = os.path.basename(raw_file_name)  # 경로 침투 공격 방지
    file_path = os.path.join('./uploads/', safe_file_name)
    try:
        file_size = int(file_size_str)
        if file_size < 0:
            raise ValueError("File size cannot be negative.")
    except ValueError as e:
        logger.error(f"Invalid file size: {file_size_str}. Error: {e}")
        print(f"\n[!] 잘못된 파일 크기: {file_size_str}")
        raise

    logger.info(f"Received File: {safe_file_name} ({file_size / (1024 * 1024):.2f} MB)")
    print(f"[*] 수신할 파일: {safe_file_name} ({file_size / (1024 * 1024):.2f} MB)")

    received_size = 0
    f = io.BytesIO()
    while received_size < file_size:
        remaining = file_size - received_size
        bytes_to_read = min(remaining, BUFFER_SIZE)

        try:
            data = conn.recv(bytes_to_read)
        except socket.timeout:
            raise TimeoutError("Timeout During File Receive")

        if not data:
            break

        # 2. 메모리 버퍼에 씁니다 (사용법은 파일과 동일)
        f.write(data)

        received_size += len(data)
        print(f"\r[*] 수신 중... {(received_size / file_size) * 100:.2f}% 완료", end='', flush=True)

    print("\n[*] 수신 완료 (메모리)")

    # 3. 중요: 쓰기가 끝났으므로 커서를 맨 앞으로 이동 (읽기 위해)
    f.seek(0)

    if received_size != file_size:
        logger.warning(f"File Transfer Uncompleted: Expected {file_size} Bytes, "
                       f"Received {received_size} Bytes")
        print(f"[!] 파일 전송 불완전: 기대 {file_size} 바이트, 수신 {received_size} 바이트")

    print(f"[*] 파일 {file_path} 저장 완료")
    return safe_file_name, f


def recieve_json(conn):
    """
    연결된 소켓으로부터 JSON 데이터를 안정적으로 수신합니다.
    [4바이트 길이 정보] + [JSON 데이터] 형식으로 수신합니다.
    """
    conn.settimeout(Config.TIMEOUT_TIME)  # 타임아웃 설정
    # 1. 데이터 길이(4바이트)를 먼저 받습니다.
    len_bytes = conn.recv(4)

    if not len_bytes:
        return None
    # 받은 4바이트를 정수로 변환합니다.
    data_length = struct.unpack('>I', len_bytes)[0]

    # Debug : 그냥 1바이트 캐릭터로 받기
    # data_length = ord(len_bytes.decode())

    # 2. 위에서 얻은 길이만큼의 데이터를 모두 수신합니다.
    data = b''
    while len(data) < data_length:
        packet = conn.recv(data_length - len(data))
        if not packet:
            return None
        data += packet

    # 3. 수신한 데이터를 JSON으로 디코딩하여 반환합니다.
    return json.loads(data.decode())


def send_json(conn, data):
    """
    연결된 소켓에 JSON 데이터를 송신합니다.
    [4바이트 길이 정보] + [JSON 데이터] 형식으로 송신합니다.
    """
    conn.settimeout(Config.TIMEOUT_TIME)  # 타임아웃 설정
    # 1. json으로 dump 후 길이 측정.
    json_bytes = json.dumps(data).encode('utf-8')
    len_bytes = struct.pack(">I", len(json_bytes))
    # 2. length 먼저 송신.
    conn.sendall(len_bytes)
    # 3. json 데이터 송신
    conn.sendall(json_bytes)
