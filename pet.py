import os
import random
from PyQt6.QtWidgets import QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QApplication, QDialog, QPushButton
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QMovie, QPixmap
from utils import ASSETS_DIR, FoodItem, PIXEL_FONT_FAMILY, DraggableDialog
from pokemon_data import POKEMON_DEX, get_ko_name

MAX_LIFE = 5
BOX_CAPACITY = 6
PC_CAPACITY = 50

FREE_FOOD_ICON = "🍎"  # 무료 먹이는 항상 이 아이콘 하나로 통일
FREE_FOOD_HUNGER = 8   # 무료 먹이 포만감 회복량 (유료 최하위 등급보다도 낮게)
FREE_FOOD_NAME = "무료 열매"
FREE_FOOD_REACTION = "😊"  # 무료 먹이를 먹였을 때 뜨는 반응 이모티콘 (웃음)

FOOD_TIERS = {
    "basic":   {"name": "오랑열매", "price": 10, "hunger": 15, "icon": "oran-berry.png", "reaction": "😀"},
    "good":    {"name": "기주열매", "price": 30, "hunger": 35, "icon": "sitrus-berry.png", "reaction": "😋"},
    "premium": {"name": "기묘열매", "price": 80, "hunger": 70, "icon": "enigma-berry.png", "reaction": "😍"},
}
FOOD_TIER_ORDER = ["premium", "good", "basic"]  # 먹이주기 시 가장 좋은 등급부터 소모


def get_food_effect(tier):
    """tier가 None이면 무료 먹이, 아니면 FOOD_TIERS[tier] 기준으로
    (포만감 회복량, 아이콘, 이름, 반응 이모티콘)을 반환한다."""
    if tier is None:
        return FREE_FOOD_HUNGER, FREE_FOOD_ICON, FREE_FOOD_NAME, FREE_FOOD_REACTION
    info = FOOD_TIERS[tier]
    return info['hunger'], info['icon'], info['name'], info['reaction']


def get_max_hunger(level):
    """레벨이 오를수록 포만감 총량(최대치)이 조금씩 늘어난다."""
    return 100 + (max(1, level) - 1) * 5


def get_hunger_decay_amount(level):
    """레벨이 오를수록 포만감이 더 빨리(한 틱에 더 많이) 줄어든다.
    (레벨 8마다 +1이던 것을 15마다 +1로 완화 — 예전엔 고레벨에서 너무 빨리
    배고파진다는 피드백이 있었다.)"""
    return 1 + (max(1, level) - 1) // 15


def apply_evolution(pet_data, new_base_name, floating=True):
    """진화를 pet_data에 실제로 적용한다. 레벨 기반/돌 기반 진화 모두 이 함수로
    귀결된다. 스폰되어 있으면(위젯 존재) 스프라이트/크기도 즉시 갱신하고,
    보관 중(상자/PC)이면 다음에 꺼낼 때 DesktopPet.__init__이 바뀐
    pokemon_base_name을 기준으로 알아서 정상 로드된다."""
    new_ko = get_ko_name(new_base_name)
    pet_data['pokemon_base_name'] = new_base_name
    pet_data['pokemon_type_ko'] = new_ko
    widget = pet_data.get('widget')
    if widget is not None:
        widget.adjust_pet_size()
        widget.update_pokemon_movie()
        if floating:
            widget.show_floating_text(f"✨ {new_ko}(으)로 진화! ✨", "#00BFFF")
    return new_ko


