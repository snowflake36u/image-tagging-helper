from typing import List
from dataclasses import dataclass

class CaptionFormatConfig:
	def __init__(
			self,
			*,
			delimiter=',',
			posi_weight_ratio=1.1,
			nega_weight_ratio=0.9,
			ommittable_levels=5,
	):
		self.delimiter = delimiter
		self.posi_weight_ratio = posi_weight_ratio
		self.nega_weight_ratio = nega_weight_ratio
		
		self.omittable_weights = {
			**{ posi_weight_ratio ** i: i for i in range(ommittable_levels) },
			**{ nega_weight_ratio ** i: -i for i in range(ommittable_levels) },
		}

def escape_for_tag(text):
	return text.replace('(', r'\(').replace(')', r'\)') \
		.replace('[', r'\[').replace(']', r'\]')

@dataclass
class TagHolder:
	text: str
	weight: float
	
	def format(self, config: CaptionFormatConfig):
		text = escape_for_tag(self.text)
		
		if self.weight == 1:
			return text
		
		if self.weight in config.omittable_weights:
			level = config.omittable_weights[self.weight]
			if level < 0:
				return f"{'[' * -level}{text}{']' * -level}"
			else:
				return f"({text}:{self.weight})"
		
		return f"({text}:{self.weight})"
	
	def clone(self) -> 'TagHolder':
		return TagHolder(self.text, self.weight)
	
	@staticmethod
	def clone_list(set: List['TagHolder']) -> List['TagHolder']:
		return [tag.clone() for tag in set]

class Caption:
	def __init__(self, tags: List[TagHolder] | None = None):
		if tags is None:
			tags = []
		self.tags = tags
	
	def __items__(self, index: int | slice):
		return self.tags[index]
	
	def __len__(self):
		return len(self.tags)
	
	def format(self, config: CaptionFormatConfig):
		return config.delimiter.join([tag.format(config) for tag in self.tags])
	
	@staticmethod
	def parse(text: str, config: CaptionFormatConfig) -> 'Caption':
		tags = []
		if not text:
			return Caption()
		
		# トークナイズ
		tokens = []
		buffer = ""
		iterator = iter(text)
		
		while True:
			try:
				char = next(iterator)
			except StopIteration:
				break
			
			if char == '\\':
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
		
		# パース
		token_iterator = iter(tokens)
		
		def recursive_parse(current_weight):
			while True:
				try:
					token = next(token_iterator)
				except StopIteration:
					break
				
				if token == '(':
					recursive_parse(current_weight * config.posi_weight_ratio)
				elif token == '[':
					recursive_parse(current_weight * config.nega_weight_ratio)
				elif token == ')' or token == ']':
					return
				elif token == config.delimiter:
					continue
				else:
					# タグテキスト
					weight = current_weight
					tag_text = token
					
					# (tag:weight) のような明示的な重み指定のチェック
					if ':' in token:
						parts = token.rsplit(':', 1)
						try:
							explicit_weight = float(parts[1])
							tag_text = parts[0]
							weight = explicit_weight
						except ValueError:
							pass
					
					tags.append(TagHolder(tag_text, weight))
		
		recursive_parse(1.0)
		
		return Caption(tags)
	
	def clean(self, remove_blanks=True, remove_dups=True) -> None:
		tags = self.tags
		
		if remove_blanks:
			for i in reversed(range(len(self.tags))):
				if not tags[i].text:
					del self.remove[i]
		
		if remove_dups:
			seen = set()
			i = 0
			n = len(self.tags)
			while i < n:
				if tags[i].text in seen:
					del self.remove[i]
					n -= 1
				else:
					seen.add(tags[i].text)
					i += 1
	
	def add(self, tags: List[TagHolder]):
		self.tags.extend(TagHolder.clone_list(tags))
	
	def insert(self, tags: List[TagHolder], index: int):
		self.tags[index:index] = TagHolder.clone_list(tags)
	
	def remove(self, index: int, count: int = 1):
		self.tags[index:index + count] = []
	
	def move(self, from_index: int, to_index: int):
		self.tags.insert(to_index, self.tags.pop(from_index))
