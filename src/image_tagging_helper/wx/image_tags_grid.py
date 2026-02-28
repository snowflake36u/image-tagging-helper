import wx
import wx.grid

from src.image_tagging_helper.models.dataset import Dataset
from src.image_tagging_helper.models.caption import Tag
from src.image_tagging_helper.models.controller import DatasetController
from src.image_tagging_helper.models.diff import (
	DatasetDiff, AppendDiff, InsertDiff, MoveDiff, DeleteDiff, MutateTagDiff, BatchDiff
)

class ImageTagsGrid(wx.grid.Grid):
	"""画像のタグを表示・編集するためのグリッドコントロール。
	
	Datasetの変更を監視し、グリッドの内容を同期させます。
	"""
	SENDER_ID = 'grid'
	
	def __init__(self, parent):
		"""ImageTagsGridを初期化します。

		Args:
			parent: 親ウィンドウ。
		"""
		super().__init__(parent, wx.ID_ANY)
		self.dataset: Dataset | None = None
		self.controller: DatasetController | None = None
		self.item_index: int | None = None
		
		self._init_grid()
		
		self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
	
	def _init_grid(self):
		"""グリッドの初期設定を行います。
		
		列の作成、ラベルの設定、列幅の調整、行ラベルの非表示、
		行サイズのドラッグ無効化、選択モードの設定を行います。
		"""
		self.CreateGrid(0, 2)
		self.SetColLabelValue(0, "Tag")
		self.SetColLabelValue(1, "Weight")
		# self.SetColLabelValue(0, __("label:tag"))
		# self.SetColLabelValue(1, __("label:weight"))
		self.SetColSize(0, 150)
		self.SetColSize(1, 50)
		self.SetRowLabelSize(0)
		self.EnableDragRowSize(False)
		# 選択モードを行選択にする
		self.SetSelectionMode(wx.grid.Grid.SelectCells)
	
	def set_dataset(self, dataset: Dataset | None):
		"""表示対象のデータセットを設定します。

		以前のデータセットのリスナーを解除し、新しいデータセットにリスナーを登録します。
		その後、グリッドを更新します。

		Args:
			dataset: 設定するDatasetオブジェクト。Noneの場合はクリアされます。
		"""
		if self.dataset:
			self.dataset.remove_listener(self.on_model_changed)
		
		self.dataset = dataset
		if dataset:
			self.controller = dataset.get_controller(self.SENDER_ID)
			self.dataset.add_listener(self.on_model_changed)
		
		self.refresh_grid()
	
	def on_cell_changed(self, evt):
		r = evt.GetRow()
		try:
			weight = float(self.GetCellValue(r, 1))
		except ValueError:
			weight = 1.0  # Default or handle error appropriately
		
		new_tag = Tag(
			self.GetCellValue(r, 0), weight
		)
		
		if self.controller and self.item_index is not None:
			self.controller.edit_tag(self.item_index, r, new_tag)
		
		evt.Skip()
	
	def on_model_changed(self, sender, diff: DatasetDiff):
		"""Datasetからの変更通知を受け取った際の処理です。

		Diffの種類に応じて、グリッドの更新メソッドを呼び出します。
		自身が送信元の変更は無視します。

		Args:
			sender: 変更通知の送信元ID。
			diff: 適用された変更内容を表すDatasetDiffオブジェクト。
		"""
		if sender == self.SENDER_ID:
			return
		
		if isinstance(diff, BatchDiff):
			self.BeginBatch()
			try:
				self._apply_diff(diff)
			finally:
				self.EndBatch()
		else:
			self._apply_diff(diff)
	
	def _apply_diff(self, diff: DatasetDiff):
		"""Diffを適用する内部メソッド。"""
		if isinstance(diff, AppendDiff):
			self.append_tags(diff.target, diff.tags)
		elif isinstance(diff, InsertDiff):
			self.insert_tags(diff.target, diff.position, diff.tags)
		elif isinstance(diff, MoveDiff):
			self.move_tag(diff.target, diff.old_position, diff.new_position)
		elif isinstance(diff, DeleteDiff):
			self.delete_tags(diff.target, diff.positions)
		elif isinstance(diff, MutateTagDiff):
			self.mutate_tag(diff.target, diff.position, diff.new_tag)
		elif isinstance(diff, BatchDiff):
			for child in diff.children:
				self._apply_diff(child)
	
	def switch_item(self, index: int):
		"""表示対象の画像インデックスを設定し、グリッドを更新します。

		Args:
			index: 表示する画像のインデックス。
		"""
		self.item_index = index
		self.refresh_grid()
	
	def refresh_grid(self):
		"""グリッドの内容を現在のデータセットとインデックスに基づいて完全に更新します。
		
		既存の行をすべて削除し、現在のキャプションのタグ情報を再設定します。
		データセットやインデックスが未設定の場合、またはインデックスが範囲外の場合は何もしません。
		"""
		
		if self.GetNumberRows() > 0:
			self.DeleteRows(0, self.GetNumberRows())
		
		if self.dataset is None or self.item_index is None:
			return
		
		if self.item_index < 0 or self.item_index >= len(self.dataset):
			return
		
		caption = self.dataset[self.item_index].caption
		
		if not caption.tags:
			return
		
		self.AppendRows(len(caption.tags))
		
		for i, tag in enumerate(caption.tags):
			self.SetCellValue(i, 0, tag.text)
			weight_str = f'{tag.weight:.2f}' if tag.weight is not None else ''
			self.SetCellValue(i, 1, weight_str)
	
	def append_tags(self, target: int, tags: tuple[Tag, ...]):
		"""タグを末尾に追加します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			tags: 追加するタグのタプル。
		"""
		if self.item_index != target:
			return
		
		start_row = self.GetNumberRows()
		self.AppendRows(len(tags))
		
		for i, tag in enumerate(tags):
			row = start_row + i
			self.SetCellValue(row, 0, tag.text)
			weight_str = f'{tag.weight:.2f}' if tag.weight is not None else ''
			self.SetCellValue(row, 1, weight_str)
	
	def insert_tags(self, target: int, position: int, tags: tuple[Tag, ...]):
		"""指定位置にタグを挿入します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			position: 挿入位置のインデックス。
			tags: 挿入するタグのタプル。
		"""
		if self.item_index != target:
			return
		
		self.InsertRows(position, len(tags))
		
		for i, tag in enumerate(tags):
			row = position + i
			self.SetCellValue(row, 0, tag.text)
			weight_str = f'{tag.weight:.2f}' if tag.weight is not None else ''
			self.SetCellValue(row, 1, weight_str)
	
	def move_tag(self, target: int, old_position: int, new_position: int):
		"""タグの位置を移動します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			old_position: 移動元のインデックス。
			new_position: 移動先のインデックス。
		"""
		if self.item_index != target:
			return
		
		if old_position == new_position:
			return
		
		tag_text = self.GetCellValue(old_position, 0)
		tag_weight = self.GetCellValue(old_position, 1)
		
		self.DeleteRows(old_position, 1)
		self.InsertRows(new_position, 1)
		
		self.SetCellValue(new_position, 0, tag_text)
		self.SetCellValue(new_position, 1, tag_weight)
	
	def delete_tags(self, target: int, positions: tuple[int, ...]):
		"""指定された位置のタグを削除します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			positions: 削除するタグの位置のリスト。降順にソート済みである必要があります。
		"""
		if self.item_index != target:
			return
		
		for pos in positions:
			self.DeleteRows(pos, 1)
	
	def mutate_tag(self, target: int, position: int, new_tag: Tag):
		"""指定位置のタグの内容を更新します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			position: 更新するタグの位置。
			new_tag: 新しいタグオブジェクト。
		"""
		if self.item_index != target:
			return
		
		self.SetCellValue(position, 0, new_tag.text)
		weight_str = f'{new_tag.weight:.2f}' if new_tag.weight is not None else ''
		self.SetCellValue(position, 1, weight_str)
