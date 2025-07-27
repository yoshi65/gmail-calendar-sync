# ANA 航空券予約メールサンプル

## ANA お支払い完了メール

### 件名
```
ANA ご予約確認 [確認番号: 887525617]
```

### メール本文例
```
山田太郎 様

この度は、ANAをご利用いただき、誠にありがとうございます。
以下の内容でご予約を承りました。

■ 確認番号: 887525617
■ 予約番号: 0709

■ 往路
便名: NH006
出発: 2024年1月15日 08:30 羽田空港(HND)
到着: 2024年1月15日 11:45 伊丹空港(ITM)
座席: 12A

■ 復路
便名: NH017
出発: 2024年1月20日 18:20 伊丹空港(ITM)
到着: 2024年1月20日 19:35 羽田空港(HND)
座席: 15C

■ 搭乗者
山田太郎

■ お支払い金額
合計: 28,000円

ご搭乗の際は、eチケットをお持ちください。

ANA
```

### 抽出されるデータ
```json
{
  "confirmation_code": "887525617",
  "booking_reference": "0709",
  "passenger_name": "山田太郎",
  "outbound_segments": [
    {
      "flight_number": "NH006",
      "departure_airport": "HND",
      "arrival_airport": "ITM",
      "departure_datetime": "2024-01-15T08:30:00",
      "arrival_datetime": "2024-01-15T11:45:00",
      "seat_number": "12A"
    }
  ],
  "return_segments": [
    {
      "flight_number": "NH017",
      "departure_airport": "ITM",
      "arrival_airport": "HND",
      "departure_datetime": "2024-01-20T18:20:00",
      "arrival_datetime": "2024-01-20T19:35:00",
      "seat_number": "15C"
    }
  ]
}
```

## ANA 予約のお知らせメール

### 件名
```
ANA 予約のお知らせ [予約番号: 0709]
```

### メール本文例
```
山田太郎 様

座席指定が完了いたしました。

■ 予約番号: 0709

■ 往路
便名: NH006
出発: 2024年1月15日 08:30 羽田空港(HND)
到着: 2024年1月15日 11:45 伊丹空港(ITM)
座席: 12A（指定完了）

■ 復路
便名: NH017
出発: 2024年1月20日 18:20 伊丹空港(ITM)
到着: 2024年1月20日 19:35 羽田空港(HND)
座席: 15C（指定完了）

ANA
```

### 抽出されるデータ
```json
{
  "confirmation_code": null,
  "booking_reference": "0709",
  "passenger_name": "山田太郎",
  "outbound_segments": [
    {
      "flight_number": "NH006",
      "departure_airport": "HND",
      "arrival_airport": "ITM",
      "departure_datetime": "2024-01-15T08:30:00",
      "arrival_datetime": "2024-01-15T11:45:00",
      "seat_number": "12A"
    }
  ],
  "return_segments": [
    {
      "flight_number": "NH017",
      "departure_airport": "ITM",
      "arrival_airport": "HND",
      "departure_datetime": "2024-01-20T18:20:00",
      "arrival_datetime": "2024-01-20T19:35:00",
      "seat_number": "15C"
    }
  ]
}
```

## 重複検出の動作

### シナリオ
1. **1番目のメール**: 「ANA お支払い完了」- 確認番号 `887525617` で新規予定作成
2. **2番目のメール**: 「ANA 予約のお知らせ」- 予約番号 `0709` で既存予定発見・更新

### 重複検出ロジック
1. 確認番号 `887525617` で検索 → 見つからない → 新規作成
2. 確認番号なし → 予約番号 `0709` で検索 → 既存予定発見 → 更新

### カレンダーイベント例

#### 往路イベント
```
タイトル: ✈️ NH006 HND→ITM
時間: 2024年1月15日 08:30-11:45
説明:
ANA NH006便
出発: 羽田空港(HND) 08:30
到着: 伊丹空港(ITM) 11:45
座席: 12A
搭乗者: 山田太郎
確認番号: 887525617
予約番号: 0709
```

#### 復路イベント
```
タイトル: ✈️ NH017 ITM→HND
時間: 2024年1月20日 18:20-19:35
説明:
ANA NH017便
出発: 伊丹空港(ITM) 18:20
到着: 羽田空港(HND) 19:35
座席: 15C
搭乗者: 山田太郎
確認番号: 887525617
予約番号: 0709
```

## プロモーションメール例（自動除外）

### 除外される件名例
```
ANAマイルキャンペーン開始！
ANAからのお知らせ - 新サービスのご案内
【ANA】メンテナンスのお知らせ
ANA特典航空券のご案内
```

### 除外理由
- キーワード「キャンペーン」「お知らせ」「メンテナンス」「特典」を含む
- スマートフィルタリング機能により OpenAI API 呼び出し前に除外
- ログには「Skipped promotional email」として記録
