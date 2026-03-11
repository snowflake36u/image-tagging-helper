# 開発者向けガイド

このドキュメントは Image Tag Editor の開発者向けの情報を提供します。

## 国際化 (i18n) / 翻訳

ソースコード内において、翻訳対象の文字列は `__("message_key")` のように `__()` 関数で囲むことで表します。`_()` の表記は、ダミー変数の表記 `_` と競合するため使用しません。

### 翻訳キーの命名規則

翻訳キー（`msgid`）は、`category:text_name` という形式の識別子で命名します。これにより、テキストがUIのどの部分で使用されるかを容易に把握できます。

#### カテゴリ(category)

カテゴリは、テキストがUIのどの部分でどのような役割を果たすかに基づいて、以下のように分類します。
メッセージのように性質で分類できるものは `.` を使って階層化します。

- **ui**: ユーザーインターフェースを構成する要素。
	| サブカテゴリ | 説明 | 例 |
	|:---| :--- | :--- |
	| `action` | ボタンやメニュー項目など、ユーザーが実行可能な操作を表すテキスト。通常、ニーモニックキーを含みます。 | `action:open_file="ファイルを開く(&O)"`, `action:save="保存(&O)"` |
	| `tooltip` | ボタンやアイコンの機能を説明する短いテキスト。ニーモニックキーは含みません。 | `tooltip:save="保存"`, `tooltip:add_item="項目の追加"` |
	| `ui_group` | メニュー項目のテキスト。 | `ui_group:file="ファイル(&F)"` |
	| `ui_option` | アクセラレータキーでアクセス可能な選択項目。 | `ui_option:show_all="すべて表示"` |
	| `label` | UI上の固定テキストや、データフィールドの見出し。 | `label:update_date="更新日時:"` |
	| `status` | 状態などを示す動的な短い表現。 | `status:loading="読み込み中"`, `status:n_items_selected="{n_selected}個の項目を選択"` |
	| `title` | ウィンドウやダイアログのタイトル。 | `title:language_change="言語の変更"` |

- **message**: ダイアログやステータスバーでユーザーに動的に通知するメッセージ。基本的に文章で構成されます。
	| サブカテゴリ | 説明 | 例 |
	|:--- | :--- | :--- |
	| `info` | 情報提供メッセージ | `info:about_app="このアプリケーションについて"` |
	| `error` | エラーメッセージ | `error:file_not_found="ファイルが見つかりません。"` |
	| `warn` | 警告メッセージ | `warn:icon_not_found="アイコンが見つかりません。"` |
	| `confirm` | 確認を求めるメッセージ | `confirm:restart_app="アプリケーションを再起動しますか？"` |

- **その他**:
	| サブカテゴリ | 説明 | 例 |
	| :--- | :--- | :--- |
	| `option`| 設定画面の選択肢など、ユーザーが選択可能な項目。 | `option:show_all="すべて表示"` |
	| `file_filter` | ファイルダイアログで使われるファイル形式のフィルタ。 | `file_filter:text_files="テキスト形式(*.txt)"` |

#### 名前(text_name)

名前の部分は、テキストの内容を簡潔に表す英語（スネークケース）で記述します。

### 翻訳ツールの使用方法

翻訳ファイルの管理には、`src/image_tag_editor/i18n/compiler.py` を使用します。
このツールは `pybabel` をラップしており、ソースコードからの文字列抽出、翻訳ファイルの更新、コンパイルを行います。

**基本的な使い方:**

```bash
python src/image_tag_editor/i18n/compiler.py <app_name> <command> [options]
```

* **`app_name`**: 対象のアプリケーション名（ドメイン名）。必須です。
* **`command`**: 実行する操作（以下参照）。

**主なコマンド:**

| コマンド             | エイリアス | 説明                                        |
|:-----------------|:------|:------------------------------------------|
| `init <locale>`  | `i`   | 指定した言語（例: `ja`）の新しい翻訳ファイル (`.po`) を作成します。 |
| `extract`        | `e`   | ソースコードから翻訳キーを抽出し、`.pot` ファイルを作成/更新します。    |
| `update`         | `u`   | `.pot` ファイルの内容を既存の `.po` ファイルに反映します。      |
| `extract+update` | `e+u` | `extract` と `update` を連続して実行します。          |
| `compile`        | `c`   | `.po` ファイルをバイナリ形式 (`.mo`) にコンパイルします。      |

**一般的なワークフロー:**

1. **ソースコードの変更**: `__("category:text_name")` の形式で記述。
2. **翻訳ファイルの更新**:
	 ```bash
	 python src/image_tag_editor/i18n/compiler.py <app_name> e+u
	 ```
3. **翻訳の編集**: 生成された `.po` ファイル (`src/image_tag_editor/i18n/locales/<lang>/LC_MESSAGES/<app_name>.po`) を編集。
4. **コンパイル**:
	 ```bash
	 python src/image_tag_editor/i18n/compiler.py <app_name> c
	 ```
