from typing import TYPE_CHECKING, Iterable, Sequence

from src.image_tagging_helper.models.history_actions import (
	AppendTagsAction, InsertTagsAction, MoveTagAction,
	DeleteTagsAction, EditTagAction, CleanAction,
	BatchAppendTagAction, BatchRemoveTagAction, BatchReplaceTagAction
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
			sender:
				操作の送信元を識別するためのID。
				主に、データ変更の通知イベントが無限ループに陥るのを防ぐために使用されます。
				例えば、UIコンポーネントAがデータを変更した場合、
				データセットは変更を通知します。この通知を受け取った他のUIコンポーネントは
				自身の表示を更新しますが、変更元のUIコンポーネントAは、
				自身が発行した変更通知を無視する必要があります。
				この`sender` IDを使うことで、自分自身に変更がすでに適用されているかどうかを判断できます。
				通常は、UIコンポーネントのユニークなID（`str(id(self))`など）を指定します。
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
	
	def remove_tags_at(self, target: int, positions: Sequence[int]):
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
	
	def remove_tag(self, target: int, tag_text: str):
		"""
		キャプションから特定のテキストを持つタグを削除します。

		Args:
			 target: 対象キャプションのインデックス。
			 tag_text: 削除するタグのテキスト。
		"""
		caption = self.dataset[target].caption
		positions = tuple(i for i, tag in enumerate(caption.tags) if tag.text == tag_text)
		if positions:
			self.remove_tags_at(target, positions)
	
	def batch_append_tags(self, targets: Iterable[int], tags: tuple['Tag', ...]):
		"""
		指定された複数のキャプションにタグを追加します。

		Args:
			 targets: 対象キャプションのインデックスのリスト。
			 tags: 追加するタグのタプル。
		"""
		action = BatchAppendTagAction.create(self.dataset, targets, tags)
		if action:
			self.dataset.execute(action, self.sender)
	
	def batch_remove_tags(self, targets: Iterable[int], tag_texts: tuple[str, ...]):
		"""
		指定された複数のキャプションから特定のタグを削除します。

		Args:
			 targets: 対象キャプションのインデックスのリスト。
			 tag_texts: 削除するタグのテキストのタプル。
		"""
		action = BatchRemoveTagAction.create(self.dataset, targets, tag_texts)
		if action:
			self.dataset.execute(action, self.sender)
	
	def batch_replace_tag(self, targets: Iterable[int], old_tag_text: str, new_tag: 'Tag', keep_weight=False):
		"""
		指定された複数のキャプション内の特定のタグを置換します。

		Args:
			 targets: 対象キャプションのインデックスのリスト。
			 old_tag_text: 置換対象のタグのテキスト。
			 new_tag: 新しいタグ。
		"""
		action = BatchReplaceTagAction.create(self.dataset, targets, old_tag_text, new_tag, keep_weight)
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
