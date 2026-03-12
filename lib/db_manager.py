import sqlite3
from contextlib import contextmanager
import queue
import uuid

from config import Config


def _add_word_logic(wordbook_id, term, meanings, distractors, example_sentence, cursor):
    """실제 단어 추가 로직을 처리하는 내부 메소드"""

    # 1. Master_Words 테이블에 단어가 이미 있는지 확인
    cursor.execute('''
        SELECT master_word_id FROM Master_Words
        WHERE term = ? AND meanings = ? AND example_sentence = ?
    ''', (term, meanings, example_sentence))
    word_row = cursor.fetchone()

    if word_row:
        # 2a. 단어가 이미 존재하면 ID를 가져옴
        master_word_id = word_row['master_word_id']
    else:
        # 2b. 단어가 없으면 새로 추가
        cursor.execute('''
            INSERT INTO Master_Words (term, meanings, distractors, example_sentence)
            VALUES (?, ?, ?, ?)
        ''', (term, meanings, distractors, example_sentence))
        master_word_id = cursor.lastrowid

    # 3. 단어장과 단어를 연결
    cursor.execute('''
        INSERT OR IGNORE INTO Wordbook_Words (wordbook_id, master_word_id)
        VALUES (?, ?)
    ''', (wordbook_id, master_word_id))

    # master_word_id를 반환하여 '버전 해시' 계산에 사용할 수 있도록 함
    return master_word_id


