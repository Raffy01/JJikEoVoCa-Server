import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 1. 프로젝트 기본 경로 설정 (프로젝트 루트)
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """
    모든 설정값을 관리하는 클래스입니다.
    """

    # [서버 네트워크 설정]
    HOST = '0.0.0.0'
    PORT = 2121
    THREADS = 5
    TIMEOUT_TIME = 5.0

    # [필수] 구글 제미나이 API 키
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # [데이터베이스 설정]
    # 기존 db_manager.py의 경로: ./res/database/app.db
    DB_NAME = os.getenv("DB_NAME", "app.db")

    # Path 객체는 '/' 연산자로 경로를 연결합니다. (가장 안전한 방법)
    DB_DIR = BASE_DIR / "res" / "database"
    DB_PATH = str(DB_DIR / DB_NAME)
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))

    # DB 폴더가 없으면 자동 생성 (에러 방지)
    if not DB_DIR.exists():
        DB_DIR.mkdir(parents=True, exist_ok=True)

    # [Vector Store 설정]
    CHROMA_DB_PATH = str(BASE_DIR / "res" / "database" / "chroma_db_data")

    # [보안/인증서 설정 (TLS)]
    # 기존 main.py 경로: ./res/cert/server.crt
    CERT_DIR = BASE_DIR / "res" / "cert"
    SSL_CERT_PATH = str(CERT_DIR / "server.crt")
    SSL_KEY_PATH = str(CERT_DIR / "server.key")

    # [앱 설정]
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # [로그 설정]
    LOG_DIR = BASE_DIR / "res" / "logs"
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(exist_ok=True)

    # [기본 단어장 설정]
    DEFAULT_WORDBOOKS = [13, 14, 15, 16, 17]


# 설정값 검증
if not Config.GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY is not set in environment variables!")