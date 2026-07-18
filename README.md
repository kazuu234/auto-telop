# Auto Telop

動画を渡すだけで自動テロップ。Whisperで文字起こし → 校閲 → Final Cut Pro用のFCPXMLを出力します。

**Mac / Windows対応のGUIアプリ**として動作します。アプリを起動し、動画をドラッグ&ドロップするだけ。ターミナルもブラウザも不要です。Mac版は従来どおり `AutoTelop.app`、Windows版は新たに `AutoTelop-win.zip`（Releasesからビルド済みzipを入手、または `build_windows.bat` で自分でビルド）で提供します。

## 全体の流れ

```
アプリ起動 → 動画をドロップ → 自動でテロップ抽出 → 一覧から選んで校閲 → 出力形式を選んで保存
```

- 複数の動画をまとめてドロップすると、順番に抽出されて一覧（ライブラリ）に並びます。
- アプリを閉じて再度開いても、以前のエントリーはそのまま残ります。
- **出力形式を選べます**：Final Cut Pro (FCPXML) / SRT字幕 / WebVTT。Premiere Pro や Filmora など他の編集ソフトにも対応。
- 保存時に出力先フォルダ・ファイル名を選べます。
- アプリ内から新しいバージョンの確認・ダウンロードができます。

---

## アプリ版を使う（推奨）

### 使い方

1. **AutoTelop.app** を起動する
2. ウィンドウに動画をドラッグ&ドロップ（または「＋ 動画を選択」をクリック）
3. 抽出が終わると、ライブラリに動画エントリーが追加される
4. エントリーをクリックすると校閲画面に移動
5. テロップを校閲したら、**出力形式を選んで**「💾 保存」→ 保存先を選ぶ
6. 出力ファイルを編集ソフトに読み込む（FCPXML→Final Cut Pro / SRT・VTT→Premiere・Filmora 等）

抽出中も別の動画を追加できます。複数動画は1本ずつ順番に処理されます。

### アプリのビルド（配布用 .app を作る）

配布用のビルド済みアプリは GitHub Releases から入手できます。自分でビルドする場合：

```bash
cd ~/auto-telop
./build_macos.sh
```

`dist/AutoTelop.app` が生成されます。`ffmpeg` はアプリに同梱されないため、利用環境に `brew install ffmpeg` で入れておいてください。Whisperのモデルは初回起動時に自動ダウンロードされます（`~/.cache/whisper`）。

> **「壊れているため開けません」と出る場合：** 署名していないアプリのため、ダウンロード直後は macOS の検疫属性で起動がブロックされます。配布zipに同梱の `初回セットアップ.command` を実行すると解除できます（初回のみ）。macOS 15以降はダブルクリック後に**システム設定 → プライバシーとセキュリティ →「このまま開く」**での承認が必要です（詳細は「よくあるトラブル」参照）。

### アプリの更新

アプリ右上の「更新を確認」ボタンで、GitHub Releases の最新版を確認できます。新しいバージョンがあれば「ダウンロード」でダウンロードフォルダに保存されるので、既存のアプリと置き換えてください。

---

## Windows版を使う

### 必要なもの

