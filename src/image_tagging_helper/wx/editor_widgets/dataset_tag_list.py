import bisect
import wx
import wx.lib.mixins.listctrl as listmix

from src.image_tagging_helper.i18n import __
from src.image_tagging_helper.models.dataset import Dataset

class DatasetTagsList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
	"""
	データセット全体のタグとその出現回数を表示・管理するリストコントロール。
	"""
	
	def __init__(self, parent: wx.Window, *args, **kwargs):
		"""
		DatasetTagsListを初期化します。

		Args:
			 parent: 親ウィンドウ。
		"""
		super().__init__(parent, *args, style=wx.LC_REPORT, **kwargs)
		listmix.ListCtrlAutoWidthMixin.__init__(self)
		
		self.dataset: Dataset | None = None
		self.dataset_tags: list[str] = []
		
		self.InsertColumn(0, __("label:tag"), width=150)
		self.InsertColumn(1, __("label:count"), width=50, format=wx.LIST_FORMAT_RIGHT)
		self.setResizeColumn(0)
	
	def set_dataset(self, dataset: Dataset | None):
		"""
		リストに表示するデータセットを設定します。

		Args:
			 dataset: 表示するデータセット。
		"""
		if self.dataset:
			self.dataset.remove_tag_usage_changed_listener(self.on_tag_usage_changed)
		
		self.dataset = dataset
		if self.dataset:
			self.dataset.add_tag_usage_changed_listener(self.on_tag_usage_changed)
		
		self.update_list()
	
	def update_list(self):
		"""
		データセット全体のタグとその出現回数をリストに表示します。
		"""
		self.DeleteAllItems()
		
		if not self.dataset or len(self.dataset) == 0:
			self.dataset_tags = []
			return
		
		# タグをアルファベット順にソートして表示
		sorted_tags = sorted(self.dataset.tag_usages.items())
		
		# 空白タグを除外
		valid_tags = [(t, c) for t, c in sorted_tags if t.strip()]
		
		for i, (tag_text, count) in enumerate(valid_tags):
			self.InsertItem(i, tag_text)
			self.SetItem(i, 1, str(count))
		
		# タグリストを保存（更新用）
		self.dataset_tags = [tag_text for tag_text, _ in valid_tags]
	
	def on_tag_usage_changed(self, tag_text: str, count: int):
		"""
		タグの使用回数が変更されたときの処理。
		リスト内の該当するタグのカウントを更新します。
		"""
		if not tag_text.strip():
			return
		
		idx = bisect.bisect_left(self.dataset_tags, tag_text)
		exists = idx < len(self.dataset_tags) and self.dataset_tags[idx] == tag_text
		
		if exists:
			if count > 0:
				self.SetItem(idx, 1, str(count))
			else:
				self.DeleteItem(idx)
				del self.dataset_tags[idx]
		elif count > 0:
			self.InsertItem(idx, tag_text)
			self.SetItem(idx, 1, str(count))
			self.dataset_tags.insert(idx, tag_text)
	
	def apply_font(self, font: wx.Font):
		"""
		指定されたフォントをリストに適用します。
		"""
		self.SetFont(font)
		self.Refresh()
