# Gmail Calendar Sync

✈️ 航空券の予約メールを自動的にGoogle Calendarの予定として追加するPythonアプリケーション

![GitHub Actions](https://img.shields.io/github/actions/workflow/status/yoshi65/gmail-calendar-sync/sync.yml?branch=main)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

OpenAI APIを使用してメール内容を自動解析し、GitHub Actionsで6時間ごとに定期実行されます。

## 🚀 主な機能

- **🤖 AI自動解析**: OpenAI APIでメール内容から航空券情報を正確に抽出
- **📅 カレンダー連携**: 往復便対応でGoogle Calendarに自動予定作成
- **⏰ 時間単位処理**: 頻繁実行に最適化された効率的なメール取得
- **🔄 重複防止**: 確認番号/予約番号ベースのインテリジェント重複検出で完全回避
- **📱 Slack通知**: 処理結果をリアルタイムでSlack通知（オプション）
- **🛡️ 型安全**: 全コンポーネントでPydantic型定義によるエラー防止
- **🔧 拡張可能**: プロセッサーパターンで新しいメール種別に簡単対応

## ✈️ サポート対象

### 航空券予約メール
- **ANA** (ana.co.jp)
- **JAL Booking** (booking.jal.com)

### 🔮 将来対応予定
- カーシェア予約
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

### GitHub Actions自動実行

1. **Environment設定**
   ```
   Settings > Environments > New environment: "production"
   Protected branches: main
   ```

2. **Secrets設定**
   - `GMAIL_CLIENT_ID`
   - `GMAIL_CLIENT_SECRET` 
   - `GMAIL_REFRESH_TOKEN`
   - `CALENDAR_CLIENT_ID`
   - `CALENDAR_CLIENT_SECRET`
   - `CALENDAR_REFRESH_TOKEN`
   - `OPENAI_API_KEY`
   - `SLACK_WEBHOOK_URL` (オプション)

3. **自動実行**
   - 6時間ごと自動実行
   - 手動実行: Actions > "Gmail Calendar Sync" > "Run workflow"

## 🧪 開発・テスト

### テスト実行

```bash
# 全テスト実行
uv run pytest

# 詳細出力
uv run pytest -v

# カバレッジ付き
uv run pytest --cov=src
```

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
│   └── 📄 calendar.py       # カレンダーイベント
├── 📁 services/         # 外部API連携
│   ├── 📄 gmail_client.py   # Gmail API操作
│   ├── 📄 calendar_client.py # Calendar API操作
│   └── 📄 openai_client.py  # OpenAI API連携
├── 📁 processors/       # メール処理ロジック
│   ├── 📄 base.py          # 基底プロセッサー
│   ├── 📄 flight_processor.py # 航空券専用処理
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
✅ Processed: 3
❌ Failed: 0  
📊 Total emails: 3

Flight confirmations added to calendar:
• ANA NH006 (2024-01-15)
• JAL JL001 (2024-02-01) 
• ANA NH007 (2024-01-20)
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

## 💰 コスト管理

### OpenAI API使用量目安

- **月間50通の航空券メール**: 約$2-5
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

## 🤝 貢献

1. フォークしてfeatureブランチを作成
2. 変更を実装
3. テストが通ることを確認
4. プルリクエストを作成

### 開発ガイドライン

- **コードスタイル**: ruff準拠
- **型注釈**: 必須（mypy strictモード）
- **テスト**: 新機能には必ずテストを追加
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