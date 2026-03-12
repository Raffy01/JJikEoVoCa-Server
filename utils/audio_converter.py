import subprocess


def convert_to_wav_bytes(input_bytes):
    """
    메모리 상의 바이트 데이터를 받아 ffmpeg로 변환 후 바이트 데이터로 반환
    """
    command = [
        "ffmpeg",
        "-y",
        "-i", "pipe:0",  # [핵심] 입력 파일을 pipe:0 (stdin)으로 설정
        "-ar", "16000",  # 샘플레이트 16kHz
        "-ac", "1",  # 모노 채널
        "-c:a", "pcm_s16le",  # 코덱
        "-f", "wav",  # [핵심] 출력 포맷 명시 (파일 확장자가 없으므로 필수)
        "pipe:1"  # [핵심] 출력 파일을 pipe:1 (stdout)으로 설정
    ]

    try:
        # input=input_bytes를 통해 데이터를 stdin으로 밀어넣음
        process = subprocess.run(
            command,
            input=input_bytes,  # 입력 데이터
            stdout=subprocess.PIPE,  # 결과 데이터 캡처
            stderr=subprocess.PIPE,  # 로그 캡처
            check=True
        )
        print(f"[*] 메모리 내 변환 성공")
        return process.stdout  # 변환된 바이트 데이터 반환

    except subprocess.CalledProcessError as e:
        print(f"[!!] ffmpeg 변환 실패")
        # 에러 로그는 stderr에 있음 (bytes 타입이므로 decode 필요)
        print(f"[*] stderr: {e.stderr.decode('utf-8') if e.stderr else 'Unknown'}")
        raise RuntimeError("Unable to convert Codec")
