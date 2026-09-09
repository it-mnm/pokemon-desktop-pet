# 포켓몬 데스크톱 펫 .exe 빌드 가이드

## 준비물

- Python 3.12 (이 프로젝트는 `%LOCALAPPDATA%\Programs\Python\Python312`에 설치되어 있음)
- PyQt6, pyinstaller

```powershell
cd E:\김명현\Pokemon
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 빌드

```powershell
cd E:\김명현\Pokemon
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name "포켓몬키우기" `
  --icon "assets/pokeball_icon.ico" `
  --add-data "assets;assets" `
  --collect-all PyQt6 `
  main.py
```

빌드가 끝나면 `dist\포켓몬키우기.exe` 파일이 생성됩니다. 이 파일 하나만 있으면 됩니다.

- `--icon "assets/pokeball_icon.ico"`: exe 파일 아이콘을 포켓볼 모양으로 지정 (아이콘은 `main.py`의 `create_pokeball_pixmap()`으로 그린 그림을 여러 해상도로 뽑아서 만든 것)

- `--onefile`: exe 파일 하나로 묶음 (내부적으로 실행할 때마다 임시 폴더에 압축을 풀어서 씀)
- `--windowed`: 콘솔 창 없이 실행 (GUI 앱이므로)
- `--add-data "assets;assets"`: 포켓몬 gif, 픽셀 폰트 등 에셋을 exe 안에 포함
- `--collect-all PyQt6`: PyQt6가 필요로 하는 플러그인(DLL)을 전부 포함해서, Python/PyQt6가 설치되어 있지 않은 PC에서도 그대로 실행되게 함

빌드 중 `Library not found: ...` 경고가 여러 줄 뜨는데, 이건 이 게임이 쓰지 않는 PyQt6 부가 기능(QML, 3D, WebEngine, SQL 드라이버 등)에 대한 경고라서 무시해도 됩니다.

## 배포 시 주의할 점 (중요)

- **저장 데이터 경로**: exe로 실행하면 저장 파일(`Pokemon_saves/pokemon_data.json`)은 항상 **exe 파일이 실제로 놓인 위치** 옆에 생성됩니다([save_manager.py](save_manager.py)에서 `sys.executable` 기준으로 처리). exe만 복사해서 옮기면 저장 데이터는 새로 시작되고, `Pokemon_saves` 폴더까지 같이 복사하면 기존 데이터를 그대로 이어할 수 있습니다.
- **에셋 경로**: 포켓몬 gif/폰트는 exe 안에 이미 포함되어 있어서 `assets` 폴더를 따로 옮길 필요가 없습니다([utils.py](utils.py)에서 `sys._MEIPASS` 기준으로 처리).
- **인터넷 연결 불필요**: 이 게임은 실행 중에 외부 서버와 통신하지 않으므로, exe 파일 하나만 옮기면 네트워크가 없는 PC에서도 그대로 실행됩니다.

## 배포 방법

`dist\포켓몬키우기.exe` 파일만 복사해서 원하는 PC의 아무 폴더에나 넣고 더블클릭하면 실행됩니다. Python 설치가 전혀 필요 없습니다.

## 문제 해결

### 실행 시 아무 반응이 없거나 바로 꺼짐
`--windowed` 옵션 때문에 콘솔 창(에러 로그)이 보이지 않습니다. 원인을 확인하려면 `--windowed`를 빼고(즉 콘솔 창을 남기고) 다시 빌드해서 에러 메시지를 확인하세요:
```powershell
python -m PyInstaller --noconfirm --clean --onefile --name "포켓몬키우기-debug" --icon "assets/pokeball_icon.ico" --add-data "assets;assets" --collect-all PyQt6 main.py
```

### 다시 빌드하기 전에
`build\`, `dist\`, `포켓몬키우기.spec` 폴더/파일을 지우고 `--clean` 옵션으로 새로 빌드하면 이전 빌드 캐시로 인한 문제를 피할 수 있습니다.
