import wx
import wx.lib.mixins.listctrl as listmix

from image_tagging_helper.i18n import __
from image_tagging_helper.models.dataset import Dataset
from image_tagging_helper.wx.events import (
	TagsEvent,
	ReplaceTagEvent,
	myEVT_ADD_TAGS_TO_FILTER,
	myEVT_APPEND_TAGS_TO_CURRENT,
	myEVT_REMOVE_TAGS_FROM_CURRENT,
	myEVT_APPEND_TAGS_TO_FILTERED,
	myEVT_REMOVE_TAGS_FROM_FILTERED,
	myEVT_APPEND_TAGS_TO_ALL,
	myEVT_REMOVE_TAGS_FROM_ALL,
	myEVT_REPLACE_TAG_IN_ALL,
)

# コンテキストメニューID
ID_ADD_TAG_TO_FILTER = wx.NewIdRef()
ID_APPEND_TAG_TO_CURRENT = wx.NewIdRef()
ID_REMOVE_TAG_FROM_CURRENT = wx.NewIdRef()
ID_APPEND_TAG_TO_FILTERED = wx.NewIdRef()
ID_REMOVE_TAG_FROM_FILTERED = wx.NewIdRef()
ID_APPEND_TAG_TO_ALL = wx.NewIdRef()
ID_REMOVE_TAG_FROM_ALL = wx.NewIdRef()
ID_REPLACE_TAG_IN_ALL = wx.NewIdRef()