class DatabaseManager:
    """
    app.db를 관리하는 통합 데이터베이스 매니저 클래스.
    컨텍스트 매니저를 사용하여 DB 연결을 효율적이고 안전하게 처리합니다.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """데이터베이스 파일 경로를 초기화하고, 커넥션 풀을 생성합니다."""
        if DatabaseManager._instance is not None:
            raise Exception("Duplicate call of singleton class")
        self.db_path = Config.DB_PATH
        self.pool_size = Config.DB_POOL_SIZE

        self._connection_pool = queue.Queue(maxsize=self.pool_size)
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                self._connection_pool.put(conn)
            except sqlite3.Error as e:
                print(f"[!!] Failed to create initial connection: {e}")
                raise
        print(f"[*] Database connecting to: {self.db_path}")
        print(f"[*] Connection pool initialized with {self._connection_pool.qsize()} connections.")

    def _create_connection(self):
        """새로운 DB 연결을 생성하는 내부 헬퍼 메소드"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # --- 연결 관리자 (Context Manager) ---
    @contextmanager
    def _managed_connection(self):
        """커넥션 풀에서 커넥션을 가져오고 반납하는 컨택스트 매니저"""
        conn = None
        try:
            # Pool에서 커넥션을 가져옴. 풀이 비어있으면 반납할 때 까지 대기.
            conn = self._connection_pool.get(block=True, timeout=5)
            conn.execute('SELECT 1')
            yield conn.cursor()
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.InterfaceError) as e:
            print(f"[!] Connection error detected ({e}). Recreating connection.")
            if conn:
                conn.rollback()  # 롤백 시도 (실패할 수도 있음)
                conn.close()  # 깨진 연결은 확실히 종료
            conn = self._create_connection()  # 새 연결 생성
            raise  # 예외는 다시 발생시켜 상위 핸들러가 알 수 있게 함
        except sqlite3.Error as e:
            conn.rollback()
            print(f"[!!] Database error: {e}")
            raise
        finally:
            self._connection_pool.put(conn)

    @contextmanager
    def _read_connection(self):
        conn = None
        try:
            conn = self._connection_pool.get(block=True, timeout=5)
            conn.execute('SELECT 1')
            yield conn.cursor()
        except (sqlite3.OperationalError, sqlite3.InterfaceError) as e:
            print(f"[!] Connection error detected ({e}). Recreating connection.")
            if conn:
                conn.close()  # 깨진 연결은 확실히 종료
            conn = self._create_connection()  # 새 연결 생성
            raise  # 예외는 다시 발생시켜 상위 핸들러가 알 수 있게 함
        except sqlite3.Error as e:
            print(f"[!!] Database error: {e}")
            raise
        finally:
            self._connection_pool.put(conn)

    @contextmanager
    def transaction(self):
        """여러 SQL 구문을 하나의 트랜잭션으로 묶는 컨텍스트 매니저"""
        conn = None
        try:
            conn = self._connection_pool.get(block=True, timeout=5)
            conn.execute('SELECT 1')
            cursor = conn.cursor()
            # 커서를 먼저 반환하고, with 블록의 모든 코드가 실행되도록 함
            yield cursor
            conn.commit()
        except (sqlite3.OperationalError, sqlite3.InterfaceError) as e:
            print(f"[!] Connection error detected ({e}). Recreating connection.")
            if conn:
                conn.rollback()  # 롤백 시도 (실패할 수도 있음)
                conn.close()  # 깨진 연결은 확실히 종료
            conn = self._create_connection()  # 새 연결 생성
            raise  # 예외는 다시 발생시켜 상위 핸들러가 알 수 있게 함
        except sqlite3.Error as e:
            conn.rollback()
            print(f"[!!] Database error: {e}")
            raise
        finally:
            self._connection_pool.put(conn)

    def close_all_connections(self):
        """어플리케이션 종료 시 커넥션 풀의 모든 연결을 닫습니다."""
        print("[*] Closing all database connections...")
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
            except Exception as e:
                print(f"[!!] Error closing connection: {e}")
                raise
        print("[*] All connections closed.")

    # --- 데이터베이스 초기화 ---
    def initialize_databases(self):
        """모든 테이블을 생성하여 데이터베이스를 초기화합니다."""
        with self. _managed_connection() as cursor:
            # User DB 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    uid INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    nickname TEXT,
                    image TEXT default '0',
                    oneline TEXT default '안녕하세요.'
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Friends(
                    uid1 INTEGER,
                    uid2 INTEGER,
                    PRIMARY KEY (uid1, uid2),
                    FOREIGN KEY (uid1) REFERENCES Users(uid) ON DELETE CASCADE,
                    FOREIGN KEY (uid2) REFERENCES Users(uid) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Requests(
                    requester INTEGER,
                    requestie INTEGER,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    PRIMARY KEY (requester, requestie),
                    FOREIGN KEY (requester) REFERENCES Users(uid) ON DELETE CASCADE,
                    FOREIGN KEY (requestie) REFERENCES Users(uid) ON DELETE CASCADE,
                    CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'BLOCKED'))
                ) 
            ''')
            # Wordbook DB 테이블 생성 (외래 키 제약조건 순서 준수)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Wordbooks (
                    wid INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL DEFAULT 'TMP',
                    hash TEXT NOT NULL,
                    owner_uid INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_uid) REFERENCES users(uid) ON DELETE SET NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Tags (
                    tid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Wordbook_Tags (
                    wid INTEGER,
                    tid INTEGER,
                    PRIMARY KEY (wid, tid),
                    FOREIGN KEY (wid) REFERENCES Wordbooks(wid) ON DELETE CASCADE,
                    FOREIGN KEY (tid) REFERENCES Tags(tid) ON DELETE CASCADE
                )
            ''')
            # tid에 대한 index 생성
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wordbook_tags_tid ON Wordbook_Tags(tid)
            ''')
            # Master Word 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Master_Words(
                    master_word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT NOT NULL,
                    meanings TEXT NOT NULL,
                    distractors TEXT,
                    example_sentence TEXT,
                    UNIQUE(term, meanings, example_sentence)
                )
            ''')
            # Word와 Wordbook의 관계 테이블 생성 (Many-to-Many)
            cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Wordbook_Words(
                        wordbook_id INTEGER,
                        master_word_id INTEGER,
                        PRIMARY KEY (wordbook_id, master_word_id),
                        FOREIGN KEY (wordbook_id) REFERENCES Wordbooks(wid) ON DELETE CASCADE,
                        FOREIGN KEY (master_word_id) REFERENCES Master_Words(master_word_id) ON DELETE CASCADE
                    )
            ''')
            # User와 Wordbook의 관계 테이블 생성 (Many-to-Many)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Wordbook_Subscriber(
                    wordbook_id INTEGER,
                    subscriber INTEGER,
                    PRIMARY KEY (wordbook_id, subscriber),
                    FOREIGN KEY (wordbook_id) REFERENCES Wordbooks(wid) ON DELETE CASCADE,
                    FOREIGN KEY (subscriber) REFERENCES Users(uid) ON DELETE CASCADE 
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_Wordbook_Subscriber_subscriber 
                ON Wordbook_Subscriber (subscriber)
            ''')
            # --- [수정] 챗봇/학습 관련 테이블 스키마 통합 ---
            # 챗봇 프로젝트의 sessions 스키마 (더 상세함) 사용
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS Sessions (
                                session_id TEXT PRIMARY KEY,
                                owner_uid INTEGER NOT NULL,
                                session_name TEXT,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                last_message_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                is_active BOOLEAN DEFAULT 1, -- SQLite는 TRUE/FALSE를 1/0으로 저장
                                FOREIGN KEY (owner_uid) REFERENCES Users (uid) ON DELETE CASCADE
                            )
                        ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_Sessions_Uid
                ON Sessions(owner_uid)
            ''')
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS chat_logs (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                owner_uid INTEGER NOT NULL,
                                session_id TEXT NOT NULL,
                                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                                message TEXT NOT NULL,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (owner_uid) REFERENCES Users (uid) ON DELETE CASCADE,
                                FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
                            )
                        ''')
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS user_vocabulary_stats (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                owner_uid INTEGER NOT NULL,
                                master_word_id INTEGER NOT NULL,
                                correct_count INTEGER DEFAULT 0,
                                incorrect_count INTEGER DEFAULT 0,
                                is_liked BOOLEAN DEFAULT 0,            -- [New] 좋아요(북마크)
                                is_marked_for_review BOOLEAN DEFAULT 0, -- [New] 복습 체크
                                date_studied TEXT DEFAULT (date('now', '+9 hours')),
                                last_reviewed TEXT DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (owner_uid) REFERENCES Users (uid) ON DELETE CASCADE,
                                FOREIGN KEY (master_word_id) REFERENCES Master_Words(master_word_id),
                                UNIQUE (owner_uid, master_word_id)
                            )
                        ''')
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS user_preferences (
                                owner_uid INTEGER PRIMARY KEY,
                                learning_language TEXT DEFAULT 'English',
                                response_language TEXT DEFAULT 'Korean',
                                study_mode TEXT DEFAULT 'vocabulary',
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (owner_uid) REFERENCES Users (uid) ON DELETE CASCADE
                            )
                        ''')
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS mistakes (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                owner_uid INTEGER NOT NULL,
                                session_id TEXT,  -- session_id는 nullable로 설정
                                master_word_id INTEGER,
                                question TEXT NOT NULL,
                                user_answer TEXT NOT NULL,
                                correct_answer TEXT NOT NULL,
                                mistake_type TEXT,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                reviewed BOOLEAN DEFAULT 0,
                                mistake_date TEXT DEFAULT (date('now', '+9 hours')),
                                FOREIGN KEY (owner_uid) REFERENCES Users (uid) ON DELETE CASCADE,
                                FOREIGN KEY (master_word_id) REFERENCES Master_Words(master_word_id)
                            )
                        ''')
        print("[*] 모든 데이터베이스 테이블이 성공적으로 초기화되었습니다.")

    # --- User 관련 메소드 ---
    def add_user(self, email, nickname, image, oneline, cursor=None):
        sql = 'INSERT INTO Users (email, nickname, image, oneline) VALUES (?, ?, ?, ?)'
        if cursor:
            cursor.execute(sql, (email, nickname, image, oneline))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (email, nickname, image, oneline))
        return cursor.lastrowid

    def get_user_by_uid(self, uid, cursor=None):
        sql = 'SELECT * FROM Users WHERE uid = ?'
        if cursor:
            cursor.execute(sql, (uid,))
            return cursor.fetchone()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (uid,))
                return cursor.fetchone()

    def get_user_by_email(self, email, cursor=None):
        sql = 'SELECT * FROM Users WHERE email = ?'
        if cursor:
            cursor.execute(sql, (email,))
            return cursor.fetchone()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (email,))
                return cursor.fetchone()

    def update_nickname(self, uid, nickname, cursor=None):
        sql = 'UPDATE Users SET nickname = ? WHERE uid = ?'
        if cursor:
            cursor.execute(sql, (nickname, uid, ))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (nickname, uid, ))

    def update_image(self, uid, image, cursor=None):
        sql = 'UPDATE Users SET image = ? WHERE uid = ?'
        if cursor:
            cursor.execute(sql, (image, uid, ))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (image, uid, ))

    def update_oneline(self, uid, oneline, cursor=None):
        sql = 'UPDATE Users SET oneline = ? WHERE uid = ?'
        if cursor:
            cursor.execute(sql, (oneline, uid, ))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (oneline, uid, ))

    def delete_user(self, uid, cursor=None):
        sql = 'DELETE FROM Users WHERE uid = ?'
        if cursor:
            cursor.execute(sql, (uid,))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (uid, ))

    # --- Friends 관련 메소드 ---
    def add_friend(self, uid1, uid2, cursor=None):
        sql = 'INSERT INTO Friends (uid1, uid2) VALUES (?, ?)'
        if cursor:
            cursor.execute(sql, (uid1, uid2))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (uid1, uid2))
        return cursor.lastrowid

    def get_friend_by_uid(self, uid, cursor=None):
        sql = 'SELECT * FROM Friends WHERE uid1 = ?'
        if cursor:
            cursor.execute(sql, (uid, ))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (uid,))
                return cursor.fetchall()

    def get_friend(self, uid1, uid2, cursor=None):
        sql = 'SELECT * FROM Friends WHERE uid1 =? AND uid2 = ?'
        if cursor:
            cursor.execute(sql, (uid1, uid2))
            return cursor.fetchone()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (uid1, uid2))
                return cursor.fetchone()

    def delete_friend(self, uid1, uid2, cursor=None):
        sql = '''DELETE FROM Friends WHERE (uid1 = ? AND uid2 = ?) OR (uid1 = ? AND uid2 = ?)'''
        if cursor:
            cursor.execute(sql, (uid1, uid2, uid2, uid1))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (uid1, uid2, uid2, uid1))

    # --- Requests 관련 메소드 ---
    def add_request(self, requester, requestie, status='PENDING', cursor=None):
        sql = 'INSERT INTO Requests (requester, requestie, status) VALUES (?, ?, ?)'
        if cursor:
            cursor.execute(sql, (requester, requestie, status))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (requester, requestie, status))
        return cursor.lastrowid

    def get_request(self, requester, requestie, cursor=None):
        """특정 친구 요청 레코드를 상태에 관계없이 조회합니다."""
        sql = 'SELECT * FROM Requests WHERE requester = ? AND requestie = ?'
        if cursor:
            cursor.execute(sql, (requester, requestie, ))
            return cursor.fetchone()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (requester, requestie, ))
                return cursor.fetchone()

    def delete_request(self, requester, requestie, cursor=None):
        sql = '''DELETE FROM Requests WHERE (requester = ? AND requestie = ?)'''
        if cursor:
            cursor.execute(sql, (requester, requestie, ))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (requester, requestie, ))

    def update_request_status(self, requester, requestie, status, cursor=None):
        """특정 친구 요청의 상태를 업데이트합니다. (ACCEPT 시 사용)"""
        sql = 'UPDATE Requests SET status = ? WHERE requester = ? AND requestie = ?'
        if cursor:
            cursor.execute(sql, (status, requester, requestie))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (status, requester, requestie))

    def get_sent_requests_by_uid(self, requester_uid, cursor=None):
        """특정 유저가 보낸 모든 PENDING 친구 요청 목록을 반환합니다."""
        sql = "SELECT * FROM Requests WHERE requester = ? AND status = 'PENDING'"
        if cursor:
            cursor.execute(sql, (requester_uid,))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (requester_uid,))
                return cursor.fetchall()

    def get_received_requests_by_uid(self, requestie_uid, cursor=None):
        """특정 유저가 받은 모든 PENDING 친구 요청 목록을 반환합니다."""
        sql = "SELECT * FROM Requests WHERE requestie = ? AND status = 'PENDING'"
        if cursor:
            cursor.execute(sql, (requestie_uid,))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (requestie_uid,))
                return cursor.fetchall()

    # --- Wordbook 관련 메소드 ---
    def add_wordbook(self, name, owner_uid, hash_value, cursor=None):
        sql = 'INSERT INTO Wordbooks (title, owner_uid, hash) VALUES (?, ?, ?)'
        if cursor:
            cursor.execute(sql, (name, owner_uid, hash_value))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (name, owner_uid, hash_value))
        return cursor.lastrowid

    def get_wordbook_by_id(self, wid, cursor=None):
        sql = 'SELECT * FROM Wordbooks WHERE wid = ?'
        if cursor:
            cursor.execute(sql, (wid,))
            return cursor.fetchone()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (wid,))
                return cursor.fetchone()

    def get_wordbook_by_title(self, title, cursor=None):
        sql = 'SELECT * FROM Wordbooks WHERE title = ?'
        if cursor:
            cursor.execute(sql, (title,))
            return cursor.fetchall()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (title,))
                return cursor.fetchall()

    def delete_wordbook(self, wid, cursor=None):
        sql = 'DELETE FROM Wordbooks WHERE wid = ?'
        if cursor:
            cursor.execute(sql, (wid,))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (wid,))

    def update_wordbook(self, wid, hash_value, cursor=None):
        sql = 'UPDATE Wordbooks SET hash = ? WHERE wid = ?'
        if cursor:
            cursor.execute(sql, (hash_value, wid))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (hash_value, wid))
        return cursor.lastrowid

    def search_wordbooks_by_tags_and(self, tids, cursor=None):
        """
        제공된 모든 tid를 포함하는(AND 조건) 단어장(wid) 목록을 반환합니다.
        """
        # tids 리스트 길이에 맞춰 IN 절의 플레이스홀더 생성
        placeholders = ','.join(['?'] * len(tids))

        sql = f'''
                -- 1. 구독자 수 계산 부분을 "SubscriberCounts"라는 임시 테이블로 정의
                WITH SubscriberCounts AS (
                SELECT 
                    wordbook_id, 
                    COUNT(subscriber) AS subscription_count
                FROM Wordbook_Subscriber
                GROUP BY wordbook_id
                )
                -- 2. 메인 쿼리에서 이 임시 테이블을 사용
                SELECT
                    T.wid,
                    COALESCE(S.subscription_count, 0) AS subscription_count
                FROM Wordbook_Tags AS T
                LEFT JOIN SubscriberCounts AS S ON T.wid = S.wordbook_id
                WHERE T.tid IN ({placeholders})
                GROUP BY T.wid, S.subscription_count
                HAVING COUNT(DISTINCT T.tid) = ?
                ORDER BY subscription_count DESC
                LIMIT 10
                '''

        # 파라미터 리스트 생성: [tid1, tid2, ..., tidN, list_length]
        params = tids + [len(tids)]

        if cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def search_wordbooks_by_tags_or(self, tids, cursor=None):
        """
        제공된 tid 중 하나라도 포함하는(OR 조건) 단어장(wid) 목록을 반환합니다.
        """
        # tids가 비어있으면 빈 리스트 반환
        if not tids:
            return []

        placeholders = ','.join(['?'] * len(tids))

        sql = f'''
                -- 1. 구독자 수 계산 (AND 쿼리와 동일)
                WITH SubscriberCounts AS (
                SELECT 
                    wordbook_id, 
                    COUNT(subscriber) AS subscription_count
                FROM Wordbook_Subscriber
                GROUP BY wordbook_id
                )
                -- 2. 메인 쿼리
                SELECT
                    T.wid,
                    COALESCE(S.subscription_count, 0) AS subscription_count
                FROM Wordbook_Tags AS T
                LEFT JOIN SubscriberCounts AS S ON T.wid = S.wordbook_id
                WHERE T.tid IN ({placeholders}) -- OR 조건: IN 절 사용
                GROUP BY T.wid, S.subscription_count -- 중복 제거 및 집계
                -- HAVING 절이 없음 (AND 조건과 가장 큰 차이)
                ORDER BY subscription_count DESC
                LIMIT 10
                '''

        # OR 조건에서는 파라미터로 tids 리스트만 전달
        params = tids

        if cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    # --- Tag 관련 메소드 ---
    def add_tag(self, tag_name, cursor=None):
        sql = 'INSERT INTO Tags (name) VALUES (?)'
        if cursor:
            cursor.execute(sql, (tag_name,))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (tag_name,))
        return cursor.lastrowid

    def get_tag_by_name(self, tag_name, cursor=None):
        sql = 'SELECT * FROM Tags WHERE name = ?'
        if cursor:
            cursor.execute(sql, (tag_name,))
            return cursor.fetchone()  # 일반적으로 태그 이름은 고유하므로 fetchone이 더 적합
        with self. _read_connection() as cursor:
            cursor.execute(sql, (tag_name,))
            return cursor.fetchone()

    def get_tag_by_tid(self, tid, cursor=None):
        sql = 'SELECT * FROM Tags WHERE tid = ?'
        if cursor:
            cursor.execute(sql, (tid,))
            return cursor.fetchone()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (tid,))
                return cursor.fetchone()

    def delete_tag(self, tid, cursor=None):
        sql = 'DELETE FROM Tags WHERE tid = ?'
        if cursor:
            cursor.execute(sql, (tid, ))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (tid, ))

    def search_tags_by_prefix(self, prefix, cursor=None):
        """
        주어진 prefix(접두사)로 시작하는 태그를 검색하고,
        각 태그가 참조된 횟수(단어장 수)와 함께 내림차순으로 반환합니다.
        """
        # T.name LIKE ? 파라미터에 'query%' 형태를 전달합니다.
        sql = '''
            SELECT
                T.tid,
                T.name,
                COUNT(WT.wid) AS reference_count
            FROM Tags T
            LEFT JOIN Wordbook_Tags WT ON T.tid = WT.tid
            WHERE T.name LIKE ?
            GROUP BY T.tid, T.name
            ORDER BY reference_count DESC, T.name ASC
            LIMIT 10
        '''
        # 검색어를 'query%' 형태로 만듭니다.
        search_term = f"{prefix}%"

        if cursor:
            cursor.execute(sql, (search_term,))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (search_term,))
                return cursor.fetchall()

    # --- Wordbook <-> Tag 연결 메소드 ---
    def link_tag_to_wordbook(self, wid, tid, cursor=None):
        sql = 'INSERT INTO Wordbook_Tags (wid, tid) VALUES (?, ?)'
        if cursor:
            cursor.execute(sql, (wid, tid))
        else:
            with self. _managed_connection() as cursor:
                cursor.execute(sql, (wid, tid))

    def get_tags_for_wordbook(self, wid, cursor=None):
        sql = '''
            SELECT t.tid, t.name FROM Tags t
            JOIN Wordbook_Tags wt ON t.tid = wt.tid
            WHERE wt.wid = ?
        '''
        if cursor:
            cursor.execute(sql, (wid,))
            return cursor.fetchall()
        else:
            with self. _read_connection() as cursor:
                cursor.execute(sql, (wid,))
                return cursor.fetchall()

    def delete_tag_for_wordbook(self, wid, tid, cursor=None):
        sql = '''DELETE FROM Wordbook_Tags WHERE wid = ? AND tid = ?'''
        if cursor:
            cursor.execute(sql, (wid, tid,))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (wid, tid, ))

    def delete_all_tags_for_wordbook(self, wid, cursor=None):
        sql = '''DELETE FROM Wordbook_Tags WHERE wid = ?'''
        if cursor:
            cursor.execute(sql, (wid,))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (wid, ))

    # --- Wordbook <-> Subscriber 연결 메소드 ---
    def link_subscriber_to_wordbook(self, wid, subscriber, cursor=None):
        sql = '''INSERT INTO Wordbook_Subscriber (wordbook_id, subscriber) VALUES (?, ?)'''
        if cursor:
            cursor.execute(sql, (wid, subscriber,))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (wid, subscriber))

    def get_subscriber_for_wordbook(self, wid, cursor=None):
        sql = '''SELECT * FROM Wordbook_Subscriber WHERE wordbook_id = ?'''
        if cursor:
            cursor.execute(sql, (wid, ))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (wid, ))
                return cursor.fetchall()

    def get_wordbook_for_subscriber(self, subscriber, cursor=None):
        sql = '''SELECT wordbook_id FROM Wordbook_Subscriber WHERE subscriber = ? ORDER BY wordbook_id ASC'''
        if cursor:
            cursor.execute(sql, (subscriber, ))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (subscriber, ))
                return cursor.fetchall()

    def delete_subscriber_to_wordbook(self, wid, subscriber, cursor=None):
        sql = '''DELETE FROM Wordbook_Subscriber WHERE wordbook_id = ? AND subscriber = ?'''
        if cursor:
            cursor.execute(sql, (wid, subscriber,))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (wid, subscriber))

    # --- Word 관련 메소드 ---
    def get_word_by_id(self, master_word_id, cursor=None):
        sql = '''SELECT * FROM Master_Words WHERE master_word_id = ?'''
        if cursor:
            cursor.execute(sql, (master_word_id,))
            return cursor.fetchone()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (master_word_id,))
                return cursor.fetchone()

    def get_random_word_for_user(self, uid, cursor=None):
        """
        특정 사용자가 접근 가능한 모든 단어장에서
        무작위 단어 1개를 DB에서 직접 선택하여 효율적으로 가져옵니다.
        """
        sql = '''
            SELECT mw.*
            FROM Master_Words mw
            JOIN Wordbook_Words ww ON mw.master_word_id = ww.master_word_id
            JOIN Wordbook_Subscriber ws ON ww.wordbook_id = ws.wordbook_id
            WHERE ws.subscriber = ?
            ORDER BY RANDOM()
            LIMIT 2
        '''

        if cursor:
            cursor.execute(sql, (uid, ))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (uid, ))
                return cursor.fetchall()

    # --- User <> Word Status 연결 메소드 ---
    def link_word_user_status(self, master_word_id, uid, status, cursor=None):
        """
        특정 단어의 상태(liked, review, wrong)를 user_vocabulary_stats 테이블에 업데이트(UPSERT)합니다.
        """
        if status == 'liked':
            # 좋아요 켜기 (기존 데이터 유지, is_liked만 1로)
            sql = '''
                INSERT INTO user_vocabulary_stats (owner_uid, master_word_id, is_liked)
                VALUES (?, ?, 1)
                ON CONFLICT(owner_uid, master_word_id) 
                DO UPDATE SET is_liked = 1, last_reviewed = CURRENT_TIMESTAMP
            '''
        elif status == 'review':
            # 복습 체크 켜기
            sql = '''
                INSERT INTO user_vocabulary_stats (owner_uid, master_word_id, is_marked_for_review)
                VALUES (?, ?, 1)
                ON CONFLICT(owner_uid, master_word_id) 
                DO UPDATE SET is_marked_for_review = 1, last_reviewed = CURRENT_TIMESTAMP
            '''
        elif status == 'wrong':
            # 오답: 없으면 1, 있으면 +1 (학습 강화)
            sql = '''
                INSERT INTO user_vocabulary_stats (owner_uid, master_word_id, incorrect_count)
                VALUES (?, ?, 1)
                ON CONFLICT(owner_uid, master_word_id) 
                DO UPDATE SET incorrect_count = incorrect_count + 1, 
                              last_reviewed = CURRENT_TIMESTAMP, 
                              date_studied = date('now', '+9 hours')
            '''
        elif status == 'correct':
            # 오답: 없으면 1, 있으면 +1 (학습 강화)
            sql = '''
                INSERT INTO user_vocabulary_stats (owner_uid, master_word_id, correct_count)
                VALUES (?, ?, 1)
                ON CONFLICT(owner_uid, master_word_id) 
                DO UPDATE SET correct_count = correct_count + 1, 
                              last_reviewed = CURRENT_TIMESTAMP, 
                              date_studied = date('now', '+9 hours')
            '''
        else:
            raise ValueError(f"Invalid status: {status}")

        if cursor:
            cursor.execute(sql, (uid, master_word_id))
            return cursor.lastrowid
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (uid, master_word_id))
                return cursor.lastrowid

    def unlink_word_user_status(self, master_word_id, uid, status, cursor=None):
        """
        특정 단어의 상태를 해제합니다. 데이터 삭제가 아닌 플래그 변경(UPDATE)입니다.
        """
        if status == 'liked':
            sql = "UPDATE user_vocabulary_stats SET is_liked = 0 WHERE owner_uid = ? AND master_word_id = ?"
        elif status == 'review':
            sql = "UPDATE user_vocabulary_stats SET is_marked_for_review = 0 WHERE owner_uid = ? AND master_word_id = ?"
        elif status == 'wrong':
            # 오답 상태 해제 -> 오답 횟수를 0으로 초기화 (또는 -1 할 수도 있으나 명확한 해제를 위해 0)
            sql = "UPDATE user_vocabulary_stats SET incorrect_count = 0 WHERE owner_uid = ? AND master_word_id = ?"
        else:
            raise ValueError(f"Invalid status: {status}")

        if cursor:
            cursor.execute(sql, (uid, master_word_id))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (uid, master_word_id))

    def get_word_user_status(self, uid, status, cursor=None):
        """
        특정 상태(liked, review, wrong)를 가진 단어들의 master_word_id를 반환합니다.
        """
        if status == 'liked':
            sql = "SELECT master_word_id FROM user_vocabulary_stats WHERE owner_uid = ? AND is_liked = 1"
        elif status == 'review':
            sql = "SELECT master_word_id FROM user_vocabulary_stats WHERE owner_uid = ? AND is_marked_for_review = 1"
        elif status == 'wrong':
            # 오답 횟수가 1 이상인 경우를 'wrong' 상태로 간주
            sql = "SELECT master_word_id FROM user_vocabulary_stats WHERE owner_uid = ? AND incorrect_count > 0"
        else:
            return []

        if cursor:
            cursor.execute(sql, (uid,))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (uid,))
                return cursor.fetchall()

    # --- Wordbook <-> Word 연결 메소드 ---
    def add_word_to_wordbook(self, wordbook_id, term, meanings, distractors, example_sentence, cursor=None):
        """
        단어를 마스터 테이블에 추가/조회하고, 이를 특정 단어장과 연결합니다.
        외부에서 cursor를 전달받으면 해당 트랜잭션에 참여하고, 그렇지 않으면 새로운 트랜잭션을 생성합니다.
        """
        # cursor가 제공되면 해당 cursor를 사용하고, 아니면 새로운 트랜잭션을 시작
        if cursor:
            return _add_word_logic(wordbook_id, term, meanings, distractors, example_sentence, cursor)
        else:
            with self.transaction() as new_cursor:
                return _add_word_logic(wordbook_id, term, meanings, distractors, example_sentence, new_cursor)

    def get_words_by_wordbook(self, wordbook_id, cursor=None):
        """특정 단어장에 속한 모든 단어의 '정보'를 조회합니다."""
        # JOIN을 사용하여 연결 테이블을 거쳐 마스터 단어 정보에 접근합니다.
        sql = '''
              SELECT mw.* FROM Master_Words mw
              JOIN Wordbook_Words ww ON mw.master_word_id = ww.master_word_id
              WHERE ww.wordbook_id = ?
          '''
        if cursor:
            cursor.execute(sql, (wordbook_id,))
            return cursor.fetchall()
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (wordbook_id,))
                return cursor.fetchall()

    def remove_word_from_wordbook(self, wordbook_id, master_word_id, cursor=None):
        """단어장에서 특정 단어의 '연결'을 삭제합니다. (마스터 단어는 삭제되지 않음)"""
        sql = 'DELETE FROM Wordbook_Words WHERE wordbook_id = ? AND master_word_id = ?'
        if cursor:
            cursor.execute(sql, (wordbook_id, master_word_id))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (wordbook_id, master_word_id))

    # ----------------------------------------------------
    # A. 챗봇 세션 및 대화 기록 관리 메소드 (New DAO)
    # ----------------------------------------------------

    def create_session(self, owner_uid: int, session_name: str, cursor=None) -> str:
        """사용자 ID로 새로운 대화 세션을 생성하고 고유 session_id를 반환합니다."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        sql = '''
                INSERT INTO Sessions (session_id, owner_uid, session_name)
                VALUES (?, ?, ?)
            '''
        if cursor:
            cursor.execute(sql, (session_id, owner_uid, session_name))
        else:
            with self._managed_connection() as cursor:
                cursor.execute(sql, (session_id, owner_uid, session_name))
        return session_id

    def get_session_with_user(self, owner_uid: int, session_id: str, cursor=None) -> str:
        sql = '''
            SELECT * FROM Sessions WHERE owner_uid = ? AND session_id = ?
        '''
        if cursor:
            cursor.execute(sql, (owner_uid, session_id))
        else:
            with self._read_connection() as cursor:
                cursor.execute(sql, (owner_uid, session_id))
        return cursor.fetchall()

    def save_chat_content(self, owner_uid: int, session_id: str, role: str, message: str):
        """특정 세션에 사용자 또는 챗봇의 대화 내용을 저장하고 세션 시간을 업데이트합니다."""
        with self._managed_connection() as cursor:
            # chat_logs 테이블에 대화 내용 기록
            cursor.execute('''
                INSERT INTO chat_logs (owner_uid, session_id, role, message)
                VALUES (?, ?, ?, ?)
            ''', (owner_uid, session_id, role, message))

            # 세션의 마지막 메시지 시간 업데이트
            cursor.execute('''
                UPDATE Sessions
                SET last_message_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (session_id,))

    def get_session_history(self, session_id: str, limit: int = 20) -> list:
        """특정 세션의 최근 대화 기록(메시지, 역할)을 조회합니다."""
        with self._read_connection() as cursor:
            # 최신 20개를 역순으로 가져와서 시간 순서대로 정렬
            cursor.execute('''
                SELECT role, message, created_at FROM chat_logs
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (session_id, limit))
            return [dict(row) for row in reversed(cursor.fetchall())]

    def get_user_stats(self, owner_uid: int, limit: int = 30) -> list:
        """
        [Missing Method] 챗봇 RAG를 위해 사용자의 단어 학습 통계를 조회합니다.
        repository.py의 기능을 user_vocabulary_stats와 Master_Words 테이블에 맞춰 이식했습니다.
        """
        with self._read_connection() as cursor:
            # 테이블 조인: user_vocabulary_stats (통계) + Master_Words (단어 정보)
            # term -> word, meanings -> meaning으로 별칭(Alias)을 주어 챗봇 로직과 호환되게 함
            cursor.execute('''
                SELECT 
                    uvs.master_word_id as word_id, 
                    mw.term as word, 
                    mw.meanings as meaning, 
                    uvs.correct_count, 
                    uvs.incorrect_count, 
                    uvs.last_reviewed
                FROM user_vocabulary_stats uvs
                JOIN Master_Words mw ON uvs.master_word_id = mw.master_word_id
                WHERE uvs.owner_uid = ? AND NOT uvs.incorrect_count = 0 
                ORDER BY uvs.last_reviewed DESC 
                LIMIT ?
            ''', (owner_uid, limit))

            # UserWordStats 객체 대신 딕셔너리 리스트 반환
            return [dict(row) for row in cursor.fetchall()]
    # ----------------------------------------------------
    # B. 학습 통계 및 오답 기록 관리 메소드 (New DAO)
    # ----------------------------------------------------

    def record_mistake(self, owner_uid: int, session_id: str, master_word_id: int, question: str, user_answer: str,
                       correct_answer: str, mistake_type: str = 'quiz'):
        """사용자의 오답 기록을 mistakes 테이블에 저장하고, user_vocabulary_stats 테이블을 업데이트합니다."""
        with self._managed_connection() as cursor:
            # 1. mistakes 테이블에 상세 로그 기록
            cursor.execute('''
                INSERT INTO mistakes (owner_uid, session_id, master_word_id, 
                                      question, user_answer, correct_answer, mistake_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (owner_uid, session_id, master_word_id, question, user_answer, correct_answer, mistake_type))

            # 2. user_vocabulary_stats (통계) 업데이트: 오답 횟수 증가
            cursor.execute('''
                INSERT INTO user_vocabulary_stats (owner_uid, master_word_id, incorrect_count)
                VALUES (?, ?, 1)
                ON CONFLICT(owner_uid, master_word_id) DO UPDATE SET
                    incorrect_count = incorrect_count + 1,
                    last_reviewed = CURRENT_TIMESTAMP,
                    date_studied = date('now', '+9 hours')
            ''', (owner_uid, master_word_id))

    def get_frequently_wrong_words(self, owner_uid: int, limit: int = 15) -> list:
        """가장 오답 횟수가 많은 단어를 조회합니다 (RAG 프롬프트용)."""
        with self._read_connection() as cursor:
            cursor.execute('''
                SELECT 
                    mw.term as word, 
                    mw.meanings, 
                    vs.correct_count, 
                    vs.incorrect_count
                FROM user_vocabulary_stats vs
                JOIN Master_Words mw ON vs.master_word_id = mw.master_word_id
                WHERE vs.owner_uid = ?
                AND vs.incorrect_count > 0
                ORDER BY vs.incorrect_count DESC 
                LIMIT ?
            ''', (owner_uid, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_mistakes(self, owner_uid: int, limit: int = 5) -> list:
        """복습이 필요한 최근 오답 기록을 조회합니다."""
        with self._read_connection() as cursor:
            cursor.execute('''
                SELECT m.id, m.owner_uid, m.session_id, m.question, 
                       m.user_answer, m.correct_answer, m.mistake_type, m.created_at,
                       mw.term as word_tested
                FROM mistakes m
                LEFT JOIN Master_Words mw ON m.master_word_id = mw.master_word_id
                WHERE m.owner_uid = ? AND m.reviewed = 0
                ORDER BY m.created_at DESC LIMIT ?
            ''', (owner_uid, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_user_preferences(self, owner_uid: int) -> dict:
        """사용자 환경 설정(학습 언어, 응답 언어 등)을 조회합니다."""
        with self._read_connection() as cursor:
            cursor.execute('''
                SELECT * FROM user_preferences
                WHERE owner_uid = ?
            ''', (owner_uid,))
            row = cursor.fetchone()
            # Row 객체를 딕셔너리로 반환 (데이터가 없으면 빈 딕셔너리)
            return dict(row) if row else {}

    def get_todays_mistakes_for_examples(self, owner_uid: int) -> list:
        """
        [예문 생성용] 오늘 발생한 오답 중, 아직 복습하지 않은 단어들을 조회합니다.
        """
        with self._read_connection() as cursor:
            # mistakes 테이블과 Master_Words 테이블을 조인
            cursor.execute('''
                SELECT DISTINCT mw.master_word_id, mw.term as word, mw.meanings
                FROM mistakes m
                JOIN Master_Words mw ON m.master_word_id = mw.master_word_id
                WHERE m.owner_uid = ?
                  AND m.mistake_date = date('now', '+9 hours')
                  AND m.reviewed = 0
            ''', (owner_uid,))
            # 딕셔너리 리스트로 변환하여 반환
            return [dict(row) for row in cursor.fetchall()]

    def get_todays_studied_words(self, owner_uid: int) -> list:
        """
        [오늘의 복습용] 오늘 학습했거나 퀴즈를 푼 단어 목록을 조회합니다.
        """
        with self._read_connection() as cursor:
            cursor.execute('''
                SELECT mw.term as word, mw.meanings, uvs.correct_count, uvs.incorrect_count
                FROM user_vocabulary_stats uvs
                JOIN Master_Words mw ON uvs.master_word_id = mw.master_word_id
                WHERE uvs.owner_uid = ?
                  AND uvs.date_studied = date('now', '+9 hours')
            ''', (owner_uid,))
            return [dict(row) for row in cursor.fetchall()]
    # ----------------------------------------------------