- **Windows 10 / 11**
- **FFmpeg**（動画の解析に使います）
- **WebView2ランタイム**（Windows 11 は標準搭載。Windows 10 は未導入の場合のみ、[Microsoft公式](https://developer.microsoft.com/microsoft-edge/webview2/)から導入してください）
- Final Cut Pro は Mac専用アプリのため、Windowsでは出力形式に **SRT / WebVTT** を選び、Premiere Pro / Filmora など対応編集ソフトに読み込んでください（FCPXMLはFinal Cut Pro向けのため利用できません）

### FFmpegをインストールする

```powershell
winget install ffmpeg
```

`choco install ffmpeg` や `scoop install ffmpeg` でも構いません。`media_env.py` が winget / chocolatey / scoop の主要インストール先を自動で探索するので、通常は追加のPATH設定は不要です。

### 使い方

1. GitHub Releases から **AutoTelop-win.zip** をダウンロードして展開する
2. `AutoTelop.exe` をダブルクリックで起動する
3. 「WindowsによってPCが保護されました」と表示されたら、**「詳細情報」→「実行」** をクリックする（署名していないアプリのためのSmartScreen警告です。Macの初回セットアップ`.command`のような別途の儀式は不要で、この操作だけでOKです）
4. 以降の使い方はMac版と同じ（動画をドロップ → 抽出 → 校閲 → 出力形式を選んで保存）

### アプリのビルド（配布用 .exe を作る）

配布用のビルド済みzipは GitHub Releases から入手できます。自分でビルドする場合（Windows実機・Python 3.9以上が必要）：

```bat
cd auto-telop
build_windows.bat
```

`dist\AutoTelop\AutoTelop.exe` と `dist\AutoTelop-win.zip` が生成されます。

---

## 開発者向け：ソースから実行する

ビルドせずにソースから動かす場合の手順です（従来のCLIも利用できます）。以下はソースから実行・ビルドする場合に必要なものです。アプリ版（`AutoTelop.app`）を使うだけなら、FFmpeg・Final Cut Pro・空きディスクだけで動きます。

### 必要なもの（ソースから実行・ビルドする場合）

- **Mac**（macOS 12以降を推奨）
- **Git**（プロジェクトのダウンロードに使います）
- **Python 3.9以上**
- **FFmpeg**（動画の解析に使います）
- **Final Cut Pro**（FCPXMLのインポート先）
- ディスク空き容量 **3GB以上**（Whisperモデル用）

### 環境セットアップ

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

## 出力する（FCP / Premiere / Filmora など）

校閲画面のツールバーで**出力形式を選んでから**「💾 保存」を押します。前回選んだ形式・保存先が次回の初期値になります。

| 形式 | 用途 | スタイル |
|---|---|---|
| **Final Cut Pro (FCPXML)** | Final Cut Pro | フォント・サイズ・縁取り・位置まで**そのまま反映**（従来どおり） |
| **SRT字幕** | Premiere Pro / Filmora / DaVinci など幅広い編集ソフト | テキスト＋タイミングのみ。見た目は**各ソフト側で設定** |
| **WebVTT** | Premiere Pro など | テキスト＋タイミング＋**おおまかな位置**。見た目は各ソフト側で設定 |

> **SRT/VTTのスタイルについて：** SRT/VTT は字幕ファイルのため、フォントや縁取りなどの見た目情報は持ちません（VTTは縦位置のみ反映）。読み込んだ編集ソフト側で、キャプションのフォント・サイズ・縁取り・位置を一度設定すれば全テロップに一括適用できます。Auto Telopのテロップは全行同じスタイルなので、初回だけ設定すればOKです。

### Final Cut Pro に読み込む（FCPXML）

1. Final Cut Pro を開く
2. メニュー → **ファイル → 読み込む → XML...**
3. 出力したFCPXMLファイルを選択
4. タイムラインにテロップ付き動画が読み込まれる（フォント・位置まで反映済み）

### Premiere Pro / Filmora に読み込む（SRT / VTT）

1. 映像を編集ソフトのタイムラインに配置する
2. 出力した **SRT（Filmoraは主にSRT）** または **VTT** を字幕/キャプションとして読み込む
   - Premiere Pro：キャプション（テキスト）として読み込み、キャプショントラックのスタイルでフォント・位置を設定
   - Filmora：SRTを字幕として読み込み
3. 必要に応じて、編集ソフト側でフォント・サイズ・縁取り・位置を設定（初回のみ）

> 保存先は、アプリ版/`python desktop.py` では保存ダイアログで選べます。ブラウザ版（`python app.py`）で保存先未指定の場合は**デスクトップ**に出力されます。

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

## フォントについて

デフォルト設定のフォントは **Noto Sans JP**（日本語）と **Inter**（英語）です。これらが未インストールの場合、自動的に **ヒラギノ角ゴシック W7**（日本語）と **Helvetica Neue Bold**（英語）で出力します（macOS標準フォントなので必ず表示されます）。

指定通りの Noto Sans JP / Inter を使いたい場合は、以下からダウンロードしてインストールしてください（ttfファイルをダブルクリック →「インストール」）。

- [Noto Sans JP（Google Fonts）](https://fonts.google.com/noto/specimen/Noto+Sans+JP)
- [Inter（Google Fonts）](https://fonts.google.com/specimen/Inter)

> **重要：** Final Cut Proは、FCPXMLで指定されたフォントが未インストールだと**テロップのスタイル全体を破棄して6ptで表示**するため、テロップが見えなくなります。本ツールのフォールバックはこれを防ぐためのものです。

## よくあるトラブル

### テロップが画面に表示されない／異常に小さい

指定フォントが未インストールの環境で古いバージョン（v1.0.2以前）で書き出したFCPXMLの症状です。v1.0.3以降で書き出し直してください（インストール済みフォントに自動フォールバックします）。

### アプリが「壊れているため開けません」と表示される

署名していないアプリのため、macOSの検疫属性（`com.apple.quarantine`）で起動がブロックされている状態です。以下の手順で解消できます。

> **画面写真つきの手順はこちら → [セットアップガイド](https://kazuu234.github.io/auto-telop/install_guide.html)**

1. ダウンロードした `AutoTelop-mac.zip` を展開する
2. `AutoTelop.app` をアプリケーションフォルダ（または任意の場所）へ移動する
3. 同じフォルダにある `初回セットアップ.command` を**ダブルクリック**する →「開けません」と出たらOKで閉じる
4. **システム設定 → プライバシーとセキュリティ** を開き、下の方にある「**"初回セットアップ.command"の使用がブロックされました**」の横の「**このまま開く**」をクリック → パスワード/Touch IDで承認
5. ターミナルに `[OK] 完了しました！` と表示されたら、`AutoTelop.app` をダブルクリックで起動できます

> **補足：** macOS 14以前では、手順3の代わりに `初回セットアップ.command` を**右クリック →「開く」→「開く」**でも実行できます（macOS 15以降ではこのバイパスは廃止され、システム設定での承認が必要です）。
>
> `初回セットアップ.command` は、内部で `xattr -cr AutoTelop.app` を実行して検疫属性を取り除いているだけの安全なスクリプトです。手動で解消する場合はターミナルで `xattr -cr /Applications/AutoTelop.app` を実行してもOKです。

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

### （Windows）SmartScreenの警告が出る

未署名のアプリのためです。「詳細情報」→「実行」をクリックすれば起動できます。

### （Windows）ffmpegが見つからない

`winget install ffmpeg` などでインストールした直後は、既に起動中のアプリにPATHの変更が反映されないことがあります。**アプリを再起動**してください。

### （Windows）ウィンドウが真っ白・開かない

WebView2ランタイムが未導入の可能性があります。[Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)を導入してください（Windows 11では標準搭載）。
