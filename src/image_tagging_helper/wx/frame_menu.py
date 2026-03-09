import wx
from typing import TYPE_CHECKING

from image_tagging_helper.i18n import __

if TYPE_CHECKING:
	from image_tagging_helper.wx.app import ImageTaggingHelperFrame

# 新しいメニュー項目IDを定義
ID_APPEND_TAG_TO_CURRENT = wx.NewIdRef()
ID_REMOVE_TAG_FROM_CURRENT = wx.NewIdRef()
ID_APPEND_TAG_TO_FILTERED = wx.NewIdRef()
ID_REMOVE_TAG_FROM_FILTERED = wx.NewIdRef()
ID_APPEND_TAG_TO_ALL = wx.NewIdRef()
ID_REMOVE_TAG_FROM_ALL = wx.NewIdRef()
ID_REPLACE_TAG_IN_ALL = wx.NewIdRef()
ID_ADD_TAG_TO_FILTER = wx.NewIdRef()

# ソートメニューID
ID_SORT_MENU = wx.NewIdRef()
ID_SORT_BY_TAG_NAME = wx.NewIdRef()
ID_SORT_BY_COUNT = wx.NewIdRef()
ID_SORT_BY_CATEGORY_ORDER = wx.NewIdRef()
ID_SORT_BY_CATEGORY_TEXT = wx.NewIdRef()
ID_SORT_DESCENDING = wx.NewIdRef()

