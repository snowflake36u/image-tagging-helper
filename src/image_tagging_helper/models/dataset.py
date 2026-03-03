from typing import List, TYPE_CHECKING, Dict, Callable
import glob
import os
from collections import Counter, deque

from src.image_tagging_helper.models.caption import Caption
from src.image_tagging_helper.models.diff import (
	DatasetDiff,
	AppendDiff, InsertDiff, MoveDiff,
	DeleteDiff, MutateTagDiff, BatchDiff,
)
from src.image_tagging_helper.models.history_manager import HistoryManager
from src.image_tagging_helper.models.history_actions import HistoryAction
from src.image_tagging_helper.models.controller import DatasetController

class DatasetItem:
	"""
	データセット内の個々の画像ファイルを表すクラス。

	Attributes:
		  image_path (str): 画像ファイルのパス。
		  caption (Caption): 画像に関連付けられたキャプション。
	"""
	
	def __init__(
			self,
			image_path: str,
			caption: Caption | None = None,
	):
		"""
		DatasetItemのコンストラクタ。

		Args:
			image_path: 画像ファイルのパス。
			caption: 画像に関連付けられたキャプション。指定されない場合は空のCaptionが作成される。
		"""
		self.image_path = image_path
		self.caption = caption or Caption()
	
	@staticmethod
	def create(image_path, caption_ext, caption_format_config, on_tag_usage_changed):
		caption = Caption()
		caption_path = os.path.splitext(image_path)[0] + caption_ext
		if os.path.exists(caption_path):
			with open(caption_path, 'r', encoding='utf-8') as f:
				caption_text = f.read()
				caption = Caption.parse(caption_text, config=caption_format_config)
		
		caption.set_tag_usage_changed_listener(on_tag_usage_changed)
		
		return DatasetItem(image_path=image_path, caption=caption)

