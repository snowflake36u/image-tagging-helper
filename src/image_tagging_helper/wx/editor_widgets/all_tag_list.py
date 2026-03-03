import bisect
import wx
import wx.lib.mixins.listctrl as listmix

from src.image_tagging_helper.i18n import __
from src.image_tagging_helper.models.dataset import Dataset

class AllTagsList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
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
		self.all_tags: list[str] = []
		
		self.InsertColumn(0, __("label:tag"), width=150)
		self.InsertColumn(1, __("label:image_count"), width=50, format=wx.LIST_FORMAT_RIGHT)
		self.setResizeColumn(0)
		
		# コンテキストメニューイベントをバインド
		self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
		self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)
	
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
			self.all_tags = []
			return
		
		# タグをアルファベット順にソートして表示
		sorted_tags = sorted(self.dataset.tag_usages.items())
		
		# 空白タグを除外
		valid_tags = [(t, c) for t, c in sorted_tags if t.strip()]
		
		for i, (tag_text, count) in enumerate(valid_tags):
			self.InsertItem(i, tag_text)
			self.SetItem(i, 1, str(count))
		
		# タグリストを保存（更新用）
		self.all_tags = [tag_text for tag_text, _ in valid_tags]
	
	def on_tag_usage_changed(self, tag_text: str, count: int):
		"""
		タグの使用回数が変更されたときの処理。
		リスト内の該当するタグのカウントを更新します。
		"""
		if not tag_text.strip():
			return
		
		idx = bisect.bisect_left(self.all_tags, tag_text)
		exists = idx < len(self.all_tags) and self.all_tags[idx] == tag_text
		
		if exists:
			if count > 0:
				self.SetItem(idx, 1, str(count))
			else:
				self.DeleteItem(idx)
				del self.all_tags[idx]
		elif count > 0:
			self.InsertItem(idx, tag_text)
			self.SetItem(idx, 1, str(count))
			self.all_tags.insert(idx, tag_text)
	
	def apply_font(self, font: wx.Font):
		"""
		指定されたフォントをリストに適用します。
		"""
		self.SetFont(font)
		self.Refresh()
	
	def on_context_menu(self, event: wx.ContextMenuEvent):
		"""
		リストアイテムのコンテキストメニューを表示します。
		"""
		# コンテキストメニューの表示位置を取得
		pos = event.GetPosition()
		
		# 選択されている全てのアイテムを取得
		selected_indices = []
		item_index = self.GetFirstSelected()
		while item_index != wx.NOT_FOUND:
			selected_indices.append(item_index)
			item_index = self.GetNextSelected(item_index)
		
		if not selected_indices:
			# マウス操作の場合、クリック位置のアイテムを選択状態にする
			if pos != wx.DefaultPosition:
				client_pos = self.ScreenToClient(pos)
				hit_index, flags = self.HitTest(client_pos)
				if hit_index != wx.NOT_FOUND:
					self.Select(hit_index)
					selected_indices.append(hit_index)
		
		if not selected_indices:
			return
		
		# キーボード操作の場合のメニュー表示位置を調整
		if pos == wx.DefaultPosition:
			rect = self.GetItemRect(selected_indices[0])
			pos = self.ClientToScreen(rect.GetTopLeft())
		
		selected_tags = [self.GetItemText(idx) for idx in selected_indices]
		
		# 親フレームにメニュー作成を依頼
		parent_frame: wx.Frame = wx.GetTopLevelParent(self)
		if hasattr(parent_frame, 'show_all_tags_context_menu'):
			parent_frame.show_all_tags_context_menu(self, selected_tags, pos)
	
	def on_select_all(self, event: wx.CommandEvent):
		"""
		リスト内のすべてのアイテムを選択します。
		"""
		for i in range(self.GetItemCount()):
			self.Select(i)
	
	def copy_selected_tags_to_clipboard(self):
		"""
		選択されているタグをクリップボードにコピーします。
		"""
		selected_tags = []
		item_index = self.GetFirstSelected()
		while item_index != wx.NOT_FOUND:
			selected_tags.append(self.GetItemText(item_index))
			item_index = self.GetNextSelected(item_index)
		
		if selected_tags:
			text_to_copy = '\n'.join(selected_tags)
			if wx.TheClipboard.Open():
				wx.TheClipboard.SetData(wx.TextDataObject(text_to_copy))
				wx.TheClipboard.Close()
