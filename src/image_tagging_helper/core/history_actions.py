from abc import abstractmethod, ABC
from typing import List

from src.image_tagging_helper.core.caption import TagHolder, clone_tag_list
from src.image_tagging_helper.core.dataset import Dataset, Caption

@abstractmethod
class HistoryAction(ABC):
	def __init__(self, dataset: Dataset):
		self.dataset = dataset
	
	def apply(self):
		return NotImplemented
	
	def revert(self):
		return NotImplemented

class AppendAction(HistoryAction):
	def __init__(
			self, dataset, targets: List[int], tags: List[TagHolder]
	):
		super().__init__(dataset)
		self.targets = targets
		self.tags = clone_tag_list(tags)
	
	def apply(self):
		for target in self.targets:
			caption: Caption = self.dataset[target].caption
			caption.extend(clone_tag_list(self.tags))
	
	def revert(self):
		for target in self.targets:
			caption: Caption = self.dataset[target].caption
			caption.remove(len(caption) - len(self.tags), len(self.tags))

class InsertAction(HistoryAction):
	def __init__(
			self, dataset: Dataset, target: int, index: int, tags: List[TagHolder]
	):
		super().__init__(dataset)
		self.target = target
		self.index = index
		self.tags = clone_tag_list(tags)
	
	def apply(self):
		caption: Caption = self.dataset[self.target].caption
		caption.insert(self.index, clone_tag_list(self.tags))
	
	def revert(self):
		caption: Caption = self.dataset[self.target].caption
		caption.remove(self.index, len(self.tags))

class MoveAction(HistoryAction):
	def __init__(
			self, dataset: Dataset, target: int, from_index: int, to_index: int
	):
		super().__init__(dataset)
		self.target = target
		self.from_index = from_index
		self.to_index = to_index
	
	def apply(self):
		caption: Caption = self.dataset[self.target].caption
		caption.move(self.from_index, self.to_index)
	
	def revert(self):
		caption: Caption = self.dataset[self.target].caption
		caption.move(self.to_index, self.from_index)

class RemoveAtAction(HistoryAction):
	def __init__(
			self, dataset: Dataset, target: int, indices: List[int]
	):
		super().__init__(dataset)
		self.target = target
		self.indices = sorted(indices)
		self.old_tags = [
			self.dataset[target].caption[index].clone() for index in self.indices
		]
	
	def apply(self):
		caption: Caption = self.dataset[self.target].caption
		for index in reversed(self.indices):
			caption.remove(index)
	
	def revert(self):
		caption: Caption = self.dataset[self.target].caption
		for index, old_tag in zip(self.indices, self.old_tags):
			caption.insert(index, old_tag.clone())

class TagMutateAction(HistoryAction):
	def __init__(
			self, dataset: Dataset, target: int, index: int, new_tag: TagHolder
	):
		super().__init__(dataset)
		self.target = target
		self.index = index
		self.old_tag = dataset[target].caption[index].clone()
		self.new_tag = new_tag.clone()
	
	def apply(self):
		caption: Caption = self.dataset[self.target].caption
		caption.set(self.index, self.new_tag.clone())
	
	def revert(self):
		caption: Caption = self.dataset[self.target].caption
		caption.set(self.index, self.old_tag.clone())