class Dataset:
	"""
	複数のCaptionを管理するデータセットクラス。
	変更を監視するためのリスナー機能や、Diffの適用機能を提供します。
	"""
	SENDER_ID = 'dataset'
	
	def __init__(self):
		self.items = None
		self.tag_usages = Counter()
		self.history = HistoryManager()
		self.folder_path = None
		self._origin_controller = self.get_controller()
		
		# タグの使用回数の更新後イベント。(tag, count) -> None
		self._tag_usage_changed_listeners: List[Callable[[str, int], None]] = []
		# 変更操作の適用後イベント。(sender, diff) -> None
		self._diff_applied_listeners: List[Callable[[str, DatasetDiff], None]] = []
	
	def __getitem__(self, item: int | slice) -> DatasetItem | List[DatasetItem]:
		return self.items[item]
	
	def __len__(self):
		return len(self.items)
	
	@property
	def initialized(self):
		return self.items is not None
	
	@property
	def is_dirty(self) -> bool:
		"""保存されていない変更があるかどうかを返します。"""
		return self.history.is_dirty
	
	# === 初期化処理 ===
	def load(
			self,
			folder_path,
			image_exts,
			caption_ext,
			caption_format_config,
	):
		self.folder_path = folder_path
		self.history = HistoryManager()
		
		image_files = []
		for ext in image_exts:
			image_files.extend(glob.glob(os.path.join(folder_path, '*' + ext)))
		
		image_files = sorted(list(set(image_files)))
		
		self.items = [
			DatasetItem.create(
				image_path=path,
				caption_ext=caption_ext,
				caption_format_config=caption_format_config,
				on_tag_usage_changed=self.on_tag_usage_changed_in_caption
			)
			for path in image_files
		]
		self._init_tag_usages()
	
	def save(self, caption_ext: str, caption_format_config):
		"""
		データセット内のすべてのキャプションをファイルに保存します。

		Args:
			caption_format_config: キャプションのフォーマット設定。
		"""
		if not self.items:
			return
		
		self._origin_controller.clean()
		self.history.mark_saved()
		
		for item in self.items:
			caption_path = os.path.splitext(item.image_path)[0] + caption_ext
			text = item.caption.format(caption_format_config)
			with open(caption_path, 'w', encoding='utf-8') as f:
				f.write(text)
	
	# === イベントリスナーの管理 ===
	
	def add_diff_applied_listener(self, callback):
		"""
		変更通知を受け取るリスナーを追加します。
		
		Args:
			callback (callable): 変更通知を受け取るコールバック関数。
		"""
		self._diff_applied_listeners.append(callback)
	
	def remove_diff_applied_listener(self, callback):
		"""
		リスナーを削除します。
		
		Args:
			callback (callable): 削除するコールバック関数。
		"""
		self._diff_applied_listeners.remove(callback)
	
	def add_tag_usage_changed_listener(self, callback):
		"""
		変更通知を受け取るリスナーを追加します。
		
		Args:
			callback (callable): 変更通知を受け取るコールバック関数。
		"""
		self._tag_usage_changed_listeners.append(callback)
	
	def remove_tag_usage_changed_listener(self, callback):
		"""
		リスナーを削除します。
		
		Args:
			callback (callable): 削除するコールバック関数。
		"""
		self._tag_usage_changed_listeners.remove(callback)
	
	# === 編集操作の管理 ===
	
	def _notify_diff_applied(self, sender, diff):
		"""
		登録されたリスナーに変更を通知します。
		
		Args:
			sender (str): 変更を行った送信元のID。
			diff (DatasetDiff): 適用された変更内容。
		"""
		for cb in self._diff_applied_listeners:
			# UIスレッドセーフな呼び出しが必要な場合は、呼び出し側(cb)でwx.CallAfter等を使用することを想定
			cb(sender, diff)
	
	def apply_diff(self, sender, diff):
		"""
		Diffオブジェクトに基づいてデータセットを更新します。
		更新後、リスナーに通知を行います。
		
		Args:
			sender (str): 変更を行った送信元のID。
			diff (DatasetDiff): 適用する変更内容。
		"""
		if sender == self.SENDER_ID:
			return
		
		self._apply_diff_internal(diff)
		self._notify_diff_applied(sender, diff)
	
	def _apply_diff_internal(self, diff):
		"""
		Diffオブジェクトに基づいてデータセットを更新します（内部用）。
		通知は行いません。
		"""
		if isinstance(diff, AppendDiff):
			self.append_tags(diff.target, diff.tags)
		elif isinstance(diff, InsertDiff):
			self.insert_tags(diff.target, diff.position, diff.tags)
		elif isinstance(diff, MoveDiff):
			self.move_tag(diff.target, diff.old_position, diff.new_position)
		elif isinstance(diff, DeleteDiff):
			self.delete_tags(diff.target, diff.positions)
		elif isinstance(diff, MutateTagDiff):
			self.mutate_tag(diff.target, diff.position, diff.new_tag)
		elif isinstance(diff, BatchDiff):
			for child in diff.children:
				self._apply_diff_internal(child)
	
	# === 履歴操作 ===
	
	def execute(self, action: HistoryAction, sender: str = None):
		"""
		アクションを実行し、履歴に追加します。
		
		Args:
			action (HistoryAction): 実行するアクション。
			sender (str): 操作の送信元ID。
		"""
		self.history.push(action, sender)
	
	def undo(self, sender: str = None):
		"""
		直前の操作を取り消します。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		self.history.undo(sender)
	
	def redo(self, sender: str = None):
		"""
		取り消した操作をやり直します。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		self.history.redo(sender)
	
	def can_undo(self) -> bool:
		return self.history.can_undo()
	
	def can_redo(self) -> bool:
		return self.history.can_redo()
	
	# === 編集操作 ===
	
	def append_tags(self, target, tags):
		"""
		指定されたキャプションの末尾にタグを追加します。
		
		Args:
			target (int): 対象のキャプションインデックス。
			tags (tuple[Tag, ...]): 追加するタグのリスト。
		"""
		caption = self.items[target].caption
		caption.append_tags(tags)
	
	def insert_tags(self, target, position, tags):
		"""
		指定されたキャプションの指定位置にタグを挿入します。
		
		Args:
			target (int): 対象のキャプションインデックス。
			position (int): 挿入位置。
			tags (tuple[Tag, ...]): 挿入するタグのリスト。
		"""
		caption = self.items[target].caption
		caption.insert_tags(position, tags)
	
	def delete_tags(self, target, positions):
		"""
		指定された位置のタグを削除します。
		
		Args:
			target (int): 対象のキャプションインデックス。
			positions (tuple[int, ...]): 削除するタグの位置のリスト。降順にソート済みである必要があります。
		"""
		caption = self.items[target].caption
		caption.remove_tags_at(positions)
	
	def move_tag(self, target, old_position, new_position):
		"""
		タグの位置を移動します。
		
		Args:
			target (int): 対象のキャプションインデックス。
			old_position (int): 移動元の位置。
			new_position (int): 移動先の位置。
		"""
		caption = self.items[target].caption
		caption.move_tag(old_position, new_position)
	
	def mutate_tag(self, target, position, new_tag):
		"""
		指定された位置のタグを新しいタグに置換します。
		
		Args:
			target (int): 対象のキャプションインデックス。
			position (int): 置換するタグの位置。
			new_tag (Tag): 新しいタグ。
		"""
		caption = self.items[target].caption
		caption.mutate_tag(position, new_tag)
	
	# === タグカウント ===
	
	def _init_tag_usages(self) -> Dict[str, int]:
		"""
		データセット内のすべてのタグとその出現回数を取得します。

		Returns:
			Dict[str, int]: タグ名をキー、出現回数を値とする辞書。
		"""
		tag_usages: Counter[str] = Counter()
		for item in self.items:
			for tag in item.caption.tags:
				tag_usages[tag.text] += 1
		self.tag_usages = tag_usages
	
	def on_tag_usage_changed_in_caption(self, text, is_used):
		if is_used:
			self.tag_usages[text] += 1
		else:
			self.tag_usages[text] -= 1
		
		for cb in self._tag_usage_changed_listeners:
			cb(text, self.tag_usages[text])
	
	# === コントローラ ===
	
	def get_controller(self, sender: str | None = None) -> DatasetController:
		"""
		DatasetControllerを生成します。
		
		Args:
			sender (str): 操作の送信元ID。
			
		Returns:
			生成されたDatasetControllerオブジェクト。
		"""
		return DatasetController(self, sender)
	
	# === フィルタ機能 ===
	
	def match_items(self, include_tags: set[str], exclude_tags: set[str]) -> list[int]:
		return [
			i for i, item in enumerate(self.items)
			if item.caption.match(include_tags, exclude_tags)
		]
