import hashlib
import logging
import hmac
logger = logging.getLogger(__name__)


def calcaulate_md5(data):
    # MD5 객체 생성
    md5_hash = hashlib.md5()
    try:
        md5_hash.update(data)
    except Exception as e:
        # 기타 에러
        logger.error(e)
        print(f'[!!] {e}')

    return md5_hash.hexdigest()


def compare_hash(hash1, hash2):
    return hmac.compare_digest(hash1, hash2)
