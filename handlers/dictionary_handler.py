import logging

import utils
from lib import hybridToText, T2T
logger = logging.getLogger(__name__)


def handle_image(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {
            "message": "An unexpected error occurred on the server."
        }
    }
    try:
        text = ""
        rep = int(payload.get('cnt'))
        print(f"[*] {rep} image(s) requested")
        logger.info(f"{rep} image(s) requested")
        filenames = payload.get('file_name')
        filesizes = payload.get('file_size')
        if not all([rep, filenames, filesizes]):
            raise ValueError("Missing required fields in payload")
        for i in range(rep):
            file_name, f = utils.receive_file(conn, filenames[i], filesizes[i])
            text += hybridToText.hybrid_image_to_formatted_text(f.getvalue(), file_name)
            logger.info(f"{file_name} parsed")
            print(f"[*] {file_name} parsed")

        parsed_data = utils.wordbook_to_json(text)
        if parsed_data is not None:
            reply = {
                "status": "ACCEPT",
                "code": "PARSED",
                "payload": {
                    "data": parsed_data
                }
            }
            utils.send_json(conn, reply)
        else:
            reply = {
                "status": "REJECT",
                "code": "OCR_FAILED",
                "payload": {
                    "message": text if not None else "Null"
                }
            }
    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)


def handle_text(conn, addr, payload):
    reply = {
        "status": "ERROR",
        "code": "INTERNAL_SERVER_ERROR",
        "payload": {
            "message": "An unexpected error occurred on the server."
        }
    }
    try:
        raw_data = payload.get('data')
        if not raw_data:
            raise ValueError("Missing required fields in payload")
        data = utils.json_to_wordbook(raw_data)
        text = T2T.text_to_formatted_text(data)
        parsed_text = utils.wordbook_to_json(text)
        if parsed_text is not None:
            reply = {
                "status": "ACCEPT",
                "code": "PARSED",
                "payload": {
                    "data": parsed_text
                }
            }
            utils.send_json(conn, reply)
        else:
            reply = {
                "status": "REJECT",
                "code": "GENERATION_FAILED",
                "payload": {
                    "message": text if not None else "Null"
                }
            }
    except ValueError as e:
        logger.error(f"Value error from {addr}: {e}")
        print(f"[!!] Value Error from {addr}: {e}")
        reply = {"status": "REJECT", "code": "BAD_REQUEST", "payload": {"message": str(e)}}
        utils.send_json(conn, reply)
    except Exception as e:
        logger.error(f"Error with {addr}: {e}")
        print(f"[!!] Error with {addr}: {e}")
        utils.send_json(conn, reply)