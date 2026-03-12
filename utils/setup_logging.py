import logging
from config import Config


def setup_logging():
    """
    애플리케이션 전체에서 사용할 로깅을 설정합니다.
    Config 설정에 따라 로그 파일 위치와 레벨이 결정됩니다.
    """
    # 1. 로그 파일 경로 설정 (Config.LOG_DIR 사용)
    # config.py에서 이미 폴더 생성(mkdir)을 처리했으므로 바로 파일 경로만 잡으면 됩니다.
    log_file_path = Config.LOG_DIR / "server.log"

    # 2. 로깅 레벨 설정
    # DEBUG 모드면 상세하게(DEBUG), 아니면 일반 정보(INFO)만 기록
    log_level = logging.DEBUG if Config.DEBUG else logging.INFO
    print(f"[*] 로그 파일 생성됨 : {log_file_path}")
    logging.basicConfig(
        filename=str(log_file_path),  # Path 객체를 문자열로 변환
        encoding='utf-8',
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',  # 포맷 가독성 살짝 개선 ([INFO] 형태)
        datefmt='%Y-%m-%d %H:%M:%S'  # 날짜 포맷 지정 (선택 사항)
    )

    # (옵션) 서버 시작 시 현재 로그 레벨을 기록
    logging.getLogger("Setup").info(f"Logging setup complete. Level: {logging.getLevelName(log_level)}")