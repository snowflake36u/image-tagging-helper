import os
import glob
import wx
import wx.grid
import ctypes

from src.image_tagging_helper.core.caption import Caption, CaptionFormatConfig
from src.image_tagging_helper.core.dataset import Dataset, DatasetItem
from src.image_tagging_helper.wx.image_list import ImageVListBox
from src.image_tagging_helper.i18n import setup_translation, __

# アプリケーションのドメイン名を設定
APP_NAME = "image_tagging_helper"
setup_translation(APP_NAME)

class ImageTaggingHelperFrame(wx.Frame):
	"""
	メインウィンドウのフレーム。
	UIコンポーネントの配置とイベント処理、データセットの管理を行います。
	"""
	
	def __init__(self, parent: wx.Window | None, title: str):
		"""
		フレームを初期化します。
		
		Args:
			parent: 親ウィンドウ。
			title: ウィンドウのタイトル。
		"""
		super().__init__(parent, title=title, size=(1200, 800))
		
		# === データメンバーの初期化 ===
		self.caption_parse_config = CaptionFormatConfig(delimiter=', ')
		self.caption_format_config = CaptionFormatConfig()
		self.caption_exts = '.caption'
		self.dataset: Dataset | None = None
		self.last_thumbnail_selection: int = wx.NOT_FOUND
		
		# === UIの初期化 ===
		self._init_ui()
	
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
		
		toggle_tag_palette_item = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_tag_palette"), __("tooltip:toggle_tag_palette"))
		toggle_dataset_tags_item = self._append_menu_item(menu, wx.ID_ANY, __("action:toggle_dataset_tags"), __("tooltip:toggle_dataset_tags"))
		
		menu.AppendSeparator()
		
		fullscreen_item = self._append_menu_item(menu, wx.ID_ANY, __("action:fullscreen"), __("tooltip:fullscreen"), 'F11')
	
	def _init_configure_menu(self, menubar):
		menu = wx.Menu()
		menubar.Append(menu, __("ui_group:configure"))
		
		preferences_item = self._append_menu_item(menu, wx.ID_PREFERENCES, __("action:preferences"), __("tooltip:preferences"))
	
	@staticmethod
	def _append_menu_item(menu: wx.Menu, item_id: int, label: str, help_str: str, accel: str = None) -> wx.MenuItem:
		"""
		メニュー項目を追加するためのヘルパーメソッド。
		ラベルとアクセラレータを結合してメニュー項目を作成します。
		"""
		text = f"{label}\t{accel}" if accel else label
		return menu.Append(item_id, text, help_str)
	
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
		self.splitter_1 = wx.SplitterWindow(parent, style=wx.SP_LIVE_UPDATE)
		self.splitter_2 = wx.SplitterWindow(self.splitter_1, style=wx.SP_LIVE_UPDATE)
		self.splitter_3 = wx.SplitterWindow(self.splitter_2, style=wx.SP_LIVE_UPDATE)
		
		splitters = [self.splitter_1, self.splitter_2, self.splitter_3]
		for splitter in splitters:
			splitter.SetMinimumPaneSize(100)
			splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
		
		# 各ペインの作成
		self._create_thumbnail_panel(self.splitter_1)
		self._create_image_tags_panel(self.splitter_2)
		self._create_tag_palette_panel(self.splitter_3)
		self._create_dataset_tags_panel(self.splitter_3)
		
		# スプリッターの分割設定
		# 初期サイズ(1200)に基づく比率 1:1:2:1 -> 240:240:480:240
		self.splitter_3.SplitVertically(self.tag_palette_panel, self.dataset_tags_panel, 480)
		self.splitter_2.SplitVertically(self.image_tags_panel, self.splitter_3, 240)
		self.splitter_1.SplitVertically(self.thumbnail_panel, self.splitter_2, 240)
		
		# ウィンドウリサイズ時の挙動を設定
		self.splitter_1.SetSashGravity(1.0 / 3.0)
		self.splitter_2.SetSashGravity(0.5)
	
	def _create_thumbnail_panel(self, parent: wx.Window):
		"""画像のサムネイルリストパネルを作成します。"""
		self.thumbnail_panel = wx.Panel(parent)
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
		self.image_tags_toolbar = wx.ToolBar(self.image_tags_panel, style=wx.TB_HORIZONTAL | wx.TB_FLAT | wx.TB_NODIVIDER)
		self.image_tags_toolbar.AddControl(wx.StaticText(self.image_tags_toolbar, label=__("label:image_tags")))
		self.image_tags_toolbar.AddSeparator()
		self.image_tags_toolbar.Realize()
		
		self.image_tags_grid = wx.grid.Grid(self.image_tags_panel)
		self.image_tags_grid.CreateGrid(0, 2)
		self.image_tags_grid.SetColLabelValue(0, __("label:tag"))
		self.image_tags_grid.SetColLabelValue(1, __("label:weight"))
		self.image_tags_grid.SetColSize(0, 150)
		self.image_tags_grid.SetColSize(1, 50)
		self.image_tags_grid.SetRowLabelSize(0)
		self.image_tags_grid.EnableDragRowSize(False)
		self.image_tags_grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_grid_select_cell)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.image_tags_toolbar, 0, wx.EXPAND)
		sizer.Add(self.image_tags_grid, 1, wx.EXPAND)
		self.image_tags_panel.SetSizer(sizer)
	
	def _create_tag_palette_panel(self, parent: wx.Window):
		"""タグパレットパネルを作成します。"""
		self.tag_palette_panel = wx.Panel(parent)
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
	
	def on_splitter_dclick(self, event: wx.SplitterEvent):
		"""スプリッターのダブルクリックによる折りたたみを防止します。"""
		event.Veto()
	
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
		selection = self.thumbnail_list.GetSelection()
		
		if selection == wx.NOT_FOUND:
			# 選択が解除された場合、最後の選択状態に戻す
			if self.last_thumbnail_selection != wx.NOT_FOUND:
				self.thumbnail_list.SetSelection(self.last_thumbnail_selection)
			return
		
		# 同じアイテムが再度選択された場合は何もしない
		if selection == self.last_thumbnail_selection:
			return
		
		self.last_thumbnail_selection = selection
		self._update_views_for_selection(selection)
	
	def on_grid_select_cell(self, event: wx.grid.GridEvent):
		"""
		グリッドのセルが選択されたときの処理。
		複数選択を無効にし、常に単一の行のみが選択されるようにします。
		"""
		row = event.GetRow()
		self.image_tags_grid.ClearSelection()
		self.image_tags_grid.SelectRow(row)
		event.Skip()
	
	# === UI更新メソッド ===
	
	def _update_views_for_selection(self, selection: int):
		"""指定された選択に基づいて関連するビューを更新します。"""
		self._update_image_path_view(selection)
		self._update_image_tags_view(selection)
	
	def _update_image_path_view(self, selection: int):
		"""選択された画像のパスを表示します。"""
		if not self.dataset or selection == wx.NOT_FOUND:
			self.path_text.SetValue('')
			return
		
		item = self.dataset[selection]
		self.path_text.SetValue(item.path)
	
	def _update_image_tags_view(self, selection: int):
		"""選択された画像のタグをグリッドに表示します。"""
		if self.image_tags_grid.GetNumberRows() > 0:
			self.image_tags_grid.DeleteRows(0, self.image_tags_grid.GetNumberRows())
		
		if not self.dataset or selection == wx.NOT_FOUND:
			return
		
		item = self.dataset[selection]
		caption = item.caption
		
		if not caption.tags:
			return
		
		self.image_tags_grid.AppendRows(len(caption.tags))
		
		for i, tag in enumerate(caption.tags):
			self.image_tags_grid.SetCellValue(i, 0, tag.text)
			weight_str = f'{tag.weight:.2f}' if tag.weight is not None else ''
			self.image_tags_grid.SetCellValue(i, 1, weight_str)
	
	# === データ処理メソッド ===
	
	def load_dataset(self, folder_path: str):
		"""
		指定されたフォルダからデータセットを構築します。
		
		Args:
			folder_path: 画像とキャプションファイルが含まれるフォルダのパス。
		"""
		extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
		image_files = []
		for ext in extensions:
			image_files.extend(glob.glob(os.path.join(folder_path, ext)))
		
		image_files = sorted(list(set(image_files)))
		
		dataset_items = [self.create_item(path) for path in image_files]
		
		self.dataset = Dataset(items=dataset_items)
		self.thumbnail_list.set_dataset(self.dataset)
		
		if self.dataset and len(self.dataset) > 0:
			self.thumbnail_list.SetSelection(0)
			# SetSelectionはイベントを発生させないため、手動で更新処理を呼び出す
			self.last_thumbnail_selection = 0
			self._update_views_for_selection(0)
	
	def create_item(self, image_path: str) -> DatasetItem:
		"""
		画像パスからキャプションを読み込み、DatasetItemを作成します。
		
		Args:
			image_path: 画像ファイルのパス。
		
		Returns:
			作成されたDatasetItemインスタンス。
		"""
		caption_path = os.path.splitext(image_path)[0] + self.caption_exts
		caption = Caption()
		if os.path.exists(caption_path):
			with open(caption_path, 'r', encoding='utf-8') as f:
				caption_text = f.read()
				caption = Caption.parse(caption_text, config=self.caption_format_config)
		
		return DatasetItem(path=image_path, caption=caption)
	
	@staticmethod
	def launch():
		"""アプリケーションを起動します。"""
		app = wx.App()
		frame = ImageTaggingHelperFrame(None, __("title:app_main_window"))
		frame.Show()
		app.MainLoop()

def main():
	"""アプリケーションのエントリポイント。"""
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
	ImageTaggingHelperFrame.launch()

if __name__ == "__main__":
	main()
