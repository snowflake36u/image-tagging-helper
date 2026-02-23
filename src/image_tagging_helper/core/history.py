from abc import abstractmethod, ABC
from typing import List
from collections import deque

from src.image_tagging_helper.core.caption import TagHolder
from src.image_tagging_helper.core.dataset import Dataset
from src.image_tagging_helper.core.history_actions import HistoryAction

class HistoryManager:
	def __init__(self):
		self.index = 0
		self.actions: deque[HistoryAction] = deque()
	
	@property
	def can_undo(self):
		return self.index > 0
	
	@property
	def can_redo(self):
		return self.index < len(self.actions)
	
	def undo(self, dataset: Dataset):
		if len(self.actions) == 0:
			return
		action = self.actions.pop()
		action.revert(dataset)
		self.index -= 1
	
	def redo(self, dataset: Dataset):
		if self.index == len(self.actions):
			return
		action = self.actions[self.index]
		action.apply(dataset)
		self.index += 1
	
	def apply(self, dataset: Dataset, action: HistoryAction):
		while self.index < len(self.actions):
			self.actions.pop()
		
		self.actions.append(action)
		action.apply(dataset)
		self.index += 1
