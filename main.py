# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QDialog
from PyQt6.QtCore import Qt, QSize, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont

STORED_HUNGER_CAP = 50  # 상자 안에서 자동으로 회복되는 포만감의 상한


class PokemonManager:
    """포켓몬 데이터 관리 클래스"""
    def __init__(self):
        self.save_manager = SaveManager()
        self.pets_data = self.save_manager.load_pets()
        # 저장 파일에는 'widget'을 담지 않으므로(직렬화 불가), 로드 직후 항상 채워둔다.
        # 그렇지 않으면 아직 소환되지 않은(상자 안) 포켓몬은 이 키가 아예 없어서
        # 상자 UI가 pet_data['widget']에 접근하는 순간 KeyError로 죽는다.
        for pet_data in self.pets_data:
            pet_data.setdefault('widget', None)

    def add_pet(self, ko_name, base_name, nickname):
        """새 포켓몬 추가 (상자 안에 넣어진 상태로 생성됨)"""
        pet_data = {
            'pokemon_type_ko': ko_name,
            'pokemon_base_name': base_name,
            'nickname': nickname,
            'level': 1,
            'friendship': 0,
            'hunger': 100,
            'life': 5,
            'dead': False,
            'stored': True,
            'widget': None
        }
        self.pets_data.append(pet_data)
        self.save_manager.save_pets(self.pets_data)
        return pet_data

    def delete_pet(self, pet_data):
        """포켓몬 삭제"""
        if pet_data in self.pets_data:
            if pet_data.get('widget'):
                # 꺼내져 있는(데스크톱에 떠 있는) 상태로 삭제하면 위젯을 닫아주지
                # 않으면 상자에서는 사라져도 화면에는 계속 남아있게 된다.
                pet_data['widget'].close()
                pet_data['widget'] = None
            self.pets_data.remove(pet_data)
            self.save_manager.save_pets(self.pets_data)

    def spawn_pet(self, pet_data):
        """포켓몬을 화면에 표시"""
        pet_widget = DesktopPet(pet_data, self)
        pet_widget.show()
        pet_data['widget'] = pet_widget
        pet_data['stored'] = False

    def despawn_pet(self, pet_data):
        """포켓몬을 상자에 넣음"""
        if pet_data['widget']:
            pet_data['widget'].close()
            pet_data['widget'] = None
        pet_data['stored'] = True

    def save_game(self):
        """게임 저장"""
        self.save_manager.save_pets(self.pets_data)

    def recover_stored_hunger(self):
        """상자 안(보관 중)인 포켓몬의 포만감을 서서히 회복시킨다 (최대 STORED_HUNGER_CAP까지).
        despawn된 포켓몬은 DesktopPet 위젯 객체가 살아있다는 보장이 없으므로(참조가
        끊기면 위젯 자신의 타이머로는 더 이상 회복되지 않는다), pet_data를 직접 갱신하는
        이 전역 타이머가 위젯 존재 여부와 무관하게 회복을 담당한다."""
        changed = False
        for pet_data in self.pets_data:
            if pet_data.get('dead', False) or not pet_data.get('stored', False):
                continue
            hunger = pet_data.get('hunger', 0)
            if hunger < STORED_HUNGER_CAP:
                pet_data['hunger'] = min(STORED_HUNGER_CAP, hunger + 2)
                changed = True
        if changed:
            self.save_game()


