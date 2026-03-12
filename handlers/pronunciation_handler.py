import os
import logging

import requests

import utils
from lib import STT_google, similarity_checker
logger = logging.getLogger(__name__)


def handle(conn, addr, payload):
    """
    파일을 전송 받은 후, STT와 유사도를 확인하여 true/false를 client에 전송
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        codec_mismatch_occured = False

        target_text = payload.get('answer')
        raw_filename = payload.get('file_name')
        raw_filesize = payload.get('file_size')
        if not all([target_text, raw_filename, raw_filesize]):
            raise ValueError("Header Information Format Error")

        safe_file_name, file_path = utils.receive_file(conn, raw_filename, raw_filesize)

        result = False
        try:
            inferred_text = STT_google.speech_to_text(file_path, codec_mismatch_occured)
        except AttributeError:
            codec_mismatch_occured = True

            print(f"[!] Codec Mismatch. Converting to pcm_s16le")
            logger.warning(f"Codec Mismatch. Converting to pcm_s16le")

            utils.convert_to_wav(file_path)

            inferred_text = STT_google.speech_to_text(os.path.join("./uploads/fixed/", safe_file_name),
                                                      codec_mismatch_occured)
        if inferred_text is None:
            raise requests.HTTPError("API Request Denied")

        similarity = similarity_checker.pronunciation_similarity_CMU(target_text, inferred_text)
        if similarity is None:
            similarity = similarity_checker.pronunciation_similarity_double_metaphone(target_text, inferred_text)
        if similarity > 0.75:
            result = True

        print(f"[*] Target Text : {target_text}, Inferred Text :{inferred_text}, Similarity : {similarity:.2f}")
        logger.info(f"Target Text : {target_text}, Inferred Text :{inferred_text}, Similarity : {similarity:.2f}")

        reply = {
            "status": "ACCEPT",
            "code": "PROCESSED" if not codec_mismatch_occured else "PROCESSED_WITH_CODEC_CONVERSION",
            "payload": {
                "result": str(result)
            }
        }
        utils.send_json(conn, reply)
    except (ValueError, requests.HTTPError) as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def sendback(conn, addr, payload):
    """
    파일을 전송 받은 후, STT하여 리턴
    """
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {"message": "An unexpected error occurred on the server."}
    }
    try:
        codec_mismatch_occured = False

        raw_filename = payload.get('file_name')
        raw_filesize = payload.get('file_size')
        if not all([raw_filename, raw_filesize]):
            raise ValueError("Header Information Format Error")

        safe_file_name, file_path = utils.receive_file(conn, raw_filename, raw_filesize)

        try:
            inferred_text = STT_google.speech_to_text(file_path, codec_mismatch_occured)
        except AttributeError:
            codec_mismatch_occured = True

            print(f"[!] Codec Mismatch. Converting to pcm_s16le")
            logger.warning(f"Codec Mismatch. Converting to pcm_s16le")

            utils.convert_to_wav(file_path)

            inferred_text = STT_google.speech_to_text(os.path.join("./uploads/fixed/", safe_file_name),
                                                      codec_mismatch_occured)
        if inferred_text is None:
            raise requests.HTTPError("API Request Denied")

        print(f"[*] Inferred Text : {inferred_text}")
        logger.info(f"Inferred Text : {inferred_text}")

        reply = {
            "status": "ACCEPT",
            "code": "PROCESSED" if not codec_mismatch_occured else "PROCESSED_WITH_CODEC_CONVERSION",
            "payload": {
                "message": inferred_text
            }
        }
        utils.send_json(conn, reply)
    except (ValueError, requests.HTTPError) as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)
