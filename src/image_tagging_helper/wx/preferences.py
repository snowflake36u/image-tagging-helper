import wx

from image_tagging_helper.core.config import Config
from image_tagging_helper.i18n import __

class PreferencesDialog(wx.Dialog):
	"""設定画面のダイアログ。"""
	
	def __init__(self, parent, config: Config):
		super().__init__(
			parent,
			title=__("title:preferences"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,  # ダイアログをリサイズ可能にする
		)
		self.config = config
		self.original_lang = self.config.get('language', 'en')
		self._init_ui()
	
	def _init_ui(self):
		dlg_sizer = wx.BoxSizer(wx.VERTICAL)
		
		panel = wx.Panel(self)
		panel_sizer = wx.BoxSizer(wx.VERTICAL)
		
		# 言語設定
		self._add_language_settings(panel, panel_sizer)
		
		# フォント設定
		self._add_font_settings(panel, panel_sizer)
		
		# 画像ビューア設定
		self._add_viewer_settings(panel, panel_sizer)
		
		panel.SetSizer(panel_sizer)
		
		dlg_sizer.Add(panel, 1, wx.EXPAND)
		
		# ボタン
		btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		dlg_sizer.Add(btns, flag=wx.EXPAND | wx.ALL, border=10)
		
		self.SetSizer(dlg_sizer)
		self.SetSize((800, 600))
		self.CenterOnParent()
	
	def _add_language_settings(self, parent: wx.Panel, sizer: wx.Sizer):
		"""言語設定のUIを追加します。"""
		sb = wx.StaticBox(parent, label=__("label:language_settings"))
		sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
		
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		st = wx.StaticText(parent, label=__("label:language"))
		
		self.languages = [("en", "English"), ("ja", "Japanese")]
		choices = [lang[1] for lang in self.languages]
		self.lang_choice = wx.Choice(parent, choices=choices)
		
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
		sizer.Add(sbs, flag=wx.EXPAND | wx.ALL, border=10)
	
	def _add_font_settings(self, parent: wx.Panel, sizer: wx.Sizer):
		"""フォント設定のUIを追加します。"""
		sb_font = wx.StaticBox(parent, label=__("label:font_settings"))
		sbs_font = wx.StaticBoxSizer(sb_font, wx.VERTICAL)
		
		hbox_font = wx.BoxSizer(wx.HORIZONTAL)
		st_font = wx.StaticText(parent, label=__("label:editor_font"))
		
		self.font_picker = wx.FontPickerCtrl(parent, style=wx.FNTP_FONTDESC_AS_LABEL)
		font_desc = self.config.get('ui.font')
		if font_desc:
			font = wx.Font(font_desc)
			if font.IsOk():
				self.font_picker.SetSelectedFont(font)
		
		hbox_font.Add(st_font, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
		hbox_font.Add(self.font_picker, proportion=1)
		
		sbs_font.Add(hbox_font, flag=wx.EXPAND | wx.ALL, border=5)
		sizer.Add(sbs_font, flag=wx.EXPAND | wx.ALL, border=10)
	
	def _add_viewer_settings(self, parent: wx.Panel, sizer: wx.Sizer):
		"""画像ビューア設定のUIを追加します。"""
		sb_viewer = wx.StaticBox(parent, label=__("label:image_viewer"))
		sbs_viewer = wx.StaticBoxSizer(sb_viewer, wx.VERTICAL)
		
		# ビューア種別の選択
		viewer_types = [__("viewer:default"), __("viewer:custom")]
		self.viewer_type_radio = wx.RadioBox(parent, label=__("label:viewer_type"), choices=viewer_types)
		
		viewer_type = self.config.get('viewer.type', 'default')
		self.viewer_type_radio.SetSelection(1 if viewer_type == 'custom' else 0)
		
		sbs_viewer.Add(self.viewer_type_radio, flag=wx.EXPAND | wx.ALL, border=5)
		
		# カスタムコマンド入力
		self.custom_viewer_panel = wx.Panel(parent)
		custom_viewer_sizer = wx.BoxSizer(wx.VERTICAL)
		
		custom_viewer_label = wx.StaticText(self.custom_viewer_panel, label=__("label:viewer_command"))
		custom_viewer_sizer.Add(custom_viewer_label, flag=wx.BOTTOM, border=5)
		
		command_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.viewer_command_text = wx.TextCtrl(self.custom_viewer_panel)
		self.viewer_command_text.SetValue(self.config.get('viewer.command', ''))
		
		browse_button = wx.Button(self.custom_viewer_panel, label=__("button:browse"))
		
		command_sizer.Add(self.viewer_command_text, 1, wx.EXPAND | wx.RIGHT, 5)
		command_sizer.Add(browse_button, 0)
		
		custom_viewer_sizer.Add(command_sizer, 1, wx.EXPAND)
		
		# ヒント
		hint_text = wx.StaticText(self.custom_viewer_panel, label=__("hint:viewer_command"))
		custom_viewer_sizer.Add(hint_text, flag=wx.TOP, border=5)
		
		self.custom_viewer_panel.SetSizer(custom_viewer_sizer)
		sbs_viewer.Add(self.custom_viewer_panel, 1, wx.EXPAND | wx.ALL, 5)
		
		sizer.Add(sbs_viewer, flag=wx.EXPAND | wx.ALL, border=10)
		
		# イベントハンドラ
		self.viewer_type_radio.Bind(wx.EVT_RADIOBOX, self.on_viewer_type_change)
		browse_button.Bind(wx.EVT_BUTTON, self.on_browse_viewer)
		
		# 初期状態の更新
		self.on_viewer_type_change(None)
	
	def on_viewer_type_change(self, event):
		"""ビューア種別の変更に応じてUIの状態を更新します。"""
		is_custom = self.viewer_type_radio.GetSelection() == 1
		self.custom_viewer_panel.Enable(is_custom)
	
	def on_browse_viewer(self, event):
		"""ビューアの実行ファイルを選択するダイアログを表示します。"""
		with wx.FileDialog(self, __("title:select_viewer_executable"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				path = dlg.GetPath()
				# パスにスペースが含まれる場合を考慮して引用符で囲む
				self.viewer_command_text.SetValue(f'"{path}" {{file}}')
	
	def save(self) -> bool:
		"""設定を保存します。言語が変更された場合はTrueを返します。"""
		# 言語設定
		idx = self.lang_choice.GetSelection()
		if idx != wx.NOT_FOUND:
			lang_code = self.languages[idx][0]
			self.config.set('language', lang_code)
		
		# フォント設定
		font = self.font_picker.GetSelectedFont()
		if font.IsOk():
			self.config.set('ui.font', font.GetNativeFontInfoDesc())
		
		# ビューア設定
		viewer_type = 'custom' if self.viewer_type_radio.GetSelection() == 1 else 'default'
		self.config.set('viewer.type', viewer_type)
		self.config.set('viewer.command', self.viewer_command_text.GetValue())
		
		self.config.save()
		
		return self.original_lang != self.config.get('language', 'en')
