import os
from typing import Dict

import wx

from src.image_tagging_helper.core.dataset import Dataset, DatasetItem

class ImageVListBox(wx.VListBox):
	"""
	画像を可変の高さで表示するための仮想リストボックス。
	"""
	
	def __init__(self, parent, style=0):
		super().__init__(parent, style=style)
		self.dataset: Dataset | None = None
		self.thumbnail_cache: Dict[tuple[str, tuple[int, int]], wx.Bitmap] = { }
		self.image_cache: Dict[str, wx.Image] = { }
	
	def set_dataset(self, dataset: Dataset | None):
		"""
		表示するデータセットを設定し、リストを更新する。
		"""
		self.dataset = dataset
		item_count = len(self.dataset) if self.dataset else 0
		self.SetItemCount(item_count)
		
		# データセットが変更されたら、キャッシュをクリア
		self.thumbnail_cache.clear()
		self.image_cache.clear()
		
		# データセットが変更されたら、選択をクリア
		if self.GetSelection() >= item_count:
			self.Select(wx.NOT_FOUND)
		
		self.Refresh()
	
	def _get_thumbnail(self, item: DatasetItem, size: tuple[int, int]) -> wx.Bitmap:
		"""
		画像を読み込み、指定されたサイズでサムネイルを生成する。
		アスペクト比を維持し、余白は白で埋める。

		生成されたサムネイルはself.thumbnailsにキャッシュされる。
		"""
		cache_key = (item.path, size)
		if cache_key in self.thumbnail_cache:
			return self.thumbnail_cache[cache_key]
		
		# 画像読み込み（キャッシュがあればそれを使用）
		if item.path not in self.image_cache:
			img = wx.Image(item.path, wx.BITMAP_TYPE_ANY)
			if not img.IsOk():
				# 読み込み失敗時はエラー用のビットマップを生成してキャッシュ
				bmp = wx.Bitmap(size[0], size[1])
				dc = wx.MemoryDC(bmp)
				dc.SetBackground(wx.Brush(wx.LIGHT_GREY))
				dc.Clear()
				dc.SelectObject(wx.NullBitmap)
				self.thumbnail_cache[cache_key] = bmp
				return bmp
			self.image_cache[item.path] = img
		
		img = self.image_cache[item.path]
		
		# サムネイル用にリサイズ（アスペクト比維持）
		w, h = img.GetWidth(), img.GetHeight()
		target_w, target_h = size
		
		# ゼロ除算や不正な画像サイズを避ける
		if w <= 0 or h <= 0:
			bmp = wx.Bitmap(target_w, target_h)
			dc = wx.MemoryDC(bmp)
			dc.SetBackground(wx.Brush(wx.WHITE))
			dc.Clear()
			dc.SelectObject(wx.NullBitmap)
			self.thumbnail_cache[cache_key] = bmp
			return bmp
		
		scale = min(target_w / w, target_h / h)
		new_w = int(w * scale)
		new_h = int(h * scale)
		
		scaled_img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
		
		# 指定サイズの背景に描画してサイズを統一
		bmp = wx.Bitmap(target_w, target_h)
		dc = wx.MemoryDC(bmp)
		# 背景色（白）
		dc.SetBackground(wx.Brush(wx.WHITE))
		dc.Clear()
		
		# 中央に描画
		x = (target_w - new_w) // 2
		y = (target_h - new_h) // 2
		dc.DrawBitmap(wx.Bitmap(scaled_img), x, y, True)
		dc.SelectObject(wx.NullBitmap)
		
		self.thumbnail_cache[cache_key] = bmp
		return bmp
	
	def OnDrawItem(self, dc: wx.DC, rect: wx.Rect, n: int):
		"""
		n番目の項目を描画する。
		"""
		if not self.dataset:
			return
		
		# 背景を描画
		if self.IsSelected(n):
			bg_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
			text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
		else:
			bg_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
			text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
		
		dc.SetBrush(wx.Brush(bg_colour))
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.DrawRectangle(rect)
		
		item = self.dataset[n]
		
		# サムネイルを取得して描画
		# 左右に5pxずつのマージン
		thumbnail_width = rect.width - 10
		if thumbnail_width < 16:
			thumbnail_width = 16
		thumbnail_size = (thumbnail_width, thumbnail_width)
		
		try:
			bmp = self._get_thumbnail(item, thumbnail_size)
			# 中央に配置
			x = rect.x + (rect.width - bmp.GetWidth()) // 2
			y = rect.y + 5  # 上マージン
			dc.DrawBitmap(bmp, x, y, True)  # useMask=True
		except Exception as e:
			# エラー発生時は代替テキストを描画
			dc.SetTextForeground(
				wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT) if not self.IsSelected(n) else wx.SystemSettings.GetColour(
					wx.SYS_COLOUR_HIGHLIGHTTEXT))
			
			error_text = 'Error loading image'
			tw, th = dc.GetTextExtent(error_text)
			dc.DrawText(error_text, rect.x + (rect.width - tw) // 2, rect.y + (rect.height - th) // 2)
			print(f'Error rendering thumbnail for {item.path}: {e}')  # ログにも出力
			return  # エラー時はファイル名を描画しない
		
		# ファイル名を描画
		dc.SetTextForeground(text_colour)
		
		filename = os.path.basename(item.path)
		
		tw, th = dc.GetTextExtent(filename)
		# 画像の下に描画
		text_y = y + thumbnail_width + 5  # 画像の下に5pxのマージン
		dc.DrawText(filename, rect.x + (rect.width - tw) // 2, text_y)
	
	def OnMeasureItem(self, n: int) -> int:
		"""
		n番目の項目の高さを計算して返す。
		"""
		if not self.dataset:
			return 0
		
		# コントロールの幅から画像の幅を決定
		width = self.GetClientSize().width
		
		# スクロールバーが表示されていると仮定して、その幅を常に考慮する
		scrollbar_width = wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
		image_width = width - scrollbar_width - 10  # 左右マージン
		
		if image_width < 64:
			image_width = 64
		
		# 画像の高さ (正方形)
		image_height = image_width
		
		# ファイル名の高さを取得
		text_height = self.GetTextExtent('X')[1]  # 1行分の高さを取得
		
		# 全体の高さ = 上マージン + 画像の高さ + 画像とテキストの間マージン + テキストの高さ + 下マージン
		total_height = 5 + image_height + 5 + text_height + 5
		
		return int(total_height)
