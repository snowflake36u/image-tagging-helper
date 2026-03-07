from abc import ABC
from typing import Any

import wx
import wx.lib.mixins.listctrl as listmix
from enum import Enum, auto

from image_tagging_helper.i18n import __
from image_tagging_helper.models.dataset import Dataset
from image_tagging_helper.models.tag_lexicon import TagLexicon
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

class TagSortOrder(Enum):
	TagName = auto()
	Count = auto()
	CategoryOrder = auto()
	CategoryText = auto()
	
	def get_key(self, lexicon) -> Any:
		if self == TagSortOrder.TagName or lexicon is None:
			return TagNameSortKey()
		elif self == TagSortOrder.Count:
			return CountSortKey()
		elif self == TagSortOrder.CategoryOrder:
			return CategoryOrderSortKey(lexicon)
		elif self == TagSortOrder.CategoryText:
			return CategoryTextSortKey(lexicon)
		
		raise ValueError(f"Unknown sort order: {self}")
	
	def get_column_index(self) -> int:
		if self == TagSortOrder.TagName:
			return 0
		elif self == TagSortOrder.Count:
			return 1
		elif self == TagSortOrder.CategoryText:
			return 2
		return -1

class TagSortKey(ABC):
	"""タグのソート順を定義します。"""
	ALL: dict[int, int] = { }
	
	def __call__(self, item) -> Any:
		raise NotImplementedError

class TagNameSortKey(TagSortKey):
	def __call__(self, item) -> Any:
		return item[0]  # name

class CountSortKey(TagSortKey):
	def __call__(self, item) -> Any:
		name, count, _ = item
		return count, name

class CategoryOrderSortKey(TagSortKey):
	def __init__(self, lexicon: TagLexicon):
		self.lexicon = lexicon
	
	def __call__(self, item) -> Any:
		name, count, _ = item
		return self.lexicon.get_tag_order(name), name

