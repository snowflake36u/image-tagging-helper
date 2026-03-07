"""
TagLexicon File Formats

# JSON の記述例
```
[
	{
		"category": "Category Name 1",
		"tags": ["tag1", "tag2"]
	},
	{
		"category": "Category Name 2",
		"tags": ["tag3", "tag4", "tag5"]
	},
]
```

# YAML の記述例
```
Category Name 1:
  - tag1
  - tag2
  
Category Name 2:
  - tag3
  - tag4
  - tag5
```

# Markdown の記述例
```
# Category Name 1
- tag1
- tag2

# Category Name 2
- tag3
- tag4
- tag5
```
"""
import json
import os
from dataclasses import dataclass
from typing import Iterable
import yaml

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
		"""指定されたパスからタグ情報を読み込みます。拡張子によって形式を判断します。"""
		if not os.path.exists(path):
			return
		
		ext = os.path.splitext(path)[1].lower()
		if ext == '.json':
			self._load_json(path)
		elif ext in ('.yaml', '.yml'):
			self._load_yaml(path)
		elif ext == '.md':
			self._load_markdown(path)
	
	def _load_json(self, path: str):
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
	
	def _load_yaml(self, path: str):
		try:
			with open(path, 'r', encoding='utf-8') as f:
				data = yaml.safe_load(f)
			
			lexicon = []
			if isinstance(data, dict):
				for category, tags in data.items():
					if isinstance(tags, list):
						for tag in tags:
							lexicon.append(TagCategory(tag, category))
			
			self.set_lexicon(lexicon)
		except (yaml.YAMLError, OSError):
			pass
	
	def _load_markdown(self, path: str):
		try:
			with open(path, 'r', encoding='utf-8') as f:
				lines = f.readlines()
			
			lexicon = []
			current_category = None
			
			for line in lines:
				line = line.strip()
				if line.startswith('# '):
					current_category = line[2:].strip()
				elif line.startswith('- ') and current_category:
					tag = line[2:].strip()
					lexicon.append(TagCategory(tag, current_category))
			
			self.set_lexicon(lexicon)
		except OSError:
			pass

	def save(self, path: str):
		"""指定されたパスにタグ情報を保存します。拡張子によって形式を判断します。"""
		ext = os.path.splitext(path)[1].lower()
		if ext == '.json':
			self._save_json(path)
		elif ext in ('.yaml', '.yml'):
			self._save_yaml(path)
		elif ext == '.md':
			self._save_markdown(path)
	
	def _save_json(self, path: str):
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
	
	def _save_yaml(self, path: str):
		# カテゴリごとにタグをまとめる
		category_tags_map = [[] for _ in range(self.n_categories)]
		for tag, cat_idx in self.tag_category_indices.items():
			category_tags_map[cat_idx].append(tag)
		
		data = { }
		for i, category in enumerate(self.categories):
			tags = category_tags_map[i]
			tags.sort()
			data[category] = tags
		
		try:
			with open(path, 'w', encoding='utf-8') as f:
				yaml.dump(data, f, allow_unicode=True, sort_keys=False)
		except (yaml.YAMLError, OSError):
			pass
	
	def _save_markdown(self, path: str):
		# カテゴリごとにタグをまとめる
		category_tags_map = [[] for _ in range(self.n_categories)]
		for tag, cat_idx in self.tag_category_indices.items():
			category_tags_map[cat_idx].append(tag)
		
		try:
			with open(path, 'w', encoding='utf-8') as f:
				for i, category in enumerate(self.categories):
					f.write(f'# {category}\n')
					tags = category_tags_map[i]
					tags.sort()
					for tag in tags:
						f.write(f'- {tag}\n')
					f.write('\n')
		except OSError:
			pass
	
	def get_tag_category(self, tag_text):
		if tag_text in self.tag_category_indices:
			return self.categories[self.tag_category_indices[tag_text]]
		else:
			return None
	
	def get_tag_order(self, tag_text):
		return self.tag_category_indices.get(tag_text, self.n_categories)
