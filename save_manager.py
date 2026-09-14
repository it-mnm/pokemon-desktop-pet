# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    # PyInstaller로 묶은 exe에서는 번들 리소스가 실행할 때마다 새로 풀리는
    # 임시 폴더(sys._MEIPASS)에 있으므로, 그 안에 저장하면 프로그램을 껐다
    # 켤 때마다 데이터가 사라진다. exe 파일이 실제로 놓인 위치를 기준으로 삼는다.
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))


def get_app_data_dir():
    """OS 표준 사용자 데이터 폴더를 반환한다. exe를 어느 폴더에 두고 실행하든
    (심지어 복사본을 여러 폴더에 두고 번갈아 실행해도) 항상 같은 경로를
    가리키므로, exe 파일만 새 버전으로 교체해도 세이브가 자동으로 이어진다.
    (예전엔 exe가 놓인 폴더 바로 옆에 Pokemon_saves를 뒀는데, 그러면 exe를
    다른 폴더로 옮기거나 복사하면 세이브를 못 찾는 문제가 있었다.)"""
    appdata = os.environ.get('APPDATA')
    if appdata:
        return os.path.join(appdata, 'PokemonKiwoogi')
    return os.path.join(os.path.expanduser('~'), '.pokemon_kiwoogi')


class SaveManager:
    """포켓몬 데이터 저장/로드 관리 클래스"""

    def __init__(self):
        self.save_dir = os.path.join(get_app_data_dir(), "Pokemon_saves")
        self.save_file = os.path.join(self.save_dir, "pokemon_data.json")
        self.ensure_save_dir()
        self._migrate_legacy_save_if_needed()

    def ensure_save_dir(self):
        """저장 폴더 생성"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def _migrate_legacy_save_if_needed(self):
        """예전 버전(exe/스크립트 바로 옆에 Pokemon_saves를 두던 방식)에서 쓰던
        세이브 파일이 있고, 새 표준 위치엔 아직 세이브가 없으면 그대로
        복사해온다. 딱 한 번만 일어나며, 원본 레거시 파일은 안전하게 그대로
        남겨둔다(혹시 몰라 지우지 않음)."""
        if os.path.exists(self.save_file):
            return  # 새 위치에 이미 세이브가 있으면 마이그레이션 불필요

        legacy_file = os.path.join(APP_DIR, "Pokemon_saves", "pokemon_data.json")
        if not os.path.exists(legacy_file) or os.path.abspath(legacy_file) == os.path.abspath(self.save_file):
            return

        try:
            shutil.copy2(legacy_file, self.save_file)
            print(f"기존 위치의 세이브 파일을 새 위치로 이전했습니다: {self.save_file}")
        except Exception as e:
            print(f"세이브 파일 이전 실패: {e}")

    def save_game(self, pets_data, gold=0, food_inventory=None, default_food=None,
                  stone_inventory=None, item_inventory=None):
        """포켓몬 데이터 + 골드 + 먹이 재고 + 기본 먹이 설정 + 진화의 돌 재고 +
        일반 아이템(이상한 사탕/부활의 약 등) 재고를 JSON 파일로 저장"""
        try:
            # widget 객체는 JSON으로 저장할 수 없으므로 제거
            save_pets = []
            for pet in pets_data:
                pet_copy = pet.copy()
                pet_copy.pop('widget', None)  # widget 제거
                pet_copy['last_saved'] = datetime.now().isoformat()
                save_pets.append(pet_copy)

            save_data = {
                "pets": save_pets,
                "gold": gold,
                "food_inventory": food_inventory or {},
                "default_food": default_food,
                "stone_inventory": stone_inventory or {},
                "item_inventory": item_inventory or {},
            }

            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            print(f"포켓몬 데이터 저장됨: {len(save_pets)}마리, 골드 {gold}")
            return True
        except Exception as e:
            print(f"저장 실패: {e}")
            return False

    def load_game(self):
        """JSON 파일에서 포켓몬 데이터 + 골드 + 먹이 재고 + 기본 먹이 설정을 로드.
        v0.2 이하의 저장 파일은 최상위가 포켓몬 배열 하나뿐이었으므로(골드 개념이
        없었음), 그 경우 골드 0 / 빈 재고로 자동 채워서 호환한다."""
        empty_defaults = {"pets": [], "gold": 0, "food_inventory": {}, "default_food": None,
                           "stone_inventory": {}, "item_inventory": {}}

        if not os.path.exists(self.save_file):
            print("저장된 포켓몬이 없습니다.")
            return dict(empty_defaults)

        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)

            if isinstance(raw, list):
                # v0.2 이하: 배열 = 포켓몬 목록 그 자체
                data = dict(empty_defaults)
                data["pets"] = raw
            else:
                data = {
                    "pets": raw.get("pets", []),
                    "gold": raw.get("gold", 0),
                    "food_inventory": raw.get("food_inventory", {}),
                    "default_food": raw.get("default_food", None),
                    "stone_inventory": raw.get("stone_inventory", {}),
                    "item_inventory": raw.get("item_inventory", {}),
                }

            print(f"포켓몬 데이터 로드됨: {len(data['pets'])}마리, 골드 {data['gold']}")
            return data
        except Exception as e:
            print(f"로드 실패: {e}")
            return dict(empty_defaults)

    def delete_save(self):
        """저장 데이터 삭제"""
        if os.path.exists(self.save_file):
            os.remove(self.save_file)
            print("포켓몬 데이터 삭제됨")
