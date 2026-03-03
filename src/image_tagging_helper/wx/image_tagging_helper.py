import wx
import wx.grid
import ctypes
import csv
import io
import bisect
import os
import sys
import subprocess

from src.image_tagging_helper.core.config import Config
from src.image_tagging_helper.models.caption import CaptionFormatConfig, Tag
from src.image_tagging_helper.models.dataset import Dataset
from src.image_tagging_helper.models.controller import DatasetController
from src.image_tagging_helper.wx.editor_widgets.all_tag_list import AllTagsList
from src.image_tagging_helper.wx.editor_widgets.image_list import ImageVListBox
from src.image_tagging_helper.wx.editor_widgets.image_tags_grid import ImageTagsGrid
from src.image_tagging_helper.wx.preferences import PreferencesDialog
from src.image_tagging_helper.i18n import setup_translation, __

# アプリケーションのドメイン名を設定
APP_NAME = "Image Tagging Helper"
APP_ID = "image_tagging_helper"

SASH_MIN_WIDTH = 120

# 新しいメニュー項目IDを定義
ID_APPEND_TAG_TO_CURRENT = wx.NewIdRef()
ID_REMOVE_TAG_FROM_CURRENT = wx.NewIdRef()
ID_APPEND_TAG_TO_FILTERED = wx.NewIdRef()
ID_REMOVE_TAG_FROM_FILTERED = wx.NewIdRef()
ID_APPEND_TAG_TO_ALL = wx.NewIdRef()
ID_REMOVE_TAG_FROM_ALL = wx.NewIdRef()
ID_REPLACE_TAG_IN_ALL = wx.NewIdRef()
ID_ADD_TAG_TO_FILTER = wx.NewIdRef()