def create_pokeball_pixmap(size=64):
    """포켓볼 모양 아이콘을 코드로 그려서 생성"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.06
    d = size - margin * 2
    circle_rect = QRectF(margin, margin, d, d)

    # 아래쪽 흰색 반원
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FAFAFA"))
    painter.drawEllipse(circle_rect)

    # 위쪽 빨간색 반원
    painter.save()
    painter.setClipRect(QRectF(0, 0, size, size / 2))
    painter.setBrush(QColor("#FF3B3B"))
    painter.drawEllipse(circle_rect)
    painter.restore()

    # 외곽 테두리
    painter.setPen(QPen(QColor("#222222"), max(2, size * 0.05)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(circle_rect)

    # 가운데 검은 띠
    band_h = max(2, size * 0.07)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#222222"))
    painter.drawRect(QRectF(margin, size / 2 - band_h / 2, d, band_h))

    # 가운데 버튼(이중 원)
    cx, cy = size / 2, size / 2
    outer_r = d * 0.22
    outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
    painter.setPen(QPen(QColor("#222222"), max(2, size * 0.045)))
    painter.setBrush(QColor("#FAFAFA"))
    painter.drawEllipse(outer_rect)

    inner_r = outer_r * 0.45
    inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
    painter.setPen(QPen(QColor("#222222"), max(1, size * 0.025)))
    painter.setBrush(QColor("#FAFAFA"))
    painter.drawEllipse(inner_rect)

    painter.end()
    return pixmap


class PokeballButton(QPushButton):
    """좌측 하단 포켓볼 아이콘 버튼. 호버 시 확대, 클릭 시 눌리는 애니메이션 포함."""
    def __init__(self, base_size=64):
        super().__init__()
        self.base_size = base_size
        self._scale = 1.0
        self._anchor_x = 0
        self._anchor_bottom_y = 0

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("포켓몬 상자 열기")

        self._icon_pixmap = create_pokeball_pixmap(256)
        self.setIcon(QIcon(self._icon_pixmap))

        self._anim = QPropertyAnimation(self, b"scaleValue", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._apply_scale()

    def set_anchor(self, x, bottom_y):
        """왼쪽 아래 기준점을 고정 (크기가 바뀌어도 그 자리에서 커지고 작아지도록)"""
        self._anchor_x = x
        self._anchor_bottom_y = bottom_y
        self._apply_scale()

    def getScaleValue(self):
        return self._scale

    def setScaleValue(self, value):
        self._scale = value
        self._apply_scale()

    scaleValue = pyqtProperty(float, getScaleValue, setScaleValue)

    def _apply_scale(self):
        size = max(16, int(self.base_size * self._scale))
        self.setFixedSize(size, size)
        self.setIconSize(QSize(size, size))
        self.move(self._anchor_x, self._anchor_bottom_y - size)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event):
        self._animate_to(1.15)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(1.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._animate_to(0.88)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._animate_to(1.15 if self.underMouse() else 1.0)
        super().mouseReleaseEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 다이얼로그(포켓몬 상자 등)를 닫아도 앱이 종료되지 않도록 설정
    app.setQuitOnLastWindowClosed(False)

    from pet import DesktopPet
    from dialogs import PokemonAddDialog, PokemonManagerDialog, StartScreenDialog, ask_confirm, show_info
    from save_manager import SaveManager
    from utils import PIXEL_FONT_FAMILY

    # 이 게임의 모든 위젯이 동일한 픽셀 폰트를 기본으로 사용하도록 설정
    app.setFont(QFont(PIXEL_FONT_FAMILY, 10))

    manager = PokemonManager()

    def show_starter_dialog():
        """시작 포켓몬을 고르게 한다. 선택해서 시작하면 True, 취소하면 False를 반환한다."""
        starter_dlg = PokemonAddDialog(title="시작 포켓몬을 선택하세요")
        screen = QApplication.primaryScreen().geometry()
        starter_dlg.move((screen.width() - starter_dlg.width()) // 2, (screen.height() - starter_dlg.height()) // 2)
        if starter_dlg.exec() != QDialog.DialogCode.Accepted:
            return False
        ko_name, base_name = starter_dlg.selected_species
        starter_pet = manager.add_pet(ko_name, base_name, starter_dlg.nickname)
        manager.spawn_pet(starter_pet)  # 시작 포켓몬은 바로 화면에 나타남
        manager.save_game()
        return True

    # 시작 화면: 새로하기 / 이어하기 / 프로그램 종료 선택
    while True:
        has_save_data = len(manager.pets_data) > 0
        start_dlg = StartScreenDialog(has_save_data=has_save_data)
        screen = QApplication.primaryScreen().geometry()
        start_dlg.move((screen.width() - start_dlg.width()) // 2, (screen.height() - start_dlg.height()) // 2)
        start_dlg.exec()

        choice = start_dlg.choice
        if choice is None:  # 테두리 없는 창이라도 Esc 등으로 닫힐 수 있어 안전하게 처리
            choice = StartScreenDialog.CONTINUE if has_save_data else StartScreenDialog.NEW_GAME

        if choice == StartScreenDialog.QUIT:
            sys.exit(0)

        if choice == StartScreenDialog.CONTINUE:
            if not has_save_data:
                show_info(None, "알림", "이어할 수 있는 저장된 데이터가 없습니다.")
                continue  # 시작 화면으로 다시
            break  # 기존 데이터 그대로 이어서 진행

        if choice == StartScreenDialog.NEW_GAME:
            if has_save_data:
                confirmed = ask_confirm(
                    None, "새로 시작",
                    "정말 새로 시작하시겠습니까?\n기존에 키우던 포켓몬 데이터가 모두 사라집니다.",
                    confirm_text="새로하기", cancel_text="취소",
                )
                if not confirmed:
                    continue  # 시작 화면으로 다시

            backup_pets_data = manager.pets_data
            manager.pets_data = []
            if not show_starter_dialog():
                # 시작 포켓몬 선택을 취소한 경우 기존 데이터를 복원하고 시작 화면으로 되돌아간다
                manager.pets_data = backup_pets_data
                continue
            break

    # 이전 종료 시점에 꺼내놨던(상자 밖에 있던) 포켓몬만 자동으로 다시 꺼냄
    for pet_data in manager.pets_data:
        if pet_data.get('dead', False):
            continue
        if not pet_data.get('stored', False) and not pet_data.get('widget'):
            manager.spawn_pet(pet_data)

    # 상자 안 포켓몬의 포만감 자동 회복 타이머
    # (DesktopPet 위젯이 실제로 계속 살아있다는 보장이 없으므로, 위젯 존재 여부와
    #  무관하게 pet_data를 직접 갱신하는 이 전역 타이머가 회복을 담당한다)
    recovery_timer = QTimer(app)
    recovery_timer.timeout.connect(manager.recover_stored_hunger)
    recovery_timer.start(2000)

    # 화면 좌측 하단 포켓볼 아이콘 버튼 (클릭 시 포켓몬 상자 오픈)
    pokeball_btn = PokeballButton(base_size=64)

    def show_manager():
        dlg = PokemonManagerDialog(manager)
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        dlg.exec()

    pokeball_btn.clicked.connect(show_manager)

    available = QApplication.primaryScreen().availableGeometry()
    edge_margin = 20
    pokeball_btn.set_anchor(available.x() + edge_margin, available.y() + available.height() - edge_margin)
    pokeball_btn.show()

    app.aboutToQuit.connect(manager.save_game)

    sys.exit(app.exec())
