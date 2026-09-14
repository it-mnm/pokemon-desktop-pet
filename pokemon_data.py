# -*- coding: utf-8 -*-
"""포켓몬 도감/진화 데이터 테이블.
PyQt 위젯을 전혀 참조하지 않는 순수 데이터 모듈이라 pet.py/dialogs.py/main.py
어디서든 평소처럼(지연 임포트 없이) 상단에서 import 가능하다."""

STONES = {
    "thunder": {"name": "천둥의 돌", "price": 500, "icon": "thunder-stone.png"},
    "water":   {"name": "물의 돌",   "price": 500, "icon": "water-stone.png"},
    "fire":    {"name": "불의 돌",   "price": 500, "icon": "fire-stone.png"},
    "leaf":    {"name": "리프의 돌", "price": 500, "icon": "leaf-stone.png"},
    "ice":     {"name": "얼음의 돌", "price": 500, "icon": "ice-stone.png"},
    "moon":    {"name": "달의 돌",   "price": 500, "icon": "moon-stone.png"},
}
STONE_ORDER = ["thunder", "water", "fire", "leaf", "ice", "moon"]

# 진화와 무관한 범용 소모 아이템(특정 종에 묶이지 않음).
# "effect" 값으로 pet.py의 실제 적용 로직(apply_rare_candy/apply_revive)을 고른다.
ITEMS = {
    "rare_candy": {"name": "이상한 사탕", "price": 300, "icon": "rare-candy.png", "effect": "level_up"},
    "revive":     {"name": "부활의 약",   "price": 2000, "icon": "revive.png", "effect": "revive"},
}
ITEM_ORDER = ["rare_candy", "revive"]


