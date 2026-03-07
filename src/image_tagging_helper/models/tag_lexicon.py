from dataclasses import dataclass
from typing import Iterable

@dataclass
class TagCategory:
	tag: str
	category: str

class TagLexicon:
	def __init__(self):
		self.n_categories = 0
		# [ category, ... ]
		self.categories: list[str] = []
		# { tag: category_index }
		self.tag_category_indices: dict[str, int] = { }
	
	def set_lexicon(self, lexicon: Iterable[TagCategory]):
		categories = []
		tag_category_indices = { }
		# { category: category_index }
		category_indices: dict[str, int] = { }
		
		n_category = 0
		for item in lexicon:
			tag, category = item.tag, item.category
			
			if tag in tag_category_indices:
				# 同じタグが2回以上現れた場合は無視する
				continue
			
			if category in category_indices:
				# カテゴリが既に登録されている場合はそれをそのまま設定する
				tag_category_indices[tag] = category_indices[category]
			else:
				# 新しいカテゴリの場合はそれを登録する
				categories.append(category)
				category_indices[category] = n_category
				tag_category_indices[tag] = n_category
				n_category += 1
		
		self.n_categories = n_category
		self.categories = categories
		self.tag_category_indices = tag_category_indices
	
	def get_tag_category(self, tag_text):
		if tag_text in self.tag_category_indices:
			return self.categories[self.tag_category_indices[tag_text]]
		else:
			return None
	
	def get_tag_order(self, tag_text):
		return self.tag_category_indices.get(tag_text, self.n_categories)
