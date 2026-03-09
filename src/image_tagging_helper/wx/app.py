import wx
import wx.grid
import ctypes
import bisect
import os
import sys
import subprocess
import traceback
from typing import TYPE_CHECKING

from image_tagging_helper.core.config import Config
from image_tagging_helper.models.caption import CaptionFormatConfig, Tag
from image_tagging_helper.models.dataset import Dataset
from image_tagging_helper.models.controller import DatasetController
from image_tagging_helper.models.tag_lexicon import TagLexicon
from image_tagging_helper.wx.editor_widgets.all_tag_list import AllTagsList, TagSortOrder
from image_tagging_helper.wx.editor_widgets.image_list import ImageVListBox
from image_tagging_helper.wx.editor_widgets.image_tags_grid import ImageTagsGrid
from image_tagging_helper.wx.events import (
	EVT_SELECT_IN_ALL_TAGS,
	EVT_ADD_TAGS_TO_FILTER,
	EVT_APPEND_TAGS_TO_CURRENT,
	EVT_REMOVE_TAGS_FROM_CURRENT,
	EVT_APPEND_TAGS_TO_FILTERED,
	EVT_REMOVE_TAGS_FROM_FILTERED,
	EVT_APPEND_TAGS_TO_ALL,
	EVT_REMOVE_TAGS_FROM_ALL,
	EVT_REPLACE_TAG_IN_ALL,
	EVT_VIEW_IMAGE,
	EVT_OPEN_IN_FOLDER,
)
from image_tagging_helper.wx.preferences import PreferencesDialog
from image_tagging_helper.wx.frame_menu import (
	FrameMenuMixin,
	ID_SORT_MENU,
	ID_SORT_BY_TAG_NAME,
	ID_SORT_BY_COUNT,
	ID_SORT_BY_CATEGORY_ORDER,
	ID_SORT_BY_CATEGORY_TEXT,
	ID_SORT_DESCENDING,
)
from image_tagging_helper.i18n import setup_translation, __

if TYPE_CHECKING:
	from image_tagging_helper.models.diff import DatasetDiff

# アプリケーションのドメイン名を設定
APP_NAME = "Image Tagging Helper"
APP_ID = "image_tagging_helper"

# アイコンリソースのパス (app.pyからの相対パス)
ICON_SORT_LINES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'sort_lines.ico'))

SASH_MIN_WIDTH = 120
TOOLBAR_CONTENT_HEIGHT = 24
STATUSBAR_PADDING = 10

