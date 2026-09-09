import os
import random
from PyQt6.QtWidgets import QWidget, QLabel, QProgressBar, QVBoxLayout, QApplication, QDialog, QPushButton, QGridLayout, QScrollArea
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QMovie, QPixmap
from utils import ASSETS_DIR, FoodItem, PIXEL_FONT_FAMILY

MAX_LIFE = 5

class EvolutionDialog(QDialog):
    """포켓몬 진화 선택 다이얼로그 (전체 진화체 표시 및 스크롤 지원)"""
    def __init__(self, current_base_name, pokemon_ko_name="이브이"):
        super().__init__()
        self.selected_evolution = None
        self.setWindowTitle("포켓몬 진화!")
        self.setFixedSize(320, 310)
        self.setStyleSheet("background-color: #FFF0F5; border-radius: 10px;")

        main_layout = QVBoxLayout(self)

        label = QLabel(f"{pokemon_ko_name}(이)가 진화할 수 있습니다!\n원하는 진화 형태를 선택하세요:", self)
        label.setStyleSheet("color: #222222;")
        label.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(label)

        # 스크롤 영역 생성 (진화체가 많아져도 전부 표시되도록 함)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        grid_layout = QGridLayout(scroll_content)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        # 전체 진화체 목록 (예시 확장 가능)
        evolutions = [
            ("샤미드", "vaporeon"),
            ("쥬피썬더", "jolteon"),
            ("부스터", "flareon"),
            ("에브이", "espeon"),
            ("블래키", "umbreon"),
            ("리피아", "leafeon"),
            ("글레이시아", "glaceon"),
            ("님피아", "sylveon")
        ]

        for i, (ko_name, base_name) in enumerate(evolutions):
            btn = QPushButton(ko_name, scroll_content)
            btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton { background-color: #FF69B4; color: white; border-radius: 5px; padding: 8px; }
                QPushButton:hover { background-color: #FF1493; }
            """)
            btn.clicked.connect(lambda checked, b=base_name, k=ko_name: self.select_evo(b, k))
            row, col = divmod(i, 2)
            grid_layout.addWidget(btn, row, col)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # 취소 버튼 추가
        button_layout = QVBoxLayout()
        cancel_btn = QPushButton("이브이로 남기", self)
        cancel_btn.setFont(QFont(PIXEL_FONT_FAMILY, 9, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #CCCCCC; color: black; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #AAAAAA; }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)

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

        self.initUI()
        self.initPhysics()
        self.update_pokemon_movie()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        screen = QApplication.primaryScreen().availableGeometry()
        self.screen_width, self.screen_height = screen.width(), screen.height()

        window_width, window_height = 160, 120
        self.floor_y = self.screen_height - window_height
        spawn_x = random.randint(100, max(100, self.screen_width - window_width - 100))
        self.setGeometry(spawn_x, self.floor_y, window_width, window_height)

        self.emoticon_label = QLabel(self)
        self.emoticon_label.setGeometry(30, 25, 100, 20)
        self.emoticon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emoticon_label.setFont(QFont(PIXEL_FONT_FAMILY, 10, QFont.Weight.Bold))
        self.emoticon_label.hide()

        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adjust_pet_size()

        self.movie = QMovie(self)
        self.movie.frameChanged.connect(self.on_frame_changed)

        self.ui_widget = QWidget(self)
        self.ui_widget.setGeometry(45, 90, 70, 35)
        ui_layout = QVBoxLayout(self.ui_widget)
        ui_layout.setContentsMargins(0, 2, 0, 0)
        ui_layout.setSpacing(0)

        # 레벨/이름 텍스트 중앙 정렬 및 "Lv.1 이브이" 순서 적용
        self.level_label = QLabel()
        self.level_label.setFont(QFont(PIXEL_FONT_FAMILY, 7, QFont.Weight.Bold))
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

    def adjust_pet_size(self):
        base_name = self.pet_data.get('pokemon_base_name', 'eevee')
        if base_name == "mimikyu":
            self.pet_label.setGeometry(30, 20, 100, 80)
        elif base_name in ["squirtle", "wartortle", "blastoise"]:
            # 꼬북이 계열은 더 작게 표시
            self.pet_label.setGeometry(50, 45, 40, 40)
        elif base_name == "gible":
            # 이어롤: 가로로 넓은 형태 (31×44), 가운데 정렬
            self.pet_label.setGeometry(65, 40, 31, 44)
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
            self.show_floating_text("🎉 LEVEL UP! 🎉", "#FFD700")
            self.check_evolution()
            self.manager.save_game()  # 레벨업 후 자동 저장
        elif amount < 0:
            self.show_floating_text("아야!", "#D32F2F")
        self.update_ui()

    def check_evolution(self):
        base_name = self.pet_data['pokemon_base_name']
        level = self.pet_data['level']
        pokemon_ko_name = self.pet_data.get('nickname') or self.pet_data['pokemon_type_ko']

        # 이브이: 레벨 10에서 선택 진화
        if level == 10 and base_name == "eevee" and not self.pet_data.get('is_evolved', False):
            dlg = EvolutionDialog(base_name, pokemon_ko_name)
            screen = QApplication.primaryScreen().geometry()
            dlg.move((screen.width() - dlg.width()) // 2, (screen.height() - dlg.height()) // 2)

            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_evolution:
                new_base, new_ko = dlg.selected_evolution
                self.pet_data['pokemon_base_name'] = new_base
                self.pet_data['pokemon_type_ko'] = new_ko
                self.update_pokemon_movie()
                self.adjust_pet_size()
                self.show_floating_text(f"✨ {new_ko}(으)로 진화! ✨", "#00BFFF")

            # 어느 쪽이든 진화 완료 플래그 설정 (취소해도 다시는 안 뜸)
            self.pet_data['is_evolved'] = True

        # 꼬북이: 레벨 15에서 어니부기로 진화
        elif level == 15 and base_name == "squirtle" and self.pet_data.get('evolution_stage', 0) == 0:
            self.pet_data['pokemon_base_name'] = "wartortle"
            self.pet_data['pokemon_type_ko'] = "어니부기"
            self.pet_data['evolution_stage'] = 1
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 어니부기(으)로 진화! ✨", "#00BFFF")

        # 꼬북이 진화체: 레벨 30에서 거북왕으로 진화
        elif level == 30 and base_name == "wartortle" and self.pet_data.get('evolution_stage', 0) == 1:
            self.pet_data['pokemon_base_name'] = "blastoise"
            self.pet_data['pokemon_type_ko'] = "거북왕"
            self.pet_data['evolution_stage'] = 2
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 거북왕(으)로 진화! ✨", "#00BFFF")

        # 이어롤: 레벨 10에서 이어롭으로 진화
        elif level == 10 and base_name == "gible" and self.pet_data.get('evolution_stage', 0) == 0:
            self.pet_data['pokemon_base_name'] = "gabite"
            self.pet_data['pokemon_type_ko'] = "이어롭"
            self.pet_data['evolution_stage'] = 1
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 이어롭(으)로 진화! ✨", "#00BFFF")

        # 리오르: 레벨 20에서 루카리오로 진화
        elif level == 20 and base_name == "riolu" and self.pet_data.get('evolution_stage', 0) == 0:
            self.pet_data['pokemon_base_name'] = "lucario"
            self.pet_data['pokemon_type_ko'] = "루카리오"
            self.pet_data['evolution_stage'] = 1
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 루카리오(으)로 진화! ✨", "#00BFFF")

        # 랄토스: 레벨 10에서 킬리아로 진화
        elif level == 10 and base_name == "ralts" and self.pet_data.get('evolution_stage', 0) == 0:
            self.pet_data['pokemon_base_name'] = "kirlia"
            self.pet_data['pokemon_type_ko'] = "킬리아"
            self.pet_data['evolution_stage'] = 1
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 킬리아(으)로 진화! ✨", "#00BFFF")

        # 킬리아: 레벨 20에서 가디안으로 진화
        elif level == 20 and base_name == "kirlia" and self.pet_data.get('evolution_stage', 0) == 1:
            self.pet_data['pokemon_base_name'] = "gardevoir"
            self.pet_data['pokemon_type_ko'] = "가디안"
            self.pet_data['evolution_stage'] = 2
            self.update_pokemon_movie()
            self.adjust_pet_size()
            self.show_floating_text("✨ 가디안(으)로 진화! ✨", "#00BFFF")

    def show_floating_text(self, text, color="#FF4081"):
        self.is_reacting = True
        self.emoticon_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
        self.emoticon_label.setText(text)
        self.emoticon_label.show()
        QTimer.singleShot(800, self.clear_reaction)

    def update_ui(self):
        display_name = self.pet_data['nickname'] or self.pet_data['pokemon_type_ko']
        # 텍스트 순서: "Lv.1 이브이" 형태로 설정
        self.level_label.setText(f"Lv.{self.pet_data['level']} {display_name}")
        self.bar.setValue(self.pet_data['friendship'])
        self.satiety_bar.setValue(int(self.pet_data['hunger']))

    def update_pokemon_movie(self):
        base_name = self.pet_data['pokemon_base_name']
        target_file = os.path.join(ASSETS_DIR, f"{base_name}.gif")
        if not os.path.exists(target_file):
            target_file = os.path.join(ASSETS_DIR, "eevee.gif")

        if self.movie.fileName() != target_file and os.path.exists(target_file):
            self.movie.stop()
            self.movie.setFileName(target_file)

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
        self.satiety_timer.start(2000)  # 2초마다 포만감 1씩 감소 (실시간 업데이트)

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

        # 포켓몬이 활성화된 상태면 포만감 감소
        if self.pet_data['hunger'] > 0:
            self.pet_data['hunger'] = max(0, self.pet_data['hunger'] - 1)

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

        # 포만감이 20% 이하면 배고픔 표시
        if self.pet_data['hunger'] <= 20:
            self.emoticon_label.setStyleSheet("color: #FF6B6B; background: transparent; font-weight: bold;")
            self.emoticon_label.setText("🍗")
            self.emoticon_label.show()
        else:
            self.emoticon_label.hide()

        self.update_ui()

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
        if self.is_dragging or self.is_reacting or self.y() < self.floor_y or self.state == 1:
            return

        new_x = self.x() + (self.direction * 2)
        if new_x < 0 or new_x > self.screen_width - self.width():
            self.direction *= -1

        self.move(new_x, self.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.has_moved = False
            self.drag_start_y = self.y()
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        elif event.button() == Qt.MouseButton.RightButton:
            FoodItem(self, event.position().toPoint())
            self.pet_data['hunger'] = min(100, self.pet_data['hunger'] + 15)
            self.add_exp(3)
            self.show_floating_text("🍎 냠냠!", "#4CAF50")

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
                # 드래그한 경우, 드롭 위치 저장
                self.drag_end_y = self.y()  # 드롭 위치 저장
                if self.y() < self.floor_y:
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
                # 화면 세로 절반 지점 계산
                screen_half_y = self.screen_height / 2

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