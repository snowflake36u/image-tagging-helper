import wx

# カスタムイベントの定義
myEVT_SELECT_IN_ALL_TAGS = wx.NewEventType()
EVT_SELECT_IN_ALL_TAGS = wx.PyEventBinder(myEVT_SELECT_IN_ALL_TAGS, 1)

class SelectInAllTagsEvent(wx.PyCommandEvent):
	def __init__(self, id, tag_texts: set[str]):
		wx.PyCommandEvent.__init__(self, eventType=myEVT_SELECT_IN_ALL_TAGS, id=id)
		self.tag_texts = tag_texts
