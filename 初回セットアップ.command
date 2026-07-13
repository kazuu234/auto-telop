#!/bin/bash
#
# AutoTelop 初回セットアップ
# ダウンロードしたアプリが「壊れている」と表示される問題を解消します。
# （macOSの検疫属性 com.apple.quarantine を取り除きます）
#
# 使い方：このファイルをダブルクリックするだけ。
#

# このスクリプトが置かれているフォルダへ移動
cd "$(dirname "$0")" || exit 1

echo "========================================"
echo " AutoTelop 初回セットアップ"
echo "========================================"
echo ""
echo "アプリの検疫属性を取り除いています..."
echo ""

FOUND=0

# 探す場所のリスト（同じフォルダ内、アプリケーション、ダウンロード、デスクトップ）
for DIR in "." "/Applications" "$HOME/Downloads" "$HOME/Desktop"; do
    APP="$DIR/AutoTelop.app"
    if [ -d "$APP" ]; then
        xattr -cr "$APP"
        echo "[OK] $APP を処理しました"
        FOUND=1
    fi
done

echo ""
if [ "$FOUND" -eq 1 ]; then
    echo "[OK] 完了しました！"
    echo ""
    echo "AutoTelop.app をダブルクリックで起動できます。"
else
    echo "[!!] AutoTelop.app が見つかりませんでした。"
    echo ""
    echo "このファイルと同じフォルダに AutoTelop.app を置くか、"
    echo "AutoTelop.app をアプリケーションフォルダに移動してから、"
    echo "もう一度このファイルをダブルクリックしてください。"
fi

echo ""
echo "このウィンドウは閉じて構いません。"
echo "========================================"
