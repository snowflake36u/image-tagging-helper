from collections import Counter
from dataclasses import dataclass
from typing import Callable

class CaptionFormatConfig:
	"""
	キャプションのフォーマット設定を管理するクラス。
	タグの区切り文字や、重み付けの括弧のスタイルなどを定義します。
	"""
	
	def __init__(
			self,
			*,
			delimiter=',',
			format_delimiter=', ',
			posi_weight_ratio=1.1,
			nega_weight_ratio=0.9,
			omittable_levels=5,
	):
		"""
		Args:
			delimiter (str): パース時に使用するタグの区切り文字。
			format_delimiter (str): フォーマット時に使用するタグの区切り文字。
			posi_weight_ratio (float): 丸括弧 () 1つあたりの重みの倍率。
			nega_weight_ratio (float): 角括弧 [] 1つあたりの重みの倍率。
			omittable_levels (int): 括弧のネストで表現可能なレベル数。これを超える重みは (tag:1.5) のような数値形式になります。
		"""
		self.delimiter = delimiter
		self.format_delimiter = format_delimiter
		self.posi_weight_ratio = posi_weight_ratio
		self.nega_weight_ratio = nega_weight_ratio
		
		# 重みから括弧のネストレベルへのマッピングを作成
		self.omittable_weights = {
			**{ posi_weight_ratio ** i: i for i in range(omittable_levels) },
			**{ nega_weight_ratio ** i: -i for i in range(omittable_levels) },
		}

def escape_for_tag(text):
	"""タグテキスト内の特殊文字をエスケープします。"""
	return text.replace('(', r'\(').replace(')', r'\)') \
		.replace('[', r'\[').replace(']', r'\]')

@dataclass(frozen=True)
class Tag:
	"""
	単一のタグを表すデータクラス。
	テキストと重みを保持します。
	"""
	text: str = ''
	weight: float = 1.0
	
	def format(self, config: CaptionFormatConfig):
		"""
		設定に基づいてタグを文字列形式にフォーマットします。
		重みに応じて括弧で囲むか、(tag:weight) 形式を使用します。

		Args:
			config (CaptionFormatConfig): フォーマット設定。

		Returns:
			str: フォーマットされたタグ文字列。
		"""
		text = escape_for_tag(self.text)
		
		if self.weight == 1:
			return text
		
		if self.weight in config.omittable_weights:
			level = config.omittable_weights[self.weight]
			if level < 0:
				return f"{'[' * -level}{text}{']' * -level}"
			else:
				return f"({'(' * (level - 1)}{text}{')' * (level - 1)})"
		
		return f"({text}:{self.weight})"
	
	def clone(self):
		"""自身の複製を返します。"""
		return Tag(self.text, self.weight)

class Caption:
	"""
	1つの画像のキャプション（タグの集合）を表すクラス。
	"""
	
	def __init__(self, tags=None):
		self.tags = tags or []
		# タグの出現回数をカウント（重複チェックなどに使用）
		self.counter = Counter([tag.text for tag in self.tags])
		self.on_tag_usage_changed: Callable[[str, bool], None] | None = None
	
	def __items__(self, index: int | slice):
		return self.tags[index]
	
	def __len__(self):
		return len(self.tags)
	
	def set_tag_usage_changed_listener(self, callback):
		self.on_tag_usage_changed = callback
	
	def format(self, config: CaptionFormatConfig):
		"""
		設定に従ってキャプションを文字列化します。

		Args:
			config (CaptionFormatConfig): フォーマット設定。

		Returns:
			str: フォーマットされたキャプション文字列。
		"""
		return config.format_delimiter.join([tag.format(config) for tag in self.tags])
	
	@staticmethod
	def parse(
			text: str,
			config: CaptionFormatConfig,
	) -> 'Caption':
		"""
		テキストをパースしてCaptionオブジェクトを生成します。
		括弧による重み付けや、(tag:1.5) のような明示的な重み指定に対応しています。

		Args:
			text (str): パース対象のテキスト。
			config (CaptionFormatConfig): パース設定。

		Returns:
			Caption: 生成されたCaptionオブジェクト。
		"""
		tags = []
		if not text:
			return Caption()
		
		# --- トークナイズ処理 ---
		# 文字列を1文字ずつ読み込み、括弧や区切り文字で分割します。
		tokens = []
		buffer = ""
		iterator = iter(text)
		
		while True:
			try:
				char = next(iterator)
			except StopIteration:
				break
			
			if char == '\\':
				# エスケープ文字の処理
				try:
					next_char = next(iterator)
					buffer += next_char
				except StopIteration:
					buffer += char
			elif char in ('(', ')', '[', ']') or char == config.delimiter:
				if buffer.strip():
					tokens.append(buffer.strip())
				tokens.append(char)
				buffer = ""
			else:
				buffer += char
		
		if buffer.strip():
			tokens.append(buffer.strip())
		
		# --- パース処理 ---
		# トークン列を再帰的に処理し、重みを計算しながらタグを抽出します。
		token_iterator = iter(tokens)
		
		def recursive_parse(current_weight):
			while True:
				try:
					token = next(token_iterator)
				except StopIteration:
					break
				
				if token == '(':
					# 丸括弧開始: 重みを増加させて再帰呼び出し
					recursive_parse(current_weight * config.posi_weight_ratio)
				elif token == '[':
					# 角括弧開始: 重みを減少させて再帰呼び出し
					recursive_parse(current_weight * config.nega_weight_ratio)
				elif token == ')' or token == ']':
					# 括弧終了: 現在の階層を終了
					return
				elif token == config.delimiter:
					continue
				else:
					# 通常のタグテキスト
					weight = current_weight
					tag_text = token
					
					# (tag:weight) のような明示的な重み指定のチェック
					if ':' in token:
						parts = token.rsplit(':', 1)
						try:
							explicit_weight = float(parts[1])
							tag_text = parts[0]
							# 明示的な重み指定がある場合は、計算された重みを上書き
							weight = explicit_weight
						except ValueError:
							pass
					
					tags.append(Tag(tag_text, weight))
		
		recursive_parse(1.0)
		
		return Caption(tags)
	
	# === 編集操作 ===
	
	def append_tags(self, tags):
		self.tags.extend(tags)
		for tag in tags:
			if self.counter[tag.text] == 0 and self.on_tag_usage_changed:
				self.on_tag_usage_changed(tag.text, True)
			self.counter[tag.text] += 1
	
	def insert_tags(self, position, tags):
		self.tags[position:position] = tags
		for tag in tags:
			if self.counter[tag.text] == 0 and self.on_tag_usage_changed:
				self.on_tag_usage_changed(tag.text, True)
			self.counter[tag.text] += 1
	
	def delete_tags(self, positions):
		for i in positions:
			tag = self.tags.pop(i)
			self.counter[tag.text] -= 1
			if self.counter[tag.text] == 0 and self.on_tag_usage_changed:
				self.on_tag_usage_changed(tag.text, False)
	
	def move_tag(self, old_position, new_position):
		tag = self.tags.pop(old_position)
		self.tags.insert(new_position, tag)
	
	def mutate_tag(self, position, new_tag):
		old_tag = self.tags[position]
		self.tags[position] = new_tag
		if old_tag.text != new_tag.text:
			self.counter[old_tag.text] -= 1
			if self.counter[old_tag.text] == 0 and self.on_tag_usage_changed:
				self.on_tag_usage_changed(old_tag.text, False)
			
			if self.counter[new_tag.text] == 0 and self.on_tag_usage_changed:
				self.on_tag_usage_changed(new_tag.text, True)
			self.counter[new_tag.text] += 1
