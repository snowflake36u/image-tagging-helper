import os
import shutil
import subprocess

from pathlib import Path

# --- Configuration ---
PROJ_PATH = Path(__file__).parent.parent.parent

APP_NAME = 'Image Tagging Helper'
ENTRY_POINT = 'image_tagging_helper/wx/app.py'
DIST_DIR = PROJ_PATH / 'dist'
BUILD_DIR = 'build'

# Nuitka options
nuitka_options = [
	'--onefile',
	'--windows-console-mode=disable',
	f'--output-dir={DIST_DIR}',
	f'--output-filename={APP_NAME}',
	'--include-package=image_tagging_helper',
	'--include-data-dir=image_tagging_helper/i18n/locales=image_tagging_helper/i18n/locales',
	'--lto=yes',
]

def build():
	"""
	Nuitkaを使ってアプリケーションをビルドします。
	"""
	print('--- Cleaning up old build artifacts ---')
	if os.path.exists(DIST_DIR):
		shutil.rmtree(DIST_DIR)
	if os.path.exists(BUILD_DIR):
		shutil.rmtree(BUILD_DIR)
	
	print('--- Building application with Nuitka ---')
	command = [
					 'python',
					 '-m',
					 'nuitka',
				 ] + nuitka_options + [
					 ENTRY_POINT
				 ]
	
	print(f"Running command: {' '.join(command)}")
	try:
		# Nuitkaコマンドの出力をコンソールに直接表示するため、capture_outputを削除
		subprocess.run(command, check=True)
		print('--- Build successful ---')
	except subprocess.CalledProcessError as e:
		print('--- Build failed ---')
		# capture_outputを削除したため、e.stdoutやe.stderrは利用できません。
		# Nuitkaの出力は既にコンソールに表示されているはずです。
		return
	
	print(f'Executable created at: {os.path.join(DIST_DIR, f"{APP_NAME}.exe")}')

if __name__ == '__main__':
	build()