class FrameMenuMixin:
	"""
	ImageTaggingHelperFrameのメニュー関連のロジックを分離するためのMixinクラス。
	"""
	
	def _init_menubar(self: 'ImageTaggingHelperFrame'):
		"""メニューバーを初期化します。"""
		menubar = wx.MenuBar()
		
		self._init_file_menu(menubar)
		self._init_edit_menu(menubar)
		self._init_dataset_menu(menubar)
		self._init_view_menu(menubar)
		self._init_configure_menu(menubar)
		
		self.SetMenuBar(menubar)
	
	def _init_file_menu(self: 'ImageTaggingHelperFrame', menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:file"))
		
		open_folder_menu = self._append_menu_item(menu, wx.ID_OPEN, __("action:open_folder"), __("tooltip:open_folder"), 'Ctrl+O')
		self.Bind(wx.EVT_MENU, self.on_open_folder, open_folder_menu)
		
		reload_menu = self._append_menu_item(menu, wx.ID_REFRESH, __("action:reload"), __("tooltip:reload"))
		self.Bind(wx.EVT_MENU, self.on_reload, reload_menu)
		
		menu.AppendSeparator()
		
		save_menu = self._append_menu_item(menu, wx.ID_SAVE, __("action:save"), __("tooltip:save"), 'Ctrl+S')
		self.Bind(wx.EVT_MENU, self.on_save, save_menu)
		
		menu.AppendSeparator()
		
		import_tags_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:import_tags"), __("tooltip:import_tags"))
		export_tags_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:export_tags"), __("tooltip:export_tags"))
		self.Bind(wx.EVT_MENU, self.on_import_tags, import_tags_menu)
		self.Bind(wx.EVT_MENU, self.on_export_tags, export_tags_menu)
		
		menu.AppendSeparator()
		
		exit_menu = self._append_menu_item(menu, wx.ID_EXIT, __("action:exit"), __("tooltip:exit"))
		self.Bind(wx.EVT_MENU, self.on_exit, exit_menu)
	
	def _init_edit_menu(self: 'ImageTaggingHelperFrame', menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:edit"))
		
		undo_menu = self._append_menu_item(menu, wx.ID_UNDO, __("action:undo"), __("tooltip:undo"), 'Ctrl+Z')
		redo_menu = self._append_menu_item(menu, wx.ID_REDO, __("action:redo"), __("tooltip:redo"), 'Ctrl+Y')
		self.Bind(wx.EVT_MENU, self.on_undo, undo_menu)
		self.Bind(wx.EVT_MENU, self.on_redo, redo_menu)
		self.Bind(wx.EVT_UPDATE_UI, self.on_update_ui_undo, undo_menu)
		self.Bind(wx.EVT_UPDATE_UI, self.on_update_ui_redo, redo_menu)
		
		menu.AppendSeparator()
		
		copy_menu = self._append_menu_item(menu, wx.ID_COPY, __("action:copy"), __("tooltip:copy"), 'Ctrl+C')
		paste_menu = self._append_menu_item(menu, wx.ID_PASTE, __("action:paste"), __("tooltip:paste"), 'Ctrl+V')
		self.Bind(wx.EVT_MENU, self.on_copy, copy_menu)
		self.Bind(wx.EVT_MENU, self.on_paste, paste_menu)
		
		menu.AppendSeparator()
		
		select_all_menu = self._append_menu_item(menu, wx.ID_SELECTALL, __("action:select_all"), __("tooltip:select_all"), 'Ctrl+A')
		self.Bind(wx.EVT_MENU, self.on_select_all, select_all_menu)
		
		menu.AppendSeparator()
		
		insert_blank_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:insert_blank_tag"), __("tooltip:insert_blank_tag"), 'Ctrl+E')
		delete_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:delete"), __("tooltip:delete"), 'Ctrl+D')
		replace_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:replace_tag"), __("tooltip:replace_tag"), 'Ctrl+H')
		replace_tag_menu.Enable(False)
		self.Bind(wx.EVT_MENU, self.on_insert_blank_tag, insert_blank_tag_menu)
		self.Bind(wx.EVT_MENU, self.on_delete_tag, delete_tag_menu)
		# self.Bind(wx.EVT_MENU, self.on_replace_tag, replace_tag_menu)
		
		menu.AppendSeparator()
		
		move_tag_up_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_up"), __("tooltip:move_tag_up"), 'Ctrl+Up')
		move_tag_down_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_down"), __("tooltip:move_tag_down"), 'Ctrl+Down')
		sort_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:sort_tag"), __("tooltip:sort_tag"))
		sort_tag_menu.Enable(False)
		self.Bind(wx.EVT_MENU, self.on_move_tag_up, move_tag_up_menu)
		self.Bind(wx.EVT_MENU, self.on_move_tag_down, move_tag_down_menu)
	
	def _init_dataset_menu(self: 'ImageTaggingHelperFrame', menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:dataset"))
		
		view_image_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:open_image_in_viewer"), __("tooltip:open_image_in_viewer"))
		open_in_folder_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:open_in_folder"), __("tooltip:open_in_folder"))
		self.Bind(wx.EVT_MENU, self.on_view_image, view_image_menu)
		self.Bind(wx.EVT_MENU, self.on_open_in_folder, open_in_folder_menu)
		
		menu.AppendSeparator()
		
		next_image_menu = self._append_menu_item(menu, wx.ID_FORWARD, __("action:next_image"), __("tooltip:next_image"), 'Shift+C')
		prev_image_menu = self._append_menu_item(menu, wx.ID_BACKWARD, __("action:prev_image"), __("tooltip:prev_image"), 'Shift+X')
		self.Bind(wx.EVT_MENU, self.on_next_image, next_image_menu)
		self.Bind(wx.EVT_MENU, self.on_prev_image, prev_image_menu)
		
		menu.AppendSeparator()
		
		filter_images_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:filter_images"), __("tooltip:filter_images"), 'Ctrl+F')
		clear_filter_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:clear_filter"), __("tooltip:clear_filter"), 'Shift+G')
		self.Bind(wx.EVT_MENU, self.on_filter_images_menu, filter_images_menu)
		self.Bind(wx.EVT_MENU, self.on_filter_cancel, clear_filter_menu)
	
	def _init_view_menu(self: 'ImageTaggingHelperFrame', menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:view"))
		
		self.toggle_all_tags_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_all_tags"), __("tooltip:toggle_all_tags"), kind=wx.ITEM_CHECK)
		self.toggle_all_tags_menu.Check(True)
		self.Bind(wx.EVT_MENU, self.on_toggle_all_tags, self.toggle_all_tags_menu)
		
		menu.AppendSeparator()
		
		fullscreen_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:fullscreen"), __("tooltip:fullscreen"), 'F11')
		self.Bind(wx.EVT_MENU, self.on_fullscreen, fullscreen_menu)
	
	def _init_configure_menu(self: 'ImageTaggingHelperFrame', menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:configure"))
		
		preferences_menu = self._append_menu_item(menu, wx.ID_PREFERENCES, __("action:preferences"), __("tooltip:preferences"))
		self.Bind(wx.EVT_MENU, self.on_preferences, preferences_menu)
	
	@staticmethod
	def _append_menu_item(menu: wx.Menu, item_id: int, label: str, help_str: str, accel: str = None, kind: wx.ItemKind = wx.ITEM_NORMAL) -> wx.MenuItem:
		"""
		メニュー項目を追加するためのヘルパーメソッド。
		ラベルとアクセラレータを結合してメニュー項目を作成します。
		"""
		text = f"{label}\t{accel}" if accel else label
		return menu.Append(item_id, text, help_str, kind)
	
	def _init_accelerators(self: 'ImageTaggingHelperFrame'):
		"""アクセラレータテーブルを初期化して設定します。"""
		accel_tbl = wx.AcceleratorTable([
			(wx.ACCEL_SHIFT, ord('F'), ID_ADD_TAG_TO_FILTER),
			(wx.ACCEL_SHIFT, ord('W'), ID_APPEND_TAG_TO_CURRENT),
			(wx.ACCEL_SHIFT, ord('R'), ID_REMOVE_TAG_FROM_CURRENT),
			(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('W'), ID_APPEND_TAG_TO_FILTERED),
			(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('R'), ID_REMOVE_TAG_FROM_FILTERED),
			(wx.ACCEL_CTRL, ord('W'), ID_APPEND_TAG_TO_ALL),
			(wx.ACCEL_CTRL, ord('R'), ID_REMOVE_TAG_FROM_ALL),
			(wx.ACCEL_CTRL, ord('L'), ID_REPLACE_TAG_IN_ALL),
		])
		self.SetAcceleratorTable(accel_tbl)
		
		# イベントバインド
		self.Bind(wx.EVT_MENU, self.on_accel_add_tags_to_filter, id=ID_ADD_TAG_TO_FILTER)
		self.Bind(wx.EVT_MENU, self.on_accel_append_tags_to_current_items, id=ID_APPEND_TAG_TO_CURRENT)
		self.Bind(wx.EVT_MENU, self.on_accel_remove_tags_from_current_items, id=ID_REMOVE_TAG_FROM_CURRENT)
		self.Bind(wx.EVT_MENU, self.on_accel_append_tags_to_filtered_items, id=ID_APPEND_TAG_TO_FILTERED)
		self.Bind(wx.EVT_MENU, self.on_accel_remove_tags_from_filtered_items, id=ID_REMOVE_TAG_FROM_FILTERED)
		self.Bind(wx.EVT_MENU, self.on_accel_append_tags_to_all_items, id=ID_APPEND_TAG_TO_ALL)
		self.Bind(wx.EVT_MENU, self.on_accel_remove_tags_from_all_items, id=ID_REMOVE_TAG_FROM_ALL)
		self.Bind(wx.EVT_MENU, self.on_accel_replace_tag_in_all_items, id=ID_REPLACE_TAG_IN_ALL)
	
	def _get_selected_tags_from_all_tags_list(self: 'ImageTaggingHelperFrame') -> list[str]:
		"""all_tags_listで選択されているタグのリストを取得します。"""
		selected_indices = []
		item_index = self.all_tags_list.GetFirstSelected()
		while item_index != wx.NOT_FOUND:
			selected_indices.append(item_index)
			item_index = self.all_tags_list.GetNextSelected(item_index)
		
		if not selected_indices:
			return []
		
		return [self.all_tags_list.GetItemText(idx) for idx in selected_indices]
	
	def on_accel_add_tags_to_filter(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) 選択中のタグをフィルターに追加します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.add_tags_to_filter(tags)
	
	def on_accel_append_tags_to_current_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) 選択中のアイテムにタグを追加します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.append_tags_to_current_items(tags)
	
	def on_accel_remove_tags_from_current_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) 選択中のアイテムからタグを削除します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.remove_tags_from_current_items(tags)
	
	def on_accel_append_tags_to_filtered_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) フィルター済みアイテムにタグを追加します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.append_tags_to_filtered_items(tags)
	
	def on_accel_remove_tags_from_filtered_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) フィルター済みアイテムからタグを削除します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.remove_tags_from_filtered_items(tags)
	
	def on_accel_append_tags_to_all_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) すべてのアイテムにタグを追加します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.append_tags_to_all_items(tags)
	
	def on_accel_remove_tags_from_all_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) すべてのアイテムからタグを削除します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if tags:
			self.remove_tags_from_all_items(tags)
	
	def on_accel_replace_tag_in_all_items(self: 'ImageTaggingHelperFrame', event: wx.CommandEvent):
		"""(ACCEL) すべてのアイテムでタグを置換します。"""
		tags = self._get_selected_tags_from_all_tags_list()
		if len(tags) == 1:
			self.replace_tag_in_all_items_with_dialog(tags[0])
