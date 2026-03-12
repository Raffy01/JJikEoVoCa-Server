import json

# DatabaseManager를 import하여 타입 힌트에 사용
from lib.db_manager import DatabaseManager
from lib.ai_client import GeminiClient
from lib.vector_store import VectorStore


# from lib.models import UserWordStats, MistakeRecord # DTO는 사용하지 않고 Dict 타입으로 처리

class VocabularyService:
    # Repository 대신 DatabaseManager 타입을 받도록 변경
    # VocabularyService가 Repository 역할을 직접 수행하게 되므로 self.repo 대신 self.db 사용
    def __init__(self, db: DatabaseManager, ai: GeminiClient, vector_store: VectorStore):
        self.db = db  # DatabaseManager 인스턴스 (DAO 역할 수행)
        self.ai = ai
        self.vector_store = vector_store

    # ====================================================
    # 1. 기본 채팅 기능
    # ====================================================
    def process_chat(self, owner_uid: int, session_id: str, user_msg: str) -> str:
        # ---------------------------------------------------------
        # 1. [RAG] 현재 질문과 관련된 '과거 기억' 검색
        # ---------------------------------------------------------
        query_vec = self.ai.get_embedding(user_msg)

        relevant_memories = []
        if query_vec:
            # db_manager는 owner_uid가 INTEGER이므로 uid 필터링을 INTEGER로 변경
            relevant_memories = self.vector_store.search_similar(
                query_vec,
                n_results=3,
                filter_condition={"uid": str(owner_uid)}  # ChromaDB는 TEXT 저장했으므로 str로 변환
            )

        # 1-3. 검색된 기억을 하나의 문자열로 합침
        memory_context = "\n".join([f"- {mem}" for mem in relevant_memories])
        if not memory_context:
            memory_context = "관련된 과거 대화 없음."

        # ---------------------------------------------------------
        # 2. [DB] 유저 통계, 실수 기록, 대화 이력 조회 (DAO 메소드 사용)
        # ---------------------------------------------------------

        # Step 2에서 db_manager에 추가한 DAO 메소드 사용
        stats = self.db.get_user_stats(owner_uid)
        mistakes = self.db.get_recent_mistakes(owner_uid)
        history = self.db.get_session_history(session_id)

        # DTO 대신 Dict를 사용하므로 필드 접근 방식을 수정합니다.
        vocab_context = "\n".join([f"- {s['word']}: {s['meaning']}" for s in stats])
        mistake_context = "\n".join([f"- Mistake: {m['question']} -> {m['user_answer']}" for m in mistakes])
        history_text = "\n".join([f"{h['role']}: {h['message']}" for h in history])

        prompt = f"""
        Context: The user is learning English.
        User Stats: {vocab_context}
        Recent Mistakes: {mistake_context}
        Chat History: {history_text}
        User Message: {user_msg}


        [Recalled Memories (관련된 과거 기억)]
        {memory_context}

        [Student's Vocabulary Stats]
        {vocab_context}

        User: {user_msg}

        위의 '과거 기억'을 참고하여 개인화된 답변을 해주세요.

        Respond naturally in Korean, using English for examples.
        """

        response = self.ai.generate(prompt)

        # ---------------------------------------------------------
        # 3. [DB] 대화 로그 저장 (DAO 메소드 사용)
        # ---------------------------------------------------------
        self.db.save_chat_content(owner_uid, session_id, 'user', user_msg)
        self.db.save_chat_content(owner_uid, session_id, 'assistant', response)

        return response

    # ====================================================
    # 2. 오답 예문 생성 기능 (generate_examples_for_mistakes)
    # ====================================================
    def generate_examples_for_mistakes(self, owner_uid: int, session_id: str) -> str:
        """오늘 틀린 단어들에 대해 예문을 생성합니다. (임시)"""
        # DB Manager에 구현되지 않은 get_todays_mistakes_for_examples 함수를 호출해야 함.
        # 이 함수가 필요하다면 db_manager.py에 추가해야 합니다.
        # 일단은 로직 구현을 위해 빈 리스트를 반환한다고 가정합니다.
        wrong_words = self.db.get_todays_mistakes_for_examples(owner_uid)

        if not wrong_words:
            return "오늘 기록된 오답이 없어 예문을 생성할 필요가 없습니다. 🎉"

        results = []
        for item in wrong_words:
            word = item['word']
            meaning = item['meanings']

            prompt = f"""
            Generate ONE natural English example sentence for the word '{word}' (meaning: {meaning}).
            Level: Intermediate. 
            Output ONLY the sentence.
            """
            example = self.ai.generate(prompt).strip()

            # DB 업데이트 (이 메소드도 db_manager에 추가해야 합니다)
            # self.db.update_word_example(owner_uid, item['word_id'], example)

            results.append(f"✅ **{word}**: {example}")

        final_report = "오늘 틀린 단어들에 대한 새 예문을 생성했습니다:\n\n" + "\n".join(results)

        # 채팅 로그에 시스템 메시지로 남기기
        self.db.save_chat_content(owner_uid, session_id, 'system', "Generated examples for wrong words.")

        return final_report

    # ====================================================
    # 3. 학습 분석 및 계획 기능 (analyze_learning_patterns)
    # ====================================================
    def analyze_learning_patterns(self, owner_uid: int, session_id: str) -> str:
        """유저의 학습 패턴을 분석하고 조언을 제공합니다."""
        # 데이터 수집 (DAO 메소드 사용)
        freq_wrong = self.db.get_frequently_wrong_words(owner_uid)
        recent_mistakes = self.db.get_recent_mistakes(owner_uid, limit=15)
        chat_history = self.db.get_session_history(session_id, limit=50)

        # 프롬프트 구성용 데이터 포맷팅
        wrong_summary = "\n".join([f"- {w['word']} (오답 {w['incorrect_count']}회)" for w in freq_wrong])
        mistake_summary = "\n".join([f"- Q:{m['question']} / User:{m['user_answer']}" for m in recent_mistakes])

        prompt = f"""
        You are an expert English learning coach. Analyze this student's data:

        [Top Incorrect Words]
        {wrong_summary if wrong_summary else "No specific data yet."}

        [Recent Mistakes]
        {mistake_summary if mistake_summary else "No recent mistakes."}
        
        [Chat Context]
        (Analysis based on conversation style...)

        Please provide a study plan in Korean:
        1. Weakness Diagnosis (취약점 진단)
        2. Study Plan for next week (학습 계획)
        3. Encouragement (격려)
        """

        analysis = self.ai.generate(prompt)

        # 로그 저장
        self.db.save_chat_content(owner_uid, session_id, 'assistant', analysis)

        return analysis

    # ====================================================
    # 4. 오늘 학습 복습 기능 (review_todays_learning)
    # ====================================================
    def review_todays_learning(self, owner_uid: int, session_id: str) -> str:
        """오늘 학습하거나 틀린 단어들을 복습하는 리포트를 생성합니다."""
        # 이 함수도 db_manager에 추가해야 합니다. (get_todays_studied_words)
        todays_words = self.db.get_todays_studied_words(owner_uid)

        if not todays_words:
            return "오늘 아직 학습한 단어가 없습니다. 퀴즈를 풀거나 대화를 시작해보세요!"

        words_list = "\n".join([f"- {w['word']}: {w['meanings']}" for w in todays_words])

        prompt = f"""
        Create a review session for today's words:
        Words:
        {words_list}

        1. Summarize the words.
        2. Create a mini fill-in-the-blank quiz (3 questions) using these words.
        3. Provide tips to memorize them.

        Output in Korean, but English for Quiz/Examples.
        """

        review_content = self.ai.generate(prompt)
        self.db.save_chat_content(owner_uid, session_id, 'assistant', review_content)

        return review_content

    # ====================================================
    # 5. 퀴즈 결과 제출 및 벡터 저장 (submit_quiz_result)
    # ====================================================
    def submit_quiz_result(self, uid: int, word_id: int, word_text: str,
                           question: str, user_answer: str, correct_answer: str):
        """
        [API용] 클라이언트로부터 오답 리포트를 받아 처리합니다.
        1. DB(SQLite)에 기록 (통계 반영)
        2. Vector Store(ChromaDB)에 '오답 기억' 추가 (RAG용)
        """

        # 1. DB에 저장 (통계 및 로그) - Step 2에서 db_manager에 추가한 메소드 사용
        # session_id가 client_quiz 시스템 로그에 해당하므로 'CLIENT_QUIZ_SYSTEM'으로 하드코딩
        session_id = 'CLIENT_QUIZ_SYSTEM'
        self.db.record_mistake(
            owner_uid=uid,
            session_id=session_id,
            master_word_id=word_id,
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer,
            mistake_type="client_quiz"
        )

        # 2. 장기 기억(Vector Store)에 저장 (RAG용)
        memory_text = f"[Mistake Record] User answered '{user_answer}' for question '{question}'. The correct answer was '{correct_answer}'. (Word: {word_text})"

        # 텍스트를 벡터로 변환
        embedding = self.ai.get_embedding(memory_text)

        if embedding:
            self.vector_store.add_memory(
                text=memory_text,
                embedding=embedding,
                metadata={
                    # ChromaDB 필터링을 위해 uid를 string으로 저장
                    "uid": str(uid),
                    "type": "mistake",
                    "word": word_text,
                    "source": "client_quiz"
                }
            )

        return "Mistake recorded successfully."

    # [New] 비즈니스 회화 기능 추가
    def process_business_conversation(self, owner_uid: int, session_id: str, user_text: str) -> str:
        """
             [회화 모드] 비즈니스 영어 코칭 및 롤플레잉
             STT로 입력된 텍스트를 받아 교정(Feedback)해주고 대화를 이어나감.
             """
        # 1. RAG: 관련 기억 검색 (회화 흐름 유지를 위해 1개만 참조)
        query_vec = self.ai.get_embedding(user_text)
        relevant_memories = []
        if query_vec:
            relevant_memories = self.vector_store.search_similar(
                query_vec, n_results=1, filter_condition={"uid": str(owner_uid)}
            )
        memory_context = "\n".join(relevant_memories)

        # 2. 최신 프롬프트 적용 (JSON 포맷 응답 요청)
        prompt = f"""
             You are a professional Business English Coach. The user is practicing speaking via STT.

             [Context Memory]
             {memory_context}

             [User's Spoken Text]
             "{user_text}"

             [Instructions]
             1. **Role**: Act as a colleague or business partner in a professional setting.
             2. **Feedback**: Check if the user's expression is natural for business. 
                - If it's rude, awkward, or grammatically incorrect, provide specific advice and a "Better Expression" **IN KOREAN**.
                - If the expression is good, keep the feedback as an empty string "".
             3. **Response**: Continue the conversation naturally **IN ENGLISH**. Keep your response concise (1-2 sentences) suitable for listening (TTS).
             4. **Format**: Return ONLY a JSON object.

             [JSON Format Example]
             {{
                 "feedback": "'give me'는 비즈니스 상황에서 너무 직설적입니다. 대신 'Could you please provide...'를 사용하는 것이 훨씬 정중합니다.",
                 "response": "Certainly. I will send you the details by email right away."
             }}
             """

        # 3. AI 응답 생성 및 파싱
        ai_raw_response = self.ai.generate(prompt)

        try:
            # 마크다운 코드 블록 제거
            clean_response = ai_raw_response.replace("```json", "").replace("```", "").strip()
            response_json = json.loads(clean_response)
            final_response = json.dumps(response_json, ensure_ascii=False)
        except Exception as e:
            # 파싱 실패 시 fallback
            print(f"[!] JSON Parsing Failed: {e}")
            final_response = json.dumps({
                "feedback": "",
                "response": ai_raw_response  # 원문 그대로 반환
            }, ensure_ascii=False)

        # 4. 대화 로그 저장
        self.db.save_chat_content(owner_uid, session_id, 'user', f"[Speech] {user_text}")
        self.db.save_chat_content(owner_uid, session_id, 'assistant', final_response)

        return final_response