POKEMON_DEX = {
    # ── 기존 구현 종 ──────────────────────────────────────────────
    "mimikyu":  {"ko": "따라큐", "evolves_to": None, "is_starter": True},

    "squirtle":  {"ko": "꼬북이", "evolves_to": "wartortle", "method": "level", "level": 15, "is_starter": True},
    "wartortle": {"ko": "어니부기", "evolves_to": "blastoise", "method": "level", "level": 30},
    "blastoise": {"ko": "거북왕", "evolves_to": None},

    "riolu":   {"ko": "리오르", "evolves_to": "lucario", "method": "level", "level": 20, "is_starter": True},
    "lucario": {"ko": "루카리오", "evolves_to": None},

    "gible":    {"ko": "이어롤", "evolves_to": "gabite", "method": "level", "level": 15, "is_starter": True},
    "gabite":   {"ko": "이어롭", "evolves_to": "garchomp", "method": "level", "level": 30},
    "garchomp": {"ko": "가스톤", "evolves_to": None},

    "ralts":     {"ko": "랄토스", "evolves_to": "kirlia", "method": "level", "level": 15, "is_starter": True},
    "kirlia":    {"ko": "킬리아", "evolves_to": "gardevoir", "method": "level", "level": 30},
    "gardevoir": {"ko": "가디안", "evolves_to": None},

    "eevee": {
        "ko": "이브이", "evolves_to": None, "method": "branch", "branch_level": 20, "is_starter": True,
        "branch_options": [("espeon", "에스퍼"), ("umbreon", "블래키"), ("sylveon", "님피아")],
        "stone_options": {"water": "vaporeon", "thunder": "jolteon", "fire": "flareon",
                           "leaf": "leafeon", "ice": "glaceon"},
    },
    "vaporeon": {"ko": "샤미드", "evolves_to": None},
    "jolteon":  {"ko": "쥬피썬더", "evolves_to": None},
    "flareon":  {"ko": "부스터", "evolves_to": None},
    "espeon":   {"ko": "에스퍼", "evolves_to": None},
    "umbreon":  {"ko": "블래키", "evolves_to": None},
    "leafeon":  {"ko": "리피아", "evolves_to": None},
    "glaceon":  {"ko": "글레이시아", "evolves_to": None},
    "sylveon":  {"ko": "님피아", "evolves_to": None},

    "pikachu": {"ko": "피카츄", "evolves_to": "raichu", "method": "stone", "stone": "thunder", "is_starter": True},
    "raichu":  {"ko": "라이츄", "evolves_to": None},

    # ── 1세대 도감 1-36번 신규 추가 ───────────────────────────────
    "bulbasaur":  {"ko": "이상해씨", "evolves_to": "ivysaur", "method": "level", "level": 15, "is_starter": True},
    "ivysaur":    {"ko": "이상해풀", "evolves_to": "venusaur", "method": "level", "level": 30},
    "venusaur":   {"ko": "이상해꽃", "evolves_to": None},

    "charmander": {"ko": "파이리", "evolves_to": "charmeleon", "method": "level", "level": 15, "is_starter": True},
    "charmeleon": {"ko": "리자드", "evolves_to": "charizard", "method": "level", "level": 30},
    "charizard":  {"ko": "리자몽", "evolves_to": None},

    "caterpie":  {"ko": "캐터피", "evolves_to": "metapod", "method": "level", "level": 15, "is_starter": True},
    "metapod":   {"ko": "단단지", "evolves_to": "butterfree", "method": "level", "level": 30},
    "butterfree": {"ko": "버터플", "evolves_to": None},

    "weedle": {"ko": "뿔충이", "evolves_to": "kakuna", "method": "level", "level": 15, "is_starter": True},
    "kakuna": {"ko": "딱충이", "evolves_to": "beedrill", "method": "level", "level": 30},
    "beedrill": {"ko": "독침붕", "evolves_to": None},

    "pidgey":    {"ko": "구구", "evolves_to": "pidgeotto", "method": "level", "level": 15, "is_starter": True},
    "pidgeotto": {"ko": "피죤", "evolves_to": "pidgeot", "method": "level", "level": 30},
    "pidgeot":   {"ko": "피죤투", "evolves_to": None},

    "rattata":  {"ko": "꼬렛", "evolves_to": "raticate", "method": "level", "level": 20, "is_starter": True},
    "raticate": {"ko": "레트라", "evolves_to": None},

    "spearow": {"ko": "깨비참", "evolves_to": "fearow", "method": "level", "level": 20, "is_starter": True},
    "fearow":  {"ko": "깨비드릴조", "evolves_to": None},

    "ekans": {"ko": "아보", "evolves_to": "arbok", "method": "level", "level": 20, "is_starter": True},
    "arbok": {"ko": "아보크", "evolves_to": None},

    "sandshrew": {"ko": "모래두지", "evolves_to": "sandslash", "method": "level", "level": 20, "is_starter": True},
    "sandslash": {"ko": "고지비도", "evolves_to": None},

    "nidoranf": {"ko": "니드런♀", "evolves_to": "nidorina", "method": "level", "level": 20, "is_starter": True},
    "nidorina": {"ko": "니드리나", "evolves_to": "nidoqueen", "method": "stone", "stone": "moon"},
    "nidoqueen": {"ko": "니드퀸", "evolves_to": None},

    "nidoranm": {"ko": "니드런♂", "evolves_to": "nidorino", "method": "level", "level": 20, "is_starter": True},
    "nidorino": {"ko": "니드리노", "evolves_to": "nidoking", "method": "stone", "stone": "moon"},
    "nidoking": {"ko": "니드킹", "evolves_to": None},

    "clefairy": {"ko": "삐삐", "evolves_to": "clefable", "method": "stone", "stone": "moon", "is_starter": True},
    "clefable": {"ko": "픽시", "evolves_to": None},
}

STARTERS = [base for base, e in POKEMON_DEX.items() if e.get("is_starter")]


def get_ko_name(base_name):
    entry = POKEMON_DEX.get(base_name)
    return entry["ko"] if entry else base_name


def stones_that_evolve(base_name):
    """이 base_name을 가진 포켓몬이 사용할 수 있는 (stone_id -> 진화 결과 base_name) 매핑을 반환.
    일반 stone 방식(예: 피카츄)과 이브이의 분기형 stone_options 둘 다 처리."""
    entry = POKEMON_DEX.get(base_name)
    if not entry:
        return {}
    if entry.get("method") == "stone" and entry.get("evolves_to"):
        return {entry["stone"]: entry["evolves_to"]}
    if entry.get("method") == "branch" and entry.get("stone_options"):
        return dict(entry["stone_options"])
    return {}
