import json
import os
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
	
	def get_lexicon(self) -> list[TagCategory]:
		"""現在のタグ情報をTagCategoryのリストとして取得します。"""
		result = []
		for tag, cat_idx in self.tag_category_indices.items():
			category = self.categories[cat_idx]
			result.append(TagCategory(tag, category))
		return result
	
	def load(self, path: str):
		"""指定されたパスからJSON形式でタグ情報を読み込みます。"""
		if not os.path.exists(path):
			return
		
		try:
			with open(path, 'r', encoding='utf-8') as f:
				data = json.load(f)
			
			lexicon = []
			if isinstance(data, list):
				for item in data:
					category = item.get('category')
					tags = item.get('tags')
					if category and isinstance(tags, list):
						for tag in tags:
							lexicon.append(TagCategory(tag, category))
			
			self.set_lexicon(lexicon)
		except (json.JSONDecodeError, OSError):
			pass
	
	def save(self, path: str):
		"""指定されたパスにJSON形式でタグ情報を保存します。"""
		# カテゴリごとにタグをまとめる
		category_tags_map = [[] for _ in range(self.n_categories)]
		for tag, cat_idx in self.tag_category_indices.items():
			category_tags_map[cat_idx].append(tag)
		
		data = []
		for i, category in enumerate(self.categories):
			tags = category_tags_map[i]
			tags.sort()
			data.append({
				'category': category,
				'tags': tags
			})
		
		try:
			with open(path, 'w', encoding='utf-8') as f:
				json.dump(data, f, indent=4, ensure_ascii=False)
		except OSError:
			pass
	
	def get_tag_category(self, tag_text):
		if tag_text in self.tag_category_indices:
			return self.categories[self.tag_category_indices[tag_text]]
		else:
			return None
	
	def get_tag_order(self, tag_text):
		return self.tag_category_indices.get(tag_text, self.n_categories)
