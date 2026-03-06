import argparse
import io
import os.path

import cairosvg
from PIL import Image

def convert_svg_to_ico(in_path, out_path, sizes):
	"""
	SVGファイルを複数のサイズを持つICOファイルに変換する関数

	Args:
		in_path: 入力するSVGファイルのパス (例: 'input.svg')
		out_path: 出力するICOファイルのパス (例: 'output.ico')
		sizes: 組み込みたい画像サイズのリスト (例: [16, 32, 48, 64, 256])
	"""
	# サイズを降順にソート（大きいサイズを先頭にするのが一般的）
	sizes = sorted(sizes, reverse=True)
	images = []
	
	try:
		# 指定されたすべてのサイズに対して処理を行う
		for size in sizes:
			# 1. SVGを特定のサイズのPNGとしてメモリ上に生成 (画質を保つため都度生成)
			png_data = cairosvg.svg2png(
				url=in_path,
				output_width=size,
				output_height=size
			)
			
			# 2. メモリ上のPNGデータをPillowのImageオブジェクトとして読み込む
			img = Image.open(io.BytesIO(png_data))
			# ストリームが閉じられる前にデータを読み込むためにload()を呼ぶ
			img.load()
			images.append(img)
		
		# 3. リストの最初の画像をベースにし、残りを追加画像としてICOに保存
		if images:
			# 最初の画像をベースにする
			base_img = images[0]
			base_img.save(
				out_path,
				format='ICO',
				sizes=[(img.width, img.height) for img in images],
				append_images=images[1:]
			)
			print(f"成功: '{out_path}' を作成しました。 (サイズ: {sizes})")
	
	except Exception as e:
		print(f"エラーが発生しました: {e}")

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('input')
	parser.add_argument('-o', '--output')
	parser.add_argument('-s', '--sizes', type=str, default='16,24,32,48,64')
	
	args = parser.parse_args()
	
	# 入力ファイルと出力ファイルの名前
	input_path = args.input
	
	if not args.output:
		output_path = os.path.splitext(input_path)[0] + '.ico'
	else:
		output_path = args.output
	
	sizes = [int(size) for size in args.sizes.split(',')]
	
	# 関数の実行
	convert_svg_to_ico(input_path, output_path, sizes)

if __name__ == "__main__":
	main()
