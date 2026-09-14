# -*- coding: utf-8 -*-
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                             QPushButton, QFrame, QLineEdit, QMenu, QInputDialog,
                             QApplication, QScrollArea, QWidget, QSpacerItem, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QMovie, QPixmap, QCursor, QPainter, QColor, QIcon
from utils import ASSETS_DIR, PIXEL_FONT_FAMILY, get_sprite_content_size, DraggableDialog
from pet import MAX_LIFE, get_max_hunger, BOX_CAPACITY, PC_CAPACITY, FOOD_TIERS, FOOD_TIER_ORDER, FREE_FOOD_ICON, FREE_FOOD_NAME, get_food_effect, apply_evolution, apply_rare_candy, apply_revive
from pokemon_data import POKEMON_DEX, STARTERS, get_ko_name, STONES, STONE_ORDER, stones_that_evolve, ITEMS, ITEM_ORDER


def create_dot_pixmap(size=14, color="#FF5252"):
    """작은 원 아이콘을 코드로 그려서 생성.
    커스텀 픽셀 폰트(dalmoori)는 🔴 같은 이모지는 물론 ● 같은 기본 기호조차
    글리프가 없어서 텍스트로 넣으면 항상 대체 폰트로 그려지고, 그 과정에서
    가장자리가 잘려 보인다. 아예 텍스트가 아닌 아이콘으로 그려서 이 문제를
    피한다."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    margin = 1
    painter.drawEllipse(margin, margin, size - margin * 2, size - margin * 2)
    painter.end()
    return pixmap


def create_dot_icon(size=14, color="#FF5252"):
    return QIcon(create_dot_pixmap(size, color))


def load_item_icon_pixmap(icon_filename, size=28):
    """assets/items/ 안의 아이템 PNG(진화의 돌 등)를 정사각형 QPixmap으로 로드."""
    path = os.path.join(ASSETS_DIR, "items", icon_filename)
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


SELECTOR_BORDER_IDLE = "#E0E0E0"
SELECTOR_BORDER_SELECTED = "#FF5252"
SELECTOR_BG_IDLE = "#FFFFFF"
SELECTOR_BG_SELECTED = "#FFEBEE"


def compute_sprite_scaled_size(native_size, base_name, fit_box):
    """스프라이트를 fit_box 안에 표시할 때 쓸 스케일 크기를 계산.
    캔버스 크기가 아니라 실제 캐릭터(투명 여백 제외) 크기를 기준으로 비율을
    맞춰서, 따라큐처럼 캔버스 여백이 큰 스프라이트도 다른 포켓몬과 체감
    크기가 비슷하게 보이도록 한다. 여백만큼 캔버스가 fit_box보다 커지는
    부분은 QLabel이 자기 영역 밖은 그리지 않으므로 자연히 잘려서 보이지
    않는다."""
    content_size = get_sprite_content_size(base_name)
    if content_size:
        cw, ch = content_size
        scale = min(fit_box.width() / cw, fit_box.height() / ch)
        return QSize(max(1, int(native_size.width() * scale)), max(1, int(native_size.height() * scale)))
    return native_size.scaled(fit_box, Qt.AspectRatioMode.KeepAspectRatio)


class PokemonSelector(QWidget):
    """포켓몬 선택 위젯 - 이미지와 호버시 이름 표시"""
    selected = pyqtSignal(str, str)  # ko_name, base_name

    def __init__(self, ko_name, base_name):
        super().__init__()
        self.ko_name = ko_name
        self.base_name = base_name
        self.is_checked = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        # 포켓몬 이미지 레이블
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setFixedSize(55, 55)
        self.img_label.setStyleSheet("background-color: #F0F0F0; border: none; border-radius: 6px;")

        img_path = os.path.join(ASSETS_DIR, f"{base_name}.gif")
        if os.path.exists(img_path):
            self.movie = QMovie(img_path)
            self.movie.jumpToFrame(0)
            native_size = self.movie.frameRect().size()
            if native_size.width() > 0 and native_size.height() > 0:
                # 비율을 유지한 채 라벨보다 살짝 작게(여백 포함) 맞춰서
                # 찌그러짐과 가장자리에 딱 붙는 느낌을 방지
                fit_box = QSize(44, 44)
                scaled_size = compute_sprite_scaled_size(native_size, base_name, fit_box)
                self.movie.setScaledSize(scaled_size)
            self.img_label.setMovie(self.movie)
            self.movie.start()

        layout.addWidget(self.img_label)

        self.setFixedSize(70, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 선택 표시용 체크 배지 (우측 상단, 선택 시에만 표시)
        self.check_badge = QLabel("✓", self)
        self.check_badge.setFixedSize(20, 20)
        self.check_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check_badge.setStyleSheet(f"""
            background-color: {SELECTOR_BORDER_SELECTED};
            color: white;
            border: 2px solid white;
            border-radius: 10px;
            font-weight: bold;
            font-size: 11px;
        """)
        self.check_badge.move(48, 2)  # 위젯(70x70) 경계 안쪽에 위치시켜 잘리지 않도록
        self.check_badge.hide()

        self.deselect()

        # 1초 후 이름 표시
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_name)
        self.timer.setSingleShot(True)

    def enterEvent(self, event):
        self.timer.start(1000)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.timer.stop()
        super().leaveEvent(event)

    def show_name(self):
        from PyQt6.QtWidgets import QToolTip
        QToolTip.showText(QCursor.pos(), self.ko_name, self)

    def select(self):
        self.is_checked = True
        self.setStyleSheet(f"""
            QWidget {{
                border: 3px solid {SELECTOR_BORDER_SELECTED};
                border-radius: 8px;
                background-color: {SELECTOR_BG_SELECTED};
                margin: 0px;
                padding: 0px;
            }}
        """)
        self.check_badge.show()
        self.check_badge.raise_()

    def deselect(self):
        self.is_checked = False
        self.setStyleSheet(f"""
            QWidget {{
                border: 2px solid {SELECTOR_BORDER_IDLE};
                border-radius: 8px;
                background-color: {SELECTOR_BG_IDLE};
                margin: 0px;
                padding: 0px;
            }}
        """)
        self.check_badge.hide()

    def mousePressEvent(self, event):
        self.selected.emit(self.ko_name, self.base_name)
        super().mousePressEvent(event)


class ThemedMessageDialog(DraggableDialog):
    """앱 전체 톤(핑크 카드 + 픽셀 폰트)에 맞춘 알림/확인 창.
    cancel_text를 주면 확인/취소 버튼 2개, 주지 않으면 확인 버튼 1개만 뜬다."""
    def __init__(self, title, message, confirm_text="확인", cancel_text=None, danger=False):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(300, 200 if cancel_text else 180)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        confirm_color = "#F44336" if danger else "#4CAF50"

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: #FFF0F2;
                border: 3px solid #FF5252;
                border-radius: 18px;
            }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QPushButton#confirmBtn {{ background-color: {confirm_color}; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }}
            QPushButton#cancelBtn {{ background-color: #CCCCCC; color: black; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        icon = "⚠️" if danger else "🔔"
        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setFont(QFont(PIXEL_FONT_FAMILY, 10))
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setObjectName("confirmBtn")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        if cancel_text:
            cancel_btn = QPushButton(cancel_text)
            cancel_btn.setObjectName("cancelBtn")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        dialog_layout.addWidget(card)


def ask_confirm(parent, title, message, confirm_text="삭제", cancel_text="취소"):
    """테마에 맞춘 확인창을 띄우고, '확인' 선택 시 True 반환"""
    dlg = ThemedMessageDialog(title, message, confirm_text=confirm_text, cancel_text=cancel_text, danger=True)
    if parent is not None:
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
    return dlg.exec() == QDialog.DialogCode.Accepted


def show_info(parent, title, message):
    """테마에 맞춘 알림창"""
    dlg = ThemedMessageDialog(title, message, confirm_text="확인")
    if parent is not None:
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
    dlg.exec()


START_SCREEN_ILLUSTRATION = "pikachu"


class StartScreenDialog(DraggableDialog):
    """게임 시작 화면 - 새로하기 / 이어하기 / 프로그램 종료 선택"""
    NEW_GAME = "new"
    CONTINUE = "continue"
    QUIT = "quit"

    def __init__(self, has_save_data):
        super().__init__()
        self.choice = None
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 480)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: #FFF0F2;
                border: 3px solid #FF5252;
                border-radius: 20px;
            }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QPushButton#newBtn {{ background-color: #4CAF50; color: white; border: none; border-radius: 10px; padding: 0 12px; font-weight: bold; }}
            QPushButton#newBtn:hover {{ background-color: #43A047; }}
            QPushButton#continueBtn {{ background-color: #2196F3; color: white; border: none; border-radius: 10px; padding: 0 12px; font-weight: bold; }}
            QPushButton#continueBtn:hover {{ background-color: #1E88E5; }}
            QPushButton#continueBtn:disabled {{ background-color: #CCCCCC; color: #EEEEEE; }}
            QPushButton#quitBtn {{ background-color: #FFCDD2; color: #B71C1C; border: none; border-radius: 10px; padding: 0 10px; font-weight: bold; }}
            QPushButton#quitBtn:hover {{ background-color: #FFAAB4; }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 26, 24, 22)
        layout.setSpacing(12)

        title_label = QLabel("포켓몬키우기")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 13, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        img_label = QLabel()
        img_label.setFixedSize(150, 150)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background-color: #F0F0F0; border-radius: 12px;")
        img_path = os.path.join(ASSETS_DIR, f"{START_SCREEN_ILLUSTRATION}.gif")
        if os.path.exists(img_path):
            self.movie = QMovie(img_path)
            self.movie.jumpToFrame(0)
            native_size = self.movie.frameRect().size()
            if native_size.width() > 0 and native_size.height() > 0:
                scaled_size = compute_sprite_scaled_size(native_size, START_SCREEN_ILLUSTRATION, QSize(120, 120))
                self.movie.setScaledSize(scaled_size)
            img_label.setMovie(self.movie)
            self.movie.start()
        layout.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("나만의 포켓몬을 키워보세요!")
        subtitle.setFont(QFont(PIXEL_FONT_FAMILY, 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addStretch()

        new_btn = QPushButton("✨ 새로하기")
        new_btn.setObjectName("newBtn")
        new_btn.setFixedHeight(42)
        new_btn.clicked.connect(self._choose_new)
        layout.addWidget(new_btn)

        continue_btn = QPushButton("▶ 이어하기")
        continue_btn.setObjectName("continueBtn")
        continue_btn.setFixedHeight(42)
        continue_btn.setEnabled(has_save_data)
        continue_btn.clicked.connect(self._choose_continue)
        layout.addWidget(continue_btn)

        quit_btn = QPushButton(" 프로그램 종료")
        quit_btn.setObjectName("quitBtn")
        quit_btn.setIcon(create_dot_icon(14, "#B71C1C"))
        quit_btn.setIconSize(QSize(14, 14))
        quit_btn.setFixedHeight(38)
        quit_btn.clicked.connect(self._choose_quit)
        layout.addWidget(quit_btn)

        dialog_layout.addWidget(card)

    def _choose_new(self):
        self.choice = self.NEW_GAME
        self.accept()

    def _choose_continue(self):
        self.choice = self.CONTINUE
        self.accept()

    def _choose_quit(self):
        self.choice = self.QUIT
        self.accept()


class PokemonAddDialog(DraggableDialog):
    """포켓몬 추가 창"""
    def __init__(self, title="포켓몬 선택"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(420, 380)
        
        self.selected_species = ("이브이", "eevee")
        self.nickname = ""
        
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame(self)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{
                background-color: #FFF0F2;
                border: 3px solid #FF5252;
                border-radius: 18px;
            }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QFrame#whiteContainer {{ background-color: #FFFFFF; border: 2px solid #FFCDD2; border-radius: 12px; }}
            QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid #FFCDD2; border-radius: 6px; padding: 6px; color: #333; }}
            QPushButton#okBtn {{ background-color: #4CAF50; color: white; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }}
            QPushButton#cancelBtn {{ background-color: #CCCCCC; color: black; border: none; border-radius: 8px; padding: 10px; font-weight: bold; }}
        """)
        
        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        title_label = QLabel(f"✨ {title} ✨")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        white_container = QFrame()
        white_container.setObjectName("whiteContainer")
        container_layout = QVBoxLayout(white_container)
        container_layout.setContentsMargins(12, 12, 12, 12)

        # 포켓몬 선택 그리드
        select_label = QLabel("포켓몬을 선택하세요:")
        select_label.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        container_layout.addWidget(select_label)

        # 스크롤 영역
        species_scroll = QScrollArea()
        species_scroll.setWidgetResizable(True)
        species_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        species_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 6px; background-color: #F0F0F0; border-radius: 3px; }
            QScrollBar::handle:vertical { background-color: #CCCCCC; border-radius: 3px; }
        """)

        species_content = QWidget()
        species_content.setStyleSheet("background-color: #F0F0F0;")
        species_layout = QGridLayout(species_content)
        species_layout.setContentsMargins(5, 5, 5, 5)
        species_layout.setSpacing(8)

        # 포켓몬 선택 위젯 생성 (STARTERS 테이블 기반으로 동적 생성 — 스타터 종이
        # 늘어나도 여기 코드를 더 손댈 필요가 없다)
        self.selectors = {}
        for i, base_name in enumerate(STARTERS):
            ko_name = get_ko_name(base_name)
            selector = PokemonSelector(ko_name, base_name)
            selector.selected.connect(lambda ko, base: self.select_spec(ko, base))
            self.selectors[base_name] = selector
            row, col = divmod(i, 3)
            species_layout.addWidget(selector, row, col)

        first_base = STARTERS[0]
        self.selectors[first_base].select()
        self.selected_species = (get_ko_name(first_base), first_base)

        species_scroll.setWidget(species_content)
        species_scroll.setFixedHeight(160)
        container_layout.addWidget(species_scroll)

        container_layout.addWidget(QLabel("닉네임 설정:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("예: 귀요미")
        container_layout.addWidget(self.name_input)

        layout.addWidget(white_container)

        # 버튼
        button_layout = QHBoxLayout()
        confirm_btn = QPushButton("완료", self)
        confirm_btn.setObjectName("okBtn")
        confirm_btn.clicked.connect(self.on_confirm)

        cancel_btn = QPushButton("취소", self)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog_layout.addWidget(self.main_card)

    def select_spec(self, ko_name, base_name):
        self.selected_species = (ko_name, base_name)
        for selector in self.selectors.values():
            selector.deselect()
        self.selectors[base_name].select()

    def on_confirm(self):
        self.nickname = self.name_input.text().strip()
        self.accept()


class PetCardFrame(QFrame):
    """포켓몬 상자의 카드 한 장. 왼쪽 클릭하면 꺼내기/집어넣기가 토글되고,
    오른쪽 클릭하면 먹이 주기·PC로 보내기·이름변경·삭제 메뉴가 뜬다."""
    def __init__(self, pet_data, dialog):
        super().__init__()
        self.pet_data = pet_data
        self.dialog = dialog
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        # toggle_spawn()이 알림창(show_info)을 띄우면 그동안 중첩 이벤트 루프가
        # 돌면서 부모의 1.5초 주기 refresh_list()가 끼어들 수 있고, 그 타이밍에
        # 상자 목록이 재구성되면 지금 클릭을 처리 중인 이 카드 위젯 자체가
        # deleteLater()로 파괴된다. 그 상태에서 아래로 내려와 super()를
        # 호출하면 이미 삭제된 C++ 객체에 접근해 앱이 그대로 죽는다(RuntimeError).
        # QFrame의 기본 mousePressEvent는 별도 동작이 없으므로 호출하지 않아도 된다.
        if event.button() == Qt.MouseButton.LeftButton and not self.pet_data.get('dead', False):
            self.dialog.toggle_spawn(self.pet_data)

    def contextMenuEvent(self, event):
        self.dialog.show_pet_context_menu(self.pet_data, event.globalPos())


class PokemonManagerDialog(DraggableDialog):
    """포켓몬 상자/관리 다이얼로그"""
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(420, 580)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_list)
        self.update_timer.start(1500)

        self.initUI()

    def initUI(self):
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame(self)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF0F2; border: 3px solid #FF5252; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QFrame#whiteBox {{ background-color: #FFFFFF; border: 2px solid #FFCDD2; border-radius: 14px; }}
            QPushButton {{ background-color: #FFF; color: #333; border: 1.5px solid #FF8A80; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: bold; }}
            QPushButton:disabled {{ background-color: #EEEEEE; color: #999; border-color: #DDDDDD; }}
            QLineEdit {{ background-color: #FFF; color: #333; border: 1.2px solid #FF8A80; border-radius: 5px; padding: 2px 4px; font-size: 10px; }}
            QLineEdit:disabled {{ background-color: #EEEEEE; color: #999; }}
        """)

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        title_dot = QLabel()
        title_dot.setPixmap(create_dot_pixmap(12, "#FF5252"))
        title_dot.setFixedSize(12, 12)
        self.title_label = QLabel(f"포켓몬 상자 ({self.manager.box_count()}/{BOX_CAPACITY})")
        self.title_label.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("border-radius: 13px; background-color: #FFF; color: #333; border: 1.5px solid #FF8A80;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(title_dot)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        gold_layout = QHBoxLayout()
        self.gold_label = QLabel()
        self.gold_label.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        self.gold_label.setStyleSheet("color: #F57F17;")
        gold_layout.addWidget(self.gold_label)
        gold_layout.addStretch()
        layout.addLayout(gold_layout)

        hint_label = QLabel("클릭: 꺼내기/집어넣기 · 우클릭: 더보기")
        hint_label.setFont(QFont(PIXEL_FONT_FAMILY, 8))
        hint_label.setStyleSheet("color: #999;")
        layout.addWidget(hint_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 8px; background-color: #FFE0E3; border-radius: 4px; margin: 2px; }
            QScrollBar::handle:vertical { background-color: #FF8A80; border-radius: 4px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background-color: #FF5252; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.white_box = QFrame()
        self.white_box.setObjectName("whiteBox")
        self.list_layout = QVBoxLayout(self.white_box)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(8)

        scroll_area.setWidget(self.white_box)
        layout.addWidget(scroll_area)
        
        self.add_btn = QPushButton("➕ 새 포켓몬 추가하기")
        self.add_btn.setFixedHeight(34)
        self.add_btn.clicked.connect(self.add_new_pokemon)
        layout.addWidget(self.add_btn)

        dialog_layout.addWidget(self.main_card)
        # 생성 시점의 첫 호출은 강제로 채운다. 이 시점엔 아직 self.exec()가
        # 시작되기 전이라(호출부가 생성자 -> exec() 순서로 부르기 때문)
        # activeModalWidget()이 아직 self가 아니라 이 상자를 연 상위 메뉴창을
        # 가리켜서, force 없이는 모달 가드에 걸려 첫 목록 표시가 다음 타이머
        # 주기(1.5초)까지 미뤄지는 지연이 있었다.
        self.refresh_list(force=True)

    def refresh_list(self, force=False):
        self.title_label.setText(f"포켓몬 상자 ({self.manager.box_count()}/{BOX_CAPACITY})")
        self.gold_label.setText(f"보유 골드: {self.manager.gold:,}G")

        # 알림창(먹이 부족, 삭제 확인, 진화 선택 등) 같은 다른 모달이 이 상자
        # 위에 떠 있는 동안에는 목록을 재구성하지 않는다. 그러지 않으면 1.5초
        # 주기 리프레시가 모달을 띄운 카드 위젯 자체를 파괴해버려서, 모달이
        # 닫히고 원래 클릭 처리로 복귀했을 때 이미 삭제된 위젯에 접근해 앱이
        # 죽는다. 이 상자 창 자신은 exec()로 열려 있는 동안 늘 "현재 활성
        # 모달"이므로, activeModalWidget()이 self가 아닌 '다른' 모달일 때만
        # 건너뛰어야 한다 (그냥 None이 아니면 건너뛰면, 열려 있는 상자 자신이
        # 매번 걸려서 목록이 영원히 비어 보이는 버그가 생긴다).
        active_modal = QApplication.activeModalWidget()
        if not force and active_modal is not None and active_modal is not self:
            return

        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            return

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        box_pets = [p for p in self.manager.pets_data if p.get('location', 'box') == 'box']
        for pet_data in box_pets:
            is_dead = pet_data.get('dead', False)
            is_out = (not pet_data.get('stored', False)) and not is_dead

            item_frame = PetCardFrame(pet_data, self)
            item_frame.setFixedHeight(64)
            if is_out:
                # 꺼내져 있는(밖에 나와있는) 포켓몬은 눈에 띄게 핑크색으로 표시
                item_frame.setStyleSheet("background-color: #FFEBEE; border: 1.5px solid #FF8A80; border-radius: 10px;")
            else:
                item_frame.setStyleSheet("background-color: #FAFAFA; border: 1.5px solid #E0E0E0; border-radius: 10px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(8, 6, 8, 6)

            base_name = pet_data['pokemon_base_name']
            img_path = os.path.join(ASSETS_DIR, f"{base_name}.gif")
            if not os.path.exists(img_path):
                img_path = os.path.join(ASSETS_DIR, "eevee.gif")

            icon_label = QLabel()
            icon_frame_size = 38  # 프레임(라벨 박스) 크기 - 원래 크기 유지
            icon_char_fit = 26    # 그 안에 표시되는 캐릭터 크기 기준 - 이 값만 줄이면 여백이 생김
            icon_label.setFixedSize(icon_frame_size, icon_frame_size)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("background-color: transparent;")

            if os.path.exists(img_path):
                movie = QMovie(img_path)
                movie.jumpToFrame(0)
                native_size = movie.frameRect().size()
                if native_size.width() > 0 and native_size.height() > 0:
                    # 비율 유지 + 캐릭터 실제 크기 기준 스케일
                    # (세로로 긴 스프라이트가 퍼져 보이지 않고, 여백이 큰 스프라이트도
                    #  다른 포켓몬과 체감 크기가 비슷하게 보이도록)
                    scaled_size = compute_sprite_scaled_size(native_size, base_name, QSize(icon_char_fit, icon_char_fit))
                    movie.setScaledSize(scaled_size)
                icon_label.setMovie(movie)
                movie.start()
                item_frame.movie = movie

            if is_dead:
                opacity_effect = QGraphicsOpacityEffect(icon_label)
                opacity_effect.setOpacity(0.3)
                icon_label.setGraphicsEffect(opacity_effect)
                item_frame.opacity_effect = opacity_effect

            right_layout = QVBoxLayout()
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(3)

            display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
            name_html = f"<b>{display_name}</b> <font color='#777'>({pet_data['pokemon_type_ko']}) Lv.{pet_data['level']}</font>"
            if is_dead:
                name_html = f"<font color='#999'>💀 {display_name} (사망)</font>"
            info_label = QLabel(name_html)
            right_layout.addWidget(info_label)

            if pet_data.get('widget'):
                friendship = getattr(pet_data.get('widget'), 'friendship', pet_data.get('friendship', 0))
                hunger = getattr(pet_data.get('widget'), 'hunger', pet_data.get('hunger', 100))
            else:
                friendship = pet_data.get('friendship', 0)
                hunger = pet_data.get('hunger', 100)

            life = pet_data.get('life', MAX_LIFE)
            hearts = "♥" * life + "♡" * (MAX_LIFE - life)
            max_hunger = get_max_hunger(pet_data.get('level', 1))

            stat_label = QLabel(
                f"<font color='#D81B60'>{hearts}</font> "
                f"<font color='#AD1457'>친밀도: {friendship}</font> | "
                f"<font color='#2E7D32'>🍗 {int(hunger)}/{max_hunger}</font>"
            )
            stat_label.setFont(QFont(PIXEL_FONT_FAMILY, 9))
            right_layout.addWidget(stat_label)

            item_layout.addWidget(icon_label)
            item_layout.addLayout(right_layout)

            self.list_layout.addWidget(item_frame)

        self.list_layout.addStretch()
        self.add_btn.setEnabled(
            self.manager.box_count() < BOX_CAPACITY or self.manager.pc_count() < PC_CAPACITY
        )

    def prompt_rename(self, pet_data):
        current = pet_data.get('nickname', '')
        new_name, ok = QInputDialog.getText(self, "이름 변경", "새 이름을 입력하세요:", text=current)
        if not ok:
            return
        pet_data['nickname'] = new_name.strip()
        if pet_data.get('widget'):
            pet_data.get('widget').update_ui()
        self.manager.save_game()
        self.refresh_list()

    def show_pet_context_menu(self, pet_data, global_pos):
        is_dead = pet_data.get('dead', False)

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: #FFF; border: 1.5px solid #FF8A80; font-family: '{PIXEL_FONT_FAMILY}', sans-serif; }}
            QMenu::item {{ padding: 6px 18px; color: #333; }}
            QMenu::item:selected {{ background-color: #FFEBEE; }}
            QMenu::item:disabled {{ color: #AAAAAA; }}
        """)

        feed_action = menu.addAction("먹이 주기")
        feed_action.setEnabled(not is_dead)  # 상자 안에 있어도(꺼내지 않았어도) 급여 가능

        pc_action = menu.addAction("오박사의 PC로 보내기")
        pc_action.setEnabled(not is_dead)

        rename_action = menu.addAction("이름 변경")
        rename_action.setEnabled(not is_dead)

        menu.addSeparator()
        delete_action = menu.addAction("삭제")

        chosen = menu.exec(global_pos)
        if chosen == feed_action:
            self.feed_from_inventory(pet_data)
        elif chosen == pc_action:
            self.send_to_pc(pet_data)
        elif chosen == rename_action:
            self.prompt_rename(pet_data)
        elif chosen == delete_action:
            self.delete_pokemon(pet_data)

    def toggle_spawn(self, pet_data):
        if pet_data.get('widget'):
            self.manager.despawn_pet(pet_data)
        else:
            if pet_data.get('hunger', 0) <= 0:
                show_info(self, "알림", "포켓몬이 배고픕니다! 먹이를 줘야합니다!")
                return
            self.manager.spawn_pet(pet_data)
            pet_data['widget'].greet_with_jumps(2)  # 상자에서 꺼내면 제자리에서 점프 두 번
        self.manager.save_game()
        self.refresh_list()

    def send_to_pc(self, pet_data):
        display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
        if not self.manager.deposit_to_pc(pet_data):
            show_info(self, "알림", "오박사의 PC가 가득 찼습니다!")
            return
        self.refresh_list()

    def feed_from_inventory(self, pet_data):
        # 인벤토리에서 지정해둔 '기본 먹이'를 사용한다 (없으면 무료 먹이로 대체되므로
        # 재고가 없어서 급여를 못 하는 경우는 없다). 상자에 들어가 있는 포켓몬도
        # 우클릭으로 급여할 수 있다 (그럴 때는 화면 이펙트만 생략).
        tier = self.manager.get_active_food_tier()
        hunger_amount, icon, name, reaction = get_food_effect(tier)
        if tier is not None:
            self.manager.food_inventory[tier] -= 1
            self.manager.clear_stale_default_food()

        max_hunger = get_max_hunger(pet_data.get('level', 1))
        pet_data['hunger'] = min(max_hunger, pet_data.get('hunger', 0) + hunger_amount)

        widget = pet_data.get('widget')
        if widget:
            widget.drop_food_effect(icon)
            widget.show_floating_text(reaction, "#4CAF50")
            widget.update_ui()

        self.manager.save_game()
        self.refresh_list()

    def add_new_pokemon(self):
        if self.manager.box_count() >= BOX_CAPACITY and self.manager.pc_count() >= PC_CAPACITY:
            show_info(self, "알림", "포켓몬 상자와 오박사의 PC가 모두 가득 찼습니다!")
            return

        dlg = PokemonAddDialog(title="새 포켓몬 추가")
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ko_name, base_name = dlg.selected_species
            new_pet = self.manager.add_pet(ko_name, base_name, dlg.nickname)
            if new_pet is not None and new_pet.get('location') == 'pc':
                show_info(self, "알림", "포켓몬 상자가 가득 차서 오박사의 PC에 보관되었습니다.")
            self.refresh_list()

    def delete_pokemon(self, pet_data):
        display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
        confirmed = ask_confirm(
            self,
            "삭제 확인",
            f"'{display_name}'을(를) 정말 삭제하시겠습니까?\n삭제하면 되돌릴 수 없습니다.",
        )
        if not confirmed:
            return

        self.manager.delete_pet(pet_data)
        self.refresh_list()


class ProfessorPCDialog(DraggableDialog):
    """오박사의 PC - 포켓몬 상자(6마리)와 별개로 최대 PC_CAPACITY마리까지 보관"""
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(420, 580)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame(self)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #EDE7F6; border: 3px solid #7E57C2; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QFrame#whiteBox {{ background-color: #FFFFFF; border: 2px solid #D1C4E9; border-radius: 14px; }}
            QPushButton {{ background-color: #FFF; color: #333; border: 1.5px solid #B39DDB; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: bold; }}
            QPushButton:disabled {{ background-color: #EEEEEE; color: #999; border-color: #DDDDDD; }}
        """)

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_dot = QLabel()
        title_dot.setPixmap(create_dot_pixmap(12, "#7E57C2"))
        title_dot.setFixedSize(12, 12)
        self.title_label = QLabel()
        self.title_label.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("border-radius: 13px; background-color: #FFF; color: #333; border: 1.5px solid #B39DDB;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(title_dot)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 8px; background-color: #EDE7F6; border-radius: 4px; margin: 2px; }
            QScrollBar::handle:vertical { background-color: #B39DDB; border-radius: 4px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background-color: #7E57C2; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.white_box = QFrame()
        self.white_box.setObjectName("whiteBox")
        self.list_layout = QVBoxLayout(self.white_box)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(8)

        scroll_area.setWidget(self.white_box)
        layout.addWidget(scroll_area)
        dialog_layout.addWidget(self.main_card)

        self.refresh_list()

    def refresh_list(self):
        self.title_label.setText(f"오박사의 PC ({self.manager.pc_count()}/{PC_CAPACITY})")

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pc_pets = [p for p in self.manager.pets_data if p.get('location', 'box') == 'pc']
        for pet_data in pc_pets:
            is_dead = pet_data.get('dead', False)

            item_frame = QFrame()
            item_frame.setFixedHeight(56)
            item_frame.setStyleSheet("background-color: #FAFAFA; border: 1.5px solid #E0E0E0; border-radius: 10px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(8, 4, 10, 4)

            base_name = pet_data['pokemon_base_name']
            img_path = os.path.join(ASSETS_DIR, f"{base_name}.gif")
            if not os.path.exists(img_path):
                img_path = os.path.join(ASSETS_DIR, "eevee.gif")

            icon_label = QLabel()
            icon_label.setFixedSize(40, 40)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("background-color: transparent;")
            if os.path.exists(img_path):
                movie = QMovie(img_path)
                movie.jumpToFrame(0)
                native_size = movie.frameRect().size()
                if native_size.width() > 0 and native_size.height() > 0:
                    scaled_size = compute_sprite_scaled_size(native_size, base_name, QSize(28, 28))
                    movie.setScaledSize(scaled_size)
                icon_label.setMovie(movie)
                movie.start()
                item_frame.movie = movie
            if is_dead:
                opacity_effect = QGraphicsOpacityEffect(icon_label)
                opacity_effect.setOpacity(0.3)
                icon_label.setGraphicsEffect(opacity_effect)
                item_frame.opacity_effect = opacity_effect

            display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
            name_html = f"<b>{display_name}</b> <font color='#777'>({pet_data['pokemon_type_ko']}) Lv.{pet_data['level']}</font>"
            if is_dead:
                name_html = f"<font color='#999'>💀 {display_name} (사망)</font>"
            info_label = QLabel(name_html)

            withdraw_btn = QPushButton("상자로 꺼내기")
            withdraw_btn.setEnabled(not is_dead and self.manager.box_count() < BOX_CAPACITY)
            withdraw_btn.clicked.connect(lambda checked, p=pet_data: self.withdraw(p))

            del_btn = QPushButton("삭제")
            del_btn.setStyleSheet("color: #D32F2F; border-color: #FFCDD2;")
            del_btn.clicked.connect(lambda checked, p=pet_data: self.delete_pokemon(p))

            item_layout.addWidget(icon_label)
            item_layout.addWidget(info_label)
            item_layout.addStretch()
            item_layout.addWidget(withdraw_btn)
            item_layout.addWidget(del_btn)

            self.list_layout.addWidget(item_frame)

        if not pc_pets:
            empty_label = QLabel("오박사의 PC가 비어있습니다.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(empty_label)

        self.list_layout.addStretch()

    def withdraw(self, pet_data):
        if not self.manager.withdraw_from_pc(pet_data):
            show_info(self, "알림", "포켓몬 상자가 가득 찼습니다!")
            return
        self.refresh_list()

    def delete_pokemon(self, pet_data):
        display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
        confirmed = ask_confirm(
            self,
            "삭제 확인",
            f"'{display_name}'을(를) 정말 삭제하시겠습니까?\n삭제하면 되돌릴 수 없습니다.",
        )
        if not confirmed:
            return
        self.manager.delete_pet(pet_data)
        self.refresh_list()


class BuyQuantityDialog(DraggableDialog):
    """상점에서 아이템을 몇 개 살지 정하는 창. +/- 버튼과 직접 숫자 입력을
    모두 지원하고, 구매/취소 버튼으로 확정한다."""
    def __init__(self, item_name, icon_pixmap, unit_price, gold):
        super().__init__()
        self.confirmed_quantity = None
        self.unit_price = unit_price
        self.max_qty = max(1, min(99, gold // unit_price)) if unit_price > 0 else 99
        self.quantity = 1

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(300, 330)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF8E1; border: 3px solid #FFB300; border-radius: 18px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QPushButton#stepBtn {{ background-color: #FFB300; color: white; border: none; border-radius: 16px; font-weight: bold; font-size: 16px; }}
            QPushButton#stepBtn:disabled {{ background-color: #E0E0E0; color: #999; }}
            QLineEdit#qtyInput {{ background-color: #FFFFFF; color: #333; border: 2px solid #FFB300; border-radius: 6px; font-weight: bold; }}
            QPushButton#confirmBtn {{ background-color: #4CAF50; color: white; border: none; border-radius: 8px; padding: 8px; font-weight: bold; }}
            QPushButton#cancelBtn {{ background-color: #CCCCCC; color: black; border: none; border-radius: 8px; padding: 8px; font-weight: bold; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedHeight(48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel(item_name)
        title.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        qty_layout = QHBoxLayout()
        qty_layout.addStretch()
        self.minus_btn = QPushButton("−")
        self.minus_btn.setObjectName("stepBtn")
        self.minus_btn.setFixedSize(34, 34)
        self.minus_btn.clicked.connect(self.decrement)
        self.qty_input = QLineEdit("1")
        self.qty_input.setObjectName("qtyInput")
        self.qty_input.setFixedSize(64, 34)
        self.qty_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_input.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        self.qty_input.editingFinished.connect(self._on_text_edited)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setObjectName("stepBtn")
        self.plus_btn.setFixedSize(34, 34)
        self.plus_btn.clicked.connect(self.increment)
        qty_layout.addWidget(self.minus_btn)
        qty_layout.addWidget(self.qty_input)
        qty_layout.addWidget(self.plus_btn)
        qty_layout.addStretch()
        layout.addLayout(qty_layout)

        self.total_label = QLabel()
        self.total_label.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_label.setStyleSheet("color: #F57F17;")
        layout.addWidget(self.total_label)

        self.hint_label = QLabel(f"최대 {self.max_qty}개까지 구매 가능")
        self.hint_label.setFont(QFont(PIXEL_FONT_FAMILY, 8))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet("color: #888;")
        layout.addWidget(self.hint_label)

        self.warning_label = QLabel("")
        self.warning_label.setFont(QFont(PIXEL_FONT_FAMILY, 8, QFont.Weight.Bold))
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warning_label.setStyleSheet("color: #D32F2F;")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        self.gold = gold
        self._refresh()

        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("구매")
        confirm_btn.setObjectName("confirmBtn")
        confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog_layout.addWidget(card)

    def _clamp(self, v):
        return max(1, min(self.max_qty, v))

    def _refresh(self):
        self.qty_input.setText(str(self.quantity))
        total = self.quantity * self.unit_price
        self.total_label.setText(f"총 {total:,}G (보유 {self.gold:,}G)")
        self.minus_btn.setEnabled(self.quantity > 1)
        self.plus_btn.setEnabled(self.quantity < self.max_qty)

    def increment(self):
        self.quantity = self._clamp(self.quantity + 1)
        self.warning_label.setText("")
        self._refresh()

    def decrement(self):
        self.quantity = self._clamp(self.quantity - 1)
        self.warning_label.setText("")
        self._refresh()

    def _on_text_edited(self):
        try:
            v = int(self.qty_input.text().strip())
        except ValueError:
            v = self.quantity

        if v > self.max_qty:
            self.warning_label.setText(f"보유 골드가 부족합니다! 최대 {self.max_qty}개까지 구매 가능합니다.")
        elif v < 1:
            self.warning_label.setText("최소 1개 이상 구매해야 합니다.")
        else:
            self.warning_label.setText("")

        self.quantity = self._clamp(v)
        self._refresh()

    def _on_confirm(self):
        self.confirmed_quantity = self.quantity
        self.accept()


class ShopDialog(DraggableDialog):
    """상점 - 골드로 먹이를 구매한다"""
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 560)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame(self)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF8E1; border: 3px solid #FFB300; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QFrame#itemBox {{ background-color: #FFFFFF; border: 2px solid #FFE082; border-radius: 12px; }}
            QPushButton#buyBtn {{ background-color: #FFD54F; color: #5D4037; border: 2px solid #F9A825; border-radius: 8px; padding: 4px 8px; font-weight: bold; font-size: 12px; }}
            QPushButton#buyBtn:hover {{ background-color: #FFCA28; }}
            QPushButton#buyBtn:disabled {{ background-color: #EEEEEE; color: #AAAAAA; border-color: #DDDDDD; }}
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ width: 8px; background-color: #FFF3CD; border-radius: 4px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background-color: #FFB300; border-radius: 4px; min-height: 24px; }}
        """)

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_dot = QLabel()
        title_dot.setPixmap(create_dot_pixmap(12, "#FFB300"))
        title_dot.setFixedSize(12, 12)
        title_label = QLabel("상점")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("border-radius: 13px; background-color: #FFF; color: #333; border: 1.5px solid #FFE082;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(title_dot)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        self.gold_label = QLabel()
        self.gold_label.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        self.gold_label.setStyleSheet("color: #F57F17;")
        layout.addWidget(self.gold_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.viewport().setStyleSheet("background-color: #FFF8E1;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #FFF8E1;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(8)

        food_header = QLabel("먹이")
        food_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        food_header.setStyleSheet("color: #F57F17;")
        scroll_layout.addWidget(food_header)

        self.food_rows = {}
        for tier in FOOD_TIER_ORDER:
            info = FOOD_TIERS[tier]
            row_frame = QFrame()
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(64)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 8, 12, 8)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(load_item_icon_pixmap(info['icon'], 30))

            text_label = QLabel(
                f"<b>{info['name']}</b><br>"
                f"<font color='#777'>{info['price']}G · 포만감 +{info['hunger']}</font>"
            )
            buy_btn = QPushButton("구매")
            buy_btn.setObjectName("buyBtn")
            buy_btn.setFixedSize(56, 36)
            buy_btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
            buy_btn.clicked.connect(lambda checked, t=tier: self.buy_food(t))

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            row_layout.addWidget(buy_btn)
            scroll_layout.addWidget(row_frame)
            self.food_rows[tier] = buy_btn

        stone_header = QLabel("진화의 돌")
        stone_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        stone_header.setStyleSheet("color: #F57F17;")
        scroll_layout.addWidget(stone_header)

        self.stone_rows = {}
        for stone_id in STONE_ORDER:
            info = STONES[stone_id]
            row_frame = QFrame()
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(64)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 8, 12, 8)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(load_item_icon_pixmap(info['icon'], 30))

            text_label = QLabel(f"<b>{info['name']}</b><br><font color='#777'>{info['price']}G</font>")
            buy_btn = QPushButton("구매")
            buy_btn.setObjectName("buyBtn")
            buy_btn.setFixedSize(56, 36)
            buy_btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
            buy_btn.clicked.connect(lambda checked, s=stone_id: self.buy_stone(s))

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            row_layout.addWidget(buy_btn)
            scroll_layout.addWidget(row_frame)
            self.stone_rows[stone_id] = buy_btn

        item_header = QLabel("아이템")
        item_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        item_header.setStyleSheet("color: #F57F17;")
        scroll_layout.addWidget(item_header)

        self.item_rows = {}
        for item_id in ITEM_ORDER:
            info = ITEMS[item_id]
            row_frame = QFrame()
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(64)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 8, 12, 8)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(load_item_icon_pixmap(info['icon'], 30))

            text_label = QLabel(f"<b>{info['name']}</b><br><font color='#777'>{info['price']}G</font>")
            buy_btn = QPushButton("구매")
            buy_btn.setObjectName("buyBtn")
            buy_btn.setFixedSize(56, 36)
            buy_btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
            buy_btn.clicked.connect(lambda checked, i=item_id: self.buy_item(i))

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            row_layout.addWidget(buy_btn)
            scroll_layout.addWidget(row_frame)
            self.item_rows[item_id] = buy_btn

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        dialog_layout.addWidget(self.main_card)

        self.refresh()

    def refresh(self):
        self.gold_label.setText(f"보유 골드: {self.manager.gold:,}G")
        for tier, btn in self.food_rows.items():
            btn.setEnabled(self.manager.gold >= FOOD_TIERS[tier]['price'])
        for stone_id, btn in self.stone_rows.items():
            btn.setEnabled(self.manager.gold >= STONES[stone_id]['price'])
        for item_id, btn in self.item_rows.items():
            btn.setEnabled(self.manager.gold >= ITEMS[item_id]['price'])

    def _open_quantity_dialog(self, name, icon_pixmap, price):
        if self.manager.gold < price:
            show_info(self, "알림", "골드가 부족합니다.")
            return None
        dlg = BuyQuantityDialog(name, icon_pixmap, price, self.manager.gold)
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.confirmed_quantity:
            return dlg.confirmed_quantity
        return None

    def buy_food(self, tier):
        info = FOOD_TIERS[tier]
        qty = self._open_quantity_dialog(info['name'], load_item_icon_pixmap(info['icon'], 44), info['price'])
        if not qty:
            return
        self.manager.gold -= info['price'] * qty
        self.manager.food_inventory[tier] = self.manager.food_inventory.get(tier, 0) + qty
        self.manager.save_game()
        show_info(self, "구매 완료", f"{info['name']} {qty}개를 구매했습니다!")
        self.refresh()

    def buy_stone(self, stone_id):
        info = STONES[stone_id]
        qty = self._open_quantity_dialog(info['name'], load_item_icon_pixmap(info['icon'], 44), info['price'])
        if not qty:
            return
        self.manager.gold -= info['price'] * qty
        self.manager.stone_inventory[stone_id] = self.manager.stone_inventory.get(stone_id, 0) + qty
        self.manager.save_game()
        show_info(self, "구매 완료", f"{info['name']} {qty}개를 구매했습니다!")
        self.refresh()

    def buy_item(self, item_id):
        info = ITEMS[item_id]
        qty = self._open_quantity_dialog(info['name'], load_item_icon_pixmap(info['icon'], 44), info['price'])
        if not qty:
            return
        self.manager.gold -= info['price'] * qty
        self.manager.item_inventory[item_id] = self.manager.item_inventory.get(item_id, 0) + qty
        self.manager.save_game()
        show_info(self, "구매 완료", f"{info['name']} {qty}개를 구매했습니다!")
        self.refresh()


def stones_that_evolve_pets(manager, stone_id):
    """이 stone_id로 진화 가능한(사망하지 않은) 소유 포켓몬 목록을 반환."""
    eligible = []
    for pet_data in manager.pets_data:
        if pet_data.get('dead', False):
            continue
        options = stones_that_evolve(pet_data['pokemon_base_name'])
        if stone_id in options:
            eligible.append(pet_data)
    return eligible


def items_eligible_pets(manager, item_id):
    """이 item_id를 사용할 수 있는 소유 포켓몬 목록을 반환.
    이상한 사탕(level_up)은 살아있는 포켓몬에게만, 부활의 약(revive)은
    사망한 포켓몬에게만 사용할 수 있다."""
    effect = ITEMS[item_id]['effect']
    if effect == 'revive':
        return [p for p in manager.pets_data if p.get('dead', False)]
    return [p for p in manager.pets_data if not p.get('dead', False)]


class PetPickerItem(QWidget):
    """StonePickerDialog에서 쓰는, 소유한 포켓몬 한 마리를 나타내는 선택 위젯."""
    selected = pyqtSignal(object)  # pet_data

    def __init__(self, pet_data):
        super().__init__()
        self.pet_data = pet_data
        base_name = pet_data['pokemon_base_name']
        display_name = pet_data.get('nickname') or pet_data.get('pokemon_type_ko', base_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(55, 55)
        img_label.setStyleSheet("background-color: #F0F0F0; border: none; border-radius: 6px;")
        img_path = os.path.join(ASSETS_DIR, f"{base_name}.gif")
        if os.path.exists(img_path):
            self.movie = QMovie(img_path)
            self.movie.jumpToFrame(0)
            native_size = self.movie.frameRect().size()
            if native_size.width() > 0 and native_size.height() > 0:
                scaled_size = compute_sprite_scaled_size(native_size, base_name, QSize(44, 44))
                self.movie.setScaledSize(scaled_size)
            img_label.setMovie(self.movie)
            self.movie.start()
        layout.addWidget(img_label)

        dead_prefix = "💀 " if pet_data.get('dead', False) else ""
        name_label = QLabel(f"{dead_prefix}{display_name}\nLv.{pet_data.get('level', 1)}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont(PIXEL_FONT_FAMILY, 7))
        name_label.setStyleSheet("color: #333; background: transparent;")
        layout.addWidget(name_label)

        self.setFixedSize(72, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QWidget { border: 2px solid #E0E0E0; border-radius: 8px; background-color: #FFFFFF; }
        """)

    def mousePressEvent(self, event):
        self.selected.emit(self.pet_data)
        super().mousePressEvent(event)


class StonePickerDialog(DraggableDialog):
    """진화의 돌을 사용할 포켓몬을 고르는 창 (돌로 진화 가능한 소유 포켓몬만 표시)."""
    def __init__(self, stone_id, targets):
        super().__init__()
        self.selected_pet = None
        info = STONES[stone_id]
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF8E1; border: 3px solid #FFB300; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(f"{info['name']}을(를) 사용할 포켓몬을 선택하세요")
        title.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background-color: #FFF8E1;")
        content = QWidget()
        content.setStyleSheet("background-color: #FFF8E1;")
        grid = QGridLayout(content)
        grid.setSpacing(8)
        for i, pet_data in enumerate(targets):
            item = PetPickerItem(pet_data)
            item.selected.connect(self._on_selected)
            row, col = divmod(i, 4)
            grid.addWidget(item, row, col)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("background-color: #CCCCCC; color: black; border: none; border-radius: 8px; padding: 8px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        dialog_layout.addWidget(card)

    def _on_selected(self, pet_data):
        self.selected_pet = pet_data
        self.accept()


class ItemTargetPickerDialog(DraggableDialog):
    """이상한 사탕/부활의 약처럼 특정 종에 묶이지 않는 범용 아이템을 사용할
    포켓몬을 고르는 창 (StonePickerDialog와 같은 톤/구조, 제목만 파라미터로 받음)."""
    def __init__(self, title_text, targets):
        super().__init__()
        self.selected_pet = None
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF8E1; border: 3px solid #FFB300; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background-color: #FFF8E1;")
        content = QWidget()
        content.setStyleSheet("background-color: #FFF8E1;")
        grid = QGridLayout(content)
        grid.setSpacing(8)
        for i, pet_data in enumerate(targets):
            item = PetPickerItem(pet_data)
            item.selected.connect(self._on_selected)
            row, col = divmod(i, 4)
            grid.addWidget(item, row, col)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("background-color: #CCCCCC; color: black; border: none; border-radius: 8px; padding: 8px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        dialog_layout.addWidget(card)

    def _on_selected(self, pet_data):
        self.selected_pet = pet_data
        self.accept()


class InventoryItemFrame(QFrame):
    """인벤토리의 먹이 한 줄. 오른쪽 클릭하면 '기본 먹이'로 지정된다.
    tier가 None이면 '무료 열매'를 의미하며 재고와 무관하게 항상 선택 가능하다."""
    def __init__(self, tier, dialog):
        super().__init__()
        self.tier = tier
        self.dialog = dialog
        self.available = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.available:
            self.dialog.set_default_food(self.tier)
        super().mousePressEvent(event)


class StoneItemFrame(QFrame):
    """인벤토리의 진화의 돌 한 줄. 왼쪽 클릭하면 이 돌을 사용할 포켓몬을 고르는
    창이 뜬다(보유 수량이 0이면 클릭해도 아무 일도 일어나지 않는다)."""
    def __init__(self, stone_id, dialog):
        super().__init__()
        self.stone_id = stone_id
        self.dialog = dialog
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dialog.use_stone(self.stone_id)
        super().mousePressEvent(event)


class GeneralItemFrame(QFrame):
    """인벤토리의 일반 아이템(이상한 사탕/부활의 약) 한 줄. 왼쪽 클릭하면
    사용할 포켓몬을 고르는 창이 뜬다(보유 수량 0이면 아무 일도 없음)."""
    def __init__(self, item_id, dialog):
        super().__init__()
        self.item_id = item_id
        self.dialog = dialog
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dialog.use_item(self.item_id)
        super().mousePressEvent(event)


class InventoryDialog(DraggableDialog):
    """인벤토리 - 보유한 먹이 재고 확인 + 기본 먹이 설정(우클릭)"""
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(380, 560)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        self.main_card = QFrame(self)
        self.main_card.setObjectName("mainCard")
        self.main_card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #E0F2F1; border: 3px solid #00897B; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QFrame#itemBox {{ background-color: #FFFFFF; border: 2px solid #B2DFDB; border-radius: 12px; }}
            QFrame#itemBoxDefault {{ background-color: #FFFFFF; border: 2px solid #00897B; border-radius: 12px; }}
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ width: 8px; background-color: #E0F2F1; border-radius: 4px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background-color: #4DB6AC; border-radius: 4px; min-height: 24px; }}
        """)

        layout = QVBoxLayout(self.main_card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_dot = QLabel()
        title_dot.setPixmap(create_dot_pixmap(12, "#00897B"))
        title_dot.setFixedSize(12, 12)
        title_label = QLabel("인벤토리")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 11, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("border-radius: 13px; background-color: #FFF; color: #333; border: 1.5px solid #B2DFDB;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(title_dot)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        hint_label = QLabel("먹이를 우클릭하면 '먹이 주기'에서 쓸 기본 먹이로 지정됩니다.\n진화의 돌·아이템을 클릭하면 사용할 포켓몬을 고를 수 있습니다.")
        hint_label.setFont(QFont(PIXEL_FONT_FAMILY, 8))
        hint_label.setStyleSheet("color: #00695C;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.viewport().setStyleSheet("background-color: #E0F2F1;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #E0F2F1;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        scroll_layout.setSpacing(8)

        food_header = QLabel("먹이")
        food_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        food_header.setStyleSheet("color: #00695C;")
        scroll_layout.addWidget(food_header)

        self.item_rows = {}
        for tier in [None] + FOOD_TIER_ORDER:
            row_frame = InventoryItemFrame(tier, self)
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(60)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 6, 12, 6)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if tier is None:
                icon_label.setText(FREE_FOOD_ICON)
                icon_label.setStyleSheet("font-size: 22px;")
            else:
                icon_label.setPixmap(load_item_icon_pixmap(FOOD_TIERS[tier]['icon'], 30))

            text_label = QLabel()

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            scroll_layout.addWidget(row_frame)
            self.item_rows[tier] = (row_frame, text_label)

        stone_header = QLabel("진화의 돌")
        stone_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        stone_header.setStyleSheet("color: #00695C;")
        scroll_layout.addWidget(stone_header)

        self.stone_rows = {}
        for stone_id in STONE_ORDER:
            info = STONES[stone_id]
            row_frame = StoneItemFrame(stone_id, self)
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(60)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 6, 12, 6)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(load_item_icon_pixmap(info['icon'], 30))

            text_label = QLabel()

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            scroll_layout.addWidget(row_frame)
            self.stone_rows[stone_id] = (row_frame, text_label)

        general_item_header = QLabel("아이템")
        general_item_header.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        general_item_header.setStyleSheet("color: #00695C;")
        scroll_layout.addWidget(general_item_header)

        self.general_item_rows = {}
        for item_id in ITEM_ORDER:
            info = ITEMS[item_id]
            row_frame = GeneralItemFrame(item_id, self)
            row_frame.setObjectName("itemBox")
            row_frame.setFixedHeight(60)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 6, 12, 6)

            icon_label = QLabel()
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(load_item_icon_pixmap(info['icon'], 30))

            text_label = QLabel()

            row_layout.addWidget(icon_label)
            row_layout.addWidget(text_label)
            row_layout.addStretch()
            scroll_layout.addWidget(row_frame)
            self.general_item_rows[item_id] = (row_frame, text_label)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        dialog_layout.addWidget(self.main_card)

        self.refresh()

    def refresh(self):
        self.manager.clear_stale_default_food()
        default_tier = self.manager.default_food
        for tier, (row_frame, text_label) in self.item_rows.items():
            if tier is None:
                name, count_text, available = FREE_FOOD_NAME, "무제한", True
            else:
                count = self.manager.food_inventory.get(tier, 0)
                name, count_text, available = FOOD_TIERS[tier]['name'], f"보유 {count}개", count > 0

            row_frame.available = available
            is_default = (tier == default_tier)
            tag = " <font color='#00897B'>(기본 먹이)</font>" if is_default else ""
            text_label.setText(f"<b>{name}</b>{tag}<br><font color='#777'>{count_text}</font>")
            row_frame.setObjectName("itemBoxDefault" if is_default else "itemBox")
            row_frame.setStyleSheet(row_frame.styleSheet())  # objectName 변경 반영을 위해 스타일 재적용

            opacity_effect = getattr(row_frame, '_opacity_effect', None)
            if opacity_effect is None:
                opacity_effect = QGraphicsOpacityEffect(row_frame)
                row_frame.setGraphicsEffect(opacity_effect)
                row_frame._opacity_effect = opacity_effect
            opacity_effect.setOpacity(1.0 if available else 0.4)
            row_frame.setCursor(Qt.CursorShape.PointingHandCursor if available else Qt.CursorShape.ArrowCursor)

        for stone_id, (row_frame, text_label) in self.stone_rows.items():
            info = STONES[stone_id]
            count = self.manager.stone_inventory.get(stone_id, 0)
            text_label.setText(f"<b>{info['name']}</b><br><font color='#777'>보유 {count}개</font>")

        for item_id, (row_frame, text_label) in self.general_item_rows.items():
            info = ITEMS[item_id]
            count = self.manager.item_inventory.get(item_id, 0)
            text_label.setText(f"<b>{info['name']}</b><br><font color='#777'>보유 {count}개</font>")

    def set_default_food(self, tier):
        self.manager.default_food = tier
        self.manager.save_game()
        self.refresh()

    def use_stone(self, stone_id):
        count = self.manager.stone_inventory.get(stone_id, 0)
        if count <= 0:
            show_info(self, "알림", "보유한 돌이 없습니다. 상점에서 먼저 구매하세요.")
            return

        targets = stones_that_evolve_pets(self.manager, stone_id)
        if not targets:
            show_info(self, "알림", "이 돌을 사용할 수 있는 포켓몬이 없습니다.")
            return

        dlg = StonePickerDialog(stone_id, targets)
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_pet is not None:
            pet_data = dlg.selected_pet
            new_base = stones_that_evolve(pet_data['pokemon_base_name'])[stone_id]
            new_ko = apply_evolution(pet_data, new_base, floating=True)
            if not pet_data.get('widget'):
                show_info(self, "진화!", f"{new_ko}(으)로 진화했습니다!")
            self.manager.stone_inventory[stone_id] = count - 1
            self.manager.save_game()
        self.refresh()

    def use_item(self, item_id):
        count = self.manager.item_inventory.get(item_id, 0)
        if count <= 0:
            show_info(self, "알림", "보유한 아이템이 없습니다. 상점에서 먼저 구매하세요.")
            return

        info = ITEMS[item_id]
        targets = items_eligible_pets(self.manager, item_id)
        if not targets:
            msg = "사망한 포켓몬이 없습니다." if info['effect'] == 'revive' else "사용할 수 있는 포켓몬이 없습니다."
            show_info(self, "알림", msg)
            return

        dlg = ItemTargetPickerDialog(f"{info['name']}을(를) 사용할 포켓몬을 선택하세요", targets)
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_pet is not None:
            pet_data = dlg.selected_pet
            if info['effect'] == 'level_up':
                apply_rare_candy(pet_data)
                if not pet_data.get('widget'):
                    show_info(self, "레벨업!", f"Lv.{pet_data['level']}(으)로 레벨업했습니다!")
            elif info['effect'] == 'revive':
                apply_revive(pet_data)
                display_name = pet_data.get('nickname') or pet_data.get('pokemon_type_ko', '')
                show_info(self, "부활!", f"{display_name}(이)가 부활했습니다!")
            self.manager.item_inventory[item_id] = count - 1
            self.manager.save_game()
        self.refresh()


class HubMenuDialog(DraggableDialog):
    """포켓볼 아이콘 클릭 시 뜨는 허브 메뉴 - 여기서 포켓몬 상자/오박사의 PC/상점/인벤토리로 들어간다"""
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(280, 440)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("mainCard")
        card.setStyleSheet(f"""
            QFrame#mainCard {{ background-color: #FFF0F2; border: 3px solid #FF5252; border-radius: 20px; }}
            QLabel {{ font-family: '{PIXEL_FONT_FAMILY}', sans-serif; color: #333; }}
            QPushButton {{ background-color: #FFF; color: #333; border: 1.5px solid #FF8A80; border-radius: 10px; padding: 0 10px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #FFEBEE; }}
            QPushButton#quitBtn {{ background-color: #FFCDD2; color: #B71C1C; border-color: #EF9A9A; }}
            QPushButton#quitBtn:hover {{ background-color: #FFAAB4; }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_dot = QLabel()
        title_dot.setPixmap(create_dot_pixmap(12, "#FF5252"))
        title_dot.setFixedSize(12, 12)
        title_label = QLabel("메뉴")
        title_label.setFont(QFont(PIXEL_FONT_FAMILY, 12, QFont.Weight.Bold))
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("border-radius: 13px; background-color: #FFF; color: #333; border: 1.5px solid #FF8A80; padding: 0;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(title_dot)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        box_btn = QPushButton("포켓몬 상자")
        box_btn.setFixedHeight(48)
        box_btn.clicked.connect(self.open_box)

        pc_btn = QPushButton("오박사의 PC")
        pc_btn.setFixedHeight(48)
        pc_btn.clicked.connect(self.open_pc)

        shop_btn = QPushButton("상점")
        shop_btn.setFixedHeight(48)
        shop_btn.clicked.connect(self.open_shop)

        inv_btn = QPushButton("인벤토리")
        inv_btn.setFixedHeight(48)
        inv_btn.clicked.connect(self.open_inventory)

        for btn in (box_btn, pc_btn, shop_btn, inv_btn):
            layout.addWidget(btn)
        layout.addStretch()

        quit_btn = QPushButton(" 프로그램 종료")
        quit_btn.setObjectName("quitBtn")
        quit_btn.setIcon(create_dot_icon(14, "#B71C1C"))
        quit_btn.setIconSize(QSize(14, 14))
        quit_btn.setFixedHeight(40)
        quit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(quit_btn)

        dialog_layout.addWidget(card)

    def _center_and_exec(self, dlg):
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
        dlg.exec()

    def open_box(self):
        self._center_and_exec(PokemonManagerDialog(self.manager))

    def open_pc(self):
        self._center_and_exec(ProfessorPCDialog(self.manager))

    def open_shop(self):
        self._center_and_exec(ShopDialog(self.manager))

    def open_inventory(self):
        self._center_and_exec(InventoryDialog(self.manager))