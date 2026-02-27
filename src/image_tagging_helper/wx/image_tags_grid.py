import wx
import wx.grid
from typing import Literal

from src.image_tagging_helper.core.manager import DatasetManager
from src.image_tagging_helper.i18n import __

class ImageTagsGrid(wx.grid.Grid):
	"""画像のタグを表示・編集するためのグリッドコントロール。"""
	
	def __init__(self, parent, dataset_manager: DatasetManager):
		super().__init__(parent, wx.ID_ANY)
		self.dataset_manager = dataset_manager
		self.item_index: int | None = None
		
		self._init_grid()
	
	# self._bind_events()
	
	def _init_grid(self):
		self.CreateGrid(0, 2)
		self.SetColLabelValue(0, __("label:tag"))
		self.SetColLabelValue(1, __("label:weight"))
		self.SetColSize(0, 150)
		self.SetColSize(1, 50)
		self.SetRowLabelSize(0)
		self.EnableDragRowSize(False)
		# 選択モードを行選択にする
		self.SetSelectionMode(wx.grid.Grid.SelectCells)
	
	# def _bind_events(self):
	# 	self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
	
	def _on_dataset_manager_event(self, event_type: Literal['dataset_loaded', 'dataset_changed'], item_index: int | None):
		"""DatasetManagerからのイベントを処理します。"""
		if event_type == 'dataset_loaded':
			self.refresh_grid()
		elif event_type == 'dataset_changed':
			# 変更が現在のターゲットアイテムに関するもの、またはターゲットが指定されていない場合
			if item_index is None or item_index == self.item_index:
				self.refresh_grid()
	
	def set_target_index(self, index: int):
		"""表示対象の画像インデックスを設定し、グリッドを更新します。"""
		self.item_index = index
		self.refresh_grid()
	
	def switch_item(self, item_index):
		self.item_index = item_index
		self.refresh_grid()
	
	def refresh_grid(self):
		"""グリッドを更新します。"""
		
		if self.GetNumberRows() > 0:
			self.DeleteRows(0, self.GetNumberRows())
		
		if not self.dataset_manager.initialized or self.item_index is None:
			return
		
		item = self.dataset_manager.dataset[self.item_index]
		caption = item.caption
		
		if not caption.tags:
			return
		
		self.AppendRows(len(caption.tags))
		
		for i, tag in enumerate(caption.tags):
			self.SetCellValue(i, 0, tag.text)
			weight_str = f'{tag.weight:.2f}' if tag.weight is not None else ''
			self.SetCellValue(i, 1, weight_str)
