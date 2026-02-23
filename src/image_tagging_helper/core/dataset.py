from typing import List

from src.image_tagging_helper.core.caption import Caption

class DatasetItem:
	"""
	データセット内の個々の画像ファイルを表すクラス。

	Attributes:
		  path (str): 画像ファイルのパス。
		  caption (Caption): 画像に関連付けられたキャプション。
	"""
	
	def __init__(
			self,
			path: str,
			caption: Caption | None = None,
	):
		"""
		DatasetItemのコンストラクタ。

		Args:
			  path: 画像ファイルのパス。
			  caption: 画像に関連付けられたキャプション。指定されない場合は空のCaptionが作成される。
		"""
		self.path = path
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
		self.item_index = { x.path: i for i, x in enumerate(items) }
	
	def __len__(self) -> int:
		"""データセットのサイズ（含まれるアイテム数）を返す。"""
		return len(self.items)
	
	def __getitem__(self, index: int | slice) -> DatasetItem | List[DatasetItem]:
		"""インデックスまたはスライスでDatasetItemを取得する。"""
		return self.items[index]
