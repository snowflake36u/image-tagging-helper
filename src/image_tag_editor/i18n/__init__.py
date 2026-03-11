import gettext
import os
from typing import Optional

from image_tag_editor.core.apppaths import get_executable_dir, is_compiled, resource_path

_translation: Optional[gettext.NullTranslations] = None

def __(message_key: str) -> str:
	"""翻訳キーに対応する文字列を返します。
	
	setup_translation() が呼び出されていない場合、または翻訳が見つからない場合は、
	キーをそのまま返します。
	"""
	if _translation is None:
		return message_key
	return _translation.gettext(message_key)

def setup_translation(domain: str, locales_dir: str | None = None, lang: str | None = None) -> None:
	"""アプリケーションの翻訳機能を初期化します。

	指定された言語の翻訳をロードし、見つからない場合は英語(en)にフォールバックします。
	英語も見つからない場合は、キーをそのまま表示するNullTranslationsを使用します。

	Args:
		domain: 翻訳ドメイン（アプリ名など。.moファイル名に対応）。
		locales_dir: 翻訳ファイル（.mo）が配置されているディレクトリのパス。Noneの場合はデフォルトのlocalesディレクトリを使用。
		lang: 強制的に使用する言語コード。Noneの場合はシステム設定を使用。
	"""
	global _translation
	
	if locales_dir is None:
		if is_compiled():
			# 実行可能ファイルの場合、実行ファイルの隣の 'locales' ディレクトリを使用
			locales_dir = str(get_executable_dir() / 'locales')
		else:
			# 開発環境では、ソースツリー内の 'locales' ディレクトリを使用
			locales_dir = resource_path('i18n/locales')

	# 1. 英語 (en) をフォールバックとしてロード
	try:
		fallback = gettext.translation(domain, localedir=locales_dir, languages=['en'])
	except FileNotFoundError:
		fallback = gettext.NullTranslations()
	
	# 2. 対象言語をロード
	languages = [lang] if lang else None
	try:
		# languages=None の場合、gettextは環境変数(LC_ALL, LC_MESSAGES, LANG)等から言語を決定します
		t = gettext.translation(domain, localedir=locales_dir, languages=languages)
		t.add_fallback(fallback)
		_translation = t
	except FileNotFoundError:
		# 対象言語が見つからない場合はフォールバック（英語またはNull）を使用
		_translation = fallback
