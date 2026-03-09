import wx

class FlatBitmapButton(wx.Button):
	"""フォーカス可能なフラットボタン。"""
	
	def __init__(self, parent: wx.Window, id: int = wx.ID_ANY, bitmap: wx.Bitmap | None = None,
			tooltip: str = "", size: tuple[int, int] | wx.Size = (32, 32)):
		super().__init__(parent, id, size=wx.Size(*size), style=wx.BORDER_NONE)
		self.bitmap = bitmap
		self.SetToolTip(tooltip)
		self._hover = False
		self._pressed = False
		
		self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
		
		self.Bind(wx.EVT_PAINT, self.OnPaint)
		self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
		self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
		self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
		self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)
		self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
		self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
		self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
	
	def AcceptsFocus(self) -> bool:
		return True
	
	def AcceptsFocusFromKeyboard(self) -> bool:
		return True
	
	def OnPaint(self, event: wx.PaintEvent) -> None:
		dc = wx.BufferedPaintDC(self)
		bg_color = self.GetParent().GetBackgroundColour()
		dc.SetBackground(wx.Brush(bg_color))
		dc.Clear()
		
		renderer = wx.RendererNative.Get()
		rect = self.GetClientRect()
		flags = 0
		if self.IsEnabled():
			if self._pressed:
				flags |= wx.CONTROL_PRESSED
			elif self._hover or self.HasFocus():
				# フォーカス状態でもホバー時と同じ外観を適用する。
				flags |= wx.CONTROL_CURRENT
			
			if self.HasFocus():
				flags |= wx.CONTROL_FOCUSED
		else:
			flags |= wx.CONTROL_DISABLED
		
		# ホバー、押下、またはフォーカスがある場合にボタンの背景を描画する。
		if self._hover or self._pressed or self.HasFocus():
			renderer.DrawPushButton(self, dc, rect, flags)
		
		if self.bitmap:
			w, h = self.GetSize()
			bw, bh = self.bitmap.GetWidth(), self.bitmap.GetHeight()
			x = (w - bw) // 2
			y = (h - bh) // 2
			
			bmp = self.bitmap
			if not self.IsEnabled():
				img = bmp.ConvertToImage().ConvertToGreyscale()
				bmp = wx.Bitmap(img)
			
			dc.DrawBitmap(bmp, x, y, True)
	
	def OnEnter(self, event: wx.MouseEvent) -> None:
		self._hover = True
		self.Refresh()
	
	def OnLeave(self, event: wx.MouseEvent) -> None:
		self._hover = False
		self._pressed = False
		self.Refresh()
	
	def OnLeftDown(self, event: wx.MouseEvent) -> None:
		self._pressed = True
		if not self.HasCapture():
			self.CaptureMouse()
		self.SetFocus()
		self.Refresh()
	
	def OnLeftUp(self, event: wx.MouseEvent) -> None:
		if self._pressed:
			self._pressed = False
			if self.HasCapture():
				try:
					self.ReleaseMouse()
				except wx.wxAssertionError:
					# キャプチャスタックが空の場合に発生するアサーションエラーを無視する。
					# HasCapture()がTrueを返しても、タイミングによってはReleaseMouse()でエラーになることがあるため。
					pass
			self.Refresh()
			
			if self.GetClientRect().Contains(event.GetPosition()):
				evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, self.GetId())
				evt.SetEventObject(self)
				wx.PostEvent(self, evt)
	
	def OnMouseCaptureLost(self, event: wx.MouseCaptureLostEvent) -> None:
		self._pressed = False
		self.Refresh()
	
	def OnSetFocus(self, event: wx.FocusEvent) -> None:
		"""フォーカスを受け取った際の処理。"""
		self.Refresh()
		event.Skip()
	
	def OnKillFocus(self, event: wx.FocusEvent) -> None:
		"""フォーカスを失った際の処理。

		スペースキー押下中にフォーカスが移動した場合に、ボタンが押下状態のままに
		なってしまう問題を解消する。また、wx.Buttonと同様に、スペースキー押下中に
		フォーカスが移動した場合はボタンが押されたとみなしてイベントを発火する。
		ただし、ウィンドウ自体がフォーカスを失った場合は発火しない。
		"""
		if self._pressed:
			self._pressed = False
			self.Refresh()
			
			# フォーカス移動先のウィンドウが存在する場合のみイベントを発火する
			# また、Shiftキーが押されていない場合のみ発火する（Shift+Tabでの戻り動作時は発火しない）
			if event.GetWindow() and not wx.GetKeyState(wx.WXK_SHIFT):
				evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, self.GetId())
				evt.SetEventObject(self)
				wx.PostEvent(self, evt)
		
		event.Skip()
	
	def OnKeyDown(self, event: wx.KeyEvent) -> None:
		if event.GetKeyCode() == wx.WXK_SPACE:
			if not self._pressed:
				self._pressed = True
				self.Refresh()
		else:
			event.Skip()
	
	def OnKeyUp(self, event: wx.KeyEvent) -> None:
		if event.GetKeyCode() == wx.WXK_SPACE:
			if self._pressed:
				self._pressed = False
				self.Refresh()
				
				evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, self.GetId())
				evt.SetEventObject(self)
				wx.PostEvent(self, evt)
		else:
			event.Skip()

class NonFocusablePanel(wx.Panel):
	"""フォーカスを受け取らないパネル。"""
	
	def AcceptsFocus(self) -> bool:
		return False
	
	def AcceptsFocusFromKeyboard(self) -> bool:
		return False  # キーボード（Tab）経路から外す