class ImageTaggingHelperFrame(wx.Frame):
	"""
	メインウィンドウのフレーム。
	UIコンポーネントの配置とイベント処理、データセットの管理を行います。
	"""
	
	def __init__(self, parent: wx.Window | None, title: str, config: Config):
		"""
		フレームを初期化します。

		Args:
			parent: 親ウィンドウ。
			title: ウィンドウのタイトル。
			config: アプリケーション設定。
		"""
		self.config = config
		
		# ウィンドウサイズを復元
		window_size = self.load_window_size_settings()
		super().__init__(parent, title=title, size=window_size)
		
		# === データメンバーの初期化 ===
		self.image_exts = ['.jpg', '.jpeg', '.png', '.webp']
		self.caption_ext = '.caption'
		self.dataset = Dataset()
		self.controller: DatasetController | None = None
		self.caption_format_config = CaptionFormatConfig()
		self.current_item_index: int = wx.NOT_FOUND
		
		# === UIの初期化 ===
		self._init_ui()
		
		# === イベントのバインド ===
		self.Bind(wx.EVT_CLOSE, self.on_close)
	
	def _init_ui(self):
		"""UI全体の初期化"""
		self._init_menubar()
		
		main_panel = wx.Panel(self)
		
		path_panel = self._create_path_panel(main_panel)
		self._create_main_sash_layout(main_panel)
		
		# メインパネルのレイアウト
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(path_panel, 0, wx.EXPAND | wx.ALL, 5)
		sizer.Add(self.splitter_1, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
		main_panel.SetSizer(sizer)
		
		self.apply_font_settings()
		
		# フォーカス遷移の順序をリストで定義
		self.focus_order = [
			self.path_text,
			self.filter_ctrl,
			self.thumbnail_list,
			self.image_tags_grid,
			self.all_tags_list,
		]
		
		# Tabキーによるフォーカス遷移を制御するためのイベントフック
		self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
		
		# 初期フォーカスをサムネイルリストに設定
		wx.CallAfter(self.thumbnail_list.SetFocus)
	
	def _init_menubar(self):
		"""メニューバーを初期化します。"""
		menubar = wx.MenuBar()
		
		self._init_file_menu(menubar)
		self._init_edit_menu(menubar)
		self._init_dataset_menu(menubar)
		self._init_view_menu(menubar)
		self._init_configure_menu(menubar)
		
		self.SetMenuBar(menubar)
	
	def _init_file_menu(self, menubar):
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
		
		exit_menu = self._append_menu_item(menu, wx.ID_EXIT, __("action:exit"), __("tooltip:exit"))
		self.Bind(wx.EVT_MENU, self.on_exit, exit_menu)
	
	def _init_edit_menu(self, menubar):
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
		
		insert_blank_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:insert_blank_tag"), __("tooltip:insert_blank_tag"), 'Ctrl+E')
		delete_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:delete_tag"), __("tooltip:delete_tag"), 'Ctrl+D')
		replace_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:replace_tag"), __("tooltip:replace_tag"), 'Ctrl+R')
		replace_tag_menu.Enable(False)
		self.Bind(wx.EVT_MENU, self.on_insert_blank_tag, insert_blank_tag_menu)
		self.Bind(wx.EVT_MENU, self.on_delete_tag, delete_tag_menu)
		# self.Bind(wx.EVT_MENU, self.on_replace_tag, replace_tag_menu)
		
		menu.AppendSeparator()
		
		move_tag_up_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_up"), __("tooltip:move_tag_up"), 'Shift+W')
		move_tag_down_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_down"), __("tooltip:move_tag_down"), 'Shift+S')
		sort_tag_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:sort_tag"), __("tooltip:sort_tag"), 'Ctrl+L')
		sort_tag_menu.Enable(False)
		self.Bind(wx.EVT_MENU, self.on_move_tag_up, move_tag_up_menu)
		self.Bind(wx.EVT_MENU, self.on_move_tag_down, move_tag_down_menu)
	
	def _init_dataset_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:dataset"))
		
		view_image_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:view_image"), __("tooltip:view_image"))
		open_in_folder_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:open_in_folder"), __("tooltip:open_in_folder"))
		self.Bind(wx.EVT_MENU, self.on_view_image, view_image_menu)
		self.Bind(wx.EVT_MENU, self.on_open_in_folder, open_in_folder_menu)
		
		menu.AppendSeparator()
		
		next_image_menu = self._append_menu_item(menu, wx.ID_FORWARD, __("action:next_image"), __("tooltip:next_image"), 'Shift+C')
		prev_image_menu = self._append_menu_item(menu, wx.ID_BACKWARD, __("action:prev_image"), __("tooltip:prev_image"), 'Shift+X')
		self.Bind(wx.EVT_MENU, self.on_next_image, next_image_menu)
		self.Bind(wx.EVT_MENU, self.on_prev_image, prev_image_menu)
		
		menu.AppendSeparator()
		
		filter_images_menu = self._append_menu_item(menu, wx.ID_FIND, __("action:filter_images"), __("tooltip:filter_images"), 'Ctrl+F')
		clear_filter_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:clear_filter"), __("tooltip:clear_filter"), 'Ctrl+Shift+F')
		self.Bind(wx.EVT_MENU, self.on_filter_images_menu, filter_images_menu)
		self.Bind(wx.EVT_MENU, self.on_filter_cancel, clear_filter_menu)
	
	def _init_view_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:view"))
		
		self.toggle_all_tags_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_all_tags"), __("tooltip:toggle_all_tags"), kind=wx.ITEM_CHECK)
		self.toggle_all_tags_menu.Check(True)
		self.Bind(wx.EVT_MENU, self.on_toggle_all_tags, self.toggle_all_tags_menu)
		
		menu.AppendSeparator()
		
		fullscreen_menu = self._append_menu_item(menu, wx.ID_ANY, __("action:fullscreen"), __("tooltip:fullscreen"), 'F11')
		self.Bind(wx.EVT_MENU, self.on_fullscreen, fullscreen_menu)
	
	def _init_configure_menu(self, menubar):
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
	
	def _create_path_panel(self, parent: wx.Window) -> wx.Window:
		"""
		ファイルパス表示パネルを作成します。

		Args:
			parent: 親となるウィンドウ。

		Returns:
			作成されたパネル。
		"""
		topbar_panel = wx.Panel(parent)
		topbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
		
		path_label = wx.StaticText(topbar_panel, label=__("label:file_path"))
		
		# スプリッターの作成
		self.topbar_splitter = wx.SplitterWindow(topbar_panel, style=wx.SP_LIVE_UPDATE | wx.SP_NOBORDER)
		self.topbar_splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
		
		# 左側：ファイルパス
		path_text_panel = wx.Panel(self.topbar_splitter)
		path_text_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.path_text = wx.TextCtrl(path_text_panel, style=wx.TE_READONLY)
		path_text_sizer.Add(self.path_text, 1, wx.ALIGN_CENTER_VERTICAL)
		path_text_panel.SetSizer(path_text_sizer)
		
		# 右側：検索フィルタ
		filter_panel = wx.Panel(self.topbar_splitter)
		filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
		
		self.filter_ctrl = wx.SearchCtrl(filter_panel, style=wx.TE_PROCESS_ENTER)
		self.filter_ctrl.ShowCancelButton(True)
		self.filter_ctrl.SetDescriptiveText(__("hint:search_filter"))
		
		# テキストボックスの高さをpath_textに合わせる
		ref_height = self.path_text.GetBestSize().height
		self.filter_ctrl.SetMinSize((-1, ref_height))
		
		filter_sizer.Add(self.filter_ctrl, 1, wx.ALIGN_CENTER_VERTICAL, 0)
		filter_panel.SetSizer(filter_sizer)
		
		# スプリッターの設定
		self.topbar_splitter.SetMinimumPaneSize(50)
		self.topbar_splitter.SplitVertically(path_text_panel, filter_panel)
		self.topbar_splitter.SetSashGravity(1.0)
		self.topbar_splitter.SetSashPosition(-250)
		
		topbar_sizer.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		topbar_sizer.Add(self.topbar_splitter, 1, wx.EXPAND)
		
		topbar_panel.SetSizer(topbar_sizer)
		
		# イベントハンドラをバインド
		self.Bind(wx.EVT_SEARCH, self.on_filter_items, self.filter_ctrl)
		self.Bind(wx.EVT_TEXT_ENTER, self.on_filter_items, self.filter_ctrl)
		self.Bind(wx.EVT_SEARCH_CANCEL, self.on_filter_cancel, self.filter_ctrl)
		self.filter_ctrl.Bind(wx.EVT_KEY_DOWN, self.on_filter_ctrl_key_down)
		
		return topbar_panel
	
	def _create_main_sash_layout(self, parent: wx.Window):
		"""
		入れ子になったスプリッターウィンドウでメインレイアウトを作成します。
		"""
		# スプリッターウィンドウの作成
		self.splitter_1 = wx.SplitterWindow(parent)
		self.splitter_2 = wx.SplitterWindow(self.splitter_1)
		
		splitters = [self.splitter_1, self.splitter_2]
		for splitter in splitters:
			splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
			splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.on_splitter_sash_pos_changing)
			splitter.Bind(wx.EVT_SIZE, self.on_splitter_resize)
		
		# 各ペインの作成
		self._create_thumbnail_panel(self.splitter_1)
		self._create_image_tags_panel(self.splitter_2)
		self._create_all_tags_panel(self.splitter_2)
		
		# スプリッターの分割設定
		# 全体幅1200に対して各パネル400ずつ割り当てる
		self.splitter_1.SplitVertically(self.thumbnail_panel, self.splitter_2, 400)
		self.splitter_2.SplitVertically(self.image_tags_panel, self.all_tags_panel, 400)
		
		# UI設定を復元
		wx.CallAfter(self.load_ui_settings)
		
		# ウィンドウリサイズ時の挙動を設定
		self.splitter_1.SetSashGravity(0)
		self.splitter_2.SetSashGravity(0.5)
	
	def _create_thumbnail_panel(self, parent: wx.Window):
		"""画像のサムネイルリストパネルを作成します。"""
		self.thumbnail_panel = wx.Panel(parent)
		self.thumbnail_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		self.thumbnail_toolbar = wx.ToolBar(self.thumbnail_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.thumbnail_toolbar.AddControl(wx.StaticText(self.thumbnail_toolbar, label=__("label:image_list")))
		self.thumbnail_toolbar.AddSeparator()
		self.thumbnail_toolbar.Realize()
		
		self.thumbnail_list = ImageVListBox(self.thumbnail_panel, style=wx.VSCROLL | wx.ALWAYS_SHOW_SB)
		self.thumbnail_list.Bind(wx.EVT_LISTBOX, self.on_thumbnail_select)
		self.thumbnail_list.Bind(wx.EVT_CONTEXT_MENU, self.on_thumbnail_context_menu)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.thumbnail_toolbar, 0, wx.EXPAND)
		sizer.Add(self.thumbnail_list, 1, wx.EXPAND)
		self.thumbnail_panel.SetSizer(sizer)
	
	def _create_image_tags_panel(self, parent: wx.Window):
		"""画像のタグ一覧パネルを作成します。"""
		self.image_tags_panel = wx.Panel(parent)
		self.image_tags_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		self.image_tags_toolbar = wx.ToolBar(self.image_tags_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.image_tags_toolbar.AddControl(wx.StaticText(self.image_tags_toolbar, label=__("label:image_tags")))
		self.image_tags_toolbar.AddSeparator()
		self.image_tags_toolbar.Realize()
		
		self.image_tags_grid = ImageTagsGrid(self.image_tags_panel)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.image_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.image_tags_grid, 1, wx.EXPAND)
		self.image_tags_panel.SetSizer(sizer)
	
	def _create_all_tags_panel(self, parent: wx.Window):
		"""データセット全体のタグ一覧パネルを作成します。"""
		self.all_tags_panel = wx.Panel(parent)
		self.all_tags_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		self.all_tags_toolbar = wx.ToolBar(self.all_tags_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.all_tags_toolbar.AddControl(wx.StaticText(self.all_tags_toolbar, label=__("label:all_tags")))
		self.all_tags_toolbar.AddSeparator()
		self.all_tags_toolbar.Realize()
		
		self.all_tags_list = AllTagsList(self.all_tags_panel)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.all_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.all_tags_list, 1, wx.EXPAND)
		self.all_tags_panel.SetSizer(sizer)
	
	# === イベントハンドラ ===
	
	def on_char_hook(self, event: wx.KeyEvent):
		"""
		キーイベントをフックして、Tabキーによるフォーカス遷移を制御します。
		フォーカス遷移の順序を self.focus_order リストに基づいて動的に決定します。
		"""
		if event.GetKeyCode() != wx.WXK_TAB:
			event.Skip()
			return
		
		focus_win = wx.Window.FindFocus()
		if not focus_win:
			event.Skip()
			return
		
		# 現在フォーカスのあるコントロールを特定します。
		# ImageTagsGridは内部にウィンドウを持つため、特別に扱います。
		current_control = None
		grid_win = self.image_tags_grid.GetGridWindow()
		is_grid_focus = (focus_win == self.image_tags_grid or focus_win == grid_win or
							  (focus_win.GetParent() and focus_win.GetParent() == grid_win))
		
		if is_grid_focus:
			current_control = self.image_tags_grid
		else:
			# self.focus_order に含まれるコントロールかどうかをチェックします。
			for ctrl in self.focus_order:
				if focus_win == ctrl:
					current_control = ctrl
					break
		
		if current_control is None:
			event.Skip()
			return
		
		try:
			current_index = self.focus_order.index(current_control)
		except ValueError:
			event.Skip()
			return
		
		shift_down = event.ShiftDown()
		num_controls = len(self.focus_order)
		
		# 次にフォーカスするコントロールのインデックスを計算します。
		offset = -1 if shift_down else 1
		next_index = (current_index + offset + num_controls) % num_controls
		
		# 次のコントロールにフォーカスを移動します。
		next_control = self.focus_order[next_index]
		next_control.SetFocus()
	
	# event.Skip() を呼ばないことで、デフォルトのTab処理を抑制します。
	
	def on_filter_ctrl_key_down(self, event: wx.KeyEvent):
		"""
		検索コントロールでのキー入力を処理します。
		空文字列でEnterキーが押された場合、EVT_SEARCHが発生しないため手動で処理します。
		"""
		if event.GetKeyCode() == wx.WXK_RETURN:
			if not self.filter_ctrl.GetValue():
				self.on_filter_items(None)
				return
		
		event.Skip()
	
	def on_filter_items(self, event: wx.CommandEvent):
		"""検索コントロールで検索が実行されたときの処理。"""
		query = self.filter_ctrl.GetValue()
		if not query:
			self.on_filter_cancel(event)
			return
		
		# フィルタリング実行
		matched_indices = self.dataset.match_items(query)
		self.thumbnail_list.set_filter(matched_indices)
		
		# 選択状態の更新
		if matched_indices:
			# 現在選択中の画像がマッチしたか確認
			current_item_idx = self.current_item_index
			if current_item_idx in matched_indices:
				# マッチした場合はその画像を選択状態にする
				self.thumbnail_list.select_item(current_item_idx)
			else:
				# マッチしなかった場合は、直前の画像を選択する
				idx = bisect.bisect_left(matched_indices, current_item_idx)
				if idx > 0:
					new_selection = matched_indices[idx - 1]
				else:
					new_selection = matched_indices[0]
				
				self.thumbnail_list.select_item(new_selection)
				self.current_item_index = new_selection
				self._update_views_for_item_selection(new_selection)
		else:
			# マッチする画像がない場合
			self.current_item_index = wx.NOT_FOUND
			self._update_views_for_item_selection(wx.NOT_FOUND)
	
	def on_filter_cancel(self, event: wx.CommandEvent):
		"""検索コントロールでキャンセルボタンが押されたときの処理。"""
		self.filter_ctrl.SetValue("")
		self.thumbnail_list.set_filter(None)
		
		# 選択状態の復元
		if self.current_item_index != wx.NOT_FOUND:
			self.thumbnail_list.select_item(self.current_item_index)
			self._update_views_for_item_selection(self.current_item_index)
	
	def on_filter_images_menu(self, event: wx.CommandEvent):
		"""検索バーにフォーカスを移動します。"""
		self.filter_ctrl.SetFocus()
	
	def on_close(self, event: wx.CloseEvent):
		"""
		ウィンドウが閉じるときにUI設定を保存し、未保存の変更がある場合は確認ダイアログを表示します。
		"""
		if self.dataset.initialized and self.dataset.is_dirty:
			ret = self.confirm_save()
			
			if ret == wx.YES:
				self.dataset.save(self.caption_ext, self.caption_format_config)
			elif ret == wx.CANCEL:
				event.Veto()
				return
		
		self.save_ui_settings()
		event.Skip()
	
	def on_splitter_dclick(self, event: wx.SplitterEvent):
		"""スプリッターのダブルクリックによる折りたたみを防止します。"""
		event.Veto()
	
	def on_splitter_sash_pos_changing(self, event: wx.SplitterEvent):
		"""
		スプリッターのサッシ位置が変更されるときの処理。
		各パネルの最小サイズを下回らないように制限します。
		"""
		new_pos = event.GetSashPosition()
		splitter: wx.SplitterWindow = event.GetEventObject()
		
		adjusted_pos = self._adjust_splitter_sash(splitter, new_pos)
		if adjusted_pos != new_pos:
			event.SetSashPosition(adjusted_pos)
	
	def on_splitter_resize(self, event: wx.SizeEvent):
		"""
		スプリッターがリサイズされたときの処理。
		サッシ位置を調整して最小サイズを維持します。
		"""
		splitter = event.GetEventObject()
		if isinstance(splitter, wx.SplitterWindow) and splitter.IsSplit():
			current_pos = splitter.GetSashPosition()
			adjusted_pos = self._adjust_splitter_sash(splitter, current_pos)
			if adjusted_pos != current_pos:
				splitter.SetSashPosition(adjusted_pos)
		event.Skip()
	
	def _adjust_splitter_sash(self, splitter: wx.SplitterWindow, new_pos: int) -> int:
		"""
		スプリッターのサッシ位置を調整して、各パネルの最小サイズを維持します。

		Args:
			splitter: 対象のスプリッターウィンドウ。
			new_pos: 提案された新しいサッシ位置。

		Returns:
			調整後のサッシ位置。
		"""
		window1 = splitter.GetWindow1()
		window2 = splitter.GetWindow2()
		
		if not window1 or not window2:
			return new_pos
		
		# 垂直分割の場合、幅をチェック
		if splitter.GetSplitMode() == wx.SPLIT_VERTICAL:
			min_width1 = self._get_min_width(window1)
			min_width2 = self._get_min_width(window2)
			
			total_width = splitter.GetClientSize().GetWidth()
			
			# 新しいサッシ位置が最小幅を侵害しないかチェック
			if new_pos < min_width1:
				return min_width1
			elif new_pos > total_width - min_width2:
				return total_width - min_width2
		
		return new_pos
	
	@staticmethod
	def _get_min_width(window: wx.Window) -> int:
		"""ウィンドウの最小幅を再帰的に計算します。非表示のウィンドウは0を返します。"""
		if not window or not window.IsShown():
			return 0
		
		if isinstance(window, wx.SplitterWindow):
			# SplitterWindowの場合、2つの子の最小幅とサッシの幅を合計する
			w1 = window.GetWindow1()
			w2 = window.GetWindow2()
			min_w = ImageTaggingHelperFrame._get_min_width(w1) + ImageTaggingHelperFrame._get_min_width(w2)
			
			if window.IsSplit():
				min_w += window.GetSashSize()
			return min_w
		else:
			# 通常のパネルの場合
			min_size = window.GetMinSize()
			return min_size.GetWidth() if min_size.GetWidth() != -1 else 0
	
	def on_exit(self, event: wx.CommandEvent):
		"""アプリケーションを終了します。"""
		self.Close()
	
	def on_open_folder(self, event: wx.CommandEvent):
		"""フォルダ選択ダイアログを表示し、データセットを読み込みます。"""
		if self.dataset.initialized and self.dataset.is_dirty:
			ret = self.confirm_save()
			
			if ret == wx.YES:
				self.dataset.save(self.caption_ext, self.caption_format_config)
			elif ret == wx.CANCEL:
				return
		
		with wx.DirDialog(self, __("title:choose_a_directory"), style=wx.DD_DEFAULT_STYLE) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.load_dataset(path)
	
	def on_reload(self, event: wx.CommandEvent):
		"""
		データセットを再読み込みします。
		未保存の変更がある場合は確認ダイアログを表示します。
		"""
		if not self.dataset.folder_path:
			return
		
		if self.dataset.initialized and self.dataset.is_dirty:
			ret = self.confirm_save()
			
			if ret == wx.YES:
				self.dataset.save(self.caption_ext, self.caption_format_config)
			elif ret == wx.CANCEL:
				return
		
		self.load_dataset(self.dataset.folder_path)
	
	def on_save(self, event: wx.CommandEvent):
		"""データセットを保存します。"""
		if self.dataset.initialized:
			self.dataset.save(self.caption_ext, self.caption_format_config)
	
	def on_thumbnail_select(self, event: wx.CommandEvent):
		"""
		サムネイルリストの選択が変更されたときの処理。
		常に単一の選択を維持します。
		"""
		view_index = self.thumbnail_list.GetSelection()
		
		if view_index == wx.NOT_FOUND:
			# 選択が解除された場合、最後の選択状態に戻す
			# ただし、フィルタリングによって選択項目が消えた場合は戻さない
			if self.current_item_index != wx.NOT_FOUND:
				# 現在のフィルタで表示されているか確認
				self.thumbnail_list.select_item(self.current_item_index)
			return
		
		dataset_index = self.thumbnail_list.get_dataset_index(view_index)
		
		# 同じアイテムが再度選択された場合は何もしない
		if dataset_index == self.current_item_index:
			return
		
		self.current_item_index = dataset_index
		self._update_views_for_item_selection(dataset_index)
	
	def on_thumbnail_context_menu(self, event: wx.ContextMenuEvent):
		"""サムネイルリストのコンテキストメニューを表示します。"""
		pos = event.GetPosition()
		
		# キーボード操作（メニューキー）の場合、posは(-1, -1)になることが多い
		if pos == wx.DefaultPosition:
			view_index = self.thumbnail_list.GetSelection()
		else:
			# マウス操作の場合、クリック位置のアイテムを選択する
			client_pos = self.thumbnail_list.ScreenToClient(pos)
			view_index = self.thumbnail_list.VirtualHitTest(client_pos.y)
			
			if view_index != wx.NOT_FOUND:
				self.thumbnail_list.SetSelection(view_index)
				self.on_thumbnail_select(None)
		
		if view_index != wx.NOT_FOUND:
			menu = wx.Menu()
			
			view_image_item = menu.Append(wx.ID_ANY, __("action:view_image"))
			open_in_folder_item = menu.Append(wx.ID_ANY, __("action:open_in_folder"))
			
			self.Bind(wx.EVT_MENU, self.on_view_image, view_image_item)
			self.Bind(wx.EVT_MENU, self.on_open_in_folder, open_in_folder_item)
			
			self.thumbnail_list.PopupMenu(menu)
			menu.Destroy()
	
	def on_preferences(self, event: wx.CommandEvent):
		"""設定ダイアログを表示します。"""
		with PreferencesDialog(self, self.config) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				lang_changed = dlg.save()
				self.apply_font_settings()
				if lang_changed:
					wx.MessageBox(
						__("message:restart_to_apply_language"),
						__("title:restart_required"),
						wx.OK | wx.ICON_INFORMATION
					)
	
	def on_toggle_all_tags(self, event: wx.CommandEvent):
		"""データセットタグの表示/非表示を切り替えます。"""
		self._update_layout_visibility()
	
	def on_fullscreen(self, event: wx.CommandEvent):
		"""フルスクリーン表示を切り替えます。"""
		self.ShowFullScreen(not self.IsFullScreen())
	
	def on_undo(self, event: wx.CommandEvent):
		"""直前の操作を元に戻します。"""
		if self.controller:
			self.controller.undo()
	
	def on_redo(self, event: wx.CommandEvent):
		"""元に戻した操作をやり直します。"""
		if self.controller:
			self.controller.redo()
	
	def on_update_ui_undo(self, event: wx.UpdateUIEvent):
		"""アンドゥメニュー項目のUIを更新します。"""
		can_undo = self.controller.can_undo() if self.controller else False
		event.Enable(can_undo)
	
	def on_update_ui_redo(self, event: wx.UpdateUIEvent):
		"""リドゥメニュー項目のUIを更新します。"""
		can_redo = self.controller.can_redo() if self.controller else False
		event.Enable(can_redo)
	
	def on_copy(self, event: wx.CommandEvent):
		# 選択範囲の取得
		selected_cells = set()
		
		# ブロック選択
		top_left = self.image_tags_grid.GetSelectionBlockTopLeft()
		bottom_right = self.image_tags_grid.GetSelectionBlockBottomRight()
		for (r1, c1), (r2, c2) in zip(top_left, bottom_right):
			for r in range(r1, r2 + 1):
				for c in range(c1, c2 + 1):
					selected_cells.add((r, c))
		
		# 行選択
		for r in self.image_tags_grid.GetSelectedRows():
			for c in range(self.image_tags_grid.GetNumberCols()):
				selected_cells.add((r, c))
		
		# 個別セル選択
		for r, c in self.image_tags_grid.GetSelectedCells():
			selected_cells.add((r, c))
		
		# 選択がない場合はカーソル位置
		if not selected_cells:
			row = self.image_tags_grid.GetGridCursorRow()
			col = self.image_tags_grid.GetGridCursorCol()
			if row >= 0:
				selected_cells.add((row, col))
		
		if not selected_cells:
			return
		
		# 範囲の特定
		min_r = min(r for r, c in selected_cells)
		max_r = max(r for r, c in selected_cells)
		min_c = min(c for r, c in selected_cells)
		max_c = max(c for r, c in selected_cells)
		
		rows_data = []
		for r in range(min_r, max_r + 1):
			# 行内に選択セルがあるか確認
			if any((r, c) in selected_cells for c in range(min_c, max_c + 1)):
				row_items = []
				for c in range(min_c, max_c + 1):
					if (r, c) in selected_cells:
						row_items.append(self.image_tags_grid.GetCellValue(r, c))
					else:
						row_items.append("")
				rows_data.append(row_items)
		
		# TSV生成
		output = io.StringIO()
		writer = csv.writer(output, delimiter='\t', lineterminator='\n')
		writer.writerows(rows_data)
		text = output.getvalue()
		
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData(wx.TextDataObject(text))
			wx.TheClipboard.Close()
	
	def on_paste(self, event: wx.CommandEvent):
		if not self.controller or self.image_tags_grid.item_index is None:
			return
		
		text = ""
		if wx.TheClipboard.Open():
			if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
				data = wx.TextDataObject()
				wx.TheClipboard.GetData(data)
				text = data.GetText()
			wx.TheClipboard.Close()
		
		if not text:
			return
		
		tags = []
		# TSVパース
		f = io.StringIO(text)
		reader = csv.reader(f, delimiter='\t')
		
		for row in reader:
			if not row:
				continue
			
			tag_text = row[0].strip()
			if not tag_text:
				continue
			
			weight = 1.0
			if len(row) > 1:
				try:
					weight = float(row[1])
				except ValueError:
					pass
			
			tags.append(Tag(tag_text, weight))
		
		if tags:
			row = self.image_tags_grid.GetGridCursorRow()
			insert_pos = row + 1 if row >= 0 else self.image_tags_grid.GetNumberRows()
			self.controller.insert_tags(self.image_tags_grid.item_index, insert_pos, tuple(tags))
	
	def on_insert_blank_tag(self, event: wx.CommandEvent):
		if not self.controller or self.image_tags_grid.item_index is None:
			return
		
		row = self.image_tags_grid.GetGridCursorRow()
		self.controller.insert_tags(self.image_tags_grid.item_index, row + 1, (Tag(),))
	
	def on_delete_tag(self, event: wx.CommandEvent):
		if not self.controller or self.image_tags_grid.item_index is None:
			return
		
		rows = self.image_tags_grid.get_selected_rows()
		if not rows:
			row = self.image_tags_grid.GetGridCursorRow()
			if row < 0:
				return
			rows = [row]
		
		self.controller.remove_tags_at(self.image_tags_grid.item_index, tuple(rows))
	
	def on_move_tag_up(self, event: wx.CommandEvent):
		if not self.controller or self.image_tags_grid.item_index is None:
			return
		
		row = self.image_tags_grid.GetGridCursorRow()
		if row <= 0:
			return
		
		self.controller.move_tag(self.image_tags_grid.item_index, row, row - 1)
	
	def on_move_tag_down(self, event: wx.CommandEvent):
		if not self.controller or self.image_tags_grid.item_index is None:
			return
		
		row = self.image_tags_grid.GetGridCursorRow()
		if row < 0 or row >= self.image_tags_grid.GetNumberRows() - 1:
			return
		
		self.controller.move_tag(self.image_tags_grid.item_index, row, row + 1)
	
	def on_view_image(self, event: wx.CommandEvent):
		"""選択されている画像を既定のビューアで開きます。"""
		if self.current_item_index == wx.NOT_FOUND:
			return
		
		item = self.dataset[self.current_item_index]
		image_path = item.image_path
		
		if not wx.LaunchDefaultApplication(image_path):
			wx.LogError(f"Failed to open file: {image_path}")
	
	def on_open_in_folder(self, event: wx.CommandEvent):
		"""選択されている画像が存在する場所をエクスプローラ等で開きます。"""
		if self.current_item_index == wx.NOT_FOUND:
			return
		
		item = self.dataset[self.current_item_index]
		image_path = os.path.abspath(item.image_path)
		
		if sys.platform == 'win32':
			# explorerは正常に動作しても非ゼロの終了コードを返すことがあるため、check=Trueは指定しない
			subprocess.run(['explorer', '/select,', image_path])
		elif sys.platform == 'darwin':
			try:
				subprocess.run(['open', '-R', image_path], check=True)
			except (FileNotFoundError, subprocess.CalledProcessError):
				wx.LogError("Failed to open Finder.")
		else:
			try:
				dir_path = os.path.dirname(image_path)
				subprocess.run(['xdg-open', dir_path], check=True)
			except (FileNotFoundError, subprocess.CalledProcessError):
				wx.LogError("Failed to open file manager. Please ensure 'xdg-open' is installed.")
	
	def on_next_image(self, event: wx.CommandEvent):
		"""次の画像を選択します。"""
		count = self.thumbnail_list.GetItemCount()
		if count == 0:
			return
		
		current = self.thumbnail_list.GetSelection()
		next_idx = 0
		if current != wx.NOT_FOUND:
			next_idx = current + 1
		
		if next_idx < count:
			self.thumbnail_list.SetSelection(next_idx)
			self.on_thumbnail_select(None)
			
			if not self.thumbnail_list.IsVisible(next_idx):
				self.thumbnail_list.ScrollToLine(next_idx)
	
	def on_prev_image(self, event: wx.CommandEvent):
		"""前の画像を選択します。"""
		count = self.thumbnail_list.GetItemCount()
		if count == 0:
			return
		
		current = self.thumbnail_list.GetSelection()
		if current == wx.NOT_FOUND:
			return
		
		prev_idx = current - 1
		
		if prev_idx >= 0:
			self.thumbnail_list.SetSelection(prev_idx)
			self.on_thumbnail_select(None)
			
			if not self.thumbnail_list.IsVisible(prev_idx):
				self.thumbnail_list.ScrollToLine(prev_idx)
	
	def show_all_tags_context_menu(self, list_ctrl: AllTagsList, selected_tags: list[str], pos: wx.Point):
		"""
		AllTagsListのコンテキストメニューを表示します。
		"""
		menu = wx.Menu()
		
		# 「フィルタに追加」メニュー
		menu.Append(ID_ADD_TAG_TO_FILTER, __("action:add_tag_to_filter"))
		menu.AppendSeparator()
		
		# 選択されたタグの数に応じてラベルを変更
		multiple_tags = len(selected_tags) > 1
		
		# 選択中のアイテムへの操作
		menu.Append(ID_APPEND_TAG_TO_CURRENT, __("action:append_tags_to_current_items"))
		menu.Append(ID_REMOVE_TAG_FROM_CURRENT, __("action:remove_tags_from_current_items"))
		
		menu.AppendSeparator()
		
		# フィルター済みアイテムへの操作
		menu.Append(ID_APPEND_TAG_TO_FILTERED, __("action:append_tags_to_filtered_items"))
		menu.Append(ID_REMOVE_TAG_FROM_FILTERED, __("action:remove_tags_from_filtered_items"))
		
		menu.AppendSeparator()
		
		# すべてのアイテムへの操作
		menu.Append(ID_APPEND_TAG_TO_ALL, __("action:append_tags_to_all_items"))
		menu.Append(ID_REMOVE_TAG_FROM_ALL, __("action:remove_tags_from_all_items"))
		
		if not multiple_tags:
			menu.Append(ID_REPLACE_TAG_IN_ALL, __("action:replace_tags_in_all_items"))
		
		# イベントバインド
		self.Bind(wx.EVT_MENU, lambda evt: self.on_add_tags_to_filter(evt, selected_tags), id=ID_ADD_TAG_TO_FILTER)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_append_tags_to_current_items(evt, selected_tags), id=ID_APPEND_TAG_TO_CURRENT)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_remove_tags_from_current_items(evt, selected_tags), id=ID_REMOVE_TAG_FROM_CURRENT)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_append_tags_to_filtered_items(evt, selected_tags), id=ID_APPEND_TAG_TO_FILTERED)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_remove_tags_from_filtered_items(evt, selected_tags), id=ID_REMOVE_TAG_FROM_FILTERED)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_append_tags_to_all_items(evt, selected_tags), id=ID_APPEND_TAG_TO_ALL)
		self.Bind(wx.EVT_MENU, lambda evt: self.on_remove_tags_from_all_items(evt, selected_tags), id=ID_REMOVE_TAG_FROM_ALL)
		
		if not multiple_tags:
			self.Bind(wx.EVT_MENU, lambda evt: self.on_replace_tag_in_all_items(evt, selected_tags[0]), id=ID_REPLACE_TAG_IN_ALL)
		
		client_pos = list_ctrl.ScreenToClient(pos)
		list_ctrl.PopupMenu(menu, client_pos)
		menu.Destroy()
	
	def on_append_tags_to_current_items(self, event: wx.CommandEvent, tags: list[str]):
		"""選択中のアイテムにタグを追加します。"""
		if not self.controller or self.current_item_index == wx.NOT_FOUND:
			return
		position = self.image_tags_grid.GetGridCursorRow()
		tags_obj = tuple(Tag(t) for t in tags)
		self.controller.append_tags(self.current_item_index, tags_obj)
	
	def on_remove_tags_from_current_items(self, event: wx.CommandEvent, tags: list[str]):
		"""選択中のアイテムからタグを削除します。"""
		if not self.controller or self.current_item_index == wx.NOT_FOUND:
			return
		for tag_text in tags:
			self.controller.batch_remove_tags([self.current_item_index], (tag_text,))
	
	def on_append_tags_to_filtered_items(self, event: wx.CommandEvent, tags: list[str]):
		"""フィルター済みアイテムにタグを追加します。"""
		if not self.controller:
			return
		filtered_indices = self.thumbnail_list.filtered_indices
		if not filtered_indices:
			return
		
		for tag_text in tags:
			self.controller.batch_append_tags(filtered_indices, (Tag(tag_text),))
	
	def on_remove_tags_from_filtered_items(self, event: wx.CommandEvent, tags: list[str]):
		"""フィルター済みアイテムからタグを削除します。"""
		if not self.controller:
			return
		filtered_indices = self.thumbnail_list.filtered_indices
		if not filtered_indices:
			return
		
		for tag_text in tags:
			self.controller.batch_remove_tags(filtered_indices, (tag_text,))
	
	def on_append_tags_to_all_items(self, event: wx.CommandEvent, tags: list[str]):
		"""すべてのアイテムにタグを追加します。"""
		if not self.controller or not self.dataset:
			return
		
		all_indices = range(len(self.dataset))
		for tag_text in tags:
			self.controller.batch_append_tags(all_indices, (Tag(tag_text),))
	
	def on_remove_tags_from_all_items(self, event: wx.CommandEvent, tags: list[str]):
		"""すべてのアイテムからタグを削除します。"""
		if not self.controller or not self.dataset:
			return
		
		all_indices = range(len(self.dataset))
		for tag_text in tags:
			self.controller.batch_remove_tags(all_indices, (tag_text,))
	
	def on_replace_tag_in_all_items(self, event: wx.CommandEvent, old_tag_text: str):
		"""すべてのアイテムでタグを置換します。"""
		if not self.controller or not self.dataset:
			return
		
		# 置換後のタグを入力するダイアログを表示
		new_tag_text = wx.GetTextFromUser(
			__("dialog:enter_new_tag_for_replacement").format(old_tag=old_tag_text),
			__("title:replace_tag"),
			old_tag_text,
			self
		)
		
		if new_tag_text and new_tag_text != old_tag_text:
			all_indices = range(len(self.dataset))
			self.controller.batch_replace_tag(all_indices, old_tag_text, Tag(new_tag_text), keep_weight=True)
	
	def on_add_tags_to_filter(self, event: wx.CommandEvent, tags: list[str]):
		"""
		選択されたタグをフィルターコントロールに追加します。
		"""
		current_filter = self.filter_ctrl.GetValue()
		
		# 新しいタグを追加
		new_filter = ' '.join([
			# タグにスペースが含まれる場合は引用符で囲む
			f'"{tag}"' if ' ' in tag else tag
			for tag in tags
		])
		
		if current_filter.rstrip(' '):
			new_filter = current_filter + ' ' + new_filter
		else:
			new_filter = current_filter + new_filter
		
		self.filter_ctrl.SetValue(new_filter)
		
		# フィルタを適用
		self.on_filter_items(None)
	
	# === ダイアログボックス ===
	
	def confirm_save(self):
		return wx.MessageBox(
			__("message:unsaved_changes"),
			__("title:save_changes"),
			wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
			self
		)
	
	# === UI更新メソッド ===
	
	def _update_layout_visibility(self):
		"""メニューのチェック状態に基づいてパネルの表示/非表示を更新します。"""
		show_all_tags = self.toggle_all_tags_menu.IsChecked()
		
		# splitter_2 の状態更新 (all_tags_panel の表示/非表示)
		if show_all_tags:
			if not self.splitter_2.IsSplit():
				self.splitter_2.SplitVertically(self.image_tags_panel, self.all_tags_panel)
				self.splitter_2.SetSashPosition(self.splitter_2.GetSize().GetWidth() // 2)
		else:
			if self.splitter_2.IsSplit():
				self.splitter_2.Unsplit(self.all_tags_panel)
		
		self.Layout()
	
	def save_ui_settings(self):
		"""UIの状態（スプリッターの位置など）を保存します。"""
		self.config.set('ui.splitter_1_pos', self.splitter_1.GetSashPosition())
		self.config.set('ui.splitter_2_pos', self.splitter_2.GetSashPosition())
		
		# ウィンドウサイズを保存
		size = self.GetSize()
		self.config.set('ui.window_width', size.width)
		self.config.set('ui.window_height', size.height)
		
		self.config.save()
	
	def load_window_size_settings(self):
		width = self.config.get('ui.window_width', 1200)
		height = self.config.get('ui.window_height', 800)
		return wx.Size(width, height)
	
	def load_ui_settings(self):
		"""UIの状態（スプリッターの位置など）を復元します。"""
		self.Freeze()
		try:
			# デフォルト値は初期レイアウトに基づく
			# 初期サイズ(1200)に基づく比率 1:1:1 -> 400:400:400
			s1_pos = self.config.get('ui.splitter_1_pos', 400)
			s2_pos = self.config.get('ui.splitter_2_pos', 400)
			
			if s1_pos > 0:
				self.splitter_1.SetSashPosition(s1_pos)
			if s2_pos > 0:
				self.splitter_2.SetSashPosition(s2_pos)
		finally:
			self.Thaw()
	
	def apply_font_settings(self):
		"""設定されたフォントをUIに適用します。"""
		font_desc = self.config.get('ui.font')
		if not font_desc:
			return
		
		font = wx.Font(font_desc)
		if not font.IsOk():
			return
		
		# ImageTagsGridへの適用
		self.image_tags_grid.SetDefaultCellFont(font)
		self.image_tags_grid.SetLabelFont(font)
		
		# 行の高さを調整
		dc = wx.ClientDC(self.image_tags_grid)
		dc.SetFont(font)
		text_width, text_height = dc.GetTextExtent("Wg")
		row_height = text_height + 4  # パディングを追加
		
		self.image_tags_grid.SetDefaultRowSize(row_height, True)
		self.image_tags_grid.ForceRefresh()
		
		# DatasetTagsListへの適用
		self.all_tags_list.apply_font(font)
	
	def _update_views_for_item_selection(self, selection: int):
		"""指定された選択に基づいて関連するビューを更新します。"""
		self._update_image_path_view(selection)
		self.image_tags_grid.switch_item(selection)
	
	def _update_image_path_view(self, selection: int):
		"""選択された画像のパスを表示します。"""
		if not self.dataset.initialized or selection == wx.NOT_FOUND:
			self.path_text.SetValue('')
			return
		
		item = self.dataset[selection]
		self.path_text.SetValue(item.image_path)
	
	# === データ処理メソッド ===
	
	def load_dataset(self, folder_path: str):
		"""
		指定されたフォルダからデータセットを構築します。

		Args:
			folder_path: 画像とキャプションファイルが含まれるフォルダのパス。
		"""
		self.dataset.load(
			folder_path,
			self.image_exts,
			caption_ext=self.caption_ext,
			caption_format_config=self.caption_format_config,
		)
		self.controller = self.dataset.get_controller('frame')
		dataset = self.dataset
		
		self.thumbnail_list.set_dataset(dataset)
		self.image_tags_grid.set_dataset(dataset)
		self.all_tags_list.set_dataset(dataset)
		
		if dataset and len(dataset) > 0:
			self.thumbnail_list.SetSelection(0)
			# SetSelectionはイベントを発生させないため、手動で更新処理を呼び出す
			self.current_item_index = 0
			self._update_views_for_item_selection(0)
		else:
			# データセットが空の場合のビュー更新
			self.current_item_index = wx.NOT_FOUND
			self._update_views_for_item_selection(wx.NOT_FOUND)
	
	@staticmethod
	def launch(config: Config):
		"""アプリケーションを起動します。"""
		app = wx.App()
		frame = ImageTaggingHelperFrame(None, __("title:app_main_window"), config=config)
		frame.Show()
		app.MainLoop()

def main():
	"""アプリケーションのエントリポイント。"""
	config = Config(APP_NAME)
	lang = config.get('language', 'en')
	setup_translation(APP_ID, lang=lang)
	
	# 高DPI対応を有効にする
	try:
		# Windows 8.1以降: Per-Monitor DPI Aware V2
		ctypes.windll.shcore.SetProcessDpiAwareness(2)
	except (AttributeError, OSError):
		try:
			# Windows Vista以降: System DPI Aware
			ctypes.windll.user32.SetProcessDPIAware()
		except (AttributeError, OSError):
			# DPI設定に対応していないOSの場合は何もしない
			pass
	ImageTaggingHelperFrame.launch(config)

if __name__ == "__main__":
	main()
