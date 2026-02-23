from abc import abstractmethod, ABC
from typing import List
import wx

from caption import TagHolder, Caption

class DatasetItem:
	def __init__(
			self,
			caption: Caption | None = None,
			path: str | None = None,
	):
		self.caption = caption
		self.path = path
	
	def load_image(self):
		pass

class Dataset:
	def __init__(self, items: List[DatasetItem]):
		self.items = items
		self.item_index = { x: i for i, x in enumerate(items) }
	
	def __len__(self):
		return len(self.items)
	
	def __getitem__(self, index: int | slice):
		return self.items[index]

