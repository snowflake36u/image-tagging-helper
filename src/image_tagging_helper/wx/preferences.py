import wx

from src.image_tagging_helper.core.config import Config
from src.image_tagging_helper.i18n import __

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
		
		# フォント設定
		sb_font = wx.StaticBox(panel, label=__("label:font_settings"))
		sbs_font = wx.StaticBoxSizer(sb_font, wx.VERTICAL)
		
		hbox_font = wx.BoxSizer(wx.HORIZONTAL)
		st_font = wx.StaticText(panel, label=__("label:editor_font"))
		
		self.font_picker = wx.FontPickerCtrl(panel, style=wx.FNTP_FONTDESC_AS_LABEL)
		font_desc = self.config.get('ui.font')
		if font_desc:
			font = wx.Font(font_desc)
			if font.IsOk():
				self.font_picker.SetSelectedFont(font)
		
		hbox_font.Add(st_font, flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=8)
		hbox_font.Add(self.font_picker, proportion=1)
		
		sbs_font.Add(hbox_font, flag=wx.EXPAND | wx.ALL, border=5)
		panel_sizer.Add(sbs_font, flag=wx.EXPAND | wx.ALL, border=10)
		
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
		
		# フォント設定の保存
		font = self.font_picker.GetSelectedFont()
		if font.IsOk():
			self.config.set('ui.font', font.GetNativeFontInfoDesc())
		
		self.config.save()
		
		return self.original_lang != self.config.get('language', 'en')
