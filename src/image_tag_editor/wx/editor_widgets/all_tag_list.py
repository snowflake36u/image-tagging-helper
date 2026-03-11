from abc import ABC
from typing import Any

import wx
import wx.lib.mixins.listctrl as listmix
from enum import Enum, auto

from image_tag_editor.i18n import __
from image_tag_editor.models.dataset import Dataset
from image_tag_editor.models.tag_lexicon import TagLexicon
from image_tag_editor.wx.events import (
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
	myEVT_SELECT_TAGS_IN_IMAGE_TAGS_GRID,
)

# コンテキストメニューID
ID_ADD_TAG_TO_FILTER = wx.NewIdRef()
ID_APPEND_TAG_TO_CURRENT = wx.NewIdRef()
ID_REMOVE_TAG_FROM_CURRENT = wx.NewIdRef()
ID_APPEND_TAG_TO_FILTERED = wx.NewIdRef()
ID_REMOVE_TAG_FROM_FILTERED = wx.NewIdRef()
ID_APPEND_TAGS_TO_ALL = wx.NewIdRef()
ID_REMOVE_TAG_FROM_ALL = wx.NewIdRef()
ID_REPLACE_TAG_IN_ALL = wx.NewIdRef()
ID_SELECT_TAGS_IN_IMAGE_TAGS_GRID = wx.NewIdRef()

class TagSortOrder(Enum):
	TagName = auto()
	Count = auto()
	CategoryOrder = auto()
	CategoryText = auto()
	
	def get_key_fn(self, lexicon) -> Any:
		if self == TagSortOrder.TagName or lexicon is None:
			return TagNameSortKeyFn()
		elif self == TagSortOrder.Count:
			return CountSortKeyFn()
		elif self == TagSortOrder.CategoryOrder:
			return CategoryOrderSortKeyFn(lexicon)
		elif self == TagSortOrder.CategoryText:
			return CategoryTextSortKeyFn(lexicon)
		
		raise ValueError(f"Unknown sort order: {self}")
	
	def get_column_index(self) -> int:
		if self == TagSortOrder.TagName:
			return 0
		elif self == TagSortOrder.Count:
			return 1
		elif self == TagSortOrder.CategoryText:
			return 2
		return -1

class TagSortKeyFn(ABC):
	"""タグのソート順を定義します。"""
	
	def __call__(self, item) -> Any:
		raise NotImplementedError

class TagNameSortKeyFn(TagSortKeyFn):
	def __call__(self, item) -> Any:
		return item[0]  # name

class CountSortKeyFn(TagSortKeyFn):
	def __call__(self, item) -> Any:
		name, count, _ = item
		return count, name

class CategoryOrderSortKeyFn(TagSortKeyFn):
	def __init__(self, lexicon: TagLexicon):
		self.lexicon = lexicon
	
	def __call__(self, item) -> Any:
		name, count, _ = item
		return self.lexicon.get_category_order_of(name), name

class CategoryTextSortKeyFn(TagSortKeyFn):
	def __init__(self, lexicon: TagLexicon):
		self.lexicon = lexicon
	
	def __call__(self, item) -> Any:
		name, count, _ = item
		return self.lexicon.get_category_of(name) or '-', name

