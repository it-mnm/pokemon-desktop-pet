# -*- coding: utf-8 -*-
import os
import sys
import random
from PyQt6.QtWidgets import QLabel, QDialog, QWidget, QLineEdit
from PyQt6.QtCore import QTimer, QEvent, Qt
from PyQt6.QtGui import QFont, QFontDatabase

if getattr(sys, 'frozen', False):
    # PyInstaller로 묶은 exe에서는 assets 같은 번들 리소스가 실행할 때마다
    # 풀리는 임시 폴더(sys._MEIPASS)에 위치한다.
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

PIXEL_FONT_FAMILY = None

def load_pixel_font():
    """픽셀 폰트 로드 (dalmoori.ttf 또는 기본값)"""
    global PIXEL_FONT_FAMILY
    if PIXEL_FONT_FAMILY is not None:
        return PIXEL_FONT_FAMILY

    try:
        # assets/fonts/dalmoori.ttf 경로
        font_path = os.path.join(ASSETS_DIR, "fonts", "dalmoori.ttf")
        print(f"[FONT] 폰트 경로: {font_path}")
        print(f"[FONT] 파일 존재: {os.path.exists(font_path)}")

        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            print(f"[FONT] 로드 ID: {font_id}")

            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                print(f"[FONT] 사용 가능한 폰트: {families}")

                if families:
                    PIXEL_FONT_FAMILY = families[0]
                    print(f"[FONT] 선택 폰트: {PIXEL_FONT_FAMILY}")
                    return PIXEL_FONT_FAMILY
            else:
                print("[FONT] 폰트 로드 실패 (ID: -1)")
        else:
            print("[FONT] 폰트 파일을 찾을 수 없습니다!")

    except Exception as e:
        print(f"[FONT] 폰트 로드 오류: {e}")
        import traceback
        traceback.print_exc()

    print("[FONT] 기본 폰트 Arial로 설정됨")
    PIXEL_FONT_FAMILY = "Arial"
    return PIXEL_FONT_FAMILY

PIXEL_FONT_FAMILY = load_pixel_font()


class DraggableDialog(QDialog):
    """테두리 없는(frameless) 다이얼로그를 마우스로 아무 데나 눌러서 드래그해
    옮길 수 있게 해주는 공용 베이스 클래스. 이 앱의 다이얼로그는 전부 프레임이
    없어서(제목 표시줄이 없어서) 기본적으로는 드래그로 옮길 방법이 없다.
    show() 시점의 모든 자식 위젯에 이벤트 필터를 걸어서, 버튼/라벨 위를
    눌러도(그 위젯 자신의 클릭 동작은 그대로 살아있는 채로) 창을 드래그할 수
    있게 한다."""

    def __init__(self):
        super().__init__()
        self._drag_pos = None

    def showEvent(self, event):
        super().showEvent(event)
        self._install_drag_filter(self)

    def _install_drag_filter(self, widget):
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        # QLineEdit 위에서의 드래그는 창 이동이 아니라 텍스트 선택으로
        # 동작해야 한다 (수량 입력창 등에서 값을 드래그로 선택하려는데 창
        # 자체가 따라 움직여서 불편하다는 피드백으로 추가한 예외 처리).
        if isinstance(obj, QLineEdit):
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif etype == QEvent.Type.MouseMove and event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        elif etype == QEvent.Type.MouseButtonRelease:
            self._drag_pos = None
        return super().eventFilter(obj, event)


_sprite_content_size_cache = {}

def get_sprite_content_size(base_name):
    """GIF 캔버스에서 투명 여백을 뺀 실제 캐릭터 크기를 반환.
    (예: 따라큐 GIF는 캔버스가 96x96으로 제일 크지만 실제 캐릭터는 그 안에
    39x48 크기로 작게 그려져 있어서, 캔버스 기준으로 스케일을 맞추면
    다른 포켓몬보다 훨씬 작게 보인다. 이 함수로 실제 캐릭터 크기를 구해
    "체감 크기"를 다른 포켓몬과 맞출 수 있다.)
    실패하거나 여백이 없으면 None을 반환한다."""
    if base_name in _sprite_content_size_cache:
        return _sprite_content_size_cache[base_name]

    result = None
    path = os.path.join(ASSETS_DIR, f"{base_name}.gif")
    try:
        from PIL import Image
        with Image.open(path) as im:
            frame = im.convert("RGBA")
            bbox = frame.getbbox()
            if bbox:
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                if w > 0 and h > 0:
                    result = (w, h)
    except Exception:
        result = None

    _sprite_content_size_cache[base_name] = result
    return result


class FoodItem(QLabel):
    """먹이 이펙트 (떨어지는 음식 애니메이션). icon은 이모지 문자(무료 먹이) 또는
    assets/items/ 안의 PNG 파일명(유료 열매)일 수 있다."""
    def __init__(self, parent, pos, icon="🍎"):
        super().__init__(parent)
        if icon.lower().endswith(".png"):
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(os.path.join(ASSETS_DIR, "items", icon))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.setPixmap(pixmap)
        else:
            self.setText(icon)
            self.setFont(QFont("Arial", 14))
        self.setStyleSheet("background: transparent;")
        self.adjustSize()
        self.move(pos.x() - 10, pos.y() - 10)
        self.show()
        
        self.vx = random.choice([-3, -2, 2, 3])
        self.vy = -7.0
        self.gravity = 0.8
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(25)
        
    def animate(self):
        new_x = self.x() + self.vx
        new_y = self.y() + int(self.vy)
        self.vy += self.gravity
        self.move(int(new_x), int(new_y))
        
        if self.vy > 6:
            self.anim_timer.stop()
            self.deleteLater()