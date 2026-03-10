import sys
from pathlib import Path

# --- Private members ---

# アプリケーションがNuitkaによってone-fileにバンドルされているかどうか
# Nuitkaのonefileモードでは、sys._MEIPASSに展開先の一時フォルダが設定されるため、その存在をチェックする
_IS_COMPILED = "__compiled__" in globals()

# バンドルされたリソースのルートパス
_BUNDLE_DIR = Path(__file__).parent.parent

# 実行ファイル(.exe)が置かれているディレクトリのパス
# - Nuitkaビルド環境: .exeファイルが存在するディレクトリ
# - 開発環境: プロジェクトのルートディレクトリ
_EXECUTABLE_DIR = Path(sys.argv[0]).parent if _IS_COMPILED else Path(__file__).parent.parent.parent

# --- Public functions ---

def is_compiled() -> bool:
	"""
	アプリケーションがNuitkaによってone-fileにバンドルされているかどうかを返します。
	"""
	return _IS_COMPILED

def get_bundle_dir() -> Path:
	"""
	バンドルされたリソースのルートディレクトリを取得します。

	- Nuitkaビルド環境: リソースが展開される一時ディレクトリ (sys._MEIPASS)。
	- 開発環境: プロジェクトの `src` ディレクトリ。

	Returns:
		 バンドルリソースのルートディレクトリのPathオブジェクト。
	"""
	return _BUNDLE_DIR

def get_executable_dir() -> Path:
	"""
	実行ファイル(.exe)が置かれているディレクトリを取得します。

	- Nuitkaビルド環境: .exeファイルが存在するディレクトリ。
	- 開発環境: プロジェクトのルートディレクトリ。

	Returns:
		 実行ファイルディレクトリのPathオブジェクト。
	"""
	return _EXECUTABLE_DIR

def resource_path(relative_path: str | Path) -> str:
	"""
	実行環境に応じて、バンドルされたリソースへの絶対パスを取得します。
	この関数は `get_bundle_dir()` を使用します。

	Args:
		 relative_path: バンドルルート(`src` ディレクトリに相当)からの相対パス。
							 (例: 'image_tagging_helper/assets/icon.png')

	Returns:
		 リソースへの絶対パス文字列。
	"""
	# build.pyでの--include-data-dir設定は、srcからのパス構造を維持するため
	# _BUNDLE_DIR (開発時はsrc、ビルド後は_MEIPASS) を基点とする
	return str(get_bundle_dir() / relative_path)
