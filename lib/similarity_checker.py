import re
from difflib import SequenceMatcher

from metaphone import doublemetaphone
import nltk
from nltk.corpus import cmudict

# cmudict 자료를 다운로드.
nltk.download('cmudict')
d = cmudict.dict()


def pronunciation_similarity_double_metaphone(word1, word2, debug=0):
    """
    두 단어의 발음 유사도 계산.

    1. 각 단어에 대해 Double Metaphone 알고리즘을 적용해 두 개의 발음 코드를 추출.
    2. 두 단어의 가능한 발음 코드들 중 하나라도 일치하면 1.0을 리턴.
    3. 일치하는 코드가 없으면, sequence_matcher를 이용해 코드 조합에 대한 유사도(0.0 ~ 1.0)를 계산하여 가장 큰 값을 리턴.

    :param word1: primary word, answer
    :param word2: secondary word, prediction
    :param debug: prints code for debugging
    :return: similarity(0.0~1.0)
    """
    # 발음 코드 추출
    meta1 = doublemetaphone(word1)
    meta2 = doublemetaphone(word2)
    # 유효한 코드를 집합으로 저장(공백 제거)
    codes1 = set(code for code in meta1 if code)
    codes2 = set(code for code in meta2 if code)

    # debug(print codes)
    if debug == 1:
        print(codes1)
        print(codes2)

    if codes1.intersection(codes2):
        return 1.0

    best_similarity = 0.0
    for code1 in codes1:
        for code2 in codes2:
            sim = SequenceMatcher(None, code1, code2).ratio()
            best_similarity = max(best_similarity, sim)
    return best_similarity


def normalize_phoneme(phoneme):
    """
    CMU Pronouncing Dictionary phoneme's 숫자 제거
    :param phoneme: target
    :return: phoneme without num
    """
    return re.sub(r'\d', '', phoneme)


def insertion_cost(phoneme):
    """
    phoneme의 insertion cost 리턴.
    default : 1
    :param phoneme: target phoneme
    :return: 1(default)
    """
    return 1


def deletion_cost(phoneme):
    """
    phoneme의 deletion cost 리턴.
    default : 1
    :param phoneme: target phoneme
    :return: 1(default)
    """
    return 1


def substitution_cost(phoneme1, phoneme2):
    """
    phoneme1과 phoneme2의 substitution cost 리턴.
    default : 1
    :param phoneme1: target 1
    :param phoneme2: target 2
    :return: 1 (default) or 0.5 (similar phoneme)
    """
    # 동일한 경우 cost = 0
    if phoneme1 == phoneme2:
        return 0

    # 비교 전 normalize
    phoneme1 = normalize_phoneme(phoneme1)
    phoneme2 = normalize_phoneme(phoneme2)

    # 발음상 유사한 음소 그룹 정의
    similar_groups = [
        {"F", "V"},
        {"T", "D"},
        {"S", "Z"},
        {"K", "G"},
        {"P", "B"},
        {"CH", "JH"},
        {"SH", "ZH"},
        {"L", "R"},
        {"IY", "IH"},
        {"EY", "EH", "AE"},
        {"AA", "AO"},
        {"UW", "OW", "UH"},
        {"AY", "AW", "OY"},

    ]
    # 같은 그룹인 경우 cost = 0.5
    for group in similar_groups:
        if phoneme1 in group and phoneme2 in group:
            return 0.5
    return 1


def get_phonemes(word):
    """
    단어에 대한 phoneme 리스트(ARPAbet) 리턴
    단어가 사전에 없으면 None 리턴
    :param word: word to convert
    :return: converted phoneme (None if not exist)
    """
    word = word.lower()
    return d[word][0] if word in d else None


def levenshtein_distance(seq1, seq2):
    """
    두 시퀀스(phoneme 리스트) 간의 Levenshtein 거리 계산
    :param seq1: primary word's sequence
    :param seq2: secondary word's sequence
    :return: levenshtein_distance between sequences
    """
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost_del = dp[i-1][j] + deletion_cost(seq1[i-1])
            cost_ins = dp[i][j-1] + insertion_cost(seq2[j-1])
            cost_sub = dp[i-1][j-1] + substitution_cost(seq1[i-1], seq2[j-1])
            dp[i][j] = min(cost_del, cost_ins, cost_sub)
    return dp[m][n]


def pronunciation_similarity_CMU(word1, word2, debug=0):
    """
    두 단어의 발음 유사도를 0.0 ~ 1.0 사이의 값으로 계산
    값이 클수록 발음 유사
    :param word1: primary word, answer
    :param word2: secondary word, prediction
    :param debug: prints code for debugging
    :return: similarity(0.0~1.0)
    """
    phonemes1 = get_phonemes(word1)
    phonemes2 = get_phonemes(word2)
    if debug == 1:
        print(phonemes1)
        print(phonemes2)
    if phonemes1 is None or phonemes2 is None:
        return None  # 사전에 없는 단어 처리

    dist = levenshtein_distance(phonemes1, phonemes2)
    max_len = max(len(phonemes1), len(phonemes2))
    similarity = 1 - (dist / max_len)
    return similarity
