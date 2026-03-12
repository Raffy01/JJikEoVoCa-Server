import os
import time

from google.cloud import vision
import google.generativeai as genai

from config import Config
GOOGLE_API_KEY = Config.GEMINI_API_KEY

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./my-service-account-key.json"


def detect_text_vision_api(image_source):
    """Google Cloud Vision API를 사용하여 이미지에서 텍스트 추출"""
    client = vision.ImageAnnotatorClient()
    content = image_source

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    if response.error.message:
        raise Exception(f"Vision API Error: {response.error.message}")

    if texts:
        return texts[0].description  # 전체 텍스트 반환
    return ""


def hybrid_image_to_formatted_text(image_source, filename):
    """
    Hybrid 방식: Vision API (OCR) -> Gemini (Text Parsing & Formatting)
    """
    start = time.time()
    # 1. Vision API로 텍스트 추출 (OCR 수행)
    raw_text = detect_text_vision_api(image_source)

    if not raw_text.strip():
        raise ValueError(f"Vision API가 텍스트를 찾지 못했습니다: {filename}")

    # 2. Gemini 설정 (Text-to-Text 모델 사용, 가벼운 flash-lite 추천)
    # T2T와 유사하지만, Raw Text를 파싱해야 하므로 프롬프트는 imageToText와 비슷하게 구성
    model = genai.GenerativeModel("gemini-2.5-flash-lite")  # 최신 라이트 모델 권장

    prompt = f"""
    The following text is OCR extracted from a Korean-English vocabulary book page. 
    Your task is to parse this text, identify vocabulary entries, and format them exactly according to the instructions below.

    **Raw OCR Text:**
    {raw_text}

    **Instructions:**
    1. Identify English words and their Korean meanings.
    2. Extract up to 4 distinct Korean meanings.
    3. Generate 3 distinct, plausible incorrect Korean meanings (distractors).
    4. Extract or generate an English example sentence.
    5. Format: `English_word|Meaning1|Meaning2|Meaning3|Meaning4|Distractor1|Distractor2|Distractor3|Example_Sentence|`
    6. Do NOT include headers. Do NOT repeat meanings.

    **Example Output:**
    abandon|버리다|포기하다|단념하다||시작하다|계속하다|유지하다|He had to abandon his car.|
    """

    # 3. Gemini에게 텍스트 처리 요청
    response = model.generate_content(prompt)
    end = time.time()

    print(f"[*] execution time : {end - start: .5f} sec")
    if response.text:
        return response.text
    else:
        raise ValueError(f"파일 {filename} 처리 중 에러 발생")
