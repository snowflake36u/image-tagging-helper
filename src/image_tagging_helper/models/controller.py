from typing import TYPE_CHECKING

from src.image_tagging_helper.models.history_actions import (
	AppendTagsAction, InsertTagsAction, MoveTagAction,
	DeleteTagsAction, EditTagAction, CleanAction,
)

if TYPE_CHECKING:
	from src.image_tagging_helper.models.dataset import Dataset
	from src.image_tagging_helper.models.caption import Tag

class DatasetController:
	"""
	Datasetを操作するためのアクションを管理するコントローラー。

	UIからのリクエストを受け取り、対応するアクションを実行します。
	アクションの実行はhistoryモジュールを通じて行われ、
	これにより操作のUndo/Redoが可能になります。
	"""
	
	def __init__(self, dataset: 'Dataset', sender: str | None = None):
		"""
		Args:
			dataset: 操作対象のDatasetオブジェクト。
			sender (str): 操作の送信元ID。
		"""
		self.dataset = dataset
		self.sender = sender
	
	def append_tags(self, target: int, tags: tuple['Tag', ...]):
		"""
		キャプションの末尾にタグを追加します。

		Args:
			 target: 対象キャプションのインデックス。
			 tags: 追加するタグのタプル。
		"""
		action = AppendTagsAction.create(self.dataset, target, tags)
		self.dataset.execute(action, self.sender)
	
	def insert_tags(self, target: int, position: int, tags: tuple['Tag', ...]):
		"""
		キャプションの指定位置にタグを挿入します。

		Args:
			 target: 対象キャプションのインデックス。
			 position: 挿入位置。
			 tags: 挿入するタグのタプル。
		"""
		action = InsertTagsAction.create(self.dataset, target, position, tags)
		self.dataset.execute(action, self.sender)
	
	def move_tag(self, target: int, old_position: int, new_position: int):
		"""
		キャプション内のタグを移動します。

		Args:
			 target: 対象キャプションのインデックス。
			 old_position: 移動元の位置。
			 new_position: 移動先の位置。
		"""
		action = MoveTagAction.create(self.dataset, target, old_position, new_position)
		self.dataset.execute(action, self.sender)
	
	def delete_tags(self, target: int, positions: tuple[int, ...]):
		"""
		キャプションからタグを削除します。

		Args:
			 target: 対象キャプションのインデックス。
			 positions: 削除するタグの位置のタプル。
		"""
		action = DeleteTagsAction.create(self.dataset, target, positions)
		self.dataset.execute(action, self.sender)
	
	def edit_tag(self, target: int, position: int, new_tag: 'Tag'):
		"""
		キャプションの特定のタグを編集します。

		Args:
			 target: 対象キャプションのインデックス。
			 position: 編集するタグの位置。
			 new_tag: 新しいタグオブジェクト。
		"""
		action = EditTagAction.create(self.dataset, target, position, new_tag)
		self.dataset.execute(action, self.sender)
	
	def clean(self):
		"""
		データセット内の不要なタグ（空文字や重複）を削除します。
		"""
		action = CleanAction.create(self.dataset)
		if action:
			self.dataset.execute(action, self.sender)
	
	# === 変更履歴の管理 ===
	
	def undo(self):
		"""
		直前の操作を取り消します。
		"""
		self.dataset.undo(self.sender)
	
	def redo(self):
		"""
		取り消した操作をやり直します。
		"""
		self.dataset.redo(self.sender)
	
	def can_undo(self) -> bool:
		return self.dataset.can_undo()
	
	def can_redo(self) -> bool:
		return self.dataset.can_redo()
