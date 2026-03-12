# 텍스트 단어장을 JSON 구조(파이썬 리스트)로 변환하는 함수
def wordbook_to_json(ocr_text):
    if not ocr_text:
        return []

    structured_data = []
    lines = ocr_text.strip().split('\n')  # 텍스트를 라인별로 나눔

    for line in lines:
        cleaned_line = line.strip().rstrip('|')
        parts = cleaned_line.split('|')
        if len(parts) != 9:
            print(f"Skipping {parts[0]}")
            # 형식이 맞지 않는 줄은 스킵
            continue

        # 데이터 매핑
        word_data = {
            "word": parts[0],
            "meanings": parts[1:5],
            "distractors": parts[5:8],
            "example": parts[8]
        }
        structured_data.append(word_data)

    return structured_data


def json_to_wordbook(wordbook_json):
    lines = []
    for entry in wordbook_json:
        try:
            # 'meanings' 리스트를 '|'를 사용해 하나의 문자열로 합칩니다.
            meanings_str = "|".join(entry.get('meanings', []))
            distractors_str = "|".join(entry.get('distractors', []))
            # 단어, 뜻, 오답, 예문을 순서대로 합쳐 한 줄을 만듭니다.
            line = f"{entry.get('word', '')}|{meanings_str}|{distractors_str}|{entry.get('example', '')}|"
            lines.append(line)
        except TypeError:
            # entry가 딕셔너리가 아닌 경우 등 예외 처리
            print(f"Skipping invalid entry: {entry}")
            continue

    # 모든 라인을 개행 문자('\n')로 합쳐 최종 결과물을 반환합니다.
    return "\n".join(lines)


