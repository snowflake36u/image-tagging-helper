import os
import glob
import wx
import wx.grid
import ctypes
from collections import Counter

from src.image_tagging_helper.core.caption import Caption, CaptionFormatConfig
from src.image_tagging_helper.core.config import Config
from src.image_tagging_helper.core.dataset import Dataset, DatasetItem
from src.image_tagging_helper.core.manager import DatasetManager
from src.image_tagging_helper.wx.image_list import ImageVListBox
from src.image_tagging_helper.wx.image_tags_grid import ImageTagsGrid
from src.image_tagging_helper.i18n import setup_translation, __

# アプリケーションのドメイン名を設定
APP_NAME = "Image Tagging Helper"
APP_ID = "image_tagging_helper"

SASH_MIN_WIDTH = 120

class PreferencesDialog(wx.Dialog):
	"""設定画面のダイアログ。"""
	
	def __init__(self, parent, config: Config):
		super().__init__(parent, title=__("title:preferences"))
		self.config = config
		self.original_lang = self.config.get('language', 'en')
		self._init_ui()
	
	def _init_ui(self):
		dlg_sizer = wx.BoxSizer(wx.VERTICAL)
		
		panel = wx.Panel(self)
		panel_sizer = wx.BoxSizer(wx.VERTICAL)
		
		# 言語設定
		sb = wx.StaticBox(panel, label=__("label:language_settings"))
		sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
		
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(panel, label=__("label:language"))
		
		self.languages = [("en", "English"), ("ja", "Japanese")]
		choices = [lang[1] for lang in self.languages]
		self.lang_choice = wx.Choice(panel, choices=choices)
		
		# 現在の設定を反映させる
		current_lang_code = self.config.get('language', 'en')
		lang_codes = [lang[0] for lang in self.languages]
		try:
			idx = lang_codes.index(current_lang_code)
			self.lang_choice.SetSelection(idx)
		except ValueError:
			self.lang_choice.SetSelection(wx.NOT_FOUND)
		
		hbox.Add(st, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
		hbox.Add(self.lang_choice, proportion=1)
		
		sbs.Add(hbox, flag=wx.EXPAND | wx.ALL, border=5)
		panel_sizer.Add(sbs, flag=wx.EXPAND | wx.ALL, border=10)
		
		panel.SetSizer(panel_sizer)
		
		dlg_sizer.Add(panel, 1, wx.EXPAND)
		
		# ボタン
		btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		dlg_sizer.Add(btns, flag=wx.EXPAND | wx.ALL, border=10)
		
		self.SetSizer(dlg_sizer)
		self.Fit()
		self.CenterOnParent()
	
	def save(self) -> bool:
		"""設定を保存します。言語が変更された場合はTrueを返します。"""
		idx = self.lang_choice.GetSelection()
		if idx != wx.NOT_FOUND:
			lang_code = self.languages[idx][0]
			self.config.set('language', lang_code)
		
		self.config.save()
		
		return self.original_lang != self.config.get('language', 'en')

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
		self.dataset_manager = DatasetManager(CaptionFormatConfig())
		self.last_thumbnail_selection: int = wx.NOT_FOUND
		
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
		
		open_folder_item = self._append_menu_item(menu, wx.ID_OPEN, __("action:open_folder"), __("tooltip:open_folder"), 'Ctrl+O')
		self.Bind(wx.EVT_MENU, self.on_open_folder, open_folder_item)
		
		reload_item = self._append_menu_item(menu, wx.ID_REFRESH, __("action:reload"), __("tooltip:reload"))
		
		menu.AppendSeparator()
		
		save_item = self._append_menu_item(menu, wx.ID_SAVE, __("action:save"), __("tooltip:save"), 'Ctrl+S')
		
		menu.AppendSeparator()
		
		exit_item = self._append_menu_item(menu, wx.ID_EXIT, __("action:exit"), __("tooltip:exit"))
		self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
	
	def _init_edit_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:edit"))
		
		undo_item = self._append_menu_item(menu, wx.ID_UNDO, __("action:undo"), __("tooltip:undo"), 'Ctrl+Z')
		redo_item = self._append_menu_item(menu, wx.ID_REDO, __("action:redo"), __("tooltip:redo"), 'Ctrl+Y')
		
		menu.AppendSeparator()
		
		cut_item = self._append_menu_item(menu, wx.ID_CUT, __("action:cut"), __("tooltip:cut"), 'Ctrl+X')
		copy_item = self._append_menu_item(menu, wx.ID_COPY, __("action:copy"), __("tooltip:copy"), 'Ctrl+C')
		paste_item = self._append_menu_item(menu, wx.ID_PASTE, __("action:paste"), __("tooltip:paste"), 'Ctrl+V')
		
		menu.AppendSeparator()
		
		add_tag_item = self._append_menu_item(menu, wx.ID_ANY, __("action:add_tag"), __("tooltip:add_tag"), 'Ctrl+E')
		delete_tag_item = self._append_menu_item(menu, wx.ID_ANY, __("action:delete_tag"), __("tooltip:delete_tag"), 'Ctrl+D')
		replace_tag_item = self._append_menu_item(menu, wx.ID_ANY, __("action:replace_tag"), __("tooltip:replace_tag"), 'Ctrl+H')
		
		menu.AppendSeparator()
		
		move_tag_up_item = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_up"), __("tooltip:move_tag_up"), 'Shift+W')
		move_tag_down_item = self._append_menu_item(menu, wx.ID_ANY, __("action:move_tag_down"), __("tooltip:move_tag_down"), 'Shift+S')
		sort_tag_item = self._append_menu_item(menu, wx.ID_ANY, __("action:sort_tag"), __("tooltip:sort_tag"), 'Ctrl+L')
	
	def _init_dataset_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:dataset"))
		
		open_in_folder_item = self._append_menu_item(menu, wx.ID_ANY, __("action:open_in_folder"), __("tooltip:open_in_folder"))
		view_image_item = self._append_menu_item(menu, wx.ID_ANY, __("action:view_image"), __("tooltip:view_image"))
		
		menu.AppendSeparator()
		
		next_image_item = self._append_menu_item(menu, wx.ID_FORWARD, __("action:next_image"), __("tooltip:next_image"), 'Shift+C')
		prev_image_item = self._append_menu_item(menu, wx.ID_BACKWARD, __("action:prev_image"), __("tooltip:prev_image"), 'Shift+X')
		
		menu.AppendSeparator()
		
		filter_images_item = self._append_menu_item(menu, wx.ID_FIND, __("action:filter_images"), __("tooltip:filter_images"), 'F3')
		clear_filter_item = self._append_menu_item(menu, wx.ID_ANY, __("action:clear_filter"), __("tooltip:clear_filter"), 'Shift+F3')
	
	def _init_view_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:view"))
		
		self.toggle_tag_palette_item = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_tag_palette"), __("tooltip:toggle_tag_palette"), kind=wx.ITEM_CHECK)
		self.toggle_tag_palette_item.Check(True)
		self.Bind(wx.EVT_MENU, self.on_toggle_tag_palette, self.toggle_tag_palette_item)
		
		self.toggle_dataset_tags_item = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_dataset_tags"), __("tooltip:toggle_dataset_tags"), kind=wx.ITEM_CHECK)
		self.toggle_dataset_tags_item.Check(True)
		self.Bind(wx.EVT_MENU, self.on_toggle_dataset_tags, self.toggle_dataset_tags_item)
		
		menu.AppendSeparator()
		
		fullscreen_item = self._append_menu_item(menu, wx.ID_ANY, __("action:fullscreen"), __("tooltip:fullscreen"), 'F11')
	
	def _init_configure_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:configure"))
		
		preferences_item = self._append_menu_item(menu, wx.ID_PREFERENCES, __("action:preferences"), __("tooltip:preferences"))
		self.Bind(wx.EVT_MENU, self.on_preferences, preferences_item)
	
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
		path_panel = wx.Panel(parent)
		path_sizer = wx.BoxSizer(wx.HORIZONTAL)
		path_label = wx.StaticText(path_panel, label=__("label:file_path"))
		self.path_text = wx.TextCtrl(path_panel, style=wx.TE_READONLY)
		path_sizer.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		path_sizer.Add(self.path_text, 1, wx.EXPAND)
		path_panel.SetSizer(path_sizer)
		return path_panel
	
	def _create_main_sash_layout(self, parent: wx.Window):
		"""
		入れ子になったスプリッターウィンドウでメインレイアウトを作成します。
		"""
		# スプリッターウィンドウの作成
		self.splitter_1 = wx.SplitterWindow(parent)
		self.splitter_2 = wx.SplitterWindow(self.splitter_1)
		self.splitter_3 = wx.SplitterWindow(self.splitter_2)
		
		splitters = [self.splitter_1, self.splitter_2, self.splitter_3]
		for splitter in splitters:
			splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
			splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.on_splitter_sash_pos_changing)
			splitter.Bind(wx.EVT_SIZE, self.on_splitter_resize)
		
		# 各ペインの作成
		self._create_thumbnail_panel(self.splitter_1)
		self._create_image_tags_panel(self.splitter_2)
		self._create_tag_palette_panel(self.splitter_3)
		self._create_dataset_tags_panel(self.splitter_3)
		
		# スプリッターの分割設定
		# 全体幅1200に対して各パネル300ずつ割り当てる
		self.splitter_1.SplitVertically(self.thumbnail_panel, self.splitter_2, 300)
		self.splitter_2.SplitVertically(self.image_tags_panel, self.splitter_3, 300)
		self.splitter_3.SplitVertically(self.tag_palette_panel, self.dataset_tags_panel, 300)
		
		# UI設定を復元
		wx.CallAfter(self.load_ui_settings)
		
		# ウィンドウリサイズ時の挙動を設定
		self.splitter_1.SetSashGravity(0.25)
		self.splitter_2.SetSashGravity(1.0 / 3.0)
		self.splitter_3.SetSashGravity(0.5)
	
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
		
		self.image_tags_grid = ImageTagsGrid(self.image_tags_panel, self.dataset_manager)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.image_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.image_tags_grid, 1, wx.EXPAND)
		self.image_tags_panel.SetSizer(sizer)
	
	def _create_tag_palette_panel(self, parent: wx.Window):
		"""タグパレットパネルを作成します。"""
		self.tag_palette_panel = wx.Panel(parent)
		self.tag_palette_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		self.tag_palette_toolbar = wx.ToolBar(self.tag_palette_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.tag_palette_toolbar.AddControl(wx.StaticText(self.tag_palette_toolbar, label=__("label:tag_palette")))
		self.tag_palette_toolbar.AddSeparator()
		self.tag_palette_toolbar.Realize()
		
		self.tag_palette_content = wx.Panel(self.tag_palette_panel)
		self.tag_palette_content.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE))
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.tag_palette_toolbar, 0, wx.EXPAND)
		sizer.Add(self.tag_palette_content, 1, wx.EXPAND)
		self.tag_palette_panel.SetSizer(sizer)
	
	def _create_dataset_tags_panel(self, parent: wx.Window):
		"""データセット全体のタグ一覧パネルを作成します。"""
		self.dataset_tags_panel = wx.Panel(parent)
		self.dataset_tags_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		self.dataset_tags_toolbar = wx.ToolBar(self.dataset_tags_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.dataset_tags_toolbar.AddControl(wx.StaticText(self.dataset_tags_toolbar, label=__("label:dataset_tags")))
		self.dataset_tags_toolbar.AddSeparator()
		self.dataset_tags_toolbar.Realize()
		
		self.dataset_tags_list = wx.ListCtrl(self.dataset_tags_panel, style=wx.LC_REPORT)
		self.dataset_tags_list.InsertColumn(0, __("label:tag"), width=150)
		self.dataset_tags_list.InsertColumn(1, __("label:count"), width=50)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.dataset_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.dataset_tags_list, 1, wx.EXPAND)
		self.dataset_tags_panel.SetSizer(sizer)
	
	# === イベントハンドラ ===
	
	def on_close(self, event: wx.CloseEvent):
		"""ウィンドウが閉じるときにUI設定を保存します。"""
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
		with wx.DirDialog(self, __("title:choose_a_directory"), style=wx.DD_DEFAULT_STYLE) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.load_dataset(path)
	
	def on_thumbnail_select(self, event: wx.CommandEvent):
		"""
		サムネイルリストの選択が変更されたときの処理。
		常に単一の選択を維持します。
		"""
		item_index = self.thumbnail_list.GetSelection()
		
		if item_index == wx.NOT_FOUND:
			# 選択が解除された場合、最後の選択状態に戻す
			if self.last_thumbnail_selection != wx.NOT_FOUND:
				self.thumbnail_list.SetSelection(self.last_thumbnail_selection)
			return
		
		# 同じアイテムが再度選択された場合は何もしない
		if item_index == self.last_thumbnail_selection:
			return
		
		self.last_thumbnail_selection = item_index
		self._update_views_for_item_selection(item_index)
	
	def on_preferences(self, event: wx.CommandEvent):
		"""設定ダイアログを表示します。"""
		with PreferencesDialog(self, self.config) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				lang_changed = dlg.save()
				if lang_changed:
					wx.MessageBox(
						__("message:restart_to_apply_language"),
						__("title:restart_required"),
						wx.OK | wx.ICON_INFORMATION
					)
	
	def on_toggle_tag_palette(self, event: wx.CommandEvent):
		"""タグパレットの表示/非表示を切り替えます。"""
		self._update_layout_visibility()
	
	def on_toggle_dataset_tags(self, event: wx.CommandEvent):
		"""データセットタグの表示/非表示を切り替えます。"""
		self._update_layout_visibility()
	
	# === UI更新メソッド ===
	
	def _update_layout_visibility(self):
		"""メニューのチェック状態に基づいてパネルの表示/非表示を更新します。"""
		show_tag_palette = self.toggle_tag_palette_item.IsChecked()
		show_dataset_tags = self.toggle_dataset_tags_item.IsChecked()
		
		# splitter_3 の状態更新
		if show_tag_palette and show_dataset_tags:
			if not self.splitter_3.IsSplit():
				self.splitter_3.SplitVertically(self.tag_palette_panel, self.dataset_tags_panel)
				# 位置を復元またはデフォルト値に設定
				self.splitter_3.SetSashPosition(self.splitter_3.GetSize().GetWidth() // 2)
		elif show_tag_palette:
			if self.splitter_3.IsSplit():
				self.splitter_3.Unsplit(self.dataset_tags_panel)
			elif self.splitter_3.GetWindow1() != self.tag_palette_panel:
				# 現在 dataset_tags_panel が表示されている場合、入れ替える
				# Unsplit 状態では GetWindow1 が表示されているウィンドウ
				# ただし、Unsplit(to_remove) を呼ぶと、残った方が GetWindow1 になるはず
				# ここでは一度初期化しなおすのが確実
				self.splitter_3.Initialize(self.tag_palette_panel)
		elif show_dataset_tags:
			if self.splitter_3.IsSplit():
				self.splitter_3.Unsplit(self.tag_palette_panel)
			elif self.splitter_3.GetWindow1() != self.dataset_tags_panel:
				self.splitter_3.Initialize(self.dataset_tags_panel)
		
		# splitter_2 の状態更新 (splitter_3 の表示/非表示)
		show_splitter_3 = show_tag_palette or show_dataset_tags
		
		if show_splitter_3:
			if not self.splitter_2.IsSplit():
				self.splitter_2.SplitVertically(self.image_tags_panel, self.splitter_3)
				self.splitter_2.SetSashPosition(self.splitter_2.GetSize().GetWidth() * 2 // 3)
		else:
			if self.splitter_2.IsSplit():
				self.splitter_2.Unsplit(self.splitter_3)
		
		self.Layout()
	
	def save_ui_settings(self):
		"""UIの状態（スプリッターの位置など）を保存します。"""
		self.config.set('ui.splitter_1_pos', self.splitter_1.GetSashPosition())
		self.config.set('ui.splitter_2_pos', self.splitter_2.GetSashPosition())
		self.config.set('ui.splitter_3_pos', self.splitter_3.GetSashPosition())
		
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
			# 初期サイズ(1200)に基づく比率 1:1:1:1 -> 300:300:300:300
			s1_pos = self.config.get('ui.splitter_1_pos', 300)
			s2_pos = self.config.get('ui.splitter_2_pos', 300)
			s3_pos = self.config.get('ui.splitter_3_pos', 300)
			
			if s1_pos > 0:
				self.splitter_1.SetSashPosition(s1_pos)
			if s2_pos > 0:
				self.splitter_2.SetSashPosition(s2_pos)
			if s3_pos > 0:
				self.splitter_3.SetSashPosition(s3_pos)
		finally:
			self.Thaw()
	
	def _update_views_for_item_selection(self, selection: int):
		"""指定された選択に基づいて関連するビューを更新します。"""
		self._update_image_path_view(selection)
		self.image_tags_grid.switch_item(selection)
	
	def _update_image_path_view(self, selection: int):
		"""選択された画像のパスを表示します。"""
		if not self.dataset_manager.initialized or selection == wx.NOT_FOUND:
			self.path_text.SetValue('')
			return
		
		item = self.dataset_manager.dataset[selection]
		self.path_text.SetValue(item.image_path)
	
	def _update_dataset_tags_view(self):
		"""データセット全体のタグとその出現回数をリストに表示します。"""
		self.dataset_tags_list.ClearAll()  # 既存の項目をクリア
		self.dataset_tags_list.InsertColumn(0, __("label:tag"), width=150)
		self.dataset_tags_list.InsertColumn(1, __("label:count"), width=50)
		
		dataset = self.dataset_manager.dataset
		if not self.dataset_manager.initialized or len(dataset) == 0:
			return
		
		all_tags = []
		for item in dataset:
			for tag in item.caption.tags:
				all_tags.append(tag.text)
		
		tag_counts = Counter(all_tags)
		
		# タグをアルファベット順にソートして表示
		sorted_tags = sorted(tag_counts.items())
		
		for i, (tag_text, count) in enumerate(sorted_tags):
			self.dataset_tags_list.InsertItem(i, tag_text)
			self.dataset_tags_list.SetItem(i, 1, str(count))
	
	# === データ処理メソッド ===
	
	def load_dataset(self, folder_path: str):
		"""
		指定されたフォルダからデータセットを構築します。
		
		Args:
			folder_path: 画像とキャプションファイルが含まれるフォルダのパス。
		"""
		self.dataset_manager.load(folder_path, self.image_exts, caption_ext=self.caption_ext)
		dataset = self.dataset_manager.dataset
		
		self.thumbnail_list.set_dataset(dataset)
		
		if dataset and len(dataset) > 0:
			self.thumbnail_list.SetSelection(0)
			# SetSelectionはイベントを発生させないため、手動で更新処理を呼び出す
			self.last_thumbnail_selection = 0
			self._update_views_for_item_selection(0)
		
		# データセットタグのビューを更新
		self._update_dataset_tags_view()
	
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