def check_evolution_for(pet_data):
    """POKEMON_DEX 테이블을 읽어 레벨/분기 진화를 판정한다. 스폰 여부와
    무관하게(상자/PC에 있는 포켓몬에게 이상한 사탕을 써도 진화가 정상 발동해야
    하므로) pet_data만으로 동작한다. 돌 진화(method == 'stone')는 여기서
    패시브로 체크하지 않고, 인벤토리에서 돌을 사용하는 액션에서만
    apply_evolution으로 직접 적용된다."""
    base_name = pet_data['pokemon_base_name']
    level = pet_data['level']
    pokemon_ko_name = pet_data.get('nickname') or pet_data['pokemon_type_ko']

    entry = POKEMON_DEX.get(base_name)
    if not entry:
        return
    method = entry.get('method')

    if method == 'level' and level >= entry['level']:
        apply_evolution(pet_data, entry['evolves_to'])

    elif method == 'branch' and level >= entry.get('branch_level', 9999) \
            and not pet_data.get('is_evolved', False):
        dlg = EvolutionDialog(base_name, pokemon_ko_name, options=entry['branch_options'])
        screen = QApplication.primaryScreen().geometry()
        dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)

        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_evolution:
            new_base, _ = dlg.selected_evolution
            apply_evolution(pet_data, new_base)

        # 어느 쪽이든 진화 완료 플래그 설정 (취소해도 다시는 안 뜸)
        pet_data['is_evolved'] = True


def apply_rare_candy(pet_data):
    """이상한 사탕: 친밀도(경험치)와 무관하게 레벨을 무조건 1 올린다.
    그 결과로 진화 조건을 충족하면 그 자리에서 진화도 함께 판정한다."""
    pet_data['level'] = pet_data.get('level', 1) + 1
    check_evolution_for(pet_data)
    widget = pet_data.get('widget')
    if widget is not None:
        widget.update_ui()
        widget.show_floating_text("🍬 레벨업!", "#FFD700")


def apply_revive(pet_data):
    """부활의 약: 사망한 포켓몬을 목숨 5(가득 찬 상태)로 되살린다."""
    pet_data['dead'] = False
    pet_data['life'] = MAX_LIFE
    widget = pet_data.get('widget')
    if widget is not None:
        widget.update_ui()


