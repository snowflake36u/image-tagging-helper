from typing import List
from dataclasses import dataclass

@dataclass
class TagHolder:
	text: str
	weight: float
	
	def format(self):
		if self.weight == 1:
			return self.text
		return f"({self.text}:{self.weight})"
	
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
	
	def format(self, delimiter=', '):
		return delimiter.join([tag.format() for tag in self.tags])
	
	def parse(self, text: str, delimiter=',', positive_amp=1.1, negative_scale=0.9):
		# タグ構文
		#   tag            : 1倍
		#   (tag)          : positive_amp 倍
		#   [tag]          : negative_amp 倍
		#   (tag:weight)   : weight 倍
		# 括弧は入れ子可能。
		# 異なる括弧内のテキストは異なるタグとして扱われる。
		# タグのテキスト両端にあるスペースは削除される。
		pass
	
	def add(self, tags: List[TagHolder]):
		self.tags.extend(TagHolder.clone_list(tags))
	
	def insert(self, tags: List[TagHolder], index: int):
		self.tags[index:index] = TagHolder.clone_list(tags)
	
	def remove(self, index: int, count: int = 1):
		self.tags[index:index + count] = []
	
	def move(self, from_index: int, to_index: int):
		self.tags.insert(to_index, self.tags.pop(from_index))
