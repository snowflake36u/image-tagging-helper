import os
import glob
import wx
from win32ctypes.core import ctypes

from src.image_tagging_helper.core.caption import Caption
from src.image_tagging_helper.core.dataset import Dataset, DatasetItem
from src.image_tagging_helper.wx.image_list import ImageVListBox

class ImageTaggingHelperFrame(wx.Frame):
	"""メインウィンドウのフレーム"""
	
	def __init__(self, parent, title):
		super().__init__(parent, title=title, size=(1200, 800))
		
		self.dataset: Dataset | None = None
		
		# メニューバーの設定
		self._init_menubar()
		
		# メインパネル
		main_panel = wx.Panel(self)
		
		# スプリッターウィンドウの作成（入れ子構造）
		# splitter_1
		# |- thumbnail_list
		# |- splitter_2
		#   |- image_tags_list
		#   |- splitter_3
		#     |- tag_palette_panel
		#     |- dataset_tags_list
		self.splitter_1 = wx.SplitterWindow(main_panel, style=wx.SP_LIVE_UPDATE)
		self.splitter_2 = wx.SplitterWindow(self.splitter_1, style=wx.SP_LIVE_UPDATE)
		self.splitter_3 = wx.SplitterWindow(self.splitter_2, style=wx.SP_LIVE_UPDATE)
		
		# ダブルクリックで折りたたまないようにイベントをバインド
		self.splitter_1.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
		self.splitter_2.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
		self.splitter_3.Bind(wx.EVT_SPLITTER_DCLICK, self.on_splitter_dclick)
		
		# 1番目のパネル: 画像のサムネイルリスト
		self.thumbnail_list = ImageVListBox(self.splitter_1)
		
		# 2番目のパネル: 画像のタグ一覧
		self.image_tags_list = wx.ListCtrl(self.splitter_2, style=wx.LC_REPORT)
		self.image_tags_list.InsertColumn(0, 'Tag', width=150)
		
		# 3番目のパネル: 空のパネル（将来的に実装）
		self.tag_palette_panel = wx.Panel(self.splitter_3)
		self.tag_palette_panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE))
		
		# 4番目のパネル: データセット全体のタグ一覧
		self.dataset_tags_list = wx.ListCtrl(self.splitter_3, style=wx.LC_REPORT)
		self.dataset_tags_list.InsertColumn(0, 'Tag', width=150)
		self.dataset_tags_list.InsertColumn(1, 'Count', width=50)
		
		# スプリッターの分割設定
		# 初期サイズ(1200)に基づく比率 1:1:2:1 -> 240:240:480:240
		self.splitter_3.SplitVertically(self.tag_palette_panel, self.dataset_tags_list, 480)
		self.splitter_2.SplitVertically(self.image_tags_list, self.splitter_3, 240)
		self.splitter_1.SplitVertically(self.thumbnail_list, self.splitter_2, 240)
		
		# ウィンドウリサイズ時の挙動を設定
		# tag_palette_panel以外の3つのパネルが均等に伸縮するように調整
		self.splitter_1.SetSashGravity(1.0 / 3.0)
		self.splitter_2.SetSashGravity(0.5)
		# splitter_3はデフォルト(0.0)のままで、左パネル(tag_palette_panel)のサイズを固定
		
		# メインパネルのレイアウト
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.splitter_1, 1, wx.EXPAND | wx.ALL, 5)
		main_panel.SetSizer(sizer)
		self.Centre()
	
	def _init_menubar(self):
		"""メニューバーの初期化"""
		menubar = wx.MenuBar()
		
		# Fileメニュー
		file_menu = wx.Menu()
		open_folder_item = file_menu.Append(wx.ID_OPEN, 'Open Folder...\tCtrl+O', 'Open a folder containing images')
		file_menu.AppendSeparator()
		exit_item = file_menu.Append(wx.ID_EXIT, 'Exit', 'Exit the application')
		
		menubar.Append(file_menu, '&File')
		self.SetMenuBar(menubar)
		
		# イベントバインド
		self.Bind(wx.EVT_MENU, self.on_open_folder, open_folder_item)
		self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
	
	def on_splitter_dclick(self, event):
		"""スプリッターのダブルクリックによる折りたたみを防止"""
		event.Veto()
	
	def on_exit(self, event):
		self.Close()
	
	def on_open_folder(self, event):
		"""フォルダ選択ダイアログを表示し、データセットを読み込む"""
		with wx.DirDialog(self, "Choose a directory", style=wx.DD_DEFAULT_STYLE) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.load_dataset(path)
	
	def load_dataset(self, folder_path: str):
		"""指定されたフォルダからデータセットを構築する"""
		# 画像ファイルの検索
		extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
		image_files = []
		for ext in extensions:
			# Windowsではglobはデフォルトで大文字小文字を区別しない
			image_files.extend(glob.glob(os.path.join(folder_path, ext)))
		
		# 重複除去とソート
		image_files = sorted(list(set(image_files)))
		
		dataset_items = []
		for image_path in image_files:
			caption_path = os.path.splitext(image_path)[0] + '.txt'
			caption = Caption.from_file(caption_path) if os.path.exists(caption_path) else Caption()
			dataset_items.append(DatasetItem(path=image_path, caption=caption))
		
		self.dataset = Dataset(items=dataset_items)
		self.thumbnail_list.set_dataset(self.dataset)
	
	@staticmethod
	def launch():
		app = wx.App()
		frame = ImageTaggingHelperFrame(None, "Image Tagging Helper")
		frame.Show()
		app.MainLoop()

def main():
	# 高DPI対応を有効にする
	try:
		# Windows 8.1以降: Per-Monitor DPI Aware V2
		# これにより、モニターごとのDPI設定に対応できる
		ctypes.windll.shcore.SetProcessDpiAwareness(2)
	except (AttributeError, OSError):
		try:
			# Windows Vista以降: System DPI Aware
			# アプリケーション全体で単一のDPI設定を使用する
			ctypes.windll.user32.SetProcessDPIAware()
		except (AttributeError, OSError):
			# DPI設定に対応していないOSの場合は何もしない
			pass
	ImageTaggingHelperFrame.launch()

if __name__ == "__main__":
	main()