class ImageTaggingHelperFrame(wx.Frame, FrameMenuMixin):
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
		self.base_title = title
		
		# ウィンドウサイズを復元
		window_size = self.load_window_size_settings()
		super().__init__(parent, title=title, size=window_size)
		
		# === データメンバーの初期化 ===
		self.image_exts = ['.jpg', '.jpeg', '.png', '.webp']
		self.caption_ext = '.caption'
		self.dataset = Dataset()
		self.remote_controller: DatasetController | None = None
		self.caption_format_config = CaptionFormatConfig()
		self.tag_lexicon = TagLexicon()
		self.current_item_index: int = wx.NOT_FOUND
		
		# タグ情報の読み込み
		self.tag_lexicon_path = os.path.join(self.config.config_dir, 'tag_lexicon.json')
		self.tag_lexicon.load(self.tag_lexicon_path)
		
		# === UIの初期化 ===
		self._init_ui()
		self._init_accelerators()  # FrameMenuMixinから呼び出される
		
		# === イベントのバインド ===
		self.Bind(wx.EVT_CLOSE, self.on_close)
	
	def _init_ui(self):
		"""UI全体の初期化"""
		self._init_menubar()  # FrameMenuMixinから呼び出される
		
		# ステータスバーの作成
		self.statusbar = self.CreateStatusBar(2)
		self.statusbar.SetStatusWidths([STATUSBAR_PADDING, -1])
		
		# 各コントロールの配置
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
			self.image_list,
			self.image_tags_grid,
			self.all_tags_list,
		]
		
		# Tabキーによるフォーカス遷移を制御するためのイベントフック
		self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
		
		# メニュー項目のヘルプ文字列をステータスバーの1番目のフィールドに表示するためのイベントバインド
		self.Bind(wx.EVT_MENU_HIGHLIGHT, self.on_menu_highlight)
		
		# AllTagsListからのイベントをバインド
		self._bind_all_tags_list_events()
		
		# 初期フォーカスをサムネイルリストに設定
		wx.CallAfter(self.image_list.SetFocus)
		self._update_statusbar()
	
	def _bind_all_tags_list_events(self):
		"""AllTagsListから発行されるイベントをバインドします。"""
		self.Bind(EVT_ADD_TAGS_TO_FILTER, self.on_add_tags_to_filter)
		self.Bind(EVT_APPEND_TAGS_TO_CURRENT, self.on_append_tags_to_current_items)
		self.Bind(EVT_REMOVE_TAGS_FROM_CURRENT, self.on_remove_tags_from_current_items)
		self.Bind(EVT_APPEND_TAGS_TO_FILTERED, self.on_append_tags_to_filtered_items)
		self.Bind(EVT_REMOVE_TAGS_FROM_FILTERED, self.on_remove_tags_from_filtered_items)
		self.Bind(EVT_APPEND_TAGS_TO_ALL, self.on_append_tags_to_all_items)
		self.Bind(EVT_REMOVE_TAGS_FROM_ALL, self.on_remove_tags_from_all_items)
		self.Bind(EVT_REPLACE_TAG_IN_ALL, self.on_replace_tag_in_all_items)
	
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
		temp_btn = wx.BitmapButton(parent, bitmap=wx.Bitmap(TOOLBAR_CONTENT_HEIGHT, TOOLBAR_CONTENT_HEIGHT))
		# Sizerのパディング(上下2*2=4)を考慮
		self.toolbar_min_height = temp_btn.GetBestSize().height + 4
		temp_btn.Destroy()
		
		# スプリッターウィンドウの作成
		self.splitter_1 = wx.SplitterWindow(parent)
		self.splitter_2 = wx.SplitterWindow(self.splitter_1)
		
		splitters = [self.splitter_1, self.splitter_2]
		for splitter in splitters:
			splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
			splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.on_splitter_sash_pos_changing)
			splitter.Bind(wx.EVT_SIZE, self.on_splitter_resize)
		
		# 各ペインの作成
		self._create_images_panel(self.splitter_1)
		self._create_image_tags_panel(self.splitter_2)
		self._create_all_tags_panel(self.splitter_2)
		
		# スプリッターの分割設定
		# 全体幅1200に対して各パネル400ずつ割り当てる
		self.splitter_1.SplitVertically(self.images_panel, self.splitter_2, 400)
		self.splitter_2.SplitVertically(self.image_tags_panel, self.all_tags_panel, 400)
		
		# UI設定を復元
		wx.CallAfter(self.load_ui_settings)
		
		# ウィンドウリサイズ時の挙動を設定
		self.splitter_1.SetSashGravity(0)
		self.splitter_2.SetSashGravity(0.5)
	
	def _create_header_panel(self, parent: wx.Window, label: str) -> wx.Panel:
		"""
		ラベル付きの標準的なツールバーパネルを作成します。
		"""
		toolbar_panel = wx.Panel(parent)
		toolbar_panel.SetMinSize((-1, self.toolbar_min_height))
		
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		# ラベルを左側に配置
		label_widget = wx.StaticText(toolbar_panel, label=label)
		sizer.Add(label_widget, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
		
		toolbar_panel.SetSizer(sizer)
		return toolbar_panel
	
	def _create_images_panel(self, parent: wx.Window):
		"""画像のサムネイルリストパネルを作成します。"""
		self.images_panel = wx.Panel(parent)
		self.images_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		
		self.images_toolbar = self._create_header_panel(self.images_panel, __("label:image_list"))
		
		self.image_list = ImageVListBox(self.images_panel, style=wx.VSCROLL | wx.ALWAYS_SHOW_SB)
		self.image_list.Bind(wx.EVT_LISTBOX, self.on_image_list_select)
		# ImageVListBoxからのカスタムイベントをバインド
		self.image_list.Bind(EVT_VIEW_IMAGE, self.on_view_image)
		self.image_list.Bind(EVT_OPEN_IN_FOLDER, self.on_open_in_folder)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.images_toolbar, 0, wx.EXPAND)
		sizer.Add(self.image_list, 1, wx.EXPAND)
		self.images_panel.SetSizer(sizer)
	
	def _create_image_tags_panel(self, parent: wx.Window):
		"""画像のタグ一覧パネルを作成します。"""
		self.image_tags_panel = wx.Panel(parent)
		self.image_tags_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		
		self.image_tags_toolbar = self._create_header_panel(self.image_tags_panel, __("label:image_tags"))
		
		self.image_tags_grid = ImageTagsGrid(self.image_tags_panel)
		self.image_tags_grid.Bind(EVT_SELECT_IN_ALL_TAGS, self.on_select_in_all_tags)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.image_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.image_tags_grid, 1, wx.EXPAND)
		self.image_tags_panel.SetSizer(sizer)
	
	def _create_all_tags_panel(self, parent: wx.Window):
		"""データセット全体のタグ一覧パネルを作成します。"""
		self.all_tags_panel = wx.Panel(parent)
		self.all_tags_panel.SetMinSize((SASH_MIN_WIDTH, -1))
		
		self.all_tags_toolbar = self._create_header_panel(self.all_tags_panel, __("label:all_tags"))
		toolbar_sizer = self.all_tags_toolbar.GetSizer()
		
		# 伸縮可能なスペースをラベルとボタンの間に追加
		toolbar_sizer.AddStretchSpacer(1)
		
		# ソートメニューボタンを追加
		try:
			icon_image = wx.Image(ICON_SORT_LINES, wx.BITMAP_TYPE_ICO)
			if not icon_image.IsOk():
				raise FileNotFoundError(f"Icon not found: {ICON_SORT_LINES}")
			
			icon_image = icon_image.Rescale(TOOLBAR_CONTENT_HEIGHT, TOOLBAR_CONTENT_HEIGHT, wx.IMAGE_QUALITY_HIGH)
			sort_icon = wx.Bitmap(icon_image)
			
			self.sort_button = wx.BitmapButton(self.all_tags_toolbar, id=ID_SORT_MENU, bitmap=sort_icon, style=wx.BORDER_NONE)
		except Exception:
			self.sort_button = wx.Button(self.all_tags_toolbar, id=ID_SORT_MENU, label=__("tooltip:sort_tags"))
		
		toolbar_sizer.Add(self.sort_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		
		self.all_tags_list = AllTagsList(self.all_tags_panel)
		self.all_tags_list.set_tag_lexicon(self.tag_lexicon)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.all_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.all_tags_list, 1, wx.EXPAND)
		self.all_tags_panel.SetSizer(sizer)
		
		# ソートメニューイベントをバインド
		self.Bind(wx.EVT_BUTTON, self.on_sort_menu_button_click, id=ID_SORT_MENU)
	
	def on_sort_menu_button_click(self, event: wx.CommandEvent):
		"""ソートメニューボタンがクリックされたときにメニューを表示します。"""
		# メニューを作成
		menu = wx.Menu()
		
		# メニュー項目を追加
		menu.Append(ID_SORT_BY_TAG_NAME, __("sort:by_tag_name"), kind=wx.ITEM_RADIO)
		menu.Append(ID_SORT_BY_COUNT, __("sort:by_count"), kind=wx.ITEM_RADIO)
		menu.Append(ID_SORT_BY_CATEGORY_TEXT, __("sort:by_category_text"), kind=wx.ITEM_RADIO)
		menu.Append(ID_SORT_BY_CATEGORY_ORDER, __("sort:by_category_order"), kind=wx.ITEM_RADIO)
		
		menu.AppendSeparator()
		menu.Append(ID_SORT_DESCENDING, __("sort:descending"), kind=wx.ITEM_CHECK)
		
		# 現在のソート順をチェックマークで表示
		current_sort_order = self.all_tags_list.sort_order
		current_sort_descending = self.all_tags_list.sort_descending
		
		sort_order_to_id = {
			TagSortOrder.TagName: ID_SORT_BY_TAG_NAME,
			TagSortOrder.Count: ID_SORT_BY_COUNT,
			TagSortOrder.CategoryOrder: ID_SORT_BY_CATEGORY_ORDER,
			TagSortOrder.CategoryText: ID_SORT_BY_CATEGORY_TEXT,
		}
		
		if current_sort_order in sort_order_to_id:
			menu.Check(sort_order_to_id[current_sort_order], True)
		
		menu.Check(ID_SORT_DESCENDING, current_sort_descending)
		
		# イベントハンドラをバインド
		self.Bind(wx.EVT_MENU, self.on_sort_menu_item_selected, id=ID_SORT_BY_TAG_NAME)
		self.Bind(wx.EVT_MENU, self.on_sort_menu_item_selected, id=ID_SORT_BY_COUNT)
		self.Bind(wx.EVT_MENU, self.on_sort_menu_item_selected, id=ID_SORT_BY_CATEGORY_ORDER)
		self.Bind(wx.EVT_MENU, self.on_sort_menu_item_selected, id=ID_SORT_BY_CATEGORY_TEXT)
		self.Bind(wx.EVT_MENU, self.on_sort_descending_selected, id=ID_SORT_DESCENDING)
		
		# ボタンの位置にメニューを表示
		btn_pos = self.sort_button.GetScreenPosition()
		btn_size = self.sort_button.GetSize()
		menu_pos = self.ScreenToClient(btn_pos)
		menu_pos.y += btn_size.height
		
		self.PopupMenu(menu, menu_pos)
		menu.Destroy()  # メニューを破棄
	
	def on_sort_menu_item_selected(self, event: wx.CommandEvent):
		"""ソートメニューの項目が選択されたときにソート順を適用します。"""
		menu_id = event.GetId()
		
		sort_map = {
			ID_SORT_BY_TAG_NAME: TagSortOrder.TagName,
			ID_SORT_BY_COUNT: TagSortOrder.Count,
			ID_SORT_BY_CATEGORY_ORDER: TagSortOrder.CategoryOrder,
			ID_SORT_BY_CATEGORY_TEXT: TagSortOrder.CategoryText,
		}
		
		if menu_id in sort_map:
			new_sort_order = sort_map[menu_id]
			# 昇順/降順の状態は現在の設定を維持
			self.all_tags_list.set_sort_order(new_sort_order, self.all_tags_list.sort_descending)
	
	def on_sort_descending_selected(self, event: wx.CommandEvent):
		"""降順チェックボックスが選択されたときにソート順を適用します。"""
		is_checked = event.IsChecked()
		self.all_tags_list.set_sort_order(self.all_tags_list.sort_order, is_checked)
	
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
		self.image_list.set_filter(matched_indices)
		
		# 選択状態の更新
		if matched_indices:
			# 現在選択中の画像がマッチしたか確認
			current_item_idx = self.current_item_index
			if current_item_idx in matched_indices:
				# マッチした場合はその画像を選択状態にする
				self.image_list.select_item(current_item_idx)
			else:
				# マッチしなかった場合は、直前の画像を選択する
				idx = bisect.bisect_left(matched_indices, current_item_idx)
				if idx > 0:
					new_selection = matched_indices[idx - 1]
				else:
					new_selection = matched_indices[0]
				
				self.image_list.select_item(new_selection)
				self.current_item_index = new_selection
				self._update_views_for_item_selection(new_selection)
		else:
			# マッチする画像がない場合
			self.current_item_index = wx.NOT_FOUND
			self._update_views_for_item_selection(wx.NOT_FOUND)
		self._update_statusbar()
	
	def on_filter_cancel(self, event: wx.CommandEvent):
		"""検索コントロールでキャンセルボタンが押されたときの処理。"""
		self.filter_ctrl.SetValue("")
		self.image_list.set_filter(None)
		
		# 選択状態の復元
		current_item_index = self.current_item_index if self.current_item_index != wx.NOT_FOUND else 0
		if current_item_index < self.image_list.GetItemCount():
			self.image_list.select_item(current_item_index)
			self._update_views_for_item_selection(current_item_index)
		self._update_statusbar()
	
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
		
		# タグ情報の保存
		self.tag_lexicon.save(self.tag_lexicon_path)
		
		self.save_ui_settings()
		self.config.save()
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
		
		default_path = self.config.get('ui.last_dataset_dir', "")
		with wx.DirDialog(self, __("title:choose_a_directory"), defaultPath=default_path, style=wx.DD_DEFAULT_STYLE) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.config.set('ui.last_dataset_dir', path)
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
			self._update_title()
	
	def on_import_tags(self, event: wx.CommandEvent):
		"""タグ情報をインポートします。"""
		wildcard = '|'.join([
			"All supported files (*.json;*.yaml;*.yml)", "*.json;*.yaml;*.yml",
			"JSON files (*.json)", "*.json",
			"YAML files (*.yaml;*.yml)", "*.yaml;*.yml",
		])
		default_dir = self.config.get('ui.last_import_tags_dir', "")
		with wx.FileDialog(self, __("title:import_tags"), defaultDir=default_dir, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.config.set('ui.last_import_tags_dir', os.path.dirname(path))
				try:
					self.tag_lexicon.load(path)
					self.all_tags_list.set_tag_lexicon(self.tag_lexicon)
				except Exception:
					error_msg = traceback.format_exc()
					wx.MessageBox(
						__("message:failed_to_import_tags").format(e=error_msg),
						__("title:error"),
						wx.OK | wx.ICON_ERROR
					)
	
	def on_export_tags(self, event: wx.CommandEvent):
		"""タグ情報をエクスポートします。"""
		wildcard = '|'.join([
			"JSON files (*.json)", "*.json",
			"YAML files (*.yaml)", "*.yaml",
		])
		default_dir = self.config.get('ui.last_export_tags_dir', "")
		with wx.FileDialog(self, __("title:export_tags"), defaultDir=default_dir, wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.config.set('ui.last_export_tags_dir', os.path.dirname(path))
				try:
					self.tag_lexicon.save(path)
				except Exception:
					error_msg = traceback.format_exc()
					wx.MessageBox(
						__("message:failed_to_export_tags").format(e=error_msg),
						__("title:error"),
						wx.OK | wx.ICON_ERROR
					)
		
	def on_image_list_select(self, event: wx.CommandEvent):
		"""
		サムネイルリストの選択が変更されたときの処理。
		常に単一の選択を維持します。
		"""
		view_index = self.image_list.GetSelection()
		
		if view_index == wx.NOT_FOUND:
			# 選択が解除された場合、最後の選択状態に戻す
			# ただし、フィルタリングによって選択項目が消えた場合は戻さない
			if self.current_item_index != wx.NOT_FOUND:
				# 現在のフィルタで表示されているか確認
				self.image_list.select_item(self.current_item_index)
			return
		
		dataset_index = self.image_list.get_dataset_index(view_index)
		
		# 同じアイテムが再度選択された場合は何もしない
		if dataset_index == self.current_item_index:
			return
		
		self.current_item_index = dataset_index
		self._update_views_for_item_selection(dataset_index)
	
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
		if self.remote_controller:
			self.remote_controller.undo()
	
	def on_redo(self, event: wx.CommandEvent):
		"""元に戻した操作をやり直します。"""
		if self.remote_controller:
			self.remote_controller.redo()
	
	def on_update_ui_undo(self, event: wx.UpdateUIEvent):
		"""アンドゥメニュー項目のUIを更新します。"""
		can_undo = self.remote_controller.can_undo() if self.remote_controller else False
		event.Enable(can_undo)
	
	def on_update_ui_redo(self, event: wx.UpdateUIEvent):
		"""リドゥメニュー項目のUIを更新します。"""
		can_redo = self.remote_controller.can_redo() if self.remote_controller else False
		event.Enable(can_redo)
	
	def on_copy(self, event: wx.CommandEvent):
		"""
		フォーカスがあるコントロールに応じてコピー動作を実行します。
		- image_tags_gridにフォーカス時: ImageTagsGridにwx.ID_COPYイベントを転送。
		- all_tags_listにフォーカス時: 選択中のタグをコピー。
		- その他のテキストコントロール: デフォルトのコピー動作を実行。
		"""
		focus_win = wx.Window.FindFocus()
		
		# ImageTagsGridまたはその内部のウィンドウにフォーカスがあるかチェック
		is_grid_focus = False
		win = focus_win
		while win:
			if win == self.image_tags_grid:
				is_grid_focus = True
				break
			win = win.GetParent()
		
		if is_grid_focus:
			self.image_tags_grid.copy_selection()
		elif focus_win == self.all_tags_list:
			self.all_tags_list.copy_selected_tags_to_clipboard()
		else:
			# 他のテキストコントロールなどの標準的なコピー動作
			if hasattr(focus_win, "CanCopy") and focus_win.CanCopy():
				focus_win.Copy()
	
	def on_paste(self, event: wx.CommandEvent):
		"""
		フォーカスがあるコントロールに応じて貼り付け動作を実行します。
		"""
		focus_win = wx.Window.FindFocus()
		
		# ImageTagsGridまたはその内部のウィンドウにフォーカスがあるかチェック
		is_grid_focus = False
		win = focus_win
		while win:
			if win == self.image_tags_grid:
				is_grid_focus = True
				break
			win = win.GetParent()
		
		if is_grid_focus:
			self.image_tags_grid.paste_from_clipboard()
		else:
			# 他のテキストコントロールなどの標準的な貼り付け動作
			if hasattr(focus_win, "CanPaste") and focus_win.CanPaste():
				focus_win.Paste()
	
	def on_select_all(self, event: wx.CommandEvent):
		"""
		フォーカスがあるコントロールに応じて全選択を実行します。
		"""
		focus_win = wx.Window.FindFocus()
		
		# ImageTagsGridまたはその内部のウィンドウにフォーカスがあるかチェック
		is_grid_focus = False
		win = focus_win
		while win:
			if win == self.image_tags_grid:
				is_grid_focus = True
				break
			win = win.GetParent()
		
		if is_grid_focus:
			self.image_tags_grid.SelectAll()
		elif focus_win == self.all_tags_list:
			# AllTagsListにwx.ID_SELECTALLイベントを転送
			self.all_tags_list.select_all()
		else:
			# 他のテキストコントロールなどの標準的な全選択動作
			if hasattr(focus_win, "SelectAll"):
				focus_win.SelectAll()
	
	def on_insert_blank_tag(self, event: wx.CommandEvent):
		"""ImageTagsGridに空のタグを挿入します。"""
		self.image_tags_grid.insert_blank_tag()
	
	def on_delete_tag(self, event: wx.CommandEvent):
		"""ImageTagsGridで選択されているタグを削除します。"""
		self.image_tags_grid.delete_selected_tags()
	
	def on_move_tag_up(self, event: wx.CommandEvent):
		"""ImageTagsGridでカーソル行のタグを上に移動します。"""
		self.image_tags_grid.move_tag_up()
	
	def on_move_tag_down(self, event: wx.CommandEvent):
		"""ImageTagsGridでカーソル行のタグを下に移動します。"""
		self.image_tags_grid.move_tag_down()
	
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
		count = self.image_list.GetItemCount()
		if count == 0:
			return
		
		current = self.image_list.GetSelection()
		next_idx = 0
		if current != wx.NOT_FOUND:
			next_idx = current + 1
		
		if next_idx < count:
			self.image_list.SetSelection(next_idx)
			self.on_image_list_select(None)
			
			if not self.image_list.IsVisible(next_idx):
				self.image_list.ScrollToLine(next_idx)
	
	def on_prev_image(self, event: wx.CommandEvent):
		"""前の画像を選択します。"""
		count = self.image_list.GetItemCount()
		if count == 0:
			return
		
		current = self.image_list.GetSelection()
		if current == wx.NOT_FOUND:
			return
		
		prev_idx = current - 1
		
		if prev_idx >= 0:
			self.image_list.SetSelection(prev_idx)
			self.on_image_list_select(None)
			
			if not self.image_list.IsVisible(prev_idx):
				self.image_list.ScrollToLine(prev_idx)
	
	def on_select_in_all_tags(self, event):
		"""ImageTagsGridからのイベントを処理し、AllTagsListでタグを選択します。"""
		self.all_tags_list.select_tags(event.tag_texts)
	
	def on_add_tags_to_filter(self, event):
		self.add_tags_to_filter(event.tags)
	
	def on_append_tags_to_current_items(self, event):
		self.append_tags_to_current_items(event.tags)
	
	def on_remove_tags_from_current_items(self, event):
		self.remove_tags_from_current_items(event.tags)
	
	def on_append_tags_to_filtered_items(self, event):
		self.append_tags_to_filtered_items(event.tags)
	
	def on_remove_tags_from_filtered_items(self, event):
		self.remove_tags_from_filtered_items(event.tags)
	
	def on_append_tags_to_all_items(self, event):
		self.append_tags_to_all_items(event.tags)
	
	def on_remove_tags_from_all_items(self, event):
		self.remove_tags_from_all_items(event.tags)
	
	def on_replace_tag_in_all_items(self, event):
		self.replace_tag_in_all_items_with_dialog(event.old_tag)
	
	def append_tags_to_current_items(self, tags: list[str]):
		"""選択中のアイテムにタグを追加します。"""
		if not self.remote_controller or self.current_item_index == wx.NOT_FOUND:
			return
		tags_obj = tuple(Tag(t) for t in tags)
		self.remote_controller.append_tags(self.current_item_index, tags_obj)
	
	def remove_tags_from_current_items(self, tags: list[str]):
		"""選択中のアイテムからタグを削除します。"""
		if not self.remote_controller or self.current_item_index == wx.NOT_FOUND:
			return
		self.remote_controller.batch_remove_tags([self.current_item_index], tags)
	
	def append_tags_to_filtered_items(self, tags: list[str]):
		"""フィルター済みアイテムにタグを追加します。"""
		if not self.remote_controller:
			return
		filtered_indices = self.image_list.filtered_indices
		if not filtered_indices:
			return
		
		tags_obj = tuple(Tag(t) for t in tags)
		self.remote_controller.batch_append_tags(filtered_indices, tags_obj)
	
	def remove_tags_from_filtered_items(self, tags: list[str]):
		"""フィルター済みアイテムからタグを削除します。"""
		if not self.remote_controller:
			return
		filtered_indices = self.image_list.filtered_indices
		if not filtered_indices:
			return
		
		self.remote_controller.batch_remove_tags(filtered_indices, tags)
	
	def append_tags_to_all_items(self, tags: list[str]):
		"""すべてのアイテムにタグを追加します。"""
		if not self.remote_controller or not self.dataset:
			return
		
		all_indices = range(len(self.dataset))
		tags_obj = tuple(Tag(t) for t in tags)
		self.remote_controller.batch_append_tags(all_indices, tags_obj)
	
	def remove_tags_from_all_items(self, tags: list[str]):
		"""すべてのアイテムからタグを削除します。"""
		if not self.remote_controller or not self.dataset:
			return
		
		all_indices = range(len(self.dataset))
		self.remote_controller.batch_remove_tags(all_indices, tags)
	
	def replace_tag_in_all_items_with_dialog(self, old_tag_text: str):
		"""すべてのアイテムでタグを置換します。"""
		if not self.remote_controller or not self.dataset:
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
			self.remote_controller.batch_replace_tag(all_indices, old_tag_text, Tag(new_tag_text), keep_weight=True)
	
	def add_tags_to_filter(self, tags: list[str]):
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
	
	def _on_dataset_diff_applied(self, sender: str, diff: 'DatasetDiff'):
		"""
		データセットの変更が適用されたときに呼び出されます。
		
		Args:
			sender: 変更の送信元ID (未使用)。
			diff: 適用された変更内容 (未使用)。
		"""
		self._update_title()
	
	def _update_title(self):
		"""ウィンドウタイトルを更新して、ダーティ状態を示します。"""
		title = self.base_title
		if self.dataset.initialized and self.dataset.is_dirty:
			title += " *"
		
		if self.GetTitle() != title:
			wx.CallAfter(self.SetTitle, title)
	
	def _update_statusbar(self):
		"""ステータスバーのテキストを更新します。"""
		if not self.dataset.initialized:
			self.SetStatusText("", 0)
			return
		
		total_items = len(self.dataset)
		
		if self.image_list.filtered_indices is not None:
			filtered_items = self.image_list.GetItemCount()
			status_text = __("statusbar:filtered_items").format(
				filtered_count=filtered_items,
				total_count=total_items
			)
		else:
			status_text = __("statusbar:total_items").format(
				total_count=total_items
			)
		
		status_text = ' ' + status_text
		self.statusbar.SetStatusText(status_text, 0)
		
		# 幅を計算
		w, h = self.statusbar.GetTextExtent(status_text)
		self.statusbar.SetStatusWidths([w + STATUSBAR_PADDING, -1])
	
	def on_menu_highlight(self, event: wx.MenuEvent):
		"""
		メニュー項目がハイライトされたときにステータスバーの1番目のフィールドにヘルプ文字列を表示します。
		"""
		menu_id = event.GetMenuId()
		item = self.GetMenuBar().FindItemById(menu_id)
		
		if item:
			# メニュー項目のヘルプテキストを取得
			help_text = item.GetHelp()
			
			# 2番目のフィールド（インデックス1）に表示
			self.statusbar.SetStatusText(help_text, 1)
		else:
			# ハイライトされたメニュー項目がない場合、ステータスバーの1番目のフィールドをクリア
			self.statusbar.SetStatusText("", 1)
	
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
		
		# AllTagsListのソート設定を保存
		self.config.set('ui.all_tags_list.sort_order', self.all_tags_list.sort_order.name)
		self.config.set('ui.all_tags_list.sort_descending', self.all_tags_list.sort_descending)
		
		# パネルの表示状態を保存
		self.config.set('ui.show_all_tags_panel', self.toggle_all_tags_menu.IsChecked())
	
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
			
			# AllTagsListのソート設定を復元
			sort_order_name = self.config.get('ui.all_tags_list.sort_order', TagSortOrder.TagName.name)
			try:
				sort_order = TagSortOrder[sort_order_name]
			except KeyError:
				sort_order = TagSortOrder.TagName
			
			sort_descending = self.config.get('ui.all_tags_list.sort_descending', False)
			self.all_tags_list.set_sort_order(sort_order, sort_descending)
			
			# パネルの表示状態を復元
			show_all_tags_panel = self.config.get('ui.show_all_tags_panel', True)
			self.toggle_all_tags_menu.Check(show_all_tags_panel)
			self._update_layout_visibility()

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
		if self.dataset.initialized:
			self.dataset.remove_diff_applied_listener(self._on_dataset_diff_applied)
		
		self.dataset.load(
			folder_path,
			self.image_exts,
			caption_ext=self.caption_ext,
			caption_format_config=self.caption_format_config,
		)
		self.dataset.add_diff_applied_listener(self._on_dataset_diff_applied)
		self.remote_controller = self.dataset.get_controller()
		dataset = self.dataset
		
		self.image_list.set_dataset(dataset)
		self.image_tags_grid.set_dataset(dataset)
		self.all_tags_list.set_dataset(dataset)
		self.all_tags_list.set_tag_lexicon(self.tag_lexicon)
		
		if dataset.initialized is not None and len(dataset) > 0:
			self.image_list.SetSelection(0)
			# SetSelectionはイベントを発生させないため、手動で更新処理を呼び出す
			self.current_item_index = 0
			self._update_views_for_item_selection(0)
		else:
			# データセットが空の場合のビュー更新
			self.current_item_index = wx.NOT_FOUND
			self._update_views_for_item_selection(wx.NOT_FOUND)
		self._update_statusbar()
		self._update_title()
	
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
