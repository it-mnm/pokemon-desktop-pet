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
    
    def save_pets(self, pets_data):
        """포켓몬 데이터를 JSON 파일로 저장"""
        try:
            # widget 객체는 JSON으로 저장할 수 없으므로 제거
            save_data = []
            for pet in pets_data:
                pet_copy = pet.copy()
                pet_copy.pop('widget', None)  # widget 제거
                pet_copy['last_saved'] = datetime.now().isoformat()
                save_data.append(pet_copy)

            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            print(f"포켓몬 데이터 저장됨: {len(save_data)}마리")
            return True
        except Exception as e:
            print(f"저장 실패: {e}")
            return False
    
    def load_pets(self):
        """JSON 파일에서 포켓몬 데이터 로드"""
        if not os.path.exists(self.save_file):
            print("저장된 포켓몬이 없습니다.")
            return []

        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                pets_data = json.load(f)

            print(f"포켓몬 데이터 로드됨: {len(pets_data)}마리")
            return pets_data
        except Exception as e:
            print(f"로드 실패: {e}")
            return []
    
    def delete_save(self):
        """저장 데이터 삭제"""
        if os.path.exists(self.save_file):
            os.remove(self.save_file)
            print("포켓몬 데이터 삭제됨")