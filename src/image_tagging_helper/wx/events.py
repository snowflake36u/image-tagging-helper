import wx

# === カスタムイベント ===

myEVT_SELECT_IN_ALL_TAGS = wx.NewEventType()
EVT_SELECT_IN_ALL_TAGS = wx.PyEventBinder(myEVT_SELECT_IN_ALL_TAGS, 1)

class SelectInAllTagsEvent(wx.PyCommandEvent):
	def __init__(self, id, tag_texts: set[str]):
		wx.PyCommandEvent.__init__(self, eventType=myEVT_SELECT_IN_ALL_TAGS, id=id)
		self.tag_texts = tag_texts

# AllTagsList関連のイベント
myEVT_ADD_TAGS_TO_FILTER = wx.NewEventType()
EVT_ADD_TAGS_TO_FILTER = wx.PyEventBinder(myEVT_ADD_TAGS_TO_FILTER, 1)

myEVT_APPEND_TAGS_TO_CURRENT = wx.NewEventType()
EVT_APPEND_TAGS_TO_CURRENT = wx.PyEventBinder(myEVT_APPEND_TAGS_TO_CURRENT, 1)

myEVT_REMOVE_TAGS_FROM_CURRENT = wx.NewEventType()
EVT_REMOVE_TAGS_FROM_CURRENT = wx.PyEventBinder(myEVT_REMOVE_TAGS_FROM_CURRENT, 1)

myEVT_APPEND_TAGS_TO_FILTERED = wx.NewEventType()
EVT_APPEND_TAGS_TO_FILTERED = wx.PyEventBinder(myEVT_APPEND_TAGS_TO_FILTERED, 1)

myEVT_REMOVE_TAGS_FROM_FILTERED = wx.NewEventType()
EVT_REMOVE_TAGS_FROM_FILTERED = wx.PyEventBinder(myEVT_REMOVE_TAGS_FROM_FILTERED, 1)

myEVT_APPEND_TAGS_TO_ALL = wx.NewEventType()
EVT_APPEND_TAGS_TO_ALL = wx.PyEventBinder(myEVT_APPEND_TAGS_TO_ALL, 1)

myEVT_REMOVE_TAGS_FROM_ALL = wx.NewEventType()
EVT_REMOVE_TAGS_FROM_ALL = wx.PyEventBinder(myEVT_REMOVE_TAGS_FROM_ALL, 1)

myEVT_REPLACE_TAG_IN_ALL = wx.NewEventType()
EVT_REPLACE_TAG_IN_ALL = wx.PyEventBinder(myEVT_REPLACE_TAG_IN_ALL, 1)

class TagsEvent(wx.PyCommandEvent):
	"""タグのリストをペイロードとして持つイベント"""
	
	def __init__(self, event_type, id, tags: list[str]):
		wx.PyCommandEvent.__init__(self, eventType=event_type, id=id)
		self.tags = tags

class ReplaceTagEvent(wx.PyCommandEvent):
	"""置換対象のタグをペイロードとして持つイベント"""
	
	def __init__(self, event_type, id, old_tag: str):
		wx.PyCommandEvent.__init__(self, eventType=event_type, id=id)
		self.old_tag = old_tag

# ImageVListBox関連のイベント
myEVT_VIEW_IMAGE = wx.NewEventType()
EVT_VIEW_IMAGE = wx.PyEventBinder(myEVT_VIEW_IMAGE, 0)

myEVT_OPEN_IN_FOLDER = wx.NewEventType()
EVT_OPEN_IN_FOLDER = wx.PyEventBinder(myEVT_OPEN_IN_FOLDER, 0)
