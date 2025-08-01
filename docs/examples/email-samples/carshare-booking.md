# カーシェア予約メールサンプル

## Times Car 予約完了メール

### 件名
```
【タイムズカー】ご利用開始のお知らせ [予約番号: TC123456]
```

### メール本文例
```
山田太郎 様

タイムズカーのご予約が完了いたしました。

■ 予約番号: TC123456
■ 利用者: 山田太郎
■ ステーション: 新宿駅南口ステーション
■ 住所: 東京都新宿区新宿3-1-1

■ 利用時間
開始: 2024年1月10日 14:00
終了: 2024年1月10日 16:00

■ 車両
車種: プリウス
ナンバー: 品川500あ1234

ご利用の際は、会員カードをお忘れなくお持ちください。

タイムズカー
```

### 抽出されるデータ
```json
{
  "provider": "TIMES_CAR",
  "booking_reference": "TC123456",
  "user_name": "山田太郎",
  "station": {
    "station_name": "新宿駅南口ステーション",
    "address": "東京都新宿区新宿3-1-1"
  },
  "start_datetime": "2024-01-10T14:00:00",
  "end_datetime": "2024-01-10T16:00:00",
  "status": "RESERVED"
}
```

## Times Car 予約変更メール

### 件名
```
【タイムズカー】予約変更のお知らせ [予約番号: TC123456]
```

### メール本文例
```
山田太郎 様

ご予約内容が変更されました。

■ 予約番号: TC123456
■ 利用者: 山田太郎
■ ステーション: 新宿駅南口ステーション

■ 変更後利用時間
開始: 2024年1月10日 15:00（変更）
終了: 2024年1月10日 17:00（変更）

タイムズカー
```

### 抽出されるデータ
```json
{
  "provider": "TIMES_CAR",
  "booking_reference": "TC123456",
  "user_name": "山田太郎",
  "station": {
    "station_name": "新宿駅南口ステーション",
    "address": null
  },
  "start_datetime": "2024-01-10T15:00:00",
  "end_datetime": "2024-01-10T17:00:00",
  "status": "CHANGED"
}
```

## 三井のカーシェアーズ 予約メール

### 件名
```
【三井のカーシェアーズ】ご予約完了 [予約番号: MS789012]
```

### メール本文例
```
山田太郎 様

ご予約ありがとうございます。

■ 予約番号: MS789012
■ 会員名: 山田太郎
■ ステーション名: 渋谷センター街ステーション

■ ご利用予定
利用開始: 2024年1月12日 10:00
利用終了: 2024年1月12日 12:00

■ 車両情報
車種: アクア
ナンバー: 品川500あ5678

三井のカーシェアーズ
```

### 抽出されるデータ
```json
{
  "provider": "MITSUI_CARSHARE",
  "booking_reference": "MS789012",
  "user_name": "山田太郎",
  "station": {
    "station_name": "渋谷センター街ステーション",
    "address": null
  },
  "start_datetime": "2024-01-12T10:00:00",
  "end_datetime": "2024-01-12T12:00:00",
  "status": "RESERVED"
}
```

## カーシェア キャンセルメール

### 件名
```
【タイムズカー】予約キャンセルのお知らせ [予約番号: TC123456]
```

### メール本文例
```
山田太郎 様

下記のご予約がキャンセルされました。

■ 予約番号: TC123456
■ 利用者: 山田太郎
■ ステーション: 新宿駅南口ステーション

■ キャンセル対象
開始: 2024年1月10日 15:00
終了: 2024年1月10日 17:00

キャンセル料金は発生いたしません。

タイムズカー
```

### 抽出されるデータ
```json
{
  "provider": "TIMES_CAR",
  "booking_reference": "TC123456",
  "user_name": "山田太郎",
  "station": {
    "station_name": "新宿駅南口ステーション",
    "address": null
  },
  "start_datetime": "2024-01-10T15:00:00",
  "end_datetime": "2024-01-10T17:00:00",
  "status": "CANCELLED"
}
```

## 時間重複解決の動作例

### シナリオ
同一ステーション・同時間帯での予約変更

1. **初回予約**: TC123456, 14:00-16:00 → 新規予定作成 🚗
2. **予約変更**: TC123456, 15:00-17:00 → 既存予定更新 🔄
3. **キャンセル**: TC123456, 15:00-17:00 → 予定削除 ❌

### 重複検出ロジック
1. 予約番号での既存予定検索
2. 同一ステーション・時間重複の検出
3. 新しい予約で既存予定を置き換え

### カレンダーイベント例

#### 予約時
```
タイトル: 🚗 新宿駅南口ステーション
時間: 2024年1月10日 14:00-16:00
説明:
タイムズカー利用予約
予約番号: TC123456
利用者: 山田太郎
ステーション: 新宿駅南口ステーション
住所: 東京都新宿区新宿3-1-1
ステータス: 予約済み
```

#### 変更時
```
タイトル: 🔄 新宿駅南口ステーション
時間: 2024年1月10日 15:00-17:00
説明:
タイムズカー利用予約（変更済み）
予約番号: TC123456
利用者: 山田太郎
ステーション: 新宿駅南口ステーション
ステータス: 変更済み
```

#### キャンセル時
```
イベント削除
```

## プロモーションメール例（自動除外）

### 除外される件名例
```
【タイムズカー】キャンペーン実施中！
【三井のカーシェアーズ】お得な料金プランのご案内
カーシェア新規入会特典のお知らせ
メンテナンスのお知らせ
```

### 除外理由
- キーワード「キャンペーン」「お知らせ」「特典」「メンテナンス」を含む
- スマートフィルタリングにより OpenAI API 呼び出し前に除外
- ログには「Skipped promotional email」として記録

## ステータス管理

### ステータス遷移
```
RESERVED (予約済み) 🚗
    ↓ 予約変更
CHANGED (変更済み) 🔄
    ↓ キャンセル
CANCELLED (キャンセル済み) ❌
    ↓ 利用完了（手動設定）
COMPLETED (利用完了) ✅
```

### カレンダー表示での絵文字
- 🚗 予約済み
- 🔄 変更済み
- ❌ キャンセル済み
- ✅ 利用完了

### 同時刻重複の処理
物理的制約により、同一ステーション・同時刻の予約は不可能なため：
1. 時系列で新しいメールが既存予約を自動的に置き換え
2. キャンセルの場合は予定を削除
3. 重複検出ログで処理状況を追跡
