import time
import io
import logging
logger = logging.getLogger(__name__)

import google.generativeai as genai
import PIL.Image

from config import Config

# 환경 변수에서 API 키 불러오기 (보안을 위해 직접 코드에 입력하지 않음)
GOOGLE_API_KEY = Config.GEMINI_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)


def image_to_formatted_text(image_source, filename):
    """이미지를 분석하여 단어장을 추출하고 txt 파일로 저장하는 함수"""
    try:
        # [수정된 부분] 입력 타입에 따라 이미지 로드 방식 분기
        if isinstance(image_source, bytes):
            # 바이트 데이터인 경우 io.BytesIO로 감싸서 파일 객체처럼 만듦
            image = PIL.Image.open(io.BytesIO(image_source))
        else:
            # 파일 경로(String)인 경우 그대로 로드
            image = PIL.Image.open(image_source)

        # Gemini Flash 모델 초기화
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

        # 프롬프트 설정
        prompt = """
The image contains pages from a Korean-English vocabulary book. Your task is to extract vocabulary information from each entry and format it as a table according to the specific instructions below.

Follow these instructions precisely for each vocabulary entry (English word and its meanings/example sentence):

1. Extract the English word.

2. Extract *all* the Korean meanings provided for that English word in the vocabulary book. List up to a maximum of 4 **distinct** Korean meanings in the order they appear (Meaning1, Meaning2, Meaning3, Meaning4).

3. The first meaning (Meaning1) must be the primary meaning or the one that corresponds to the example sentence provided.

4. **Important**: If fewer than 4 distinct Korean meanings are found for a word in the book:
   - Fill only the available meaning slots with the extracted meanings
   - Leave the remaining meaning slots **completely empty** (no text between the pipes)
   - **Do NOT repeat the same meaning multiple times**

5. Generate exactly **3 incorrect Korean words** as distractors:
   - These incorrect words must **not** be correct translations of the English word
   - They should be **semantically plausible incorrect options** related to the English word, its correct meanings, or the example sentence
   - Avoid generating completely arbitrary words unless they are relevant in a misleading way
   - Prioritize generating words of a similar type (e.g., a verb if the meaning is a verb)
   - Choose distractors that are plausible wrong answers within a vocabulary learning context
   - **Distractors must be distinct from each other and from the correct meanings**

6. Extract the example sentence provided for the word. If no example sentence is present in the book for a word, create one in English that uses the word according to its Meaning1.

7. Format the output for each vocabulary entry as a single line using the pipe symbol (|) as the separator. The format is:
`English_word|Meaning1_in_Korean|Meaning2_in_Korean|Meaning3_in_Korean|Meaning4_in_Korean|Distractor1_in_Korean|Distractor2_in_Korean|Distractor3_in_Korean|Example_Sentence|`

8. Ensure that:
   - Meaning1-4 contain only Korean meanings extracted from the book (leave empty if not available)
   - Distractor1-3 contain only incorrect Korean words that serve as plausible wrong answers
   - The Example_Sentence field contains the English example sentence
   - Absolutely no English text (except in the Example Sentence field) should appear in the meaning or distractor fields
   - **Never repeat the same Korean word in multiple fields**

9. Do not include column headers in the output.

Example output formats:
- Word with 4 meanings: `abandon|버리다|포기하다|단념하다|중단하다|시작하다|계속하다|유지하다|He had to abandon his car in the snow.|`
- Word with 2 meanings: `summit|꼭대기|정상|||기슭|계곡|평지|I am the two hundred and ninth person to stand on the summit of Mount Everest.|`
- Word with 1 meaning: `durability|내구성||||가격|무게|속도|Price is a secondary consideration and durability is not value at all.|`
"""
        start = time.time()
        # 이미지 분석 요청
        response = model.generate_content([prompt, image])

        end = time.time()
        print(f"[*] execution time : {end - start: .5f} sec")

        # 응답에서 텍스트 가져오기
        extracted_text = response.text if response.text else "텍스트를 추출하지 못했습니다."
        return extracted_text
    except Exception as e:
        print(f"[!!] 오류 발생: {filename} 처리 중 문제 발생 - {e}")
        logger.error(f"Error Processing {filename} : {e}")
        raise
