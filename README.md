# Auto Telop

動画を渡すだけで自動テロップ。Whisperで文字起こし → ブラウザで校閲 → Final Cut Pro用のFCPXMLを出力します。

## 全体の流れ

```
動画ファイル → Whisper文字起こし → ブラウザで校閲・修正 → FCPXML出力
```

保存ボタンを押すと、テロップ付きのFCPXMLファイルがデスクトップに自動で出力されます。あとはFinal Cut Proにインポートするだけ。

## 必要なもの

- **Mac**（macOS 12以降を推奨）
- **Git**（プロジェクトのダウンロードに使います）
- **Python 3.9以上**
- **FFmpeg**（動画の解析に使います）
- **Final Cut Pro**（FCPXMLのインポート先）
- ディスク空き容量 **3GB以上**（Whisperモデル用）

## 環境セットアップ

ターミナル.app を開いて、以下を**上から順に**コピー＆ペーストして実行してください。

### Homebrewをインストール（まだの場合）

```bash
# Homebrewが入っているか確認
brew --version

# 入っていなければインストール（パスワードを聞かれます）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Git, Python, FFmpeg をインストール

```bash
brew install git python ffmpeg
```

### パスを通す

Homebrewで入れたPythonにパスが通っていない場合があります。以下を実行してください。

```bash
# zsh（macOSのデフォルト）の場合
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 確認（バージョンが表示されればOK）
python3 --version
```

### Auto Telop をダウンロード

```bash
cd ~
git clone https://github.com/kazuu234/auto-telop.git
cd auto-telop
```

### 仮想環境を作成してライブラリをインストール

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

openai-whisper, flask, ffmpeg-python, pyyaml がインストールされます。
初回は Whisper のモデルダウンロード（約1.5GB）が入るため数分かかります。

> **注意：** 2回目以降の利用時も、先に `cd ~/auto-telop && source venv/bin/activate` を実行してから使ってください。

## 動画を文字起こしする

テロップをつけたい動画ファイルのパスを指定して実行します。

```bash
cd ~/auto-telop
python transcribe.py ~/Desktop/買ってよかった.mp4
```

出力例：

```
Transcribing with Whisper (medium)...
Raw segments: 134
Refined segments: 365 (silence gaps: 53)
Average: 19 chars / 2.9s per segment

Project ready: projects/買ってよかった
Open http://localhost:5050 to edit
```

> **処理時間の目安：** 18分の動画で約5〜15分（PCスペックにより変動）。GPUがあるMacなら速くなります。

## Webエディタで校閲する

文字起こしが終わったら、Webエディタを起動します。

```bash
python app.py
```

ブラウザで `http://localhost:5050` を開くとエディタが表示されます。

### エディタの使い方

| 操作 | 説明 |
|---|---|
| **左：動画プレーヤー** | 動画を再生しながら、対応するテロップ行が自動ハイライトされます |
| **右：テロップ一覧** | 各行のテキストを直接編集できます。タイムスタンプ・CPS（文字/秒）も確認できます |
| **行をクリック** | その位置に動画がジャンプします。テキスト欄をクリックすれば直接編集 |
| **行のマージ** | Shift+クリックで複数行を選択 →「▶ マージ」ボタンで結合できます |

### 主な校閲作業

- Whisperの誤変換を修正する（例: monograph → モノグラフ）
- 短すぎる行をマージする
- 検索機能で特定の単語をまとめて確認する
- CPS（文字/秒）が高すぎる行は文を短くする

校閲が終わったら **「💾 保存」ボタン** を押してください。

## FCPにインポートする

保存ボタンを押すと、**デスクトップ**に以下のファイルが自動生成されます。

```
~/Desktop/買ってよかった_テロップ付き_0713_1430.fcpxml

# フォント: A P-OTF A1Gothic StdN / 35pt が適用済み
```

このファイルをFinal Cut Proで開く手順：

1. Final Cut Pro を開く
2. メニュー → **ファイル → 読み込む → XML...**
3. デスクトップのFCPXMLファイルを選択
4. タイムラインにテロップ付き動画が読み込まれる

FCP上でテロップの位置やスタイルをさらに微調整できます。

## 設定をカスタマイズする

`config.yaml` を編集すると、テロップのスタイルやWhisperの動作を変更できます。

```yaml
# テロップの見た目
style:
  font_name: "A P-OTF A1Gothic StdN"
  font_size: 35
  bold: true
  outline_width: 3

# Whisperの精度（large にすると精度↑ だが遅い）
whisper:
  model: "medium"   # tiny / base / small / medium / large
  language: "ja"

# セグメント分割の調整
segment:
  max_chars: 25     # 1行の最大文字数
  max_duration: 4.0 # 1セグメントの最大秒数
```

## アプリケーションの更新

新しいバージョンが公開されたら、以下のコマンドで更新できます。

```bash
cd ~/auto-telop
git pull
source venv/bin/activate
pip install -r requirements.txt
```

> **補足：** `git pull` でコードを最新に取得し、`pip install` で新しく追加された依存ライブラリがあればインストールされます。既存のプロジェクトデータ（`projects/` フォルダ内）はそのまま残ります。

## よくあるトラブル

### `command not found: python` と出る

`python3` に読み替えて実行してください。`pip` も `pip3` に変えてください。

### `ffprobe: command not found` と出る

FFmpegが入っていません。`brew install ffmpeg` を実行してください。

### Whisperの処理が非常に遅い

`config.yaml` の `whisper.model` を `"small"` や `"base"` に変えると速くなります（精度は少し落ちます）。

### 動画がエディタで再生されない

mp4形式以外の動画（.mov, .avi等）の場合、ブラウザが対応していない可能性があります。FFmpegでmp4に変換してから使ってください。

```bash
ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4
```

### ポート5050が使えない

`app.py` の最後の行にあるポート番号を変更してください（例: 5051）。
