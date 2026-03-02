import os
from typing import Dict, List, Optional
import bisect

import wx

from src.image_tagging_helper.models.dataset import Dataset, DatasetItem

class ImageVListBox(wx.VListBox):
	"""
	画像を可変の高さで表示するための仮想リストボックス。
	"""
	
	def __init__(self, parent, style=0):
		super().__init__(parent, style=style)
		self.dataset: Dataset | None = None
		self.filtered_indices: List[int] | None = None
		self.thumbnail_cache: Dict[tuple[str, tuple[int, int]], wx.Bitmap] = { }
		self.image_cache: Dict[str, wx.Image] = { }
		self._thumbnail_display_width = 64  # デフォルト値
		self.padding_h = 5
		self.padding_v = 5
		self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
	
	def set_dataset(self, dataset: Dataset | None):
		"""
		表示するデータセットを設定し、リストを更新する。
		"""
		self.dataset = dataset
		self.filtered_indices = None
		item_count = len(self.dataset) if self.dataset else 0
		self.SetItemCount(item_count)
		
		# データセットが変更されたら、キャッシュをクリア
		self.thumbnail_cache.clear()
		self.image_cache.clear()
		
		# データセットが変更されたら、選択をクリア
		if self.GetSelection() >= item_count:
			self.SetSelection(wx.NOT_FOUND)
		
		self.Refresh()
	
	def set_filter(self, indices: List[int] | None):
		"""
		表示するアイテムのインデックスリストを設定する。
		Noneの場合は全アイテムを表示する。
		"""
		self.filtered_indices = indices
		item_count = len(indices) if indices is not None else (len(self.dataset) if self.dataset else 0)
		self.SetItemCount(item_count)
		
		if self.GetSelection() >= item_count:
			self.SetSelection(wx.NOT_FOUND)
		self.Refresh()
	
	def get_dataset_index(self, n: int) -> int:
		"""
		表示上のインデックス n に対応するデータセットの実インデックスを返す。
		"""
		if self.filtered_indices is not None:
			if 0 <= n < len(self.filtered_indices):
				return self.filtered_indices[n]
			return -1  # Invalid
		return n
	
	def get_view_index(self, dataset_index: int) -> int:
		"""
		データセットの実インデックスに対応する表示上のインデックスを返す。
		表示されていない場合は wx.NOT_FOUND を返す。
		"""
		if self.filtered_indices is None:
			if 0 <= dataset_index < (len(self.dataset) if self.dataset else 0):
				return dataset_index
			return wx.NOT_FOUND
		
		# dataset.match_items は enumerate 順に返すので昇順である。
		idx = bisect.bisect_left(self.filtered_indices, dataset_index)
		if idx < len(self.filtered_indices) and self.filtered_indices[idx] == dataset_index:
			return idx
		return wx.NOT_FOUND
	
	def _get_thumbnail(self, item: DatasetItem, size: tuple[int, int]) -> wx.Bitmap:
		"""
		画像を読み込み、指定されたサイズでサムネイルを生成する。
		アスペクト比を維持し、余白は白で埋める。

		生成されたサムネイルはself.thumbnailsにキャッシュされる。
		"""
		cache_key = (item.image_path, size)
		if cache_key in self.thumbnail_cache:
			return self.thumbnail_cache[cache_key]
		
		# 画像読み込み（キャッシュがあればそれを使用）
		if item.image_path not in self.image_cache:
			with wx.LogNull():
				img = wx.Image(item.image_path, wx.BITMAP_TYPE_ANY)
			if not img.IsOk():
				# 読み込み失敗時はエラー用のビットマップを生成してキャッシュ
				bmp = wx.Bitmap(size[0], size[1])
				dc = wx.MemoryDC(bmp)
				dc.SetBackground(wx.Brush(wx.LIGHT_GREY))
				dc.Clear()
				dc.SelectObject(wx.NullBitmap)
				self.thumbnail_cache[cache_key] = bmp
				return bmp
			self.image_cache[item.image_path] = img
		
		img = self.image_cache[item.image_path]
		
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
		else:
			bg_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOX)
		
		dc.SetBrush(wx.Brush(bg_colour))
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.DrawRectangle(rect)
		
		dataset_index = self.get_dataset_index(n)
		if dataset_index < 0:
			return
		item = self.dataset[dataset_index]
		
		# サムネイルを取得して描画
		# OnMeasureItemで計算された幅を使用
		thumbnail_width = self._thumbnail_display_width
		if thumbnail_width < 16:
			thumbnail_width = 16
		thumbnail_size = (thumbnail_width, thumbnail_width)
		
		try:
			bmp = self._get_thumbnail(item, thumbnail_size)
			# 中央に配置
			x = rect.x + (rect.width - bmp.GetWidth()) // 2
			y = rect.y + self.padding_v  # 上パディング
			dc.DrawBitmap(bmp, x, y, True)  # useMask=True
		except Exception as e:
			# エラー発生時は代替テキストを描画
			dc.SetTextForeground(
				wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT) if not self.IsSelected(n) else wx.SystemSettings.GetColour(
					wx.SYS_COLOUR_HIGHLIGHTTEXT))
			
			error_text = 'Error loading image'
			tw, th = dc.GetTextExtent(error_text)
			dc.DrawText(error_text, rect.x + (rect.width - tw) // 2, rect.y + (rect.height - th) // 2)
			print(f'Error rendering thumbnail for {item.image_path}: {e}')  # ログにも出力
			return  # エラー時はファイル名を描画しない
	
	def OnMeasureItem(self, n: int) -> int:
		"""
		n番目の項目の高さを計算して返す。
		"""
		if not self.dataset:
			return 0
		
		# コントロールの幅から画像の幅を決定
		# スクロールバーが表示されている場合、その幅は含まれない。
		width = self.GetClientSize().width
		
		# 画像幅 = 全体の幅 - 左右パディング
		image_width = width - self.padding_h * 2
		
		if image_width < 64:
			image_width = 64
		
		# 計算した幅を保存してOnDrawItemで使用する
		self._thumbnail_display_width = image_width
		
		# 画像の高さ (正方形)
		image_height = image_width
		
		# 全体の高さ = 画像の高さ + 上下パディング
		total_height = image_height + self.padding_v * 2
		
		return int(total_height)
	
	def on_mouse_wheel(self, event: wx.MouseEvent):
		"""
		マウスホイールイベントを処理し、スクロール量を調整する。
		"""
		rotation = event.GetWheelRotation()
		
		# 1回転あたりのスクロール行数を1に設定
		lines_to_scroll = 1
		
		if rotation > 0:
			# 上にスクロール
			self.ScrollLines(-lines_to_scroll)
		elif rotation < 0:
			# 下にスクロール
			self.ScrollLines(lines_to_scroll)
