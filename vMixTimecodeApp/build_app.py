import PyInstaller.__main__
import os
import shutil

# 프로젝트 루트 디렉토리 (main.py가 있는 곳)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))

# 빌드 결과물이 저장될 디렉토리
dist_path = os.path.join(project_root, 'dist')
build_path = os.path.join(project_root, 'build')

# 기존 빌드 결과물 삭제
if os.path.exists(dist_path):
    shutil.rmtree(dist_path)
if os.path.exists(build_path):
    shutil.rmtree(build_path)

# settings.json 파일이 없으면 빈 파일 생성
settings_file_path = os.path.join(project_root, "settings.json")
if not os.path.exists(settings_file_path):
    with open(settings_file_path, 'w', encoding='utf-8') as f:
        f.write('{}') # 빈 JSON 객체로 초기화
    print(f"Created empty settings.json at: {settings_file_path}")

# logs 디렉토리가 없으면 생성
logs_dir_path = os.path.join(project_root, "logs")
os.makedirs(logs_dir_path, exist_ok=True)
print(f"Ensured logs directory exists at: {logs_dir_path}")

# PyInstaller 명령어 인자
# --noconsole: 콘솔 창을 띄우지 않음 (GUI 앱용)
# --onefile: 단일 실행 파일 생성
# --name: 실행 파일 이름
# --add-data: 추가 파일/폴더 포함 (source;destination)
# --clean: 빌드 전 임시 파일 삭제
# --distpath: 빌드 결과물 저장 경로
# --workpath: 임시 작업 파일 저장 경로
# --specpath: .spec 파일 저장 경로
pyinstaller_args = [
    '--noconsole',
    '--onefile',
    '--name=vMixTimecodeApp',
    f'--add-data={settings_file_path}{os.pathsep}.', # settings.json 포함
    f'--add-data={logs_dir_path}{os.pathsep}logs', # logs 폴더 포함
    f'--add-data={os.path.join(project_root, "src")}{os.pathsep}src', # src 폴더 포함
    '--clean',
    f'--distpath={dist_path}',
    f'--workpath={build_path}',
    f'--specpath={project_root}', # .spec 파일을 프로젝트 루트에 생성
    os.path.join(project_root, 'main.py') # 메인 스크립트
]

# 아이콘 파일이 있다면 추가 (예: icon.ico)
# if os.path.exists(os.path.join(project_root, 'assets', 'icon.ico')):
#     pyinstaller_args.insert(0, f'--icon={os.path.join(project_root, "assets", "icon.ico")}')

print(f"PyInstaller arguments: {pyinstaller_args}")

# PyInstaller 실행
PyInstaller.__main__.run(pyinstaller_args)

print("\n--- PyInstaller 빌드 완료 ---")
print(f"실행 파일: {os.path.join(dist_path, 'vMixTimecodeApp.exe')}")
print("이제 이 실행 파일을 다른 컴퓨터에서 실행할 수 있습니다.")

# 빌드 후 불필요한 파일 정리 (선택 사항)
# os.remove(os.path.join(project_root, 'vMixTimecodeApp.spec'))
# shutil.rmtree(build_path)