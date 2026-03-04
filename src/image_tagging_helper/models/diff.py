from dataclasses import dataclass
from abc import ABC

from image_tagging_helper.models.caption import Tag

@dataclass(frozen=True)
class DatasetDiff(ABC):
	"""
	データセットへの変更を表す基底クラス。
	全てのDiffクラスはこのクラスを継承します。
	"""
	pass

@dataclass(frozen=True)
class AppendDiff(DatasetDiff):
	"""
	タグの追加を表すDiff。
	対象のキャプションの末尾にタグを追加します。
	"""
	target: int
	tags: tuple[Tag, ...]

@dataclass(frozen=True)
class InsertDiff(DatasetDiff):
	"""
	タグの挿入を表すDiff。
	対象のキャプションの指定位置にタグを挿入します。
	"""
	target: int
	position: int
	tags: tuple[Tag, ...]

@dataclass(frozen=True)
class DeleteDiff(DatasetDiff):
	"""
	タグの削除を表すDiff。
	対象のキャプションから指定された位置のタグを削除します。
	"""
	target: int
	positions: tuple[int, ...]

@dataclass(frozen=True)
class MoveDiff(DatasetDiff):
	"""
	タグの移動を表すDiff。
	対象のキャプション内でタグの位置を変更します。
	"""
	target: int
	old_position: int
	new_position: int

@dataclass(frozen=True)
class MutateTagDiff(DatasetDiff):
	"""
	タグの内容変更を表すDiff。
	対象のキャプションの指定位置にあるタグを新しいタグに置換します。
	"""
	target: int
	position: int
	new_tag: Tag

@dataclass(frozen=True)
class BatchDiff(DatasetDiff):
	"""
	複数のDiffをまとめたDiff。
	複数の変更を一度に適用する場合に使用します。
	"""
	children: tuple[DatasetDiff, ...]