class AllTagsList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
	"""
	データセット全体のタグとその出現回数を表示・管理するリストコントロール。
	ヘッダーをクリックすることで、各列でソートが可能です。
	"""
	
	def __init__(self, parent: wx.Window, *args, **kwargs):
		"""
		AllTagsListを初期化します。

		Args:
			 parent: 親ウィンドウ。
		"""
		wx.ListCtrl.__init__(self, parent, *args, style=wx.LC_REPORT, **kwargs)
		listmix.ListCtrlAutoWidthMixin.__init__(self)
		
		# ソートのためにitemDataMapを初期化
		self.itemDataMap = { }
		# ColumnSorterMixinを初期化（2列）
		listmix.ColumnSorterMixin.__init__(self, 2)
		
		self.dataset: Dataset | None = None
		
		self.InsertColumn(0, __("label:tag"), width=150)
		self.InsertColumn(1, __("label:image_count"), width=50, format=wx.LIST_FORMAT_RIGHT)
		self.setResizeColumn(0)
		
		# コンテキストメニューイベントをバインド
		self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
		self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)
	
	def GetListCtrl(self):
		"""ColumnSorterMixinのためにListCtrlインスタンスを返します。"""
		return self
	
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
		self.itemDataMap.clear()
		
		if not self.dataset or len(self.dataset) == 0:
			return
		
		# 空白タグを除外
		valid_tags = [(t, c) for t, c in self.dataset.tag_usages.items() if t.strip()]
		
		# リストにアイテムを追加
		for i, (tag_text, count) in enumerate(valid_tags):
			index = self.InsertItem(self.GetItemCount(), tag_text)
			self.SetItem(index, 1, str(count))
			# ソート用のデータを設定
			self.SetItemData(index, i)
			self.itemDataMap[i] = (tag_text, count)
		
		# 初期ソート（タグ名、昇順）
		self.SortListItems(0, 1)
	
	def on_tag_usage_changed(self, tag_text: str, count: int):
		"""
		タグの使用回数が変更されたときの処理。
		リスト内の該当するタグのカウントを更新、またはアイテムの追加・削除を行います。
		"""
		if not tag_text.strip():
			return
		
		# FindItemを使用して、タグ名でアイテムを検索
		item_index = self.FindItem(-1, tag_text)
		
		if item_index != wx.NOT_FOUND:  # アイテムが存在する場合
			if count > 0:
				# カウントを更新
				self.SetItem(item_index, 1, str(count))
				# ソート用データを更新
				item_data_key = self.GetItemData(item_index)
				self.itemDataMap[item_data_key] = (tag_text, count)
			else:
				# アイテムを削除
				item_data_key = self.GetItemData(item_index)
				del self.itemDataMap[item_data_key]
				self.DeleteItem(item_index)
		elif count > 0:  # アイテムが存在せず、追加する必要がある場合
			# 新しいキーを決定
			new_key = max(self.itemDataMap.keys()) + 1 if self.itemDataMap else 0
			# アイテムを追加
			index = self.InsertItem(self.GetItemCount(), tag_text)
			self.SetItem(index, 1, str(count))
			self.SetItemData(index, new_key)
			self.itemDataMap[new_key] = (tag_text, count)
		
		# 現在のソート状態を維持して再ソート
		col, asc = self.GetSortState()
		if col != -1:
			self.SortListItems(col, asc)
	
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
		
		self._show_context_menu(selected_tags, pos)
	
	def _show_context_menu(self, selected_tags: list[str], pos: wx.Point):
		"""
		コンテキストメニューを表示し、選択されたアクションに応じてイベントを発行します。
		"""
		menu = wx.Menu()
		
		# メニュー項目の作成
		menu.Append(ID_ADD_TAG_TO_FILTER, __("action:add_tag_to_filter") + "\tShift+F")
		menu.AppendSeparator()
		
		multiple_tags = len(selected_tags) > 1
		
		menu.Append(ID_APPEND_TAG_TO_CURRENT, __("action:append_tags_to_current_items") + "\tShift+W")
		menu.Append(ID_REMOVE_TAG_FROM_CURRENT, __("action:remove_tags_from_current_items") + "\tShift+R")
		menu.AppendSeparator()
		
		menu.Append(ID_APPEND_TAG_TO_FILTERED, __("action:append_tags_to_filtered_items") + "\tCtrl+Shift+W")
		menu.Append(ID_REMOVE_TAG_FROM_FILTERED, __("action:remove_tags_from_filtered_items") + "\tCtrl+Shift+R")
		menu.AppendSeparator()
		
		menu.Append(ID_APPEND_TAG_TO_ALL, __("action:append_tags_to_all_items") + "\tCtrl+W")
		menu.Append(ID_REMOVE_TAG_FROM_ALL, __("action:remove_tags_from_all_items") + "\tCtrl+R")
		
		if not multiple_tags:
			menu.Append(ID_REPLACE_TAG_IN_ALL, __("action:replace_tag_in_all_items") + "\tCtrl+L")
		
		# イベントハンドラのバインド
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_ADD_TAGS_TO_FILTER, selected_tags), id=ID_ADD_TAG_TO_FILTER)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_CURRENT, selected_tags), id=ID_APPEND_TAG_TO_CURRENT)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_REMOVE_TAGS_FROM_CURRENT, selected_tags), id=ID_REMOVE_TAG_FROM_CURRENT)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_FILTERED, selected_tags), id=ID_APPEND_TAG_TO_FILTERED)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_REMOVE_TAGS_FROM_FILTERED, selected_tags), id=ID_REMOVE_TAG_FROM_FILTERED)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_ALL, selected_tags), id=ID_APPEND_TAG_TO_ALL)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_REMOVE_TAGS_FROM_ALL, selected_tags), id=ID_REMOVE_TAG_FROM_ALL)
		
		if not multiple_tags:
			menu.Bind(wx.EVT_MENU, lambda evt: self._fire_replace_tag_event(myEVT_REPLACE_TAG_IN_ALL, selected_tags[0]), id=ID_REPLACE_TAG_IN_ALL)
		
		self.PopupMenu(menu, self.ScreenToClient(pos))
		menu.Destroy()
	
	def _fire_tags_event(self, event_type, tags: list[str]):
		"""TagsEventを発行します。"""
		event = TagsEvent(event_type, self.GetId(), tags)
		self.GetEventHandler().ProcessEvent(event)
	
	def _fire_replace_tag_event(self, event_type, old_tag: str):
		"""ReplaceTagEventを発行します。"""
		event = ReplaceTagEvent(event_type, self.GetId(), old_tag)
		self.GetEventHandler().ProcessEvent(event)
	
	def on_select_all(self, event: wx.CommandEvent):
		"""
		リスト内のすべてのアイテムを選択します。
		"""
		self.select_all()
	
	def select_all(self):
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
	
	def clear_selection(self):
		for i in range(self.GetItemCount()):
			self.Select(i, on=False)
	
	def select_tags(self, tags: set[str]):
		"""
		指定されたタグのリストに一致するアイテムを選択します。
		"""
		# 最初にすべての選択を解除
		self.clear_selection()
		
		first_selected_index = -1
		for tag in tags:
			item_index = self.FindItem(-1, tag)
			if item_index != wx.NOT_FOUND:
				self.Select(item_index, on=True)
				if first_selected_index == -1:
					first_selected_index = item_index
		
		if first_selected_index != -1:
			self.EnsureVisible(first_selected_index)
