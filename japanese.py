from fugashi import Tagger

def is_japanese(char: str) -> bool:
    # Check if the character is Hiragana
    if '\u3040' <= char <= '\u309F':
        return True
    # Check if the character is Katakana
    if '\u30A0' <= char <= '\u30FF':
        return True
    # Check if the character is Kanji (CJK Unified Ideographs)
    if '\u4E00' <= char <= '\u9FFF':
        return True
    # Check if the character is Halfwidth Katakana
    if '\uFF65' <= char <= '\uFF9F':
        return True
    return False

tagger = Tagger('-Owakati')
def tagger_dump(text: str):
    def dump(c):
        return {k: getattr(c, k) for k in dir(c) if not k.startswith('_')}
    for word in tagger(text):
        print(word, dump(word), dump(word.feature)) # {k: getattr(word.feature, k) for k in dir(word.feature) if not k.startswith('_')})
    
# MeCab character types; see char.def
CHAR_ALPHA = 5
CHAR_HIRAGANA = 6
CHAR_KATAKANA = 7

def word_to_kana(word) -> str:
    # copied from https://github.com/polm/cutlet/blob/9574fada889a54f365e84f569c569e1f2205298c/cutlet/cutlet.py#L307

    # if word.surface in self.exceptions:
    #     return self.exceptions[word.surface]

    if word.surface.isdigit():
        return word.surface

    if word.surface.isascii():
        return word.surface

    # deal with unks first
    if word.is_unk:
        # at this point is is presumably an unk
        # Check character type using the values defined in char.def.
        # This is constant across unidic versions so far but not guaranteed.
        # if word.char_type in (CHAR_HIRAGANA, CHAR_KATAKANA):
        #     kana = jaconv.kata2hira(word.surface)
        #     return self.map_kana(kana)
        
        return word.surface

        # At this point this is an unknown word and not kana. Could be
        # unknown kanji, could be hangul, cyrillic, something else.
        # By default ensure ascii by replacing with ?, but allow pass-through.

    if word.feature.kana:
        return word.feature.kana
        # for known words
        kana = jaconv.kata2hira(word.feature.kana)
        return self.map_kana(kana)
    else:
        # unclear when we would actually get here
        return word.surface

def convert_to_kana(text: str) -> str:
    return ''.join(word_to_kana(word) for word in tagger(text))

kata_families = {'ア': 'アイウエオ', 'ヴ': 'ヴ', 'カ': 'カキクケコガギグゲゴ', 'サ': 'サシスセソザジズゼゾ', 'タ': 'タチツテトダヂヅデド', 'ナ': 'ナニヌネノ', 'ハ': 'ハヒフヘホバビブベボパピプペポ', 'マ': 'マミムメモ', 'ヤ': 'ヤユヨ', 'ラ': 'ラリルレロ', 'ワ': 'ワヲ', 'ン': 'ン'}
kata_group = {}
for k,v in kata_families.items():
    for c in v:
        kata_group[c] = k

def kana_group(kana: str) -> str:
    return kata_group[kana]