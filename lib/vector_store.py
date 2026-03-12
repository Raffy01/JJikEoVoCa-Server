# app/vector_store.py
import chromadb
import uuid
from typing import List, Dict

from config import Config


class VectorStore:
    def __init__(self, collection_name: str = "chat_memory"):
        # 1. 데이터가 저장될 로컬 폴더 지정 (서버 껐다 켜도 데이터 유지됨)
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        print(f"[*] VectorStore initializing at: {Config.CHROMA_DB_PATH}")
        # 2. 컬렉션(테이블 같은 개념) 생성 또는 불러오기
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_memory(self, text: str, embedding: List[float], metadata: Dict):
        """
        대화 내용과 임베딩 벡터를 저장합니다.
        """
        self.collection.add(
            documents=[text],  # 실제 텍스트 (나중에 검색 결과로 나옴)
            embeddings=[embedding],  # Gemini가 만든 벡터 (검색용)
            metadatas=[metadata],  # 추가 정보 (uid, session_id, role 등)
            ids=[str(uuid.uuid4())]  # 고유 ID
        )

    #filter 인자 추가
    def search_similar(self, query_embedding: List[float], n_results: int = 3,
                       filter_condition: Dict = None) -> List[str]:
        """
        질문 벡터와 유사한 기억을 찾아서 텍스트 리스트로 반환합니다.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_condition  # 여기에 필터 조건(uid 등)을 넣습니다.
        )

        # results['documents']는 이중 리스트 형태라 풀어줘야 함 [[text1, text2...]]
        if results['documents']:
            return results['documents'][0]
        return []
