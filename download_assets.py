import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

POKEMON_DEX_NUM = {
    "eevee": 133,
    "vaporeon": 134,
    "jolteon": 135,
    "flareon": 136,
    "espeon": 196,
    "umbreon": 197,
    "leafeon": 470,
    "glaceon": 471,
    "sylveon": 700,
    "mimikyu": 778,  # ?°ë¼??
    "squirtle": 7,   # ê¼¬ë¶??
    "wartortle": 8,  # ?´ë‹ˆë¶€ê¸?
    "blastoise": 9,  # ê±°ë¶??
    "riolu": 447,    # ë¦¬ì˜¤ë¥?
    "lucario": 448,  # ë£¨ì¹´ë¦¬ì˜¤
    "gible": 427,    # ?´ì–´ë¡?
    "gabite": 428,   # ?´ì–´ë¡?
    "ralts": 280,    # ?„í† ????NEW
    "kirlia": 281,   # ?¬ë¦¬????NEW
    "gardevoir": 282 # ê°€?”ì•ˆ
}

def download_all_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    print("?“¦ assets ?´ë” ???„ìš”???Œì¼ ?¤ìš´ë¡œë“œë¥??œì‘?©ë‹ˆ??..")

    # 1. ?°íŠ¸ ?¤ìš´ë¡œë“œ
    font_path = os.path.join(ASSETS_DIR, "pixel_font.ttf")
    if not os.path.exists(font_path):
        print("  - ?°íŠ¸(Galmuri9.ttf) ?¤ìš´ë¡œë“œ ì¤?..")
        try:
            url = "https://raw.githubusercontent.com/galmuri/galmuri/main/dist/Galmuri9.ttf"
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            print(f"    ???°íŠ¸ ?¤ìš´ë¡œë“œ ?¤íŒ¨: {e}")

    # 2. ê°??¬ì¼“ëª?GIF ?¤ìš´ë¡œë“œ
    for name, dex_id in POKEMON_DEX_NUM.items():
        file_path = os.path.join(ASSETS_DIR, f"{name}.gif")
        right_path = os.path.join(ASSETS_DIR, f"{name}_right.gif")
        
        if os.path.exists(file_path) or os.path.exists(right_path):
            print(f"  - [{name}] ?´ë? ?ì…‹??ì¡´ì¬?©ë‹ˆ??")
            continue

        url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/{dex_id}.gif"
        print(f"  - [{name}] (?„ê° ë²ˆí˜¸ #{dex_id}) ?¤ìš´ë¡œë“œ ì¤?..")
        try:
            urllib.request.urlretrieve(url, file_path)
        except Exception as e:
            print(f"    ??[{name}] ?¤ìš´ë¡œë“œ ?¤íŒ¨: {e}")

    print("\n??ëª¨ë“  ?ì…‹ ì¤€ë¹„ê? ?„ë£Œ?˜ì—ˆ?µë‹ˆ?? main.pyë¥??¤í–‰??ì£¼ì„¸??")

if __name__ == "__main__":
    download_all_assets()
