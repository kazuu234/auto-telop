# Auto Telop

動画を渡すだけで自動テロップ。Whisperで文字起こし → 校閲 → Final Cut Pro用のFCPXMLを出力します。

**Mac用のGUIアプリ**として動作します。アプリを起動し、動画をドラッグ&ドロップするだけ。ターミナルもブラウザも不要です。

## 全体の流れ

```
アプリ起動 → 動画をドロップ → 自動でテロップ抽出 → 一覧から選んで校閲 → 保存先を選んでFCPXML出力
```

- 複数の動画をまとめてドロップすると、順番に抽出されて一覧（ライブラリ）に並びます。
- アプリを閉じて再度開いても、以前のエントリーはそのまま残ります。
- 保存時に出力先フォルダ・ファイル名を選べます。
- アプリ内から新しいバージョンの確認・ダウンロードができます。

---

## アプリ版を使う（推奨）

### 使い方

1. **AutoTelop.app** を起動する
2. ウィンドウに動画をドラッグ&ドロップ（または「＋ 動画を選択」をクリック）
3. 抽出が終わると、ライブラリに動画エントリーが追加される
4. エントリーをクリックすると校閲画面に移動
5. テロップを校閲したら「💾 保存」→ 保存先を選ぶ → FCPXML出力
6. 出力したFCPXMLを Final Cut Pro に読み込む（ファイル → 読み込む → XML...）

抽出中も別の動画を追加できます。複数動画は1本ずつ順番に処理されます。

### アプリのビルド（配布用 .app を作る）

配布用のビルド済みアプリは GitHub Releases から入手できます。自分でビルドする場合：

```bash
cd ~/auto-telop
./build_macos.sh
```

`dist/AutoTelop.app` が生成されます。`ffmpeg` はアプリに同梱されないため、利用環境に `brew install ffmpeg` で入れておいてください。Whisperのモデルは初回起動時に自動ダウンロードされます（`~/.cache/whisper`）。

> **Gatekeeperの警告：** 署名していないアプリは初回起動時に警告が出ます。アプリを右クリック →「開く」→ 確認、で起動できます。

### アプリの更新

アプリ右上の「更新を確認」ボタンで、GitHub Releases の最新版を確認できます。新しいバージョンがあれば「ダウンロード」でダウンロードフォルダに保存されるので、既存のアプリと置き換えてください。

---

## 開発者向け：ソースから実行する

ビルドせずにソースから動かす場合の手順です（従来のCLIも利用できます）。

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

openai-whisper, flask, ffmpeg-python, pyyaml, pywebview がインストールされます。
初回は Whisper のモデルダウンロード（約1.5GB）が入るため数分かかります。

> **注意：** 2回目以降の利用時も、先に `cd ~/auto-telop && source venv/bin/activate` を実行してから使ってください。

### GUIアプリとしてソースから起動する

ビルドせずにGUIアプリを起動するには：

```bash
cd ~/auto-telop
source venv/bin/activate
python desktop.py
```

ネイティブウィンドウが開きます。以降の使い方はアプリ版と同じ（動画をドロップ → 抽出 → 校閲 → 保存）です。

### ブラウザ版として起動する（従来方式）

`python app.py` で Flask サーバーを起動し、ブラウザで `http://localhost:5050` を開くこともできます。この場合、ネイティブのファイル選択ダイアログが使えないため、動画の追加はフルパスを入力する形になります。CLI（下記）で先に文字起こししておく方式もそのまま使えます。

## 動画を文字起こしする（CLI）

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

保存ボタンを押すと、FCPXMLファイルが出力されます。

- **アプリ版 / `python desktop.py`**：保存時に**保存先フォルダ・ファイル名を選べます**。前回選んだフォルダが次回の初期値になります。
- **ブラウザ版（`python app.py`）**：保存先を指定しない場合は従来どおり**デスクトップ**に出力されます。

```
例) ~/Desktop/買ってよかった_テロップ付き_0713_1430.fcpxml
```

このファイルをFinal Cut Proで開く手順：

1. Final Cut Pro を開く
2. メニュー → **ファイル → 読み込む → XML...**
3. 出力したFCPXMLファイルを選択
4. タイムラインにテロップ付き動画が読み込まれる

FCP上でテロップの位置やスタイルをさらに微調整できます。

## 設定をカスタマイズする

初回起動時に `config.default.yaml` から `config.yaml` が自動生成されます。`config.yaml` を編集してカスタマイズしてください（このファイルは git 管理外なので `git pull` で競合しません）。

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

### アプリ版

アプリ右上の「更新を確認」ボタンから、GitHub Releases の最新版をチェックできます。新しいバージョンがあれば「ダウンロード」でダウンロードフォルダに保存されるので、既存のアプリと差し替えてください。バージョン番号は `VERSION` ファイルで管理されています。

### ソースから実行している場合

```bash
cd ~/auto-telop
git pull
source venv/bin/activate
pip install -r requirements.txt
```

> **補足：** `git pull` でコードを最新に取得し、`pip install` で新しく追加された依存ライブラリがあればインストールされます。既存のプロジェクトデータ（`projects/` フォルダ内）や `config.yaml` はそのまま残ります。

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