if __name__ == '__main__':
    text = """ 
apple|사과||||배|복숭아|포도|I ate an apple for lunch.|
book|책|예약|||책갈피|독서|장|She is reading a book.|
run|달리다|운영하다|출마하다|달리기|걷다|넘어지다|쉬다|He can run very fast.|
ball|공|무도회|||돌|막대기|장난감|He kicked the ball.|
dog|개|비열한 사람|||고양이|새|쥐|My dog loves to play fetch.|
sun|태양|햇살|||달|별|구름|The sun is shining brightly.|
pen|펜|우리|감금하다||연필|볼펜|붓|Give me a pen.|
hat|모자|역할|||모자걸이|모자 가게|모자끈|He wore a blue hat.|
cup|컵|우승컵|||잔|병|그릇|The cup is on the table.|
bag|가방|봉지|||주머니|배낭|지갑|He packed his bag.|
box|상자|권투하다|||상자 열기|상자 닫기|빈 상자|Put the shoes in the box.|
tree|나무|계통도|||숲|가지|잎|The tree is tall.|
fish|물고기|낚시하다|||새우|게|돌고래|She caught a fish.|
boy|소년|남자아이|||소녀|어른|아이|The boy is laughing.|
girl|소녀|여자아이|||소년|여성|아이|That girl is kind.|
bed|침대|화단|||소파|의자|책상|He is lying on the bed.|
eye|눈|눈동자|주시하다||귀|코|입|She closed her eye.|
face|얼굴|직면하다|||머리|몸|다리|Wash your face.|
hand|손|건네주다|도와주다||팔|손가락|손목|Raise your hand.|
foot|발|피트|||다리|발가락|발목|He hurt his foot.|
door|문|입구|||창문|벽|천장|Close the door.|
floor|바닥|층|||벽|천장|가구|The floor is clean.|
chair|의자|의장|||탁자|소파|침대|He sat on the chair.|
school|학교|학파|||교실|학생|선생님|We go to school every day.|
class|수업|반|계층||학생|수업 시간|방|Our class starts at 9.|
rice|쌀|밥|||밀|보리|빵|We eat rice.|
water|물|물에 넣다|||불|공기|땅|Water is essential for life.|
house|집|건물|||집 짓기|집 안|작은 집|They live in a big house.|
baby|아기|갓난아기처럼 행동하다|||어린이|성인|노인|The baby is crying.|
cake|케이크|간단한 일|||빵|과자|쿠키|She baked a chocolate cake.|
phone|전화기|전화하다|||핸드폰|휴대폰|집 전화|I lost my phone.|
mouse|쥐|마우스|||햄스터|고양이|강아지|The mouse ran away.|
monitor|모니터|감시하다|||화면|컴퓨터|텔레비전|Clean the monitor.|
notebook|공책|노트북|||메모장|일기장|필기구|Take your notebook.|
ruler|자|지배자|||연필|각도기|컴퍼스|Draw a line with a ruler.|
glue|풀|붙이다|||테이프|접착제|본드|Use glue.|
paint|물감|칠하다|||색깔|붓|그림|Paint the wall.|
color|색|색칠하다|||그림|색깔 바꾸기|다채로운|What is your favorite color?|
draw|그리다|끌다|||그림|스케치|채색|Draw a picture.|
picture|그림|사진|||이미지|작품|그림책|Look at the picture.|
game|게임|경기|||놀이|시합|스포츠|Let's play a game.|
play|놀다|연주하다|연극||경기|무대|공연|The children play in the yard.|
jump|점프하다|뛰다|||뛰기|도약|착지|Jump high!|
walk|걷다|산책|도보||뛰다|달리다|멈추다|We walk to school.|
wake|깨다|깨우다|||자다|일어나다|졸다|I wake up at 7.|
light|빛|가벼운|불|밝은||어둠|무거운|Turn on the light.|
bat|박쥐|야구방망이|때리다||공|야구|날다|He hit the ball with a bat.|
spring|봄|용수철|튀다|샘|겨울|여름|가을|Flowers bloom in spring.|
point|점|가리키다|의견|단계|선|각도|위치|That is a good point.|
match|경기|성냥|어울리다|맞추다|틀린|어색한|안 맞는|It was a great match.|
check|확인하다|수표|검사|견제|실수|문제|오류|Check your answers.|
kind|친절한|종류|||상냥한|다정한|정중한|He is a kind person.|
rock|바위|흔들다|록음악||돌멩이|절벽|산|He threw a rock.|
ring|반지|울리다|경기장|고리|귀걸이|목걸이|팔찌|She wears a gold ring.|
bank|은행|둑|쌓다||돈|계좌|금융|I went to the bank.|
seal|물개|봉인하다|도장|확정짓다|바다표범|바다|섬|The seal clapped.|
bark|짖다|나무껍질|||개|고양이|소리|The dog will bark.|
nail|손톱|못|고정하다||망치|벽|나무|I broke my nail.|
file|파일|줄|제출하다|보관하다|서류|철|문서|Save the file.|
scale|비늘|저울|규모|비례하다|체중계|크기|측정|Check your weight on the scale.|
can|캔|할 수 있다|통조림|해고하다|병|상자|주스|I opened a can of juice.|
bear|곰|참다|낳다|가지다|동물|숲|사냥|We saw a bear.|
row|줄|노 젓기|소동|노를 젓다|열|행|강|Sit in a row.|
cook|요리하다|요리사|||음식|주방|식사|I will cook dinner tonight.|
clean|청소하다|깨끗한|||더러운|지저분한|오염된|Please clean your room.|
ride|타다|탈 것|||운전하다|걷다|뛰다|I ride a bike.|
write|쓰다|작성하다|||읽다|말하다|그리다|I will write a letter.|
read|읽다|해석하다|||쓰다|말하다|보이다|He likes to read books.|
open|열다|개방하다|||닫다|잠그다|막다|Open the window.|
close|닫다|가까운|||열다|열림|열쇠|Close the door.|
help|돕다|도움|||지원|지지|조력|Help your friend.|
look|보다|살펴보다|||듣다|만지다|맛보다|Look at this picture.|
listen|듣다|귀 기울이다|||보다|말하다|읽다|Listen to the teacher.|
talk|말하다|이야기하다|||듣다|소통하다|대화하다|Can I talk to you?|
answer|대답하다|답변|||질문하다|묻다|대화|Answer the question.|
question|질문|문제|||답변|묻다|대화|She asked a question.|
story|이야기|스토리|||전설|소설|동화|Tell me a story.|
sit|앉다|자리잡다|||서다|눕다|기다리다|Please sit down.|
stand|서다|참다|||앉다|눕다|움직이다|Stand still.|
move|움직이다|이사하다|||정지하다|머물다|멈추다|Move to the left.|
watch|손목시계|지켜보다|관찰하다|시계|카메라|TV|He bought a new watch.|
date|날짜|데이트하다|||시간|요일|월|What is today’s date?|
block|블록|막다|||건축|게임|장애물|Put the block on the table.|
drop|떨어지다|물방울|||흘리다|기름|액체|A drop of water fell.|
back|등|뒤쪽|돌아가다||앞|옆|정면|He hurt his back.|
fall|떨어지다|가을|||오르다|뜨다|멈추다|The leaves fall in autumn.|
present|선물|출석한|현재의||기념품|상자|증정품|I gave her a birthday present.|
bat|박쥐|방망이|||새|날개|어둠|The bat flew away.|
train|훈련하다|기차|||기차역|열차|싸우다|She trained her dog.|
    """
    parsed_data = wordbook_to_json(text)

    print(parsed_data)