class AllTagsList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
	"""
	データセット全体のタグとその出現回数を表示・管理するリストコントロール。
	ヘッダーをクリックすることで、各列でソートが可能です。
	仮想リストコントロールとして実装され、大量のタグを効率的に扱います。
	"""
	
	def __init__(self, parent: wx.Window, *args, **kwargs):
		"""
		AllTagsListを初期化します。

		Args:
			 parent: 親ウィンドウ。
		"""
		# 仮想リストスタイルを追加
		style = kwargs.get('style', 0) | wx.LC_REPORT | wx.LC_VIRTUAL
		kwargs['style'] = style
		
		wx.ListCtrl.__init__(self, parent, *args, **kwargs)
		listmix.ListCtrlAutoWidthMixin.__init__(self)
		
		self.dataset: Dataset | None = None
		self.tag_lexicon: TagLexicon | None = None
		self.sort_order: TagSortOrder = TagSortOrder.TagName
		self.sort_descending: bool = False
		self.sort_key = self.sort_order.get_key_fn(self.tag_lexicon)
		
		# データ保持用リスト: list[tuple[tag_text, count, category]]
		self.item_list: list[tuple[str, int, str | None]] = []
		
		self.InsertColumn(0, __("label:tag"), width=150)
		self.InsertColumn(1, __("label:image_count"), width=50, format=wx.LIST_FORMAT_RIGHT)
		self.InsertColumn(2, __("label:category"), width=150)
		self.setResizeColumn(0)
		
		# コンテキストメニューイベントをバインド
		self.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
		self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)
		
		# 列クリックイベントをバインド
		self.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)
	
	def OnGetItemText(self, item, col):
		"""仮想リストのアイテムテキストを取得します。"""
		if 0 <= item < len(self.item_list):
			data = self.item_list[item]
			if col == 0:
				return data[0]
			elif col == 1:
				return str(data[1])
			elif col == 2:
				return data[2] or __("label:uncategorized_symbol")
		return ""
	
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
		
		self.sort_key = self.sort_order.get_key_fn(self.tag_lexicon)
		
		# ソートインジケータの表示（wxPython 4.1+）
		if hasattr(self, "ShowSortIndicator"):
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
	
	def update_list(self):
		"""
		データセット全体のタグとその出現回数をリストに表示し、現在の設定でソートします。
		"""
		self.Freeze()
		try:
			# 選択状態をクリア（データが全入れ替えになるため）
			self.clear_selection()
			self.item_list.clear()
			
			if not self.dataset or len(self.dataset) == 0:
				self.SetItemCount(0)
				return
			
			lexicon = self.tag_lexicon
			valid_tags = [
				(t, c, lexicon.get_category_of(t) if lexicon else None)
				for t, c in self.dataset.tag_usages.items() if t.strip()
			]
			
			self.item_list = sorted(valid_tags, key=self.sort_key, reverse=self.sort_descending)
			self.SetItemCount(len(self.item_list))
			self.Refresh()
		finally:
			self.Thaw()
	
	def _find_index_by_tag(self, tag_text: str) -> int:
		"""
		タグ名からインデックスを検索します。
		ソート順がTagNameの場合は二分探索を使用し、それ以外は線形探索を行います。
		"""
		if self.sort_order == TagSortOrder.TagName:
			# 二分探索
			low = 0
			high = len(self.item_list)
			while low < high:
				mid = (low + high) // 2
				mid_tag = self.item_list[mid][0]
				
				if mid_tag == tag_text:
					return mid
				
				if not self.sort_descending:
					if mid_tag < tag_text:
						low = mid + 1
					else:
						high = mid
				else:
					if mid_tag > tag_text:
						low = mid + 1
					else:
						high = mid
			return -1
		else:
			# 線形探索
			for i, item in enumerate(self.item_list):
				if item[0] == tag_text:
					return i
			return -1

	def on_tag_usage_changed(self, tag_text: str, count: int):
		"""
		タグの使用回数が変更されたときの処理。
		リスト全体を再構築せず、適切な位置に挿入または削除を行います。
		"""
		if not tag_text.strip():
			return
		
		# 現在のリストから対象タグを検索
		found_idx = self._find_index_by_tag(tag_text)
		
		# 選択状態の退避
		selected_indices = set()
		item = self.GetFirstSelected()
		while item != wx.NOT_FOUND:
			selected_indices.add(item)
			item = self.GetNextSelected(item)
		
		insert_idx = -1
		
		# 削除の場合
		if count <= 0:
			if found_idx != -1:
				self.item_list.pop(found_idx)
				self.SetItemCount(len(self.item_list))
				# 削除時はRefreshが必要
				self.Refresh()
		else:
			# 更新または挿入
			categ = self.tag_lexicon.get_category_of(tag_text) if self.tag_lexicon else None
			new_data = (tag_text, count, categ)
			
			if found_idx != -1:
				# データが変わっていない場合は何もしない
				if self.item_list[found_idx] == new_data:
					return
				
				# 削除して再挿入（ソート順を維持するため）
				self.item_list.pop(found_idx)
			
			# 挿入位置を検索
			insert_idx = self._find_insert_position(new_data)
			self.item_list.insert(insert_idx, new_data)
			self.SetItemCount(len(self.item_list))
			self.Refresh()
		
		# 選択状態の復元
		new_selected_indices = set()
		for idx in selected_indices:
			new_idx = idx
			if found_idx != -1:  # 削除があった
				if idx == found_idx:
					continue  # 削除されたアイテム
				if idx > found_idx:
					new_idx -= 1
			
			if insert_idx != -1:  # 挿入があった
				if new_idx >= insert_idx:
					new_idx += 1
			
			new_selected_indices.add(new_idx)
		
		# 移動したアイテムの選択状態維持（更新時のみ）
		if found_idx != -1 and insert_idx != -1 and found_idx in selected_indices:
			new_selected_indices.add(insert_idx)
		
		# 適用
		self.clear_selection()
		for idx in new_selected_indices:
			self.Select(idx)

	def _find_insert_position(self, new_data) -> int:
		"""
		二分探索を使用して、新しいアイテムを挿入すべきインデックスを検索します。
		"""
		low = 0
		high = len(self.item_list)
		
		new_key = self.sort_key(new_data)
		
		while low < high:
			mid = (low + high) // 2
			mid_data = self.item_list[mid]
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
		menu.Append(ID_SELECT_TAGS_IN_IMAGE_TAGS_GRID, __("action:select_in_image_tags"))
		menu.AppendSeparator()
		
		menu.Append(ID_ADD_TAG_TO_FILTER, __("action:add_tag_to_filter") + "\tShift+F")
		menu.AppendSeparator()
		
		multiple_tags = len(selected_tags) > 1
		
		menu.Append(ID_APPEND_TAG_TO_CURRENT, __("action:append_tags_to_current_items") + "\tShift+W")
		menu.Append(ID_REMOVE_TAG_FROM_CURRENT, __("action:remove_tags_from_current_items") + "\tShift+R")
		menu.AppendSeparator()
		
		menu.Append(ID_APPEND_TAG_TO_FILTERED, __("action:append_tags_to_filtered_items") + "\tCtrl+Shift+W")
		menu.Append(ID_REMOVE_TAG_FROM_FILTERED, __("action:remove_tags_from_filtered_items") + "\tCtrl+Shift+R")
		menu.AppendSeparator()
		
		menu.Append(ID_APPEND_TAGS_TO_ALL, __("action:append_tags_to_all_items") + "\tCtrl+W")
		menu.Append(ID_REMOVE_TAG_FROM_ALL, __("action:remove_tags_from_all_items") + "\tCtrl+R")
		
		if not multiple_tags:
			menu.Append(ID_REPLACE_TAG_IN_ALL, __("action:replace_tag_in_all_items") + "\tCtrl+L")
		
		# イベントハンドラのバインド
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_SELECT_TAGS_IN_IMAGE_TAGS_GRID, selected_tags), id=ID_SELECT_TAGS_IN_IMAGE_TAGS_GRID)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_ADD_TAGS_TO_FILTER, selected_tags), id=ID_ADD_TAG_TO_FILTER)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_CURRENT, selected_tags), id=ID_APPEND_TAG_TO_CURRENT)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_REMOVE_TAGS_FROM_CURRENT, selected_tags), id=ID_REMOVE_TAG_FROM_CURRENT)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_FILTERED, selected_tags), id=ID_APPEND_TAG_TO_FILTERED)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_REMOVE_TAGS_FROM_FILTERED, selected_tags), id=ID_REMOVE_TAG_FROM_FILTERED)
		menu.Bind(wx.EVT_MENU, lambda evt: self._fire_tags_event(myEVT_APPEND_TAGS_TO_ALL, selected_tags), id=ID_APPEND_TAGS_TO_ALL)
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
		self.Freeze()
		try:
			for i in range(self.GetItemCount()):
				self.Select(i)
		finally:
			self.Thaw()
	
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
		item = self.GetFirstSelected()
		while item != wx.NOT_FOUND:
			self.Select(item, on=False)
			item = self.GetNextSelected(item)
	
	def select_tags(self, tags: set[str]):
		"""
		指定されたタグのリストに一致するアイテムを選択します。
		"""
		# 最初にすべての選択を解除
		self.clear_selection()
		
		first_selected_index = -1
		for i, item in enumerate(self.item_list):
			if item[0] in tags:
				self.Select(i, on=True)
				if first_selected_index == -1:
					first_selected_index = i
		
		if first_selected_index != -1:
			self.EnsureVisible(first_selected_index)
