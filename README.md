Jリーグ試合スケジュールのicsファイルを作成するpythonスクリプトです。  
icsファイル対応のカレンダーに読み込ませることができます。  
また、 **前日(21時間前)にメール通知、3時間前にポップアップ通知されます**（なお、時刻未定の場合は終日予定で登録されます。日付も未定の場合は登録されません）。

## 環境設定

Linuxで動作確認済みです。他のOSは適宜読み替えて下さい。

```bash
git clone https://github.com/takahashimasaki4biz/j-schedule-ics-maker.git
cd j-schedule-ics-maker
chmod +x j-schedule-ics-maker.py
python3 -m venv .venv
. .venv/bin/activate
pip3 install -r requirements.txt
deactivate
```

## icsファイルを作成／更新する

```bash
cd j-schedule-ics-maker
. .venv/bin/activate
./j-schedule-ics-maker.py 2025
```

しばらく待つと、all-clubs-icsフォルダ内にJ全クラブのicsファイルが生成されているはずです。  

## icsファイルを作成しカレンダーに設定／再設定する

お好みのファイルをicsファイル対応のカレンダーに読み込ませて下さい（それぞれ手順が違うと思うので詳しく書きません）。

最後に下記でpython仮想環境を後始末します。

```bash
deactivate
exit
```

## その他

何かうまくいかった場合は、カレンダーを削除＆再作成して、やりなおして下さい
（なので、専用のカレンダーを作った方が良いでしょう。まるごと削除して、再作成すれば良いです）。
