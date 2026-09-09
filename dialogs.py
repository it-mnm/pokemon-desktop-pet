# -*- coding: utf-8 -*-
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                             QPushButton, QFrame, QLineEdit,
                             QApplication, QScrollArea, QWidget, QSpacerItem, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QMovie, QPixmap, QCursor, QPainter, QColor, QIcon
from utils import ASSETS_DIR, PIXEL_FONT_FAMILY, get_sprite_content_size
from pet import MAX_LIFE


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


class ThemedMessageDialog(QDialog):
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


class StartScreenDialog(QDialog):
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


class PokemonAddDialog(QDialog):
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

        # 포켓몬 선택 위젯 생성
        self.eevee_selector = PokemonSelector("이브이", "eevee")
        self.eevee_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))
        self.eevee_selector.select()

        self.mimi_selector = PokemonSelector("따라큐", "mimikyu")
        self.mimi_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))

        self.squirtle_selector = PokemonSelector("꼬북이", "squirtle")
        self.squirtle_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))

        self.riolu_selector = PokemonSelector("리오르", "riolu")
        self.riolu_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))

        self.gible_selector = PokemonSelector("이어롤", "gible")
        self.gible_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))

        self.ralts_selector = PokemonSelector("랄토스", "ralts")
        self.ralts_selector.selected.connect(lambda ko, base: self.select_spec(ko, base))

        # 그리드에 배치 (3열)
        selectors = [
            self.eevee_selector, self.mimi_selector, self.squirtle_selector,
            self.riolu_selector, self.gible_selector, self.ralts_selector
        ]
        for i, selector in enumerate(selectors):
            row = i // 3
            col = i % 3
            species_layout.addWidget(selector, row, col)

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
        self.eevee_selector.deselect()
        self.mimi_selector.deselect()
        self.squirtle_selector.deselect()
        self.riolu_selector.deselect()
        self.gible_selector.deselect()
        self.ralts_selector.deselect()

        if base_name == "eevee":
            self.eevee_selector.select()
        elif base_name == "mimikyu":
            self.mimi_selector.select()
        elif base_name == "squirtle":
            self.squirtle_selector.select()
        elif base_name == "riolu":
            self.riolu_selector.select()
        elif base_name == "gible":
            self.gible_selector.select()
        elif base_name == "ralts":
            self.ralts_selector.select()

    def on_confirm(self):
        self.nickname = self.name_input.text().strip()
        self.accept()


class PokemonManagerDialog(QDialog):
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
        self.title_label = QLabel(f"포켓몬 상자 ({len(self.manager.pets_data)}/6)")
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

        quit_btn = QPushButton(" 프로그램 종료")
        quit_btn.setIcon(create_dot_icon(14, "#B71C1C"))
        quit_btn.setIconSize(QSize(14, 14))
        quit_btn.setFixedHeight(34)
        quit_btn.setStyleSheet("background-color: #FFCDD2; color: #B71C1C; border-color: #EF9A9A;")
        quit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(quit_btn)

        dialog_layout.addWidget(self.main_card)
        self.refresh_list()

    def refresh_list(self):
        self.title_label.setText(f"포켓몬 상자 ({len(self.manager.pets_data)}/6)")

        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            return

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for pet_data in self.manager.pets_data:
            is_dead = pet_data.get('dead', False)
            is_out = (not pet_data.get('stored', False)) and not is_dead

            item_frame = QFrame()
            item_frame.setFixedHeight(95)
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

            # 첫 번째 줄: 이름, 레벨, 상호작용 버튼
            top_row = QHBoxLayout()
            display_name = pet_data['nickname'] if pet_data['nickname'] else pet_data['pokemon_type_ko']
            name_html = f"<b>{display_name}</b> <font color='#777'>({pet_data['pokemon_type_ko']}) Lv.{pet_data['level']}</font>"
            if is_dead:
                name_html = f"<font color='#999'>💀 {display_name} (사망)</font>"
            info_label = QLabel(name_html)

            spawn_btn = QPushButton("집어넣기" if pet_data.get('widget') else "꺼내기")
            spawn_btn.setEnabled(not is_dead)
            spawn_btn.clicked.connect(lambda checked, p=pet_data: self.toggle_spawn(p))

            del_btn = QPushButton("삭제")
            del_btn.setStyleSheet("color: #D32F2F; border-color: #FFCDD2;")
            del_btn.clicked.connect(lambda checked, p=pet_data: self.delete_pokemon(p))

            top_row.addWidget(info_label)
            top_row.addStretch()
            top_row.addWidget(spawn_btn)
            top_row.addWidget(del_btn)
            right_layout.addLayout(top_row)

            # 두 번째 줄: 친밀도, 포만감, 목숨(하트)
            stat_row = QHBoxLayout()
            if pet_data.get('widget'):
                friendship = getattr(pet_data.get('widget'), 'friendship', pet_data.get('friendship', 0))
                hunger = getattr(pet_data.get('widget'), 'hunger', pet_data.get('hunger', 100))
            else:
                friendship = pet_data.get('friendship', 0)
                hunger = pet_data.get('hunger', 100)

            life = pet_data.get('life', MAX_LIFE)
            hearts = "♥" * life + "♡" * (MAX_LIFE - life)

            stat_label = QLabel(
                f"<font color='#D81B60'>{hearts}</font> "
                f"<font color='#AD1457'>친밀도: {friendship}</font> | "
                f"<font color='#2E7D32'>🍗 포만감: {int(hunger)}</font>"
            )
            stat_label.setFont(QFont(PIXEL_FONT_FAMILY, 9))
            stat_row.addWidget(stat_label)
            stat_row.addStretch()
            right_layout.addLayout(stat_row)

            # 세 번째 줄: 이름 변경
            bottom_row = QHBoxLayout()
            name_input = QLineEdit()
            name_input.setPlaceholderText("새 이름 입력")
            name_input.setText(pet_data['nickname'])
            name_input.setEnabled(not is_dead)

            rename_btn = QPushButton("이름변경")
            rename_btn.setStyleSheet("background-color: #E3F2FD; color: #0D47A1; border-color: #90CAF9;")
            rename_btn.setEnabled(not is_dead)
            rename_btn.clicked.connect(lambda checked, p=pet_data, ni=name_input: self.change_name(p, ni))

            bottom_row.addWidget(name_input)
            bottom_row.addWidget(rename_btn)
            right_layout.addLayout(bottom_row)

            item_layout.addWidget(icon_label)
            item_layout.addLayout(right_layout)

            self.list_layout.addWidget(item_frame)

        self.list_layout.addStretch()
        self.add_btn.setEnabled(len(self.manager.pets_data) < 6)

    def change_name(self, pet_data, name_input):
        new_name = name_input.text().strip()
        pet_data['nickname'] = new_name
        if pet_data.get('widget'):
            pet_data.get('widget').update_ui()
        self.refresh_list()

    def toggle_spawn(self, pet_data):
        if pet_data.get('widget'):
            self.manager.despawn_pet(pet_data)
        else:
            self.manager.spawn_pet(pet_data)
            pet_data['widget'].greet_with_jumps(2)  # 상자에서 꺼내면 제자리에서 점프 두 번
        self.manager.save_game()
        self.refresh_list()

    def add_new_pokemon(self):
        if len(self.manager.pets_data) < 6:
            dlg = PokemonAddDialog(title="새 포켓몬 추가")
            screen = QApplication.primaryScreen().geometry()
            dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                ko_name, base_name = dlg.selected_species
                self.manager.add_pet(ko_name, base_name, dlg.nickname)
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