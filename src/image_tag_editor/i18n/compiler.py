import argparse
import subprocess
import sys
from pathlib import Path

# パスの定数定義
# compiler.py の場所: src/image_tag_editor/i18n/
I18N_DIR = Path(__file__).resolve().parent
# プロジェクトルート
PROJECT_ROOT = I18N_DIR.parent.parent.parent
# デフォルトのロケールディレクトリ: src/image_tag_editor/i18n/locales
DEFAULT_LOCALES_DIR = I18N_DIR / 'locales'
# デフォルトのソースディレクトリ: src/image_tag_editor
DEFAULT_SRC_DIR = I18N_DIR.parent

APP_NAME = "image_tag_editor"

def run_pybabel(args: list[str], cwd: Path | None = None) -> None:
	"""pybabelコマンドを実行するラッパー関数。"""
	cmd = [sys.executable, '-m', 'babel.messages.frontend'] + [str(arg) for arg in args]
	print(f"Running in {cwd}: {' '.join(cmd)}")
	try:
		subprocess.run(cmd, check=True, cwd=cwd)
	except subprocess.CalledProcessError as e:
		print(f"Error running pybabel: {e}", file=sys.stderr)
		sys.exit(1)
	except FileNotFoundError:
		print(f"Error: command not found: {cmd[0]}", file=sys.stderr)
		print("Please ensure pybabel (or the python executable) is in your PATH.", file=sys.stderr)
		sys.exit(1)

def command_extract(args: argparse.Namespace) -> None:
	"""extractコマンドのハンドラ: ソースから翻訳キーを抽出して.potを作成。"""
	output_file = args.locales_dir / f'{APP_NAME}.pot'
	
	# pybabelに渡すパスは、プロジェクトルートからの相対パスにする
	# これにより、.potファイルに記録されるソースファイルのパスが相対パスになり、
	# 環境への依存をなくす。
	relative_output = output_file.relative_to(PROJECT_ROOT)
	relative_src = args.src_dir.relative_to(PROJECT_ROOT)
	
	pybabel_args = [
		'extract',
		'-k', '__',
		# バージョン管理のノイズを減らすためのオプション
		'--no-location',  # ファイルパスと行番号を出力しない
		'--omit-header',  # POT-Creation-Date などのヘッダーを出力しない
		# '--sort-output',  # メッセージIDでソートして順序を安定させる
		# '--no-wrap',      # 自動折り返しを無効にする
		'-o', relative_output,
		relative_src,
	]
	
	print(f"Extracting messages from {relative_src} to {relative_output}...")
	run_pybabel(pybabel_args, cwd=PROJECT_ROOT)

def command_update(args: argparse.Namespace) -> None:
	"""updateコマンドのハンドラ: .potの内容を.poに反映。"""
	input_file = args.locales_dir / f'{APP_NAME}.pot'
	
	if not input_file.exists():
		print(f"Error: POT file not found: {input_file}", file=sys.stderr)
		print("Run 'extract' command first.", file=sys.stderr)
		sys.exit(1)
	
	# pybabelに渡すパスは、プロジェクトルートからの相対パスにする
	relative_input = input_file.relative_to(PROJECT_ROOT)
	relative_locales = args.locales_dir.relative_to(PROJECT_ROOT)
	
	pybabel_args = [
		'update',
		'-i', relative_input,
		'-d', relative_locales,
		'-D', APP_NAME,
		'--omit-header',  # POT-Creation-Date などのヘッダーを出力しない
		'--no-fuzzy-matching',
	]
	
	print(f"Updating .po files in {relative_locales} from {relative_input}...")
	run_pybabel(pybabel_args, cwd=PROJECT_ROOT)

def command_compile(args: argparse.Namespace) -> None:
	"""compileコマンドのハンドラ: .poを.moにコンパイル。"""
	# .moファイルに絶対パスが記録されるのを防ぐため、
	# プロジェクトルートを基準とした相対パスで操作を行う。
	relative_locales = args.locales_dir.relative_to(PROJECT_ROOT)
	
	pybabel_args = [
		'compile',
		'-f',  # fuzzyフラグがついた翻訳もコンパイルに含める
		'-d', relative_locales,
		'-D', APP_NAME,
	]
	
	print(f"Compiling .po files in {relative_locales} for domain '{APP_NAME}'...")
	run_pybabel(pybabel_args, cwd=PROJECT_ROOT)

def command_init(args: argparse.Namespace) -> None:
	"""initコマンドのハンドラ: 新しい言語の.poファイルを作成。"""
	input_file = args.locales_dir / f'{APP_NAME}.pot'
	
	if not input_file.exists():
		print(f"Error: POT file not found: {input_file}", file=sys.stderr)
		print("Run 'extract' command first.", file=sys.stderr)
		sys.exit(1)
	
	# pybabelに渡すパスは、プロジェクトルートからの相対パスにする
	relative_input = input_file.relative_to(PROJECT_ROOT)
	relative_locales = args.locales_dir.relative_to(PROJECT_ROOT)
	
	pybabel_args = [
		'init',
		'-i', relative_input,
		'-d', relative_locales,
		'-l', args.locale,
		'-D', APP_NAME,
	]
	
	print(f"Initializing new catalog for locale '{args.locale}'...")
	run_pybabel(pybabel_args, cwd=PROJECT_ROOT)

def command_extract_update(args: argparse.Namespace) -> None:
	"""extractとupdateを連続して実行するハンドラ。"""
	print(">>> Executing extract...")
	command_extract(args)
	print("\n>>> Executing update...")
	command_update(args)

def main() -> None:
	parser = argparse.ArgumentParser(description='Translation management tool using pybabel.')
	
	# 共通引数
	parser.add_argument(
		'-l',
		'--locales-dir',
		type=Path,
		default=DEFAULT_LOCALES_DIR,
		help=f'Locales directory (default: {DEFAULT_LOCALES_DIR})',
	)
	
	subparsers = parser.add_subparsers(dest='command', required=True, help='Sub-command to run')
	
	# extract (e) コマンド
	parser_extract = subparsers.add_parser('extract', aliases=['e'], help='Extract messages from source code to .pot file')
	parser_extract.add_argument(
		'-i',
		'--src-dir',
		type=Path,
		default=DEFAULT_SRC_DIR,
		help=f'Source directory to search (default: {DEFAULT_SRC_DIR})',
	)
	parser_extract.set_defaults(func=command_extract)
	
	# update (u) コマンド
	parser_update = subparsers.add_parser('update', aliases=['u'], help='Update .po files from .pot file')
	parser_update.set_defaults(func=command_update)
	
	# compile (c) コマンド
	parser_compile = subparsers.add_parser('compile', aliases=['c'], help='Compile .po files to .mo files')
	parser_compile.set_defaults(func=command_compile)
	
	# init (i) コマンド
	parser_init = subparsers.add_parser('init', aliases=['i'], help='Initialize a new language catalog')
	parser_init.add_argument('locale', help='Locale code (e.g. ja, en)')
	parser_init.set_defaults(func=command_init)
	
	# extract+update (e+u) コマンド
	parser_eu = subparsers.add_parser('extract+update', aliases=['e+u'], help='Run extract then update')
	parser_eu.add_argument(
		'--src-dir', type=Path, default=DEFAULT_SRC_DIR, help=f'Source directory to search (default: {DEFAULT_SRC_DIR})'
	)
	parser_eu.set_defaults(func=command_extract_update)
	
	args = parser.parse_args()
	
	# ロケールディレクトリが存在しない場合は作成
	if not args.locales_dir.exists():
		args.locales_dir.mkdir(parents=True, exist_ok=True)
	
	if hasattr(args, 'func'):
		args.func(args)
	else:
		parser.print_help()

if __name__ == '__main__':
	main()
