# Gmail Calendar Sync

✈️🚗 航空券・カーシェア予約メールを自動的にGoogle Calendarの予定として追加するPythonアプリケーション

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Cloud Run](https://img.shields.io/badge/deploy-Cloud%20Run%20Jobs-blue)

OpenAI APIを使用してメール内容を自動解析し、Cloud Run Jobsで定期実行されます。

## 🚀 主な機能

- **🤖 AI自動解析**: OpenAI APIでメール内容から航空券・カーシェア情報を正確に抽出
- **📅 カレンダー連携**: 往復便・レンタル期間対応でGoogle Calendarに自動予定作成
- **⏰ 時間単位処理**: 頻繁実行に最適化された効率的なメール取得
- **🔄 重複防止**: 確認番号/予約番号ベースのインテリジェント重複検出で完全回避
- **📱 Slack通知**: 処理結果をリアルタイムでSlack通知（オプション）
- **🛡️ 型安全**: 全コンポーネントでPydantic型定義によるエラー防止
- **🔧 拡張可能**: プロセッサーパターンで新しいメール種別に簡単対応
- **⚡ 時間ベース競合解決**: カーシェアの時間重複を自動検出・解決

## ✈️🚗 サポート対象

### 航空券予約メール
- **ANA** (ana.co.jp)
- **JAL Booking** (booking.jal.com)

### カーシェア予約メール ✨ NEW!
- **Times Car** (share.timescar.jp)
- **三井のカーシェアーズ** (carshares.jp)

### 🔮 将来対応予定
- 飲食店予約
- ホテル予約

## 📋 前提条件

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (推奨) または pip
- Google Cloud Platform アカウント
- OpenAI API アカウント

## 🆕 NEW: 時間単位 & 日付範囲指定機能

頻繁実行に最適化された時間単位指定と、初回実行用の日付範囲指定機能を追加！

```bash
# ⏰ 時間単位指定（推奨）
SYNC_PERIOD_HOURS=8 uv run python src/main.py

# 📅 日付範囲指定
SYNC_START_DATE=2024-01-01 SYNC_END_DATE=2024-01-31 uv run python src/main.py
```

### 優先順位
1. **絶対日付指定** (`SYNC_START_DATE` / `SYNC_END_DATE`) - 最優先
2. **時間単位指定** (`SYNC_PERIOD_HOURS`) - 推奨（頻繁実行用）
3. **日単位指定** (`SYNC_PERIOD_DAYS`) - 後方互換性

### 用途別推奨設定
- **通常運用**: `SYNC_PERIOD_HOURS=8` (6時間ごと実行に最適)
- **初回実行**: 日付範囲指定で段階的処理
- **デバッグ**: `SYNC_PERIOD_HOURS=1` で直近のメールのみ

## 🛠️ セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/yoshi65/gmail-calendar-sync.git
cd gmail-calendar-sync
```

### 2. 依存関係のインストール

```bash
# uvを使用（推奨）
uv sync

# または pip
pip install -e .
```

### 3. API認証の設定

#### Google APIs (Gmail & Calendar)

1. **Google Cloud Consoleでプロジェクトを作成**
   - [Google Cloud Console](https://console.cloud.google.com/)にアクセス
   - 新しいプロジェクトを作成

2. **APIを有効化**
   - Gmail API
   - Google Calendar API

3. **OAuth 2.0 認証情報を作成**
   - 「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類：「デスクトップアプリケーション」
   - クライアントIDとクライアントシークレットをメモ

4. **リフレッシュトークンを取得**
   ```bash
   # .envファイルにクライアント情報を設定
   echo "GOOGLE_CLIENT_ID=your_client_id" >> .env
   echo "GOOGLE_CLIENT_SECRET=your_client_secret" >> .env

   # リフレッシュトークン取得スクリプトを実行
   uv run python get_refresh_token.py
   ```

   ブラウザが開くのでGoogleアカウントで認証し、表示されたリフレッシュトークンを`.env`に追加してください。

#### OpenAI API

1. [OpenAI Platform](https://platform.openai.com/)でAPIキーを取得
2. 課金設定を確認（従量課金）

### 4. 環境変数の設定

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
# Gmail API
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token

# Google Calendar API
CALENDAR_CLIENT_ID=your_calendar_client_id
CALENDAR_CLIENT_SECRET=your_calendar_client_secret
CALENDAR_REFRESH_TOKEN=your_calendar_refresh_token

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# オプション設定
SLACK_WEBHOOK_URL=your_slack_webhook_url  # Slack通知用
SYNC_PERIOD_HOURS=8                       # 同期対象期間（時間）推奨
SYNC_PERIOD_DAYS=30                       # 同期対象期間（日数）後方互換性
LOG_LEVEL=INFO                            # ログレベル

# 日付範囲指定（オプション、最優先）
# SYNC_START_DATE=2024-01-01              # 開始日（YYYY-MM-DD形式）
# SYNC_END_DATE=2024-01-31                # 終了日（YYYY-MM-DD形式）
```

## 🏃‍♂️ 使用方法

### ローカル実行

```bash
# 🔄 通常実行（推奨：過去8時間のメール）
uv run python src/main.py

# ⏰ 時間単位指定での実行
# 直近3時間の新着メールをチェック
SYNC_PERIOD_HOURS=3 uv run python src/main.py

# 1日分のメールをチェック
SYNC_PERIOD_HOURS=24 uv run python src/main.py

# 🛠️ デバッグ実行
LOG_LEVEL=DEBUG SYNC_PERIOD_HOURS=1 uv run python src/main.py

# 📅 日付範囲指定での実行（初回実行・特定期間処理）
# 初回実行：過去1年間のメールを段階的に取得
SYNC_START_DATE=2023-01-01 SYNC_END_DATE=2024-01-01 uv run python src/main.py

# 特定月のメールを再処理
SYNC_START_DATE=2024-01-01 SYNC_END_DATE=2024-01-31 uv run python src/main.py

# 開始日のみ指定（それ以降全て）
SYNC_START_DATE=2024-01-01 uv run python src/main.py

# 📊 後方互換性（日単位指定）
SYNC_PERIOD_DAYS=7 LOG_LEVEL=DEBUG uv run python src/main.py
```

### Cloud Run Jobs実行

1. **デプロイ**
   - mainブランチへのpushで自動デプロイ
   - Cloud BuildでContainer imageをビルド
   - Cloud Run Jobsに自動配布

2. **手動実行**
   ```bash
   gcloud run jobs execute gmail-calendar-sync-job --region=asia-northeast1
   ```

3. **定期実行**
   - Cloud Schedulerで6時間ごと自動実行
   - タイムゾーン: Asia/Tokyo
   - リトライ: 最大3回、タイムアウト: 30分

### 実行フロー
1. **Cloud Scheduler** → Cloud Run Jobs API呼び出し
2. **OAuth認証** → サービスアカウントによる認証
3. **Secret Manager** → 環境変数の安全な取得
4. **同期処理実行** → Gmail解析 + Calendar更新

## 🧪 開発・テスト

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 詳細出力
uv run pytest -v

# カバレッジ付き
uv run pytest --cov=src --cov-report=term-missing

# 特定のテストのみ実行
uv run pytest tests/test_models.py -v
uv run pytest tests/test_processors.py::TestCarShareEmailProcessor -v
```

### テストカバレッジ

- **全体**: 43% (75テスト)
- **モデル**: 95-100% (型安全・データ検証)
- **プロセッサー**: 52-81% (メール処理ロジック)
- **カーシェア**: 100% (完全テスト済み) ✨
- **Email Filter**: 94% (プロモーション除外)

### コード品質チェック

```bash
# 型チェック
uv run mypy src/

# リンター
uv run ruff check src/

# フォーマッター
uv run ruff format src/

# 自動修正
uv run ruff check src/ --fix
```

## 🏗️ アーキテクチャ

```
src/
├── 📁 models/           # Pydanticデータモデル
│   ├── 📄 email_types.py    # メール種別・処理結果
│   ├── 📄 flight.py         # 航空券予約情報
│   ├── 📄 carshare.py       # カーシェア予約情報 ✨ NEW!
│   └── 📄 calendar.py       # カレンダーイベント
├── 📁 services/         # 外部API連携
│   ├── 📄 gmail_client.py   # Gmail API操作
│   ├── 📄 calendar_client.py # Calendar API操作
│   └── 📄 openai_client.py  # OpenAI API連携
├── 📁 processors/       # メール処理ロジック
│   ├── 📄 base.py          # 基底プロセッサー
│   ├── 📄 flight_processor.py # 航空券専用処理
│   ├── 📄 carshare_processor.py # カーシェア専用処理 ✨ NEW!
│   └── 📄 factory.py       # プロセッサーファクトリー
├── 📁 utils/           # ユーティリティ
│   ├── 📄 config.py        # 設定管理
│   ├── 📄 logging.py       # 構造化ログ
│   └── 📄 exceptions.py    # カスタム例外
└── 📄 main.py          # エントリーポイント
```

### 設計パターン

- **Factory Pattern**: メール種別ごとのプロセッサー選択
- **Strategy Pattern**: メール解析ロジックの切り替え
- **Dependency Injection**: テスタビリティの向上
- **型安全**: Pydanticによる実行時検証

## 🔧 拡張ガイド

新しいメール種別（例: ホテル予約）を追加：

1. **データモデル定義**
   ```python
   # src/models/hotel.py
   class HotelBooking(BaseModel):
       confirmation_code: str
       # ...
   ```

2. **プロセッサー実装**
   ```python
   # src/processors/hotel_processor.py
   class HotelEmailProcessor(BaseEmailProcessor):
       def can_process(self, email: EmailMessage) -> bool:
           return email.domain in self.settings.hotel_domains
   ```

3. **ファクトリー登録**
   ```python
   # src/processors/factory.py
   self._processors.append(HotelEmailProcessor(self.settings))
   ```

4. **設定追加**
   ```python
   # src/utils/config.py
   hotel_domains: list[str] = ["booking.com", "hotels.com"]
   ```

## 📊 監視・ログ

### ログ出力

- **本番**: JSON形式の構造化ログ
- **開発**: 人間が読みやすい色付きログ
- **個人情報マスキング**: 自動的にAPIキー等をマスク

### Slack通知例

```
📧 Gmail Calendar Sync Summary
✅ Processed: 5
❌ Failed: 0
📊 Total emails: 5

Flight confirmations added to calendar:
• ANA NH006 (2024-01-15)
• JAL JL001 (2024-02-01)
• ANA NH007 (2024-01-20)

Car sharing bookings added to calendar:
• 🚗 新宿駅南口ステーション (2024-01-10 14:00-16:00)
• 🔄 渋谷センター街ステーション (2024-01-12 10:00-12:00)
```

## 🚨 トラブルシューティング

### よくある問題

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| 認証エラー | リフレッシュトークン期限切れ | OAuth2トークンを再取得 |
| OpenAI API制限 | レート制限/課金制限 | API使用量確認・プラン変更 |
| メール解析失敗 | 新しいメール形式 | OpenAIプロンプトを調整 |
| 重複イベント作成 | 確認番号/予約番号の誤認識 | メール内容確認、プロンプト調整 |

### 🔍 重複防止機能の仕組み

**優先順位による重複検出**:
1. **確認番号（confirmation_code）**を主キーとして使用
2. 確認番号がない場合は**予約番号（booking_reference）**をフォールバック
3. 既存の予定が見つかった場合は**情報更新**（座席番号など）
4. 見つからない場合のみ**新規作成**

**メール種別での動作例**:
- **ANA お支払い完了**: 確認番号 `887525617` → 新規予定作成
- **ANA 予約のお知らせ**: 確認番号なし → 予約番号 `0709` で既存予定を発見・更新
- **JAL 購入/予約**: 同一予約番号で重複防止

**重要な教訓**:
- **確認番号と予約番号の違い**: ANAでは便ごとに予約番号が発行されるが、確認番号は予約全体で一意
- **OpenAIプロンプトの精度**: 明確な指示で誤認識を防ぐ（「確認番号」ラベルのみを使用するよう指定）
- **フォールバック設計**: 確認番号がない場合の予約番号フォールバックで柔軟性を確保
- **テスト環境**: ラベル・予定削除機能でクリーンな状態でのテストが重要

### 🚗 カーシェア重複解決の仕組み

**時間ベース競合解決**:
1. **重複検出**: 同一ステーション・同時間帯の予約を自動検出
2. **新しい予約が優先**: 時系列で後のメールが前の予約を自動的に置き換え
3. **予約状況の追跡**: RESERVED → CHANGED → CANCELLED → COMPLETED
4. **ステータス別表示**: 🚗(予約) 🔄(変更) ❌(キャンセル) ✅(完了)

**カーシェア特有の課題と解決**:
- **同日複数メール**: 予約変更・キャンセルが頻繁に発生 → 時系列処理で解決
- **同一時間制約**: 物理的に同時刻・同場所の予約は不可能 → 重複検出ロジックで自動置換
- **プロバイダー別管理**: Times Car と三井のカーシェアーズの異なるメール形式に対応

### デバッグコマンド

```bash
# 詳細ログ出力
LOG_LEVEL=DEBUG uv run python src/main.py

# ⏰ 時間単位でのデバッグ（推奨）
# 直近1時間のメールのみテスト
SYNC_PERIOD_HOURS=1 LOG_LEVEL=DEBUG uv run python src/main.py

# 過去3時間のメールをテスト
SYNC_PERIOD_HOURS=3 LOG_LEVEL=DEBUG uv run python src/main.py

# 📅 絶対日付でのデバッグ
# 特定月のメールのみテスト
SYNC_START_DATE=2024-01-01 SYNC_END_DATE=2024-01-31 LOG_LEVEL=DEBUG uv run python src/main.py

# エラー発生時の再処理（特定日以降）
SYNC_START_DATE=2024-01-15 LOG_LEVEL=DEBUG uv run python src/main.py

# 📊 後方互換性（日単位）
SYNC_PERIOD_DAYS=7 uv run python src/main.py

# Slack通知なしでテスト
unset SLACK_WEBHOOK_URL && uv run python src/main.py

# 🧹 テスト用クリーンアップ（開発時のみ）
# 処理済みラベルとカレンダー予定を削除して初期状態に戻す
uv run python cleanup_for_test.py
```

### 🧹 テスト環境のクリーンアップ

開発・テスト時に、処理済みラベルとカレンダー予定を削除してクリーンな状態でテストを行う機能を提供：

```bash
# テスト用クリーンアップスクリプト
uv run python cleanup_for_test.py
```

**⚠️ 重要**: この機能は開発・テスト時のみ使用してください。本番環境では実行しないでください。

**削除される内容**:
- `PROCESSED_BY_GMAIL_SYNC` ラベルが付いているメールからラベルを削除
- `gmail-calendar-sync` で作成されたカレンダー予定を削除

## 📚 開発経験と教訓

### 🎯 プロジェクト開発で学んだ重要な教訓

#### **1. 設計・アーキテクチャ**
- **プロセッサーパターンの威力**: 航空券実装後、カーシェア機能を1日で追加完了
  - 基底クラス（`BaseEmailProcessor`）の抽象化が功を奏した
  - ファクトリーパターンで新しいプロセッサーを簡単に追加
  - 既存コードを一切変更せずに新機能を統合

- **型安全の重要性**: Pydanticモデルでランタイムエラーを設計時に防止
  - 複雑なネストしたデータ構造でもエラーを早期発見
  - APIレスポンスの不整合を実行時に検出
  - リファクタリング時の破壊的変更を型チェックで予防

#### **2. AI統合の課題と解決**
- **プロンプトエンジニアリングの精度**: OpenAI APIの応答品質は指示の明確さに直結
  ```
  ❌ 悪い例: "予約番号を抽出してください"
  ✅ 良い例: "「確認番号」ラベルの後に続く6桁以上の数字のみを確認番号として抽出"
  ```

- **フォールバック戦略**: 複数の識別子（確認番号→予約番号）で堅牢性を確保
  - 主キー（確認番号）が取得できない場合の代替手段を用意
  - 航空券とカーシェアで異なる重複検出ロジックを実装

- **構造化出力**: JSON形式での厳密な出力指定でパースエラーを最小化

#### **3. ドメイン固有の課題**

**航空券特有の複雑さ**:
- **確認番号 vs 予約番号**: ANAでは便ごとに予約番号、全体で確認番号
- **マルチセグメント**: 乗り継ぎ便の処理で往復各セグメントを個別管理
- **時刻とタイムゾーン**: 国際線での正確な時刻管理

**カーシェア特有の複雑さ**:
- **時間競合**: 物理的制約（同時刻同場所の予約不可）を重複検出で解決
- **頻繁な変更**: 同日内の複数メール（予約→変更→キャンセル）への対応
- **プロバイダー差異**: Times Car と三井のカーシェアーズの異なるメール形式

#### **4. 運用・保守性**

- **構造化ログの価値**: 本番環境での問題特定に必須
  - 個人情報のマスキング処理で安全性と可読性を両立
  - トランザクションID的な仕組み（email_id）で処理の追跡が容易

- **環境別設定**: 開発・本番での動作差異を環境変数で制御
  - `LOG_LEVEL=DEBUG` での詳細ログは開発時のみ
  - `SYNC_PERIOD_HOURS` で実行頻度を柔軟に調整

- **テスト環境の重要性**: クリーンアップ機能で反復テストを可能に
  ```bash
  # テスト用クリーンアップで初期状態に戻す
  uv run python cleanup_for_test.py
  ```

#### **5. テスト駆動開発の重要性**

- **型安全なテスト**: Pydanticモデルのテストで実行時エラーを事前防止
  ```python
  # 日本語含むデータの正確なテスト
  def test_carshare_booking_creation(self):
      booking = CarShareBooking(
          provider=CarShareProvider.TIMES_CAR,
          user_name="山田太郎",
          station=StationInfo(station_name="新宿ステーション")
      )
  ```

- **包括的なテストスイート**:
  - **モデルテスト**: データ検証・プロパティ計算の正確性
  - **プロセッサーテスト**: メール処理ロジック・エラーハンドリング
  - **統合テスト**: プロモーション除外・重複検出の動作確認

- **CI/CDによる品質保証**: GitHub Actionsで自動テスト・型チェック・リンターを実行
  - Python 3.11/3.12 マトリックステスト
  - カバレッジレポート（Codecov連携）
  - ruff, mypy による厳格なコード品質チェック

#### **6. 拡張性を考慮した設計**

- **新しいメール種別の追加が容易**:
  1. モデル定義（`src/models/新種別.py`）
  2. プロセッサー実装（`src/processors/新種別_processor.py`）
  3. ファクトリー登録（`factory.py`に1行追加）
  4. **テスト追加** (`tests/test_models.py`, `tests/test_processors.py`) ⚠️ 重要

- **設定の外部化**: ドメインリスト・API設定を簡単に変更可能

- **API抽象化**: Gmail/Calendar/OpenAI クライアントを独立させ、差し替え容易

#### **7. パフォーマンス最適化**

- **時間単位指定**: 頻繁実行での無駄なAPI呼び出しを削減
  - `SYNC_PERIOD_HOURS=8` で6時間ごと実行に最適化
  - 初回実行時の日付範囲指定で段階的処理

- **重複検出の効率化**: 確認番号での高速検索 → 予約番号フォールバック

#### **8. セキュリティベストプラクティス**

- **個人情報保護**:
  - 本番環境では自動マスキング
  - デバッグ時のローカル実行を徹底
  - GitHub Actionsでの機密情報をSecrets管理

- **権限最小化**: OAuth2スコープを必要最小限に制限

### 🔄 継続的改善のポイント

1. **監視とアラート**: Slack通知で異常を早期発見
2. **A/Bテスト**: 新しいプロンプトの効果測定
3. **ユーザビリティ**: カレンダーイベントの見やすさ改善
4. **コスト最適化**: OpenAI API使用量の継続的モニタリング

### 🚀 次期プロジェクトへの適用

この開発で得られた知見は、他の類似プロジェクト（ホテル予約、飲食店予約等）に直接活用可能：

- **プロセッサーパターン**: 新しいメール種別を迅速に追加
- **AI統合手法**: 構造化された情報抽出のベストプラクティス
- **重複解決ロジック**: ドメイン特性に応じた柔軟な実装
- **型安全設計**: Pydanticベースの堅牢なデータモデル
- **テスト戦略**: モデル・プロセッサー・統合テストの包括的カバレッジ
- **CI/CD手法**: 品質保証とデプロイメント自動化

### 📊 開発成果サマリー

**実装済み機能**:
- ✅ 航空券処理 (ANA, JAL) - **完全実装**
- ✅ カーシェア処理 (Times Car, 三井) - **完全実装**
- ✅ プロモーション除外 - **自動フィルタリング**
- ✅ CI/CD パイプライン - **GitHub Actions**
- ✅ 包括的テストスイート - **75テスト**

**技術的成果**:
- **43%** テストカバレッジ (1169行中)
- **100%** カーシェアモデルカバレッジ
- **0エラー** 静的解析 (ruff, mypy)
- **Python 3.11/3.12** マトリックステスト対応

**開発効率**:
- 航空券実装後、**カーシェア機能を1日で追加完了**
- プロセッサーパターンにより**既存コード変更なし**で新機能統合
- 型安全設計により**ランタイムエラーをゼロに**

## 💰 コスト管理

### OpenAI API使用量目安

- **月間50通の航空券・カーシェアメール**: 約$2-5
- **1通あたり**: 約$0.05-0.10
- **トークン数**: 1通あたり1000-3000トークン

### 節約のコツ

- **通常運用**: `SYNC_PERIOD_HOURS=8`で重複を最小化（6時間ごと実行に最適）
- **初回実行**: 日付範囲指定で段階的に処理（例：月ごと）
- **デバッグ**: `SYNC_PERIOD_HOURS=1`で直近のメールのみ
- **不要ドメイン除外**: 対象ドメインを厳選
- **ログレベル**: `INFO`以上に設定（DEBUGは開発時のみ）

### 🎯 実行頻度別推奨設定

| 実行間隔 | 推奨設定 | 理由 |
|----------|----------|------|
| 6時間ごと | `SYNC_PERIOD_HOURS=8` | 重複最小、新着確実にカバー |
| 3時間ごと | `SYNC_PERIOD_HOURS=4` | 高頻度チェック |
| 1日1回 | `SYNC_PERIOD_HOURS=30` | 余裕を持った範囲 |
| デバッグ | `SYNC_PERIOD_HOURS=1` | 最新メールのみ |

## 🔧 開発・保守の自動化

### Pre-commit Hooks ✨ NEW!
ローカル開発でのコード品質を自動保証：

```bash
# Pre-commit hooks のインストール
uv run pre-commit install

# 手動実行
uv run pre-commit run --all-files
```

**自動実行される品質チェック**:
- **ruff**: コードフォーマット・リンター
- **mypy**: 型チェック
- **一般チェック**: ファイル形式・末尾改行・機密情報検出

### Renovate 依存関係自動更新 ✨ NEW!
パッケージとセキュリティの自動保守：

- **スケジュール**: 月曜深夜（日本時間）に自動チェック
- **Auto-merge**: 安全なパッチアップデートは自動マージ
- **セキュリティアラート**: 脆弱性発見時の即座PR作成
- **分離管理**: 本番/開発依存関係を別々に処理

### 開発プロセス改善の教訓

#### **CI失敗防止の重要性**
```bash
# ❌ 以前: CI でフォーマットエラー
# ✅ 現在: Pre-commit でローカル検出
git commit  # 自動的にruff・mypy実行
```

#### **依存関係管理の自動化**
```bash
# ❌ 以前: 手動でのパッケージ更新
# ✅ 現在: Renovateの自動PR + auto-merge
```

#### **バージョン管理の標準化**
```bash
# 開発環境の一貫性確保
.python-version    # Python 3.11
.tool-versions     # asdf/rtx互換
```

## 🤝 貢献

詳細な貢献ガイドは [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

### クイックスタート

1. フォークしてfeatureブランチを作成
2. 変更を実装
3. Pre-commit hooksでローカル品質チェック
4. テストが通ることを確認
5. プルリクエストを作成

### 開発ガイドライン

- **コードスタイル**: ruff準拠（Pre-commitで自動チェック）
- **型注釈**: 必須（mypy strictモード）
- **テスト**: 新機能には必ずテストを追加
- **セキュリティ**: [SECURITY.md](SECURITY.md) を参照
- **ドキュメント**: README・CLAUDE.mdを更新

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)を参照

## 🙏 謝辞

- [OpenAI](https://openai.com/) - GPT-3.5によるメール解析
- [Google](https://developers.google.com/) - Gmail/Calendar API
- [Pydantic](https://pydantic.dev/) - データ検証
- [uv](https://github.com/astral-sh/uv) - 高速パッケージ管理

---

⭐ このプロジェクトが役に立ったらスターをお願いします！

📧 質問やフィードバックは[Issues](https://github.com/yoshi65/gmail-calendar-sync/issues)でお気軽にどうぞ
