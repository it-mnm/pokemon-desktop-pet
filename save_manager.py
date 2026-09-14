# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    # PyInstaller로 묶은 exe에서는 번들 리소스가 실행할 때마다 새로 풀리는
    # 임시 폴더(sys._MEIPASS)에 있으므로, 그 안에 저장하면 프로그램을 껐다
    # 켤 때마다 데이터가 사라진다. exe 파일이 실제로 놓인 위치를 기준으로 삼는다.
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

class SaveManager:
    """포켓몬 데이터 저장/로드 관리 클래스"""

    def __init__(self):
        self.save_dir = os.path.join(APP_DIR, "Pokemon_saves")
        self.save_file = os.path.join(self.save_dir, "pokemon_data.json")
        self.ensure_save_dir()

    def ensure_save_dir(self):
        """저장 폴더 생성"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

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
