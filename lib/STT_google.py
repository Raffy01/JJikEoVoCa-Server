import base64
import json
import time

import requests

from config import Config

# 1. API 키와 오디오 파일 경로를 설정합니다. (주의: 코드에 키를 직접 넣는 것은 위험합니다!)

API_KEY = Config.GEMINI_API_KEY
URL = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"


def speech_to_text(audio, flag):
    # 2. 오디오 파일을 읽고 Base64로 인코딩합니다.
    encoded_content = base64.b64encode(audio).decode('utf-8')

    # 3. API에 보낼 요청 본문(payload)을 구성합니다.
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 16000,
            "languageCode": "en-US",
        },
        "audio": {
            "content": encoded_content
        }
    }

    # 4. HTTP POST 요청을 보냅니다.
    headers = {"Content-Type": "application/json"}
    start_time = time.time()
    response = requests.post(URL, data=json.dumps(payload), headers=headers)
    end_time = time.time()
    print(f"[*] execution time : {end_time - start_time: .5f} sec")
    # 5. 결과를 출력합니다.
    if response.status_code == 200:
        results = response.json().get('results', [])

        # [수정] 모든 세그먼트의 텍스트를 수집
        transcripts = []
        for result in results:
            # alternatives가 있고, 그 안에 내용이 있는지 확인
            if 'alternatives' in result and result['alternatives']:
                # 가장 신뢰도 높은 첫 번째 대안 선택
                alternative = result['alternatives'][0]
                if 'transcript' in alternative:
                    transcripts.append(alternative['transcript'])

        # 수집된 텍스트가 있다면 공백으로 이어 붙임
        if transcripts:
            full_text = " ".join(transcripts)
            return full_text.replace(",", "").replace(".", "").lower().strip()
        else:
            return None
    else:
        print("API 오류 발생:", response.status_code)
        print("오류 내용:", response.text)

        if flag:
            return None
        else:
            raise AttributeError("API_REQUEST_ERROR")
