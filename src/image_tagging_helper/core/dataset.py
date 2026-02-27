from collections import defaultdict, Counter
from typing import List, Dict

from src.image_tagging_helper.core.caption import Caption

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
			caption_path: str,
			caption: Caption | None = None,
	):
		"""
		DatasetItemのコンストラクタ。

		Args:
			  path: 画像ファイルのパス。
			  caption: 画像に関連付けられたキャプション。指定されない場合は空のCaptionが作成される。
		"""
		self.image_path = image_path
		self.caption_path = caption_path
		self.caption = caption or Caption()

class Dataset:
	"""
	DatasetItemのコレクションを管理するクラス。

	Attributes:
		  items (List[DatasetItem]): データセットに含まれるDatasetItemのリスト。
		  item_index (dict[str, int]): ファイルパスをキーとし、itemsリストのインデックスを値とする辞書。
	"""
	
	def __init__(self, items: List[DatasetItem]):
		"""
		Datasetのコンストラクタ。

		Args:
			  items: データセットに含めるDatasetItemのリスト。
		"""
		self.items = items
		self.item_index = { x.image_path: i for i, x in enumerate(items) }
	
	def __len__(self) -> int:
		"""データセットのサイズ（含まれるアイテム数）を返す。"""
		return len(self.items)
	
	def __getitem__(self, index: int | slice) -> DatasetItem | List[DatasetItem]:
		"""インデックスまたはスライスでDatasetItemを取得する。"""
		return self.items[index]
	
	def get_all_tags_with_counts(self) -> Dict[str, int]:
		"""
		データセット内のすべてのタグとその出現回数を取得します。
		
		Returns:
			Dict[str, int]: タグ名をキー、出現回数を値とする辞書。
		"""
		all_tags: Counter[str] = Counter()
		for item in self.items:
			for tag, cnt in item.caption.counter.items():
				if cnt > 0:
					all_tags[tag.text] += 1
		return dict(all_tags)
