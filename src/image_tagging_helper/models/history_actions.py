from image_tagging_helper.models.caption import Tag
from image_tagging_helper.models.diff import (
	DatasetDiff, AppendDiff, InsertDiff, MoveDiff, DeleteDiff, MutateTagDiff, BatchDiff
)

class HistoryAction:
	"""
	履歴管理のためのアクション基底クラス。
	順方向の操作（Do）と逆方向の操作（Undo）を保持します。
	"""
	
	def __init__(self, dataset, forward, inverse):
		"""
		Args:
			dataset (Dataset): 操作対象のデータセット。
			forward (DatasetDiff): 順方向のDiff（Do用）。
			inverse (DatasetDiff): 逆方向のDiff（Undo用）。
		"""
		self.dataset = dataset
		self.forward = forward
		self.inverse = inverse
	
	def apply(self, sender: str = None):
		"""
		アクションを適用します（Redo）。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		self.dataset.apply_diff(sender, self.forward)
	
	def revert(self, sender=None):
		"""
		アクションを取り消します（Undo）。
		
		Args:
			sender (str): 操作の送信元ID。
		"""
		self.dataset.apply_diff(sender, self.inverse)

class InsertBlankAction(HistoryAction):
	"""
	空のタグを挿入するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, position):
		"""
		空タグ挿入アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			position (int): 挿入位置。
		"""
		forward = InsertDiff(
			target=target, position=position, tags=(Tag(),),
		)
		inverse = DeleteDiff(
			target=target, positions=(position,),
		)
		return InsertBlankAction(dataset, forward, inverse)

class AppendTagsAction(HistoryAction):
	"""
	タグを末尾に追加するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, tags):
		"""
		タグ追加アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			tags (tuple[Tag, ...]): 追加するタグのリスト。
		"""
		caption = dataset[target].caption
		position = len(caption.tags)
		ins_positions = range(position, position + len(tags))
		forward = AppendDiff(
			target=target, tags=tags,
		)
		inverse = DeleteDiff(
			target=target, positions=tuple(reversed(ins_positions))
		)
		return AppendTagsAction(dataset, forward, inverse)

class InsertTagsAction(HistoryAction):
	"""
	タグを指定位置に挿入するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, position, tags):
		"""
		タグ挿入アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			position (int): 挿入位置。
			tags (tuple[Tag, ...]): 挿入するタグのリスト。
		"""
		ins_positions = range(position, position + len(tags))
		forward = InsertDiff(
			target=target, position=position, tags=tags,
		)
		inverse = DeleteDiff(
			target=target, positions=tuple(reversed(ins_positions))
		)
		return InsertTagsAction(dataset, forward, inverse)

class MoveTagAction(HistoryAction):
	"""
	タグを移動するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, old_position, new_position):
		"""
		タグ移動アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			old_position (int): 移動元の位置。
			new_position (int): 移動先の位置。
		"""
		forward = MoveDiff(
			target=target, old_position=old_position, new_position=new_position,
		)
		inverse = MoveDiff(
			target=target, old_position=new_position, new_position=old_position,
		)
		return MoveTagAction(dataset, forward, inverse)

class DeleteTagsAction(HistoryAction):
	"""
	タグを削除するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, positions):
		"""
		タグ削除アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			positions (tuple[int, ...]): 削除するタグの位置のリスト。
		"""
		positions = sorted(positions)
		caption = dataset[target].caption
		tags = [caption.tags[i] for i in positions]
		forward = DeleteDiff(
			target=target, positions=tuple(reversed(positions)),
		)
		inverse = BatchDiff(tuple(
			InsertDiff(target, i, (tag,)) for i, tag in zip(positions, tags)
		))
		return DeleteTagsAction(dataset, forward, inverse)

class EditTagAction(HistoryAction):
	"""
	タグの内容を変更するアクション。
	"""
	
	@staticmethod
	def create(dataset, target, position, new_tag):
		"""
		タグ変更アクションを生成します。
		
		Args:
			dataset (Dataset): 対象データセット。
			target (int): 対象キャプションインデックス。
			position (int): 変更するタグの位置。
			new_tag (Tag): 新しいタグの内容。
		"""
		caption = dataset[target].caption
		old_tag = caption.tags[position]
		forward = MutateTagDiff(
			target=target, position=position, new_tag=new_tag,
		)
		inverse = MutateTagDiff(
			target=target, position=position, new_tag=old_tag,
		)
		return EditTagAction(dataset, forward, inverse)

