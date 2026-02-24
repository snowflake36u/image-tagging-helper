import os
import json
import platform
from typing import Any

class Config:
	"""アプリケーションの設定を管理するクラス。"""
	
	def __init__(self, app_name: str):
		self.app_name = app_name
		self.config_dir = self._get_config_dir()
		self.config_file = os.path.join(self.config_dir, 'config.json')
		self.data = self._load_config()
	
	def _get_config_dir(self) -> str:
		"""プラットフォームに応じた設定ディレクトリのパスを取得します。"""
		system = platform.system()
		if system == 'Windows':
			base_dir = os.environ.get('APPDATA')
		elif system == 'Darwin':
			base_dir = os.path.expanduser('~/Library/Application Support')
		else:
			base_dir = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
		
		path = os.path.join(base_dir, self.app_name)
		if not os.path.exists(path):
			os.makedirs(path)
		return path
	
	def _load_config(self) -> dict[str, Any]:
		"""設定ファイルから設定を読み込みます。"""
		if not os.path.exists(self.config_file):
			return { }
		
		try:
			with open(self.config_file, 'r', encoding='utf-8') as f:
				return json.load(f)
		except (json.JSONDecodeError, OSError):
			return { }
	
	def save(self):
		"""現在の設定をファイルに保存します。"""
		try:
			with open(self.config_file, 'w', encoding='utf-8') as f:
				json.dump(self.data, f, indent=4)
		except OSError:
			pass
	
	def get(self, key: str, default: Any = None) -> Any:
		"""設定値を取得します。"""
		return self.data.get(key, default)
	
	def set(self, key: str, value: Any):
		"""設定値を設定します。"""
		self.data[key] = value
