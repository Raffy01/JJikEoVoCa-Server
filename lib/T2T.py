import google.generativeai as genai
import logging

from config import Config
logger = logging.getLogger(__name__)

# 환경 변수에서 API 키 불러오기
GOOGLE_API_KEY = Config.GEMINI_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)


def text_to_formatted_text(input_text):
    """텍스트 파일에서 단어와 뜻을 읽어 완전한 형식으로 변환하는 함수"""
    try:
        if not input_text:
            raise ValueError("Empty Input : T2T")

        # Gemini 모델 초기화
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        # 프롬프트 설정
        prompt = f"""
You are given a list of English vocabulary entries with partial information. Each line contains:
`English_word|Meaning1_in_Korean|Meaning2_in_Korean|Meaning3_in_Korean|Meaning4_in_Korean|Distractor1_in_Korean|Distractor2_in_Korean|Distractor3_in_Korean|Example_Sentence|`

Your task is to complete the missing information for each entry according to these rules:

**Input Format Rules:**
1. The English word is always provided (first field)
2. Meaning1 (second field) is always provided and is the primary meaning
3. Meaning2, Meaning3, Meaning4 may or may not be provided (could be empty)
4. Distractor1, Distractor2, Distractor3 are always empty in the input
5. Example_Sentence may or may not be provided (could be empty or partial)

**Your Tasks:**
1. **Keep all provided meanings as-is** (Meaning1, Meaning2, Meaning3, Meaning4)
   - Do NOT modify or remove any existing Korean meanings
   - If a meaning slot is empty, leave it empty

2. **Generate exactly 3 distractors** (incorrect Korean words):
   - These must **not** be correct translations of the English word
   - They should be **semantically plausible incorrect options** related to the word or its meanings
   - Choose words of similar type (e.g., verbs for verb meanings, nouns for noun meanings)
   - Make them plausible wrong answers in a vocabulary quiz context
   - **All 3 distractors must be distinct from each other and from the correct meanings**

3. **Handle the example sentence**:
   - If an example sentence is already provided (even if partial), **complete it or improve it** to make it a full, natural English sentence
   - If no example sentence is provided, **create a new one** in English
   - The example sentence must use the English word according to its **Meaning1** (primary meaning)
   - Make the sentence natural, clear, and demonstrative of the word's usage

4. **Output Format**:
   - Maintain the exact pipe-delimited format: `English_word|Meaning1|Meaning2|Meaning3|Meaning4|Distractor1|Distractor2|Distractor3|Example_Sentence|`
   - Keep empty meaning slots empty (nothing between pipes)
   - Ensure all fields are properly separated by pipes
   - Do not include headers or extra lines

**Example Transformations:**

Input: `compliment|칭찬하다|칭찬|||||||`
Output: `compliment|칭찬하다|칭찬|||비난하다|무시하다|비판하다|She received many compliments on her presentation.|`

Input: `durability|내구성|||||||Price is a secondary consideration and|`
Output: `durability|내구성||||가격|무게|속도|Price is a secondary consideration and durability is the primary factor.|`

Input: `abandon|버리다|포기하다|단념하다||||He had to abandon|`
Output: `abandon|버리다|포기하다|단념하다||시작하다|계속하다|유지하다|He had to abandon his car in the snow.|`

**Now process the following vocabulary entries:**

{input_text}
"""

        # 텍스트 생성 요청
        response = model.generate_content(prompt)

        # 응답에서 텍스트 가져오기
        generated_text = response.text if response.text else "텍스트를 생성하지 못했습니다."

        print(f"[*] 입력 라인 수: {len(input_text.splitlines())}")
        print(f"[*] 출력 라인 수: {len(generated_text.splitlines())}")

        return generated_text
    except Exception as e:
        logger.error(f"Error During T2T : {e}")
        print(f"[!!] Error During T2T : {e}")
        raise

