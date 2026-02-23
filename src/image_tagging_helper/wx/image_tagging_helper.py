import os
import glob
import wx

class MainFrame(wx.Frame):
	"""メインウィンドウのフレーム"""
	
	def __init__(self, parent, title):
		super().__init__(parent, title=title, size=(1200, 800))
		
		self.image_size = (256, 256)  # サムネイルサイズ
		
		# メニューバーの設定
		self._init_menubar()
		
		# メインパネル
		main_panel = wx.Panel(self)
		
		# 水平方向に並べるサイザー
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		
		# 1番目のパネル: 画像のサムネイルリスト
		self.thumbnail_list = wx.ListCtrl(main_panel, style=wx.LC_ICON | wx.LC_AUTOARRANGE)
		# ImageListの初期化
		self.image_list = wx.ImageList(self.image_size[0], self.image_size[1])
		self.thumbnail_list.AssignImageList(self.image_list, wx.IMAGE_LIST_NORMAL)
		
		hbox.Add(self.thumbnail_list, 1, wx.EXPAND | wx.ALL, 5)
		
		# 2番目のパネル: 画像のタグ一覧
		self.image_tags_list = wx.ListCtrl(main_panel, style=wx.LC_REPORT)
		self.image_tags_list.InsertColumn(0, 'Tag', width=150)
		hbox.Add(self.image_tags_list, 1, wx.EXPAND | wx.ALL, 5)
		
		# 3番目のパネル: 空のパネル（将来的に実装）
		self.center_panel = wx.Panel(main_panel)
		self.center_panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_APPWORKSPACE))
		hbox.Add(self.center_panel, 2, wx.EXPAND | wx.ALL, 5)
		
		# 4番目のパネル: データセット全体のタグ一覧
		self.dataset_tags_list = wx.ListCtrl(main_panel, style=wx.LC_REPORT)
		self.dataset_tags_list.InsertColumn(0, 'Tag', width=150)
		self.dataset_tags_list.InsertColumn(1, 'Count', width=50)
		hbox.Add(self.dataset_tags_list, 1, wx.EXPAND | wx.ALL, 5)
		
		main_panel.SetSizer(hbox)
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
	
	def on_exit(self, event):
		self.Close()
	
	def on_open_folder(self, event):
		"""フォルダ選択ダイアログを表示し、画像を読み込む"""
		with wx.DirDialog(self, "Choose a directory", style=wx.DD_DEFAULT_STYLE) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				self.load_images(path)
	
	def load_images(self, folder_path):
		"""指定されたフォルダから画像を読み込み、サムネイルリストを更新する"""
		self.thumbnail_list.DeleteAllItems()
		self.image_list.RemoveAll()
		
		# 画像ファイルの検索 (簡易的に拡張子でフィルタ)
		extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
		image_files = []
		for ext in extensions:
			# 大文字小文字を区別しない検索が望ましいが、ここではglobで簡易実装
			# Windowsでは通常大文字小文字を区別しない
			image_files.extend(glob.glob(os.path.join(folder_path, ext)))
			image_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))
		
		# 重複除去とソート
		image_files = sorted(list(set(image_files)))
		
		for i, file_path in enumerate(image_files):
			try:
				# 画像読み込み
				img = wx.Image(file_path, wx.BITMAP_TYPE_ANY)
				
				# サムネイル用にリサイズ（アスペクト比維持）
				w, h = img.GetWidth(), img.GetHeight()
				aspect = w / h
				
				target_w, target_h = self.image_size
				
				if aspect > 1:
					new_w = target_w
					new_h = int(target_w / aspect)
				else:
					new_h = target_h
					new_w = int(target_h * aspect)
				
				img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
				
				# 256x256の背景に描画してサイズを統一
				bmp = wx.Bitmap(target_w, target_h)
				dc = wx.MemoryDC(bmp)
				# 背景色（白）
				dc.SetBackground(wx.Brush(wx.WHITE))
				dc.Clear()
				
				# 中央に描画
				x = (target_w - new_w) // 2
				y = (target_h - new_h) // 2
				dc.DrawBitmap(wx.Bitmap(img), x, y, True)
				dc.SelectObject(wx.NullBitmap)
				
				# ImageListに追加
				img_idx = self.image_list.Add(bmp)
				
				# ListCtrlに追加
				item = wx.ListItem()
				item.SetId(i)
				item.SetText(os.path.basename(file_path))
				item.SetImage(img_idx)
				# 実際のファイルパスをデータとして保持させたい場合は別途管理が必要だが、
				# ここでは簡易表示のみとする
				self.thumbnail_list.InsertItem(item)
			
			except Exception as e:
				print(f"Error loading image {file_path}: {e}")

def main():
	app = wx.App()
	frame = MainFrame(None, "Image Tagging Helper")
	frame.Show()
	app.MainLoop()

if __name__ == "__main__":
	main()
