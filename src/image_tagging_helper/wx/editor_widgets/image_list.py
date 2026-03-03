import os
import threading
import queue
from typing import Dict, List, Optional, Set
import bisect

import wx

from src.image_tagging_helper.models.dataset import Dataset, DatasetItem

# サムネイルの固定サイズを定義。メモリと品質のバランスを考慮して調整可能。
THUMBNAIL_CACHE_FIXED_SIZE = (384, 384)

class ImageVListBox(wx.VListBox):
	"""
	画像を可変の高さで表示するための仮想リストボックス。
	"""
	
	def __init__(self, parent, style=0):
		super().__init__(parent, style=style)
		self.dataset: Dataset | None = None
		self.filtered_indices: List[int] | None = None
		# サムネイルキャッシュ。{ 画像パス: サムネイルビットマップ }
		self.thumbnail_cache: Dict[str, wx.Bitmap] = { }
		self._thumbnail_display_width = 64  # デフォルト値
		self.padding_h = 5
		self.padding_v = 5
		self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
		
		# 非同期サムネイル生成のための準備
		self.thumbnail_queue = queue.Queue()
		self.pending_thumbnails: Set[str] = set()  # 生成中のサムネイルパスを追跡
		self.worker_thread: threading.Thread | None = None
		self.worker_running = False
		self._start_thumbnail_worker()
		
		# アプリケーション終了時にワーカーを停止するためのイベントハンドラ
		self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
	
	def _start_thumbnail_worker(self):
		"""
		サムネイル生成ワーカースレッドを開始する。
		"""
		if not self.worker_running:
			self.worker_running = True
			self.worker_thread = threading.Thread(target=self._thumbnail_worker_task)
			self.worker_thread.daemon = True  # メインスレッド終了時に一緒に終了
			self.worker_thread.start()
	
	def _stop_thumbnail_worker(self):
		"""
		サムネイル生成ワーカースレッドを停止する。
		"""
		if self.worker_running:
			self.worker_running = False
			self.thumbnail_queue.put(None)  # 終了シグナル
			if self.worker_thread and self.worker_thread.is_alive():
				self.worker_thread.join(timeout=1.0)  # 終了を待つ
	
	def _on_destroy(self, event: wx.Event):
		"""
		ウィンドウ破棄時にワーカースレッドを停止する。
		"""
		self._stop_thumbnail_worker()
		event.Skip()
	
	def _thumbnail_worker_task(self):
		"""
		ワーカースレッドでサムネイル生成処理を実行する。
		"""
		while self.worker_running:
			item_data = self.thumbnail_queue.get()
			if item_data is None:  # 終了シグナル
				break
			
			image_path, item_index = item_data
			
			# 既に生成依頼が出ているか確認
			if image_path not in self.pending_thumbnails:
				self.thumbnail_queue.task_done()
				continue
			
			try:
				# 画像ファイルを直接読み込む
				with wx.LogNull():
					img = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
				
				if not img.IsOk():
					# 読み込み失敗時はエラー用のビットマップを生成
					bmp = wx.Bitmap(THUMBNAIL_CACHE_FIXED_SIZE[0], THUMBNAIL_CACHE_FIXED_SIZE[1])
					dc = wx.MemoryDC(bmp)
					dc.SetBackground(wx.Brush(wx.LIGHT_GREY))
					dc.Clear()
					dc.SelectObject(wx.NullBitmap)
					generated_bmp = bmp
				else:
					# サムネイル用にリサイズ（アスペクト比維持）
					w, h = img.GetWidth(), img.GetHeight()
					target_w, target_h = THUMBNAIL_CACHE_FIXED_SIZE
					
					if w <= 0 or h <= 0:
						bmp = wx.Bitmap(target_w, target_h)
						dc = wx.MemoryDC(bmp)
						dc.SetBackground(wx.Brush(wx.WHITE))
						dc.Clear()
						dc.SelectObject(wx.NullBitmap)
						generated_bmp = bmp
					else:
						scale = min(target_w / w, target_h / h)
						new_w = int(w * scale)
						new_h = int(h * scale)
						
						# 品質を通常に設定してリサイズ
						scaled_img = img.Scale(new_w, new_h, wx.IMAGE_QUALITY_HIGH)
						
						bmp = wx.Bitmap(target_w, target_h)
						dc = wx.MemoryDC(bmp)
						dc.SetBackground(wx.Brush(wx.WHITE))
						dc.Clear()
						
						x = (target_w - new_w) // 2
						y = (target_h - new_h) // 2
						dc.DrawBitmap(wx.Bitmap(scaled_img), x, y, True)
						dc.SelectObject(wx.NullBitmap)
						generated_bmp = bmp
				
				# UIスレッドに結果を通知
				wx.CallAfter(self._on_thumbnail_generated, image_path, generated_bmp, item_index)
			
			except Exception as e:
				print(f"Error generating thumbnail for {image_path}: {e}")
				# エラー時もpending_thumbnailsから削除
				wx.CallAfter(self._on_thumbnail_generated, image_path, None, item_index)
			finally:
				self.thumbnail_queue.task_done()
	
	def _on_thumbnail_generated(self, image_path: str, bitmap: wx.Bitmap | None, item_index: int):
		"""
		ワーカースレッドでサムネイルが生成された後にUIスレッドで呼び出される。
		キャッシュを更新し、該当アイテムを再描画する。
		"""
		if image_path in self.pending_thumbnails:
			self.pending_thumbnails.remove(image_path)
		
		if bitmap:
			self.thumbnail_cache[image_path] = bitmap
			# 該当アイテムが現在表示されている範囲内であれば再描画を要求
			# VListBoxのRefreshItemはview_indexを要求するので、dataset_indexから変換
			view_index = self.get_view_index(item_index)
			if view_index != wx.NOT_FOUND and self.IsVisible(view_index):
				self.RefreshLine(view_index)
		else:
			# エラー発生時は、エラー用のビットマップをキャッシュするなどの対応も可能
			# 今回はキャッシュしないでおく（次回描画時に再試行される）
			pass
	
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
		self.pending_thumbnails.clear()
		
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
	
	def get_dataset_index(self, view_index: int) -> int:
		"""
		表示上のインデックス n に対応するデータセットの実インデックスを返す。
		"""
		if self.filtered_indices is not None:
			if 0 <= view_index < len(self.filtered_indices):
				return self.filtered_indices[view_index]
			return -1  # Invalid
		return view_index
	
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
	
	def select_item(self, item_index: int):
		"""
		指定されたインデックスのアイテムを選択する
		"""
		view_index = self.get_view_index(item_index)
		if view_index != wx.NOT_FOUND:
			self.SetSelection(view_index)
	
	def _get_thumbnail(self, item: DatasetItem, item_index: int) -> wx.Bitmap:
		"""
		画像を読み込み、固定サイズでサムネイルを生成する。
		アスペクト比を維持し、余白は白で埋める。
		キャッシュに存在しない場合は、非同期で生成を依頼し、プレースホルダーを返す。
		"""
		image_path = item.image_path
		
		# キャッシュに存在すればそれを返す
		if image_path in self.thumbnail_cache:
			return self.thumbnail_cache[image_path]
		
		# キャッシュになく、まだ生成中でなければ、非同期生成を依頼
		if image_path not in self.pending_thumbnails:
			self.pending_thumbnails.add(image_path)
			self.thumbnail_queue.put((image_path, item_index))
		
		# プレースホルダーを返す
		placeholder_bmp = wx.Bitmap(THUMBNAIL_CACHE_FIXED_SIZE[0], THUMBNAIL_CACHE_FIXED_SIZE[1])
		dc = wx.MemoryDC(placeholder_bmp)
		dc.SetBackground(wx.Brush(wx.LIGHT_GREY))
		dc.Clear()
		# 読み込み中を示すテキストを追加
		text = "Loading..."
		# フォントサイズをサムネイルの幅に合わせて調整
		font_size = THUMBNAIL_CACHE_FIXED_SIZE[0] // 10
		font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
		dc.SetFont(font)
		tw, th = dc.GetTextExtent(text)
		dc.SetTextForeground(wx.BLACK)
		dc.DrawText(text, (THUMBNAIL_CACHE_FIXED_SIZE[0] - tw) // 2, (THUMBNAIL_CACHE_FIXED_SIZE[1] - th) // 2)
		dc.SelectObject(wx.NullBitmap)
		return placeholder_bmp
	
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
			text_colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
		
		dc.SetBrush(wx.Brush(bg_colour))
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.DrawRectangle(rect)
		
		dataset_index = self.get_dataset_index(n)
		if dataset_index < 0:
			return
		item = self.dataset[dataset_index]
		
		# サムネイルを取得して描画
		# OnMeasureItemで計算された幅を使用
		thumbnail_display_width = self._thumbnail_display_width
		if thumbnail_display_width < 16:
			thumbnail_display_width = 16
		
		try:
			bmp = self._get_thumbnail(item, dataset_index)
			
			draw_w = thumbnail_display_width
			draw_h = thumbnail_display_width  # 正方形を想定
			
			x = rect.x + (rect.width - draw_w) // 2
			y = rect.y + self.padding_v  # 上パディング
			
			# wx.GraphicsContext を使用してスケーリング描画
			gc = wx.GraphicsContext.Create(dc)
			if gc:
				gc.SetInterpolationQuality(wx.INTERPOLATION_BEST)  # 高品質な補間
				gc.DrawBitmap(bmp, x, y, draw_w, draw_h)
			else:
				# GraphicsContextが利用できない場合のフォールバック
				# このパスは通常通らないが、念のため元のサイズで描画
				dc.DrawBitmap(bmp, x, y, True)
		
		except Exception as e:
			# エラー発生時は代替テキストを描画
			dc.SetTextForeground(text_colour)
			
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
