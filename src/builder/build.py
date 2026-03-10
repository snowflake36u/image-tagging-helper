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

def make_options():
	# Nuitka options
	nuitka_options = [
		'--onefile',
		'--windows-console-mode=disable',
		f'--output-dir={DIST_DIR}',
		f'--output-filename={APP_NAME}',
		'--include-package=image_tagging_helper',
		'--lto=yes',
		# アプリケーションのアイコンを設定します。
		f'--windows-icon-from-ico={PROJ_PATH / "assets_src" / "app_icon.ico"}',
	]
	
	# 実行ファイルに同梱するリソース
	include_data_files = []
	include_data_dirs = [
		('image_tagging_helper/assets', 'image_tagging_helper/assets'),
	]
	include_onefile_external_data = []
	locale_files, locale_external_data = include_locale_files()
	include_data_files.extend(locale_files)
	include_onefile_external_data.extend(locale_external_data)
	
	for src, dest in include_data_files:
		nuitka_options.append(f'--include-data-file={src}={dest}')
	
	for src, dest in include_data_dirs:
		nuitka_options.append(f'--include-data-dir={src}={dest}')
	
	for d in include_onefile_external_data:
		nuitka_options.append(f'--include-onefile-external-data={d}')
	
	return nuitka_options

def include_locale_files():
	# 翻訳ファイルの追加
	languages = ['en', 'ja']
	locale_files = [(
		f'image_tagging_helper/i18n/locales/{lang}/LC_MESSAGES/*.mo',
		f'locales/{lang}/LC_MESSAGES/'
	) for lang in languages]
	locale_external_data = [
		'locales',
	]
	return locale_files, locale_external_data

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
	nuitka_options = make_options()
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