class EvolutionDialog(DraggableDialog):
    """포켓몬 진화 선택 다이얼로그 (전체 진화체 표시 및 스크롤 지원)"""
    def __init__(self, current_base_name, pokemon_ko_name="이브이", options=None):
        super().__init__()
        self.selected_evolution = None
        self.setWindowTitle("포켓몬 진화!")
        # 항상 맨 위에 뜨도록: 이 창은 포켓몬 상자 등이 이미 열려있는 상태에서
        # 레벨업 중에 갑자기 뜰 수 있는데, 이 플래그가 없으면 상자 창(항상 위)에
        # 가려져서 선택을 못 하는 문제가 있었다.
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        evolutions = options if options is not None else []
        btn_width = 100
        dialog_width = max(320, len(evolutions) * (btn_width + 12) + 40)
        self.setFixedSize(dialog_width, 220)
        self.setStyleSheet("background-color: #FFF0F5; border-radius: 10px;")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        main_layout = QVBoxLayout(self)

        label = QLabel(f"{pokemon_ko_name}(이)가 진화할 수 있습니다!\n원하는 진화 형태를 선택하세요:", self)
        label.setStyleSheet("color: #222222;")
        label.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(label)

        # 선택지들을 한 줄로 나란히 배치 (창 폭은 위에서 개수에 맞춰 이미 계산됨)
        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        for base_name, ko_name in evolutions:
            btn = QPushButton(ko_name, self)
            btn.setFixedWidth(btn_width)
            btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton { background-color: #FF69B4; color: white; border-radius: 5px; padding: 8px; }
                QPushButton:hover { background-color: #FF1493; }
            """)
            btn.clicked.connect(lambda checked, b=base_name, k=ko_name: self.select_evo(b, k))
            row_layout.addWidget(btn)
        main_layout.addLayout(row_layout)

        # 취소 버튼 추가
        button_layout = QVBoxLayout()
        cancel_btn = QPushButton(f"{pokemon_ko_name}(으)로 남기", self)
        cancel_btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #CCCCCC; color: black; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #AAAAAA; }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def select_evo(self, base_name, ko_name):
        self.selected_evolution = (base_name, ko_name)
        self.accept()


class DesktopPet(QWidget):
    """데스크톱 펫 본체"""
    def __init__(self, pet_data, manager):
        super().__init__()
        self.pet_data = pet_data
        self.manager = manager
        self.pet_data['widget'] = self

        # 데이터 연결 (없으면 기본값 설정)
        if 'friendship' not in self.pet_data:
            self.pet_data['friendship'] = 0
        if 'hunger' not in self.pet_data:
            self.pet_data['hunger'] = 100
        if 'level' not in self.pet_data:
            self.pet_data['level'] = 1
        if 'is_evolved' not in self.pet_data:
            self.pet_data['is_evolved'] = False
        if 'life' not in self.pet_data:
            self.pet_data['life'] = MAX_LIFE
        if 'dead' not in self.pet_data:
            self.pet_data['dead'] = False
        if 'stored' not in self.pet_data:
            self.pet_data['stored'] = False

        self.is_dragging = False
        self.has_moved = False
        self.is_reacting = False
        self.direction = 1  # 1: 오른쪽, -1: 왼쪽

        self.state = 0  # 0: 걷기, 1: 멈춤, 2: 점프/낙하 중
        self.drag_start_y = 0  # 드래그 시작 높이
        self.drag_end_y = 0  # 드래그 종료(드롭) 높이
        self.is_user_dragging = False  # 사용자 드래그 여부 구분

        self.jump_vy = 0.0
        self.gravity = 0.8
        self.pending_greeting_jumps = 0  # 상자에서 꺼낼 때 제자리 환영 점프 남은 횟수
        self.dash_ticks_remaining = 0  # 포켓몬 상호작용으로 질주 중인 남은 틱 수(100ms 단위)

        self.initUI()
        self.initPhysics()
        self.update_pokemon_movie()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.window_width, self.window_height = 160, 120

        primary_avail = QApplication.primaryScreen().availableGeometry()
        spawn_x = random.randint(
            primary_avail.x(),
            max(primary_avail.x(), primary_avail.x() + primary_avail.width() - self.window_width - 100)
        )
        spawn_y = primary_avail.y() + primary_avail.height() - self.window_height
        self.setGeometry(spawn_x, spawn_y, self.window_width, self.window_height)

        # 지금 실제로 놓인 모니터 기준으로 바닥/좌우 경계를 계산해둔다
        self.update_screen_bounds()

        # 긴 문구("LEVEL UP! +50G", "에스퍼(으)로 진화!" 등)도 잘리지 않도록
        # 창 폭(160)에 거의 맞춰 넓게 잡고 줄바꿈을 허용한다. 예전에는 100px
        # 고정 폭이라 텍스트가 박스보다 길면 앞부분이 그대로 잘려 보였다.
        self.emoticon_label = QLabel(self)
        self.emoticon_label.setGeometry(5, 12, 150, 32)
        self.emoticon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emoticon_label.setWordWrap(True)
        self.emoticon_label.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        self.emoticon_label.hide()

        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adjust_pet_size()

        self.movie = QMovie(self)
        self.movie.frameChanged.connect(self.on_frame_changed)

        # 닉네임이 길면 "Lv.5 xxxx" 표시가 잘리던 문제 — 예전엔 이 컨테이너가
        # 70px밖에 안 돼서 조금만 길어도 잘렸다. 창(160px) 안에서 최대한
        # 넓게(130px) 잡고 폰트도 살짝 줄인다.
        self.ui_widget = QWidget(self)
        self.ui_widget.setGeometry(15, 90, 130, 35)
        ui_layout = QVBoxLayout(self.ui_widget)
        ui_layout.setContentsMargins(0, 2, 0, 0)
        ui_layout.setSpacing(0)

        # 레벨/이름 텍스트 중앙 정렬 및 "Lv.1 이브이" 순서 적용
        self.level_label = QLabel()
        self.level_label.setFont(QFont(PIXEL_FONT_FAMILY, 6, QFont.Weight.Bold))
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_label.setStyleSheet("color: black;")
        self.level_label.setFixedHeight(10)

        # 친밀도 게이지바 (분홍색)
        self.bar = QProgressBar()
        self.bar.setMaximum(100)
        self.bar.setFixedHeight(5)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar { background-color: #E0E0E0; border-radius: 2px; margin: 0px; padding: 0px; }
            QProgressBar::chunk { background-color: #FF69B4; border-radius: 2px; }
        """)

        # 포만감 게이지바 (주황색)
        self.satiety_bar = QProgressBar()
        self.satiety_bar.setMaximum(100)
        self.satiety_bar.setFixedHeight(5)
        self.satiety_bar.setTextVisible(False)
        self.satiety_bar.setStyleSheet("""
            QProgressBar { background-color: #E0E0E0; border-radius: 2px; margin: 0px; padding: 0px; }
            QProgressBar::chunk { background-color: #FFA500; border-radius: 2px; }
        """)

        ui_layout.addWidget(self.level_label)
        ui_layout.addWidget(self.bar)
        ui_layout.addWidget(self.satiety_bar)

        self.update_ui()
        self.show()

    def update_screen_bounds(self):
        """현재 위젯이 걸쳐 있는 모니터를 기준으로 바닥(floor_y)과 좌우 이동
        경계를 다시 계산한다. 모니터마다 해상도/작업표시줄 높이가 달라서,
        스폰 시 한 번만 계산해두면 다른 모니터로 옮겼을 때 작업표시줄 아래로
        반쯤 잠기거나 화면 경계에서 계속 튕기며 끼는 문제가 생긴다."""
        screen = self.screen() or QApplication.primaryScreen()
        avail = screen.availableGeometry()
        self.floor_y = avail.y() + avail.height() - self.window_height

        # 좌우 이동 범위는 모니터 하나가 아니라 가상 데스크톱 전체(연결된
        # 모니터를 모두 합친 영역)로 잡아서, 듀얼모니터 사이를 걸어서
        # 넘어갈 수 있게 한다.
        virt = screen.virtualGeometry()
        self.left_bound = virt.x()
        self.right_bound = virt.x() + virt.width() - self.window_width

    def adjust_pet_size(self):
        base_name = self.pet_data.get('pokemon_base_name', 'eevee')
        if base_name == "mimikyu":
            self.pet_label.setGeometry(30, 20, 100, 80)
        elif base_name in ["squirtle", "wartortle", "blastoise"]:
            # 꼬북이 계열은 더 작게 표시
            self.pet_label.setGeometry(50, 45, 40, 40)
        elif base_name == "gible":
            # 이어롤: 세로로 긴 형태, 가운데 정렬 (원래 크기로 복원 — 실제로
            # 해상도가 깨져 보였던 건 이어롭(gabite)이었음)
            self.pet_label.setGeometry(65, 40, 31, 44)
        elif base_name == "gabite":
            # 이어롭: 원본 비율 약 0.85(53×62)로 이어롤보다 훨씬 통통한 체형.
            # 전용 박스로 크게 표시한다.
            self.pet_label.setGeometry(48, 30, 64, 62)
        else:
            self.pet_label.setGeometry(50, 40, 60, 50)

    def on_frame_changed(self, frame_number):
        pixmap = self.movie.currentPixmap()
        if not pixmap.isNull():
            if self.direction > 0:
                img = pixmap.toImage().mirrored(True, False)
                self.pet_label.setPixmap(QPixmap.fromImage(img))
            else:
                self.pet_label.setPixmap(pixmap)

    def add_exp(self, amount):
        self.pet_data['friendship'] += amount
        self.pet_data['friendship'] = max(0, self.pet_data['friendship'])  # 친밀도 0 이하 방지

        if self.pet_data['friendship'] >= 100:
            self.pet_data['level'] += 1
            self.pet_data['friendship'] -= 100
            gold_bonus = self.pet_data['level'] * 10
            self.manager.gold += gold_bonus
            self.show_floating_text(f"🎉 LEVEL UP! +{gold_bonus}G 🎉", "#FFD700")
            self.check_evolution()
            self.manager.save_game()  # 레벨업 후 자동 저장
        elif amount < 0:
            self.show_floating_text("아야!", "#D32F2F")
        self.update_ui()

    def check_evolution(self):
        check_evolution_for(self.pet_data)

    def show_floating_text(self, text, color="#FF4081"):
        self.is_reacting = True
        self.emoticon_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.emoticon_label.setText(text)
        self.emoticon_label.show()
        QTimer.singleShot(800, self.clear_reaction)

    def drop_food_effect(self, icon):
        """포켓몬 상자의 '먹이 주기'처럼 클릭 위치가 없는 곳에서 급여할 때,
        위젯 가운데에서 떨어지는 먹이 이펙트를 보여준다."""
        from PyQt6.QtCore import QPoint
        FoodItem(self, QPoint(self.width() // 2, self.height() // 2), icon=icon)

    def update_ui(self):
        display_name = self.pet_data['nickname'] or self.pet_data['pokemon_type_ko']
        # 텍스트 순서: "Lv.1 이브이" 형태로 설정
        self.level_label.setText(f"Lv.{self.pet_data['level']} {display_name}")
        self.bar.setValue(self.pet_data['friendship'])
        self.satiety_bar.setMaximum(get_max_hunger(self.pet_data['level']))
        self.satiety_bar.setValue(int(self.pet_data['hunger']))

    def update_pokemon_movie(self):
        base_name = self.pet_data['pokemon_base_name']
        target_file = os.path.join(ASSETS_DIR, f"{base_name}.gif")
        if not os.path.exists(target_file):
            target_file = os.path.join(ASSETS_DIR, "eevee.gif")

        if self.movie.fileName() != target_file and os.path.exists(target_file):
            self.movie.stop()
            self.movie.setFileName(target_file)

            # QMovie는 파일을 바꿔도 이전에 setScaledSize()로 지정했던 스케일 값이
            # 그대로 남아 있어서, 이 상태로 바로 frameRect()를 읽으면 새 파일의
            # 진짜 원본 크기가 아니라 "이전 포켓몬 기준으로 스케일된 크기"가
            # 나온다 (진화 직후 포켓몬이 진화 전 비율로 찌그러져 보이던 원인).
            # 스케일을 초기화하고 한 번 start/stop을 거쳐야 새 파일의 첫 프레임이
            # 제대로 디코딩되어 frameRect()가 정확한 원본 크기를 돌려준다.
            self.movie.setScaledSize(QSize())
            self.movie.start()
            self.movie.stop()

            # GIF 원본 크기 확인
            self.movie.jumpToFrame(0)
            original_size = self.movie.frameRect().size()

            # 포켓몬 표시 크기 가져오기
            geometry = self.pet_label.geometry()
            display_width = geometry.width()
            display_height = geometry.height()

            # 원본이 설정 크기보다 작으면 원본 크기 그대로 사용, 크면 설정 크기로 스케일
            if original_size.width() > 0 and original_size.height() > 0:
                if original_size.width() <= display_width and original_size.height() <= display_height:
                    # 원본이 작으면 원본 크기 그대로 사용 (품질 유지)
                    self.movie.setScaledSize(original_size)
                else:
                    # 원본이 크면 비율을 유지한 채 설정된 크기 안에 맞춰 축소
                    # (가로/세로를 각각 display_width/height로 강제로 늘리면 비율이 깨져
                    #  이어롤처럼 세로로 긴 포켓몬이 납작하게 찌그러져 보인다)
                    scaled_size = original_size.scaled(
                        QSize(display_width, display_height), Qt.AspectRatioMode.KeepAspectRatio
                    )
                    self.movie.setScaledSize(scaled_size)

            self.movie.start()

    def initPhysics(self):
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.auto_walk)
        self.move_timer.start(100)

        self.gravity_timer = QTimer(self)
        self.gravity_timer.timeout.connect(self.apply_physics)

        self.behavior_timer = QTimer(self)
        self.behavior_timer.timeout.connect(self.decide_random_behavior)
        self.behavior_timer.start(3000)

        self.satiety_timer = QTimer(self)
        self.satiety_timer.timeout.connect(self.decrease_satiety)
        self.satiety_timer.start(15000)  # 15초마다 포만감 감소 (예전 10초는 너무 빨리 배고파진다는 피드백으로 완화)

        self.friendship_timer = QTimer(self)
        self.friendship_timer.timeout.connect(self.passive_friendship_gain)
        self.friendship_timer.start(15000)  # 꺼내놓은 동안 15초마다 친밀도 자동 상승

        self.gold_timer = QTimer(self)
        self.gold_timer.timeout.connect(self.passive_gold_gain)
        self.gold_timer.start(15000)  # 꺼내놓은 동안 15초마다 일정 확률로 골드 획득

        self.interaction_timer = QTimer(self)
        self.interaction_timer.timeout.connect(self.check_pokemon_interaction)
        self.interaction_timer.start(4000)  # 4초마다 근처 포켓몬과 상호작용할지 확인

    def decrease_satiety(self):
        if 'hunger' not in self.pet_data:
            self.pet_data['hunger'] = 100
        if 'stored' not in self.pet_data:
            self.pet_data['stored'] = False
        if 'life' not in self.pet_data:
            self.pet_data['life'] = MAX_LIFE
        if 'dead' not in self.pet_data:
            self.pet_data['dead'] = False

        # 이미 죽었거나 상자에 들어간(=이 위젯은 곧 정리될) 포켓몬은 처리하지 않는다.
        # 상자 안 포켓몬의 포만감 회복은 위젯이 살아있는지와 무관하게
        # PokemonManager의 전역 타이머(recover_stored_hunger)가 담당한다.
        if self.pet_data['dead'] or self.pet_data['stored']:
            return

        # 포켓몬이 활성화된 상태면 포만감 감소 (레벨이 높을수록 더 빨리 줄어듦)
        if self.pet_data['hunger'] > 0:
            decay = get_hunger_decay_amount(self.pet_data['level'])
            self.pet_data['hunger'] = max(0, self.pet_data['hunger'] - decay)

        # 포만감이 바닥나면(방금 떨어졌든, 0인 채로 다시 꺼내진 것이든) 목숨을 깎고
        # 상자로 돌려보낸다. hunger > 0 블록 밖에서 체크해야, 0인 상태로 다시
        # 꺼낸 포켓몬이 아무 반응 없이 계속 방치되는 문제가 생기지 않는다.
        if self.pet_data['hunger'] <= 0:
            self.pet_data['life'] = max(0, self.pet_data['life'] - 1)

            # 목숨이 0이 되면 포켓몬 사망 처리
            if self.pet_data['life'] == 0:
                self.pet_data['dead'] = True
                self.show_floating_text("💀 사망...", "#333333")

            # 단순히 hide()만 하면 pet_data['widget']이 그대로 남아 있어서
            # 포켓몬 상자에서는 여전히 "꺼내져 있는 것"으로 보여 버튼이
            # "집어넣기"로 잘못 표시된다. despawn_pet으로 widget 참조까지 정리한다.
            self.manager.despawn_pet(self.pet_data)
            self.manager.save_game()
            return

        # 포만감이 최대치의 20% 이하면 배고픔 표시 (레벨이 올라 최대치가 커져도
        # 상대적인 기준을 유지하기 위해 절대값 20이 아니라 비율로 계산)
        max_hunger = get_max_hunger(self.pet_data['level'])
        if self.pet_data['hunger'] <= max_hunger * 0.2:
            self.emoticon_label.setStyleSheet("color: #FF6B6B; background: transparent; font-weight: bold;")
            self.emoticon_label.setText("🍗")
            self.emoticon_label.show()
        else:
            self.emoticon_label.hide()

        self.update_ui()

    def passive_friendship_gain(self):
        """데스크톱에 꺼내놓은 포켓몬은 가만히 있어도 친밀도가 조금씩 쌓인다."""
        if self.pet_data.get('dead', False) or self.pet_data.get('stored', False):
            return
        if self.is_dragging:
            return
        self.add_exp(4)

    def passive_gold_gain(self):
        """데스크톱에 꺼내놓은 포켓몬은 가끔 골드를 주워온다."""
        if self.pet_data.get('dead', False) or self.pet_data.get('stored', False):
            return
        if self.is_dragging:
            return
        if random.random() >= 0.2:  # 20% 확률
            return
        amount = random.randint(1, 5)
        self.manager.gold += amount
        self.show_floating_text(f"+{amount}G", "#F9A825")
        self.manager.save_game()

    def check_pokemon_interaction(self):
        """근처에 다른 포켓몬이 나란히 서서 마주보고 있으면 확률적으로 상호작용한다."""
        if self.is_dragging or self.is_reacting or self.state != 0:
            return
        if self.pet_data.get('dead', False) or self.pet_data.get('stored', False):
            return
        if self.y() != self.floor_y:
            return

        for other_data in self.manager.pets_data:
            other = other_data.get('widget')
            if other is None or other is self:
                continue
            if other_data.get('dead', False) or other_data.get('stored', False):
                continue
            if other.is_dragging or other.is_reacting or other.state != 0:
                continue
            if other.y() != other.floor_y:
                continue

            dx = other.x() - self.x()
            if abs(dx) > self.width() + 30:
                continue  # 나란히(가까이) 있지 않으면 패스

            facing_each_other = (
                (dx > 0 and self.direction == 1 and other.direction == -1) or
                (dx < 0 and self.direction == -1 and other.direction == 1)
            )
            if not facing_each_other:
                continue

            # 같은 두 포켓몬 쌍을 양쪽에서 중복 처리하지 않도록 한쪽만 트리거한다
            if id(self) > id(other):
                continue

            if random.random() < 0.6:
                self.trigger_interaction(other)
            return

    def trigger_interaction(self, other):
        """다른 포켓몬과 마주쳤을 때 벌어지는 이벤트를 무작위로 하나 실행한다."""
        roll = random.random()
        if roll < 0.34:
            self.show_floating_text("❗", "#D32F2F")
            other.show_floating_text("❗", "#D32F2F")
        elif roll < 0.67:
            self.greet_with_jumps(2)
            other.greet_with_jumps(2)
        else:
            toward = random.random() < 0.5
            self.start_dash(other.x(), toward)
            other.start_dash(self.x(), toward)

    def start_dash(self, other_x, toward=True):
        """상대 포켓몬 쪽으로(또는 반대로) 평소보다 훨씬 빠르게 잠깐 멀리 달린다."""
        target_direction = 1 if other_x > self.x() else -1
        if not toward:
            target_direction *= -1
        self.direction = target_direction
        self.dash_ticks_remaining = 25  # auto_walk 틱(100ms) 기준 약 2.5초 (더 멀리 달리도록 연장)

    def decide_random_behavior(self):
        if self.is_dragging or self.is_reacting or self.y() < self.floor_y:
            return

        rand_val = random.random()
        if rand_val < 0.60:
            self.state = 0
            if random.random() < 0.5:
                self.direction *= -1
        elif rand_val < 0.85:
            self.state = 1
        else:
            self.perform_jump()

    def perform_jump(self):
        if self.y() >= self.floor_y:
            self.state = 2
            self.jump_vy = -6.5
            self.gravity_timer.start(20)

    def greet_with_jumps(self, count=2):
        """상자에서 꺼낼 때 제자리에서 통통 튀는 환영 점프 + 머리 위 하트 표시"""
        self.pending_greeting_jumps = max(0, count - 1)  # 이번 점프 이후 이어서 할 점프 수
        self.perform_jump()
        self.show_floating_text("♥", "#FF4081")

    def auto_walk(self):
        if self.is_dragging or self.is_reacting or self.state == 1:
            return

        # 걸어서 다른 모니터로 넘어갈 수 있으므로 매 틱마다 바닥/경계를 다시 확인한다
        self.update_screen_bounds()

        if self.gravity_timer.isActive():
            return  # 낙하/점프 중에는 좌우 이동 보류

        if self.y() != self.floor_y:
            # 모니터를 넘어가면서 바닥 높이가 바뀐 경우: 새 바닥으로 자연스럽게 떨어뜨린다
            self.state = 2
            self.jump_vy = 0.0
            self.gravity_timer.start(20)
            return

        step = 8 if self.dash_ticks_remaining > 0 else 2  # 평소 걸음(2)의 4배 속도로 질주
        if self.dash_ticks_remaining > 0:
            self.dash_ticks_remaining -= 1

        new_x = self.x() + (self.direction * step)
        if new_x <= self.left_bound:
            new_x = self.left_bound
            self.direction = 1
        elif new_x >= self.right_bound:
            new_x = self.right_bound
            self.direction = -1

        self.move(new_x, self.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.has_moved = False
            self.drag_start_y = self.y()
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        elif event.button() == Qt.MouseButton.RightButton:
            # 인벤토리에서 지정한 '기본 먹이'를 그대로 사용한다 (없으면 무료 먹이).
            tier = self.manager.get_active_food_tier()
            hunger_amount, icon, name, reaction = get_food_effect(tier)
            if tier is not None:
                self.manager.food_inventory[tier] -= 1
                self.manager.clear_stale_default_food()
                self.manager.save_game()

            FoodItem(self, event.position().toPoint(), icon=icon)
            max_hunger = get_max_hunger(self.pet_data['level'])
            self.pet_data['hunger'] = min(max_hunger, self.pet_data['hunger'] + hunger_amount)
            self.add_exp(3)
            self.show_floating_text(reaction, "#4CAF50")

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.has_moved = True
            self.move(event.globalPosition().toPoint() - self.drag_start_position)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

            if not self.has_moved:
                self.add_exp(5)
                self.show_floating_text("♥ (≧◡≦) ♥", "#FF4081")
            else:
                # 다른 모니터에 드롭했을 수 있으므로 바닥/경계를 먼저 다시 계산한다
                self.update_screen_bounds()

                # 드래그한 경우, 드롭 위치 저장
                self.drag_end_y = self.y()  # 드롭 위치 저장
                if self.y() != self.floor_y:
                    self.is_user_dragging = True  # 드래그 낙하 플래그 설정
                    self.jump_vy = 0
                    self.gravity_timer.start(20)

    def apply_physics(self):
        """중력 및 낙하 명세 적용: 화면 절반 기준 친밀도 증감"""
        new_y = self.y() + int(self.jump_vy)
        self.jump_vy += self.gravity

        if new_y >= self.floor_y:
            self.move(self.x(), self.floor_y)
            self.gravity_timer.stop()
            self.jump_vy = 0.0

            # 사용자 드래그에 의한 낙하인 경우에만 친밀도 변화
            if self.is_user_dragging:
                # 화면 세로 절반 지점 계산 (지금 놓인 모니터 기준)
                screen = self.screen() or QApplication.primaryScreen()
                avail = screen.availableGeometry()
                screen_half_y = avail.y() + avail.height() / 2

                # 드롭 위치(drag_end_y)가 화면 절반보다 위(Y값이 작음)인지 확인
                if self.drag_end_y < screen_half_y:
                    # 화면 절반보다 위에서 드롭 -> 높은 곳
                    self.add_exp(-15)
                    self.show_floating_text("😵", "#D32F2F")
                else:
                    # 화면 절반보다 아래에서 드롭 -> 낮은 곳
                    self.add_exp(10)
                    self.show_floating_text("✨", "#FF9800")

                self.is_user_dragging = False  # 플래그 리셋
            # else: 자동 점프인 경우 친밀도 변화 없음

            if self.pending_greeting_jumps > 0:
                # 환영 점프가 더 남아있으면, 다음 점프를 시작하기 전까지
                # (state=1로) 제자리에 멈춰있게 해서 걷지 않도록 한다.
                self.pending_greeting_jumps -= 1
                self.state = 1
                QTimer.singleShot(150, self.perform_jump)
            else:
                self.state = 0
        else:
            self.move(self.x(), new_y)

    def clear_reaction(self):
        self.emoticon_label.hide()
        self.is_reacting = False