from abc import abstractmethod, ABC
from typing import List

from src.image_tagging_helper.core.caption import TagHolder
from src.image_tagging_helper.core.dataset import Dataset

@abstractmethod
class HistoryAction(ABC):
	def apply(self, dataset: Dataset):
		return NotImplemented
	
	def revert(self, dataset: Dataset):
		return NotImplemented

class AddAction(HistoryAction):
	def __init__(self, targets: List[int], tags: List[TagHolder]):
		self.targets = targets
		self.tags = tags
	
	def apply(self, dataset: Dataset):
		for target in self.targets:
			caption = dataset[target].caption
			caption.extend(self.tags)
	
	def revert(self, dataset: Dataset):
		for target in self.targets:
			caption = dataset[target].caption
			caption.remove(len(caption) - len(self.tags), len(self.tags))

class InsertAction(HistoryAction):
	def __init__(self, target: int, index: int, tags: List[TagHolder]):
		self.target = target
		self.index = index
		self.tags = tags
	
	def apply(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption.insert(self.index, self.tags)
	
	def revert(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption.remove(self.index, len(self.tags))

class MoveAction(HistoryAction):
	def __init__(self, target: int, from_index: int, to_index: int):
		self.target = target
		self.from_index = from_index
		self.to_index = to_index
	
	def apply(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption.move(self.from_index, self.to_index)
	
	def revert(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption.move(self.to_index, self.from_index)

class RemoveAtAction(HistoryAction):
	def __init__(self, target: int, indices: List[int]):
		self.target = target
		self.indices = sorted(indices)
	
	def apply(self, dataset: Dataset):
		caption = dataset[self.target].caption
		for index in reversed(self.indices):
			caption.remove(index)

class TagMutateAction(HistoryAction):
	def __init__(self, target: int, index: int, old_tag: TagHolder, new_tag: TagHolder):
		self.target = target
		self.index = index
		self.old_tag = old_tag
		self.new_tag = new_tag
	
	def apply(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption[self.index] = self.new_tag
	
	def revert(self, dataset: Dataset):
		caption = dataset[self.target].caption
		caption[self.index] = self.old_tag