class CleanAction(HistoryAction):
	"""
	データセット内の不要なタグ（空文字や重複）を削除するアクション。
	"""
	
	@staticmethod
	def create(dataset):
		"""
		クリーンアップアクションを生成します。
		空文字のタグや、同一キャプション内で重複しているタグを削除します。
		
		Args:
			dataset (Dataset): 対象データセット。
			
		Returns:
			CleanAction | None: 削除対象がない場合はNoneを返します。
		"""
		deletions = []
		for t, item in enumerate(dataset):
			seen = set()
			# 削除対象のインデックスを保存するリスト
			to_delete_indices = []
			for i, tag in enumerate(item.caption.tags):
				if tag.text != '' and tag.text not in seen:
					seen.add(tag.text)
				else:
					to_delete_indices.append(i)
			
			if to_delete_indices:
				# 削除アクションを作成
				# 複数のインデックスを一度に削除するアクションを生成
				action = DeleteTagsAction.create(dataset, t, tuple(to_delete_indices))
				deletions.append(action)
		
		if not deletions:
			return None
		
		# 複数のキャプションにまたがる変更をまとめる
		forward_children = []
		inverse_children = []
		for action in reversed(deletions):
			forward_children.append(action.forward)
			inverse_children.append(action.inverse)
		
		forward = BatchDiff(children=tuple(forward_children))
		inverse = BatchDiff(children=tuple(reversed(inverse_children)))
		
		return CleanAction(dataset, forward, inverse)

class BatchAppendTagAction(HistoryAction):
	"""
	複数のキャプションにタグを追加するアクション。
	"""
	
	@staticmethod
	def create(dataset, targets, tags: tuple['Tag', ...]):
		forward_children = []
		inverse_children = []
		for target_idx in targets:
			caption = dataset[target_idx].caption
			
			# 既存のタグテキストをセットとして保持
			existing_tag_texts = { t.text for t in caption.tags }
			# 追加対象のタグのうち、まだ存在しないものだけをフィルタリング
			tags_to_add = tuple(tag for tag in tags if tag.text not in existing_tag_texts)
			
			if tags_to_add:
				position = len(caption.tags)
				forward_children.append(AppendDiff(target=target_idx, tags=tags_to_add))
				
				delete_positions = range(position, position + len(tags_to_add))
				inverse_children.append(DeleteDiff(target=target_idx, positions=tuple(reversed(delete_positions))))
		
		if not forward_children:
			return None
		
		forward = BatchDiff(children=tuple(forward_children))
		inverse = BatchDiff(children=tuple(reversed(inverse_children)))
		return BatchAppendTagAction(dataset, forward, inverse)

class BatchRemoveTagAction(HistoryAction):
	"""
	複数のキャプションから特定のタグを削除するアクション。
	"""
	
	@staticmethod
	def create(dataset, targets, tag_texts: tuple[str, ...]):
		deletions = []
		tag_texts_set = set(tag_texts)
		for target_idx in targets:
			caption = dataset[target_idx].caption
			to_delete_indices = [i for i, tag in enumerate(caption.tags) if tag.text in tag_texts_set]
			if to_delete_indices:
				action = DeleteTagsAction.create(dataset, target_idx, tuple(to_delete_indices))
				deletions.append(action)
		
		if not deletions:
			return None
		
		forward_children = []
		inverse_children = []
		for action in reversed(deletions):
			forward_children.append(action.forward)
			inverse_children.append(action.inverse)
		
		forward = BatchDiff(children=tuple(forward_children))
		inverse = BatchDiff(children=tuple(reversed(inverse_children)))
		return BatchRemoveTagAction(dataset, forward, inverse)

class BatchReplaceTagAction(HistoryAction):
	"""
	複数のキャプション内の特定のタグを置換するアクション。
	"""
	
	@staticmethod
	def create(dataset, targets, old_tag_text, new_tag, keep_weight=False):
		forward_children = []
		inverse_children = []
		for target_idx in targets:
			caption = dataset[target_idx].caption
			for i, old_tag in enumerate(caption.tags):
				if old_tag.text == old_tag_text:
					tag_to_insert = Tag(text=new_tag.text, weight=old_tag.weight) if keep_weight else new_tag
					forward_children.append(MutateTagDiff(target=target_idx, position=i, new_tag=tag_to_insert))
					inverse_children.append(MutateTagDiff(target=target_idx, position=i, new_tag=old_tag))
		
		if not forward_children:
			return None
		
		forward = BatchDiff(children=tuple(forward_children))
		inverse = BatchDiff(children=tuple(reversed(inverse_children)))
		return BatchReplaceTagAction(dataset, forward, inverse)
