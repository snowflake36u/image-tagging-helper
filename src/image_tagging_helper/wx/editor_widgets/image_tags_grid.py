import wx
import wx.grid
import io
import csv

from image_tagging_helper.models.dataset import Dataset
from image_tagging_helper.models.caption import Tag
from image_tagging_helper.models.controller import DatasetController
from image_tagging_helper.models.diff import (
	DatasetDiff, AppendDiff, InsertDiff, MoveDiff, DeleteDiff, MutateTagDiff, BatchDiff
)

from image_tagging_helper.i18n import __

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
		self.ui_driven_controller: DatasetController | None = None
		self.remote_controller: DatasetController | None = None
		self.item_index: int | None = None
		
		self._init_grid()
		
		self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
		self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
		self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.on_cell_left_click)
		self.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
		self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)
	
	def _init_grid(self):
		"""グリッドの初期設定を行います。
		
		列の作成、ラベルの設定、列幅の調整、行ラベルの非表示、
		行サイズのドラッグ無効化、選択モードの設定を行います。
		"""
		self.CreateGrid(0, 2)
		self.SetColLabelValue(0, __("label:tag"))
		self.SetColLabelValue(1, __("label:weight"))
		self.SetColSize(0, 150)
		self.SetColSize(1, 50)
		self.SetRowLabelSize(0)
		self.EnableDragRowSize(False)
		# 選択モードをセル選択にする
		self.SetSelectionMode(wx.grid.Grid.SelectCells)
	
	def set_dataset(self, dataset: Dataset | None):
		"""表示対象のデータセットを設定します。

		以前のデータセットのリスナーを解除し、新しいデータセットにリスナーを登録します。
		その後、グリッドを更新します。

		Args:
			dataset: 設定するDatasetオブジェクト。Noneの場合はクリアされます。
		"""
		if self.dataset:
			self.dataset.remove_diff_applied_listener(self.on_model_changed)
		
		self.dataset = dataset
		if dataset:
			self.ui_driven_controller = dataset.get_controller(self.SENDER_ID)
			self.remote_controller = dataset.get_controller()
			self.dataset.add_diff_applied_listener(self.on_model_changed)
		
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
		
		if self.ui_driven_controller and self.item_index is not None:
			self.ui_driven_controller.edit_tag(self.item_index, r, new_tag)
		
		evt.Skip()
	
	def on_key_down(self, event: wx.KeyEvent):
		"""キー入力イベントを処理します。

		タブキーが押された場合、コントロール間のフォーカス移動を行います。
		これにより、グリッド内でのセル移動のデフォルト動作をオーバーライドします。
		十字キー（Shiftなし）が押された場合、カーソル移動に合わせてセルを選択します。

		Args:
			event: wx.KeyEventオブジェクト。
		"""
		key_code = event.GetKeyCode()
		
		if key_code == wx.WXK_TAB:
			if event.ShiftDown():
				self.Navigate(wx.NAVDIR_PREVIOUS)
			else:
				self.Navigate(wx.NAVDIR_NEXT)
			return
		
		if key_code in (wx.WXK_UP, wx.WXK_DOWN, wx.WXK_LEFT, wx.WXK_RIGHT):
			if event.ShiftDown():
				event.Skip()
				return
			
			if event.ControlDown():
				event.Skip()
				wx.CallAfter(self._sync_selection_with_cursor)
				return
			
			# デフォルトのナビゲーションを無効にし、独自処理を行う
			current_row = self.GetGridCursorRow()
			current_col = self.GetGridCursorCol()
			
			new_row, new_col = current_row, current_col
			
			if key_code == wx.WXK_UP:
				new_row = max(0, current_row - 1)
			elif key_code == wx.WXK_DOWN:
				new_row = min(self.GetNumberRows() - 1, current_row + 1)
			elif key_code == wx.WXK_LEFT:
				new_col = max(0, current_col - 1)
			elif key_code == wx.WXK_RIGHT:
				new_col = min(self.GetNumberCols() - 1, current_col + 1)
			
			if new_row != current_row or new_col != current_col:
				self.focus_cell(new_row, new_col)
				self.MakeCellVisible(new_row, new_col)
			return
		
		if key_code == wx.WXK_DELETE:
			if self.dataset and self.item_index is not None:
				# ユーザー操作として実行するため、senderがNoneのコントローラーを取得して実行する
				# これにより、変更通知がUIに正しく反映される
				self.remote_controller.remove_tags_at(self.item_index, self.get_selected_rows())
			return
		
		event.Skip()
	
	def on_cell_left_click(self, event):
		"""左クリック時の処理。

		修飾キーがない場合、クリックされたセルを選択状態にします。
		"""
		if event.ShiftDown() or event.ControlDown():
			event.Skip()
			return
		
		row = event.GetRow()
		col = event.GetCol()
		self.focus_cell(row, col)
	
	def on_copy(self, event: wx.CommandEvent):
		"""
		選択されているセルの内容をTSV形式でクリップボードにコピーします。
		"""
		# 選択されているブロックを取得
		top_left = self.GetSelectionBlockTopLeft()
		bottom_right = self.GetSelectionBlockBottomRight()
		
		# 選択されているセルを取得
		selected_cells = self.GetSelectedCells()
		
		if not top_left and not selected_cells:
			# 単一セルの選択の場合 (カーソル位置)
			row = self.GetGridCursorRow()
			col = self.GetGridCursorCol()
			if row != -1 and col != -1:
				data = self.GetCellValue(row, col)
				self._copy_text_to_clipboard(data)
			return
		
		output = io.StringIO()
		writer = csv.writer(output, delimiter='\t')
		
		# 選択範囲の行と列を特定
		min_row, max_row = float('inf'), float('-inf')
		min_col, max_col = float('inf'), float('-inf')
		
		if top_left:
			for (r1, c1), (r2, c2) in zip(top_left, bottom_right):
				min_row = min(min_row, r1)
				max_row = max(max_row, r2)
				min_col = min(min_col, c1)
				max_col = max(max_col, c2)
		
		if selected_cells:
			for r, c in selected_cells:
				min_row = min(min_row, r)
				max_row = max(max_row, r)
				min_col = min(min_col, c)
				max_col = max(max_col, c)
		
		if min_row == float('inf'):  # No selection
			return
		
		# データを書き込み
		for r in range(min_row, max_row + 1):
			row_data = [self.GetCellValue(r, c) for c in range(min_col, max_col + 1)]
			writer.writerow(row_data)
		
		self._copy_text_to_clipboard(output.getvalue())
	
	def on_select_all(self, event: wx.CommandEvent):
		"""
		グリッド内のすべてのセルを選択します。
		"""
		self.SelectAll()
	
	def _copy_text_to_clipboard(self, text: str):
		"""
		指定されたテキストをクリップボードにコピーします。
		"""
		if not text:
			return
		
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData(wx.TextDataObject(text))
			wx.TheClipboard.Close()
	
	def _sync_selection_with_cursor(self):
		"""現在のカーソル位置に合わせて選択範囲を更新します。"""
		row = self.GetGridCursorRow()
		col = self.GetGridCursorCol()
		if 0 <= row < self.GetNumberRows() and 0 <= col < self.GetNumberCols():
			self.focus_cell(row, col)
	
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
		if self.GetNumberRows() > 0:
			self.focus_cell(0, 0)
	
	def focus_cell(self, row: int, col: int):
		"""指定されたセルを選択状態にし、カーソルを移動します。"""
		self.ClearSelection()
		self.SetGridCursor(row, col)
		self.SelectBlock(row, col, row, col)
	
	def get_selected_rows(self) -> list[int]:
		"""選択されている行のインデックスリストを返します。"""
		rows = list(self.GetSelectedRows())
		
		# ブロック選択の処理
		top_left = self.GetSelectionBlockTopLeft()
		bottom_right = self.GetSelectionBlockBottomRight()
		
		for (r1, c1), (r2, c2) in zip(top_left, bottom_right):
			rows.extend(range(r1, r2 + 1))
		
		return sorted(list(set(rows)))
	
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
		
		if tags:
			self.focus_cell(len(tags) + start_row - 1, 0)
	
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
		
		if tags:
			self.focus_cell(len(tags) + position - 1, 0)
	
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
		
		self.focus_cell(new_position, 0)
	
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
		
		if positions and self.GetNumberRows() > 0:
			# 移動先の行インデックス
			target_row = max(0, min(self.GetNumberRows() - 1, positions[-1] - 1))
			self.focus_cell(target_row, 0)
	
	def mutate_tag(self, target: int, position: int, new_tag: Tag):
		"""指定位置のタグの内容を更新します。

		Args:
			target: 対象のキャプションインデックス。現在の表示対象と異なる場合、操作はスキップされます。
			position: 更新するタグの位置。
			new_tag: 新しいタグオブジェクト。
		"""
		if self.item_index != target:
			return
		
		column = 0
		if self.GetCellValue(position, 0) != new_tag.text:
			self.SetCellValue(position, 0, new_tag.text)
		else:
			column = 1
			self.SetCellValue(position, 1, f'{new_tag.weight:.2f}')
		
		self.focus_cell(position, column)
