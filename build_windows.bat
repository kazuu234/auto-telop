@echo off
chcp 65001 >nul
REM Auto Telop Windows ビルドスクリプト
REM 使い方: build_windows.bat  (Windows実機で実行)
REM 出力: dist\AutoTelop\AutoTelop.exe と dist\AutoTelop-win.zip

if not exist venv (
  echo ==^> Creating virtualenv
  python -m venv venv
  if errorlevel 1 (
    echo ERROR: venv creation failed
    exit /b 1
  )
)

call venv\Scripts\activate.bat

echo ==^> Installing dependencies
pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
  echo ERROR: dependency install failed
  exit /b 1
)
pip install pyinstaller -q

echo ==^> Cleaning previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo ==^> Building AutoTelop
pyinstaller AutoTelop.spec --noconfirm
if errorlevel 1 (
  echo ERROR: pyinstaller build failed
  exit /b 1
)

echo ==^> Creating distribution zip
powershell -Command "Compress-Archive -Path 'dist\AutoTelop' -DestinationPath 'dist\AutoTelop-win.zip' -Force"
if errorlevel 1 (
  echo ERROR: zip creation failed
  exit /b 1
)

echo.
echo Done. App is at: dist\AutoTelop\AutoTelop.exe
echo Distribution zip: dist\AutoTelop-win.zip
echo （アセット名 AutoTelop-win.zip は、アプリ内アップデータが名前に含まれる「win」で自動判別します）
echo.
echo 注意: 未署名のためSmartScreenの警告が出ます。「詳細情報」→「実行」で起動してください。