class CategoryTextSortKey(TagSortKey):
	def __init__(self, lexicon: TagLexicon):
		self.lexicon = lexicon
	
	def __call__(self, item) -> Any:
		name, count, _ = item
		return self.lexicon.get_tag_category(name) or '', name

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
		self.tag_to_item_id = { }
		self.next_item_id = 0
		
		# ColumnSorterMixinを初期化（3列）
		listmix.ColumnSorterMixin.__init__(self, 3)
		
		self.dataset: Dataset | None = None
		self.tag_lexicon: TagLexicon | None = None
		self.sort_order: TagSortOrder = TagSortOrder.TagName
		self.sort_descending: bool = False
		self.sort_key = self.sort_order.get_key(self.tag_lexicon)
		
		self.InsertColumn(0, __("label:tag"), width=150)
		self.InsertColumn(1, __("label:image_count"), width=50, format=wx.LIST_FORMAT_RIGHT)
		self.InsertColumn(2, __("label:category"), width=150)
		self.setResizeColumn(0)
		
		# コンテキストメニューイベントをバインド
		self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
		self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)
		
		# 列クリックイベントをバインド
		self.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)
	
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
	
	def set_tag_lexicon(self, tag_lexicon: TagLexicon | None):
		"""
		ソートに使用するTagLexiconを設定します。
		"""
		self.tag_lexicon = tag_lexicon
		self.update_list()
	
	def set_sort_order(self, sort_order: TagSortOrder, descending: bool = False):
		"""
		リストのソート順を設定し、リストを更新します。
		"""
		self.sort_order = sort_order
		self.sort_descending = descending
		
		sort_col = self.sort_order.get_column_index()
		
		self.sort_key = self.sort_order.get_key(self.tag_lexicon)
		
		self.RemoveSortIndicator()
		if sort_col != -1:
			self.ShowSortIndicator(sort_col, not descending)
		
		self.update_list()
	
	def on_column_click(self, event: wx.ListEvent):
		"""
		列ヘッダーがクリックされたときの処理。
		ソート順を変更します。
		"""
		col = event.GetColumn()
		
		new_order = self.sort_order
		
		target_order = None
		if col == 0:
			target_order = TagSortOrder.TagName
		elif col == 1:
			target_order = TagSortOrder.Count
		elif col == 2:
			target_order = TagSortOrder.CategoryText
		
		if target_order:
			if self.sort_order == target_order:
				new_descending = not self.sort_descending
			else:
				new_order = target_order
				# デフォルトのソート方向
				if target_order == TagSortOrder.Count:
					new_descending = True
				else:
					new_descending = False
			
			self.set_sort_order(new_order, new_descending)
	
	# ColumnSorterMixinのデフォルト処理を抑制するためにSkipしない
	
	def update_list(self):
		"""
		データセット全体のタグとその出現回数をリストに表示し、現在の設定でソートします。
		"""
		self.Freeze()
		try:
			self.DeleteAllItems()
			self.itemDataMap.clear()
			self.tag_to_item_id.clear()
			self.next_item_id = 0
			
			if not self.dataset or len(self.dataset) == 0:
				return
			
			valid_tags = [
				(t, c, self.tag_lexicon.get_tag_category(t))
				for t, c in self.dataset.tag_usages.items() if t.strip()
			]
			
			sorted_tags = sorted(valid_tags, key=self.sort_key, reverse=self.sort_descending)
			
			for tag_text, count, categ in sorted_tags:
				self._insert_item_at(self.GetItemCount(), tag_text, count, categ)
		finally:
			self.Thaw()
	
	def _insert_item_at(self, index: int, tag_text: str, count: int, categ: str | None):
		"""
		指定された位置にアイテムを挿入し、内部データを更新します。
		"""
		item_id = self.next_item_id
		self.next_item_id += 1
		
		idx = self.InsertItem(index, tag_text)
		self.SetItem(idx, 1, str(count))
		self.SetItem(idx, 2, categ or __("label:uncategorized_symbol"))
		
		self.SetItemData(idx, item_id)
		self.itemDataMap[item_id] = (tag_text, count, categ)
		self.tag_to_item_id[tag_text] = item_id
		return idx
	
	def on_tag_usage_changed(self, tag_text: str, count: int):
		"""
		タグの使用回数が変更されたときの処理。
		リスト全体を再構築せず、適切な位置に挿入または削除を行います。
		"""
		if not tag_text.strip():
			return
		
		item_id = self.tag_to_item_id.get(tag_text)
		found_idx = wx.NOT_FOUND
		if item_id is not None:
			found_idx = self.FindItem(-1, data=item_id)
		
		# 削除の場合
		if count <= 0:
			if found_idx != wx.NOT_FOUND:
				self.DeleteItem(found_idx)
				if item_id in self.itemDataMap:
					del self.itemDataMap[item_id]
				if tag_text in self.tag_to_item_id:
					del self.tag_to_item_id[tag_text]
			return
		
		# 更新または挿入の場合
		categ = self.tag_lexicon.get_tag_category(tag_text)
		new_data = (tag_text, count, categ)
		
		if found_idx != wx.NOT_FOUND:
			# データが変わっていない場合は何もしない
			old_data = self.itemDataMap.get(item_id)
			if old_data == new_data:
				return
			
			# 削除して再挿入（ソート順を維持するため）
			self.DeleteItem(found_idx)
			if item_id in self.itemDataMap:
				del self.itemDataMap[item_id]
			if tag_text in self.tag_to_item_id:
				del self.tag_to_item_id[tag_text]
		
		# 挿入位置を検索
		insert_idx = self._find_insert_position(new_data)
		self._insert_item_at(insert_idx, tag_text, count, categ)
	
	def _find_insert_position(self, new_data) -> int:
		"""
		二分探索を使用して、新しいアイテムを挿入すべきインデックスを検索します。
		"""
		low = 0
		high = self.GetItemCount()
		
		new_key = self.sort_key(new_data)
		
		while low < high:
			mid = (low + high) // 2
			item_id = self.GetItemData(mid)
			mid_data = self.itemDataMap[item_id]
			mid_key = self.sort_key(mid_data)
			
			# 降順の場合の比較
			if self.sort_descending:
				if mid_key > new_key:  # midの方が大きい -> newはもっと後ろ
					low = mid + 1
				else:
					high = mid
			else:
				if mid_key < new_key:  # midの方が小さい -> newはもっと後ろ
					low = mid + 1
				else:
					high = mid
		
		return low
	
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
