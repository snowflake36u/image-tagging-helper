from typing import List
from src.image_tagging_helper.models.history_actions import HistoryAction

class HistoryManager:
	"""
	履歴（Undo/Redo）を管理するクラス。
	"""
	
	def __init__(self):
		self.undo_stack: List[HistoryAction] = []
		self.redo_stack: List[HistoryAction] = []
		self._saved_index = 0
	
	@property
	def is_dirty(self) -> bool:
		"""
		保存されていない変更があるかどうかを返します。
		"""
		return self._saved_index != len(self.undo_stack)
	
	def mark_saved(self):
		"""
		現在の状態を保存済みとしてマークします。
		"""
		self._saved_index = len(self.undo_stack)
	
	def push(self, action: HistoryAction, sender: str = None):
		"""
		新しいアクションを実行し、履歴に追加します。
		Redoスタックはクリアされます。
		
		Args:
			action (HistoryAction): 実行するアクション。
			sender (str): 操作の送信元ID。
		"""
		action.apply(sender)
		
		# 保存された状態からUndoして新しい操作を行った場合、
		# 以前の保存状態には戻れなくなるため、saved_indexを無効化する
		if self._saved_index > len(self.undo_stack):
			self._saved_index = -1
		
		self.undo_stack.append(action)
		self.redo_stack.clear()
	
	def undo(self, sender: str = None):
		"""
		直前の操作を取り消します。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		if not self.undo_stack:
			return
		
		action = self.undo_stack.pop()
		action.revert(sender)
		self.redo_stack.append(action)
	
	def redo(self, sender: str = None):
		"""
		取り消した操作をやり直します。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		if not self.redo_stack:
			return
		
		action = self.redo_stack.pop()
		action.apply(sender)
		self.undo_stack.append(action)
	
	def can_undo(self) -> bool:
		return len(self.undo_stack) > 0
	
	def can_redo(self) -> bool:
		return len(self.redo_stack) > 0
