"""
TagLexicon File Formats

# JSON での記述例
```
{
	"wildcards": {
		"color": ["red", "blue"]
	},
	"categories": {
		"Target": ["1girl", "1boy"],
		"Hair": ["no hair", "{color} hair"]
	}
}
```

# YAML での記述例
```
wildcards:
  color: ["red", "blue"]
categories:
  Target:
    - 1girl
    - 1boy
  Hair:
    - no hair
    - "{color} hair"
```
"""
import json
import os
import re
import itertools
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
		
		# wildcardsと展開前のタグ情報を保持する
		self.wildcards: dict[str, list[str]] = { }
		self.raw_categories: dict[str, list[str]] = { }
	
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
		"""指定されたパスからタグ情報を読み込みます。拡張子によって形式を判断します。
		
		読み込みに失敗した場合、例外を送出します。
		"""
		ext = os.path.splitext(path)[1].lower()
		if ext == '.json':
			self._load_json(path)
		elif ext in ('.yaml', '.yml'):
			self._load_yaml(path)
		else:
			raise ValueError(f"Unsupported file extension: {ext}")
	
	def _expand_wildcards(self, tags: list[str], wildcards: dict[str, list[str]]) -> list[str]:
		expanded_tags = []
		for tag in tags:
			# Find all wildcard keys in the tag
			try:
				keys = set(re.findall(r'\{([a-zA-Z0-9_]+)\}', tag))
			except TypeError:
				raise ValueError(f"Invalid tag format: {tag}")
			
			# Filter keys that exist in the wildcards dictionary
			valid_keys = [k for k in keys if k in wildcards]
			
			if not valid_keys:
				expanded_tags.append(tag)
				continue
			
			# Generate all combinations of wildcard values
			combinations = itertools.product(*(wildcards[k] for k in valid_keys))
			
			for combo in combinations:
				temp_tag = tag
				for k, v in zip(valid_keys, combo):
					temp_tag = temp_tag.replace(f'{{{k}}}', v)
				expanded_tags.append(temp_tag)
		
		return expanded_tags
	
	def _load_json(self, path: str):
		with open(path, 'r', encoding='utf-8') as f:
			data = json.load(f)
		
		if not isinstance(data, dict):
			raise ValueError("Invalid JSON format: root must be a dictionary")
		
		wildcards = data.get('wildcards', { })
		raw_categories = data.get('categories', { })
		lexicon = []
		
		if isinstance(raw_categories, dict):
			for category, tags in raw_categories.items():
				if isinstance(tags, list):
					expanded_tags = self._expand_wildcards(tags, wildcards)
					for tag in expanded_tags:
						lexicon.append(TagCategory(tag, category))
		
		self.wildcards = wildcards
		self.raw_categories = raw_categories
		self.set_lexicon(lexicon)
	
	def _load_yaml(self, path: str):
		with open(path, 'r', encoding='utf-8') as f:
			data = yaml.safe_load(f)
		
		if not isinstance(data, dict):
			raise ValueError("Invalid YAML format: root must be a dictionary")
		
		wildcards = data.get('wildcards', { })
		raw_categories = data.get('categories', { })
		lexicon = []
		
		if isinstance(raw_categories, dict):
			for category, tags in raw_categories.items():
				if isinstance(tags, list):
					expanded_tags = self._expand_wildcards(tags, wildcards)
					for tag in expanded_tags:
						lexicon.append(TagCategory(tag, category))
		
		self.wildcards = wildcards
		self.raw_categories = raw_categories
		self.set_lexicon(lexicon)
	
	def save(self, path: str):
		"""指定されたパスにタグ情報を保存します。拡張子によって形式を判断します。"""
		ext = os.path.splitext(path)[1].lower()
		if ext == '.json':
			self._save_json(path)
		elif ext in ('.yaml', '.yml'):
			self._save_yaml(path)
		else:
			raise ValueError(f"Unsupported file extension: {ext}")
	
	def _save_json(self, path: str):
		data = {
			"wildcards": self.wildcards,
			"categories": self.raw_categories
		}
		
		with open(path, 'w', encoding='utf-8') as f:
			json.dump(data, f, indent=2, ensure_ascii=False)
	
	def _save_yaml(self, path: str):
		data = {
			"wildcards": self.wildcards,
			"categories": self.raw_categories
		}
		
		with open(path, 'w', encoding='utf-8') as f:
			yaml.dump(data, f, allow_unicode=True, sort_keys=False)
	
	def get_tag_category(self, tag_text):
		if tag_text in self.tag_category_indices:
			return self.categories[self.tag_category_indices[tag_text]]
		else:
			return None
	
	def get_tag_category_order(self, tag_text):
		return self.tag_category_indices.get(tag_text, self.n_categories)
