# Gmail Calendar Sync プロジェクト完了ガイド

## プロジェクト概要
GmailからOpenAI APIを使用してメール内容を解析し、航空券予約情報を抽出してGoogle Calendarに自動で予定を追加するシステム。

**現在の状況**: ✅ Phase 2まで完全実装済み、運用可能状態

## 📁 ファイル管理方針
- **CLAUDE.md**: 公開技術情報（Publicリポジトリで共有）
- **.claude/**: 個人的なメモ・問題情報（.gitignoreで除外済み）

## アーキテクチャ
- **実行環境**: Cloud Run Jobs (Cloud Schedulerで定期実行)
- **デプロイ**: GitHub Actions + Cloud Build
- **言語**: Python 3.11+
- **パッケージ管理**: uv
- **LLM**: OpenAI API (gpt-3.5-turbo)
- **認証**: Gmail API / Google Calendar API (OAuth2)
- **通知**: Slack (オプション)

## 実装済み機能
✅ **航空券メール自動処理**: ANA・JALの予約メールを自動検出・解析
✅ **重複防止**: 処理済みメールラベリング
✅ **カレンダー連携**: 往復便対応の自動予定作成
✅ **エラーハンドリング**: 構造化ログとSlack通知
✅ **型安全性**: 全コンポーネントでPydantic型定義
✅ **テスト**: 基本的な単体テストカバレッジ
✅ **CI/CD**: GitHub Actions + Cloud Build + Cloud Run Jobs

## プロジェクト構造
```
src/
├── models/           # Pydanticモデル定義
│   ├── email_types.py    # メール種別の型定義
│   ├── flight.py         # 航空券情報モデル
│   ├── carshare.py       # カーシェア情報モデル
│   └── calendar.py       # カレンダーイベントモデル
├── services/         # 外部API連携
│   ├── gmail_client.py   # Gmail API クライアント
│   ├── calendar_client.py # Google Calendar API クライアント
│   └── openai_client.py  # OpenAI API クライアント
├── processors/       # メール処理ロジック
│   ├── base.py          # 基底プロセッサー
│   ├── flight_processor.py # 航空券処理
│   ├── carshare_processor.py # カーシェア処理
│   └── factory.py       # プロセッサーファクトリー
├── utils/           # ユーティリティ
│   ├── config.py        # 設定管理
│   ├── logging.py       # ログ設定
│   ├── email_filter.py  # 宣伝メールフィルタ
│   └── exceptions.py    # カスタム例外
└── main.py          # エントリーポイント
```

## 環境変数
```
# Gmail API
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=

# Google Calendar API
CALENDAR_CLIENT_ID=
CALENDAR_CLIENT_SECRET=
CALENDAR_REFRESH_TOKEN=

# OpenAI
OPENAI_API_KEY=

# オプション
SLACK_WEBHOOK_URL=  # エラー通知用
SYNC_PERIOD_DAYS=30  # 同期対象期間
```

## メール種別と対応ドメイン
- **航空券**: ana.co.jp, booking.jal.com
- **カーシェア**: carshares.jp, share.timescar.jp
- **飲食店**: (将来拡張)

## 実装完了状況

### ✅ Phase 1: 基盤構築 (完了)
- ✅ プロジェクト初期化 (pyproject.toml, .github/workflows)
- ✅ Gmail/Calendar API認証設定
- ✅ OpenAI API統合 (gpt-3.5-turbo)
- ✅ 構造化ログ設定 (structlog + JSON出力)

### ✅ Phase 2: 航空券処理 (完了)
- ✅ 航空券メール検出ロジック (ana.co.jp, booking.jal.com)
- ✅ OpenAI APIを使用した情報抽出
- ✅ Google Calendar予定作成 (往復便対応)
- ✅ 重複防止ロジック (処理済みラベル)

### ✅ Phase 2.5: カーシェア処理 (完了)
- ✅ カーシェアメール検出ロジック (carshares.jp, share.timescar.jp)
- ✅ 時間ベース競合解決（新規予約が既存予約を自動置換）
- ✅ キャンセルメール対応（既存イベント削除）
- ✅ 予約状態管理（予約・変更・キャンセル・完了）
- ✅ 時系列処理（メール受信順でのイベント処理）

### ✅ Phase 3: 運用改善 (完了)
- ✅ エラーハンドリング強化 (カスタム例外)
- ✅ Slack通知機能 (成功・失敗レポート)
- ✅ 単体テスト追加 (models, processors, config)
- ✅ CI/CDパイプライン (型チェック・リンター統合)
- ✅ 宣伝メールフィルタ（OpenAI API送信前の自動除外）
- ✅ コスト最適化（不要なOpenAI API呼び出し削減）
- ✅ Cloud Run Jobs移行（バッチ処理最適化）

### ✅ Phase 4: インフラ最適化 (完了)
- ✅ Cloud Scheduler設定（6時間ごと定期実行）
- ✅ Cloud Run Jobs完全移行（バッチ処理最適化）

### 🔮 Phase 5: 将来拡張 (未実装)
- [ ] 飲食店予約メール対応
- [ ] メール形式の機械学習改善
- [ ] 複数カレンダー対応

## コマンド
```bash
# 開発環境セットアップ
uv sync

# テスト実行
uv run pytest

# 型チェック
uv run mypy src/

# コードフォーマット
uv run ruff format src/
uv run ruff check src/ --fix

# ローカル実行
uv run python src/main.py
```

## 運用開始手順

### 1. API認証設定
```bash
# 1. Google Cloud Console でプロジェクト作成
# 2. Gmail API / Calendar API を有効化
# 3. OAuth 2.0 認証情報を作成
# 4. クライアント認証情報をダウンロードして.envに設定
# 5. リフレッシュトークンを取得
uv run python get_refresh_token.py
# 6. 表示されたトークンを.envに追加
# 7. OpenAI Platform でAPIキー取得
```

### 2. GitHub Secrets設定
```
# production環境に以下を設定:
GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
CALENDAR_CLIENT_ID, CALENDAR_CLIENT_SECRET, CALENDAR_REFRESH_TOKEN
OPENAI_API_KEY
SLACK_WEBHOOK_URL (オプション)
```

### 3. 運用開始
- Protected branch (main) でpush → Cloud Run Jobsが自動デプロイ
- 手動実行: `gcloud run jobs execute gmail-calendar-sync-job --region=asia-northeast1`
- 定期実行: Cloud Scheduler設定済み（6時間ごと自動実行）

### 実行フロー詳細
1. **Cloud Scheduler**: 6時間ごと（0 */6 * * *）にタイマー発火
2. **Cloud Run Jobs API**: OAuth認証でサービスアカウント使用
3. **Secret Manager**: 環境変数（API Keys）を安全に取得
4. **同期処理**: Gmail API → OpenAI API → Calendar API
5. **Slack通知**: 処理結果をSlackに送信（オプション）

## トラブルシューティング

### よくある問題
1. **認証エラー**: リフレッシュトークンの期限切れ → 再取得
2. **OpenAI API制限**: レート制限 → 実行間隔調整
3. **メール解析失敗**: 新しいメール形式 → プロンプト調整
4. **重複作成**: ラベル付与失敗 → Gmail API権限確認

### デバッグ方法

**⚠️ セキュリティ重要**: デバッグは必ずローカル環境で実行

```bash
# ローカルデバッグ実行（推奨）
LOG_LEVEL=DEBUG uv run python src/main.py

# 特定期間のメールテスト
SYNC_PERIOD_DAYS=7 LOG_LEVEL=DEBUG uv run python src/main.py

# テスト実行
uv run pytest -v

# 型チェック
uv run mypy src/

# コード品質チェック
uv run ruff check src/
```

**GitHub Actions上では**:
- 本番運用のみ（`LOG_LEVEL=INFO`）
- メール内容は自動マスク済み
- デバッグログは出力しない（個人情報保護）

## 拡張ガイド

新しいメール種別を追加する場合:

1. `src/models/` に新しいデータモデル追加
2. `src/processors/` に新しいプロセッサー実装
3. `src/processors/factory.py` でプロセッサー登録
4. `src/utils/config.py` でドメイン設定追加
5. テストケース追加

## セキュリティ・運用注意事項

### 個人情報保護
- **デバッグ**: 必ずローカル環境で実行（メール内容漏洩防止）
- **ログ設計**: 本番環境では個人情報を自動マスク
- **GitHub Actions**: 本番運用のみ、詳細ログ出力禁止

### API・認証管理
- **GitHub Secrets**: production環境でAPIキー管理
- **Protected branch**: mainブランチでのみ本番実行
- **OAuth2トークン**: 定期的な有効期限確認が必要

### コスト・パフォーマンス
- **OpenAI API**: 従量課金のため使用量監視必須
- **実行頻度**: 6時間間隔で適切なバランス
- **同期期間**: `SYNC_PERIOD_DAYS`で処理対象を調整

### メール管理
- **重複防止**: `PROCESSED_BY_GMAIL_SYNC`ラベル自動付与
- **対象ドメイン**: ana.co.jp, booking.jal.com のみ
- **拡張時**: 新ドメイン追加は慎重に検討

## 開発で得られた重要な教訓

### 🔐 認証方式の選択
- **OAuth2 vs Service Account**: 当初OAuth2で実装したが、サービスアカウント方式がより運用に適している
- **認証情報管理**: JSONキーファイルの安全な管理が重要（`.gitignore`必須）
- **権限スコープ**: 必要最小限の権限で運用（Gmail読み取り、Calendar書き込み）

### 📊 設定管理の重要性
- **環境変数**: Pydantic Settingsで型安全な設定管理を実装
- **オプション設定**: Slack通知など必須でない機能は適切にオプション化
- **設定の優先順位**: 環境変数 > .env ファイル > デフォルト値の順序を明確化

### 🔧 段階的実装アプローチ
- **Phase分けの効果**: 基盤→コア機能→運用改善の段階的実装が成功要因
- **MVP優先**: 最小限の価値あるプロダクトから始めて段階的に拡張
- **テスト駆動**: 各フェーズでテストカバレッジを確保

### 🛡️ セキュリティファースト設計
- **ログマスキング**: 個人情報（メール内容）の自動マスク機能実装
- **環境分離**: ローカル開発とGitHub Actions本番環境の明確な分離
- **認証情報保護**: サービスアカウントキーの適切な管理方法確立

### 🚀 CI/CD最適化
- **GitHub Actions**: 6時間ごとの定期実行で適切な頻度バランス
- **品質チェック**: mypy、ruff、pytestの統合で品質担保
- **デプロイ自動化**: Protected branchでの自動デプロイ実現

### 📝 ドキュメント戦略
- **技術文書**: CLAUDE.mdで開発方針・運用手順を一元管理
- **設定例**: .env.exampleで設定項目を明示
- **トラブルシューティング**: よくある問題と解決法を事前整理

### 💰 コスト最適化
- **API使用量**: OpenAI APIの従量課金を考慮した実行頻度調整
- **処理効率**: 重複防止でAPI呼び出し最小化
- **期間設定**: SYNC_PERIOD_HOURSで処理対象メール数制御
- **早期フィルタリング**: 件名ベースの事前判定でOpenAI API呼び出し削減

### 🔄 拡張性設計
- **Factory Pattern**: プロセッサーファクトリーで新メール種別追加を容易化
- **型定義**: Pydanticモデルで構造化データ管理
- **設定駆動**: 対応ドメインを設定ファイルで管理

### 🎯 ログ品質とエラーハンドリング
- **適切なログレベル**: 「No flight info found」は警告ではなく情報レベル
- **メール分類**: 宣伝メール、予約メール、情報なしメールの明確な区別
- **Subject-based判定**: 件名から予約メールかどうかを高精度で事前判定
- **エラー通知**: Slack通知で真の失敗のみを報告（情報なしは除外）

### 🔍 メール処理の最適化
- **段階的フィルタリング**: 件名チェック → 宣伝メールチェック → OpenAI処理
- **パターンマッチング**: 正規表現による高精度な予約メール判定
- **False Positive削減**: 予約確認パターンを優先して誤判定を防止
- **処理ログ**: 各段階での処理理由を明確にログ出力

## 💡 開発・運用で得られた重要な教訓

### 🏗️ アーキテクチャ設計

#### **実行頻度とデータ範囲の最適化**
- **問題**: 6時間間隔で30日分処理 → 大量の既処理メール再確認が非効率
- **解決**: 1時間間隔で3時間分処理（重複処理で安全性確保）
- **効果**: 処理対象メール数大幅削減、OpenAI API使用量削減、監視精度向上

#### **段階的フィルタリングアーキテクチャ**
```
メール取得 → 件名判定 → 宣伝メールフィルタ → OpenAI API → Calendar API
```
- **効果**: OpenAI API呼び出し40-60%削減
- **学び**: 高コストな外部API呼び出しは最終段階に配置

### 🔧 技術実装

#### **ログ形式とインフラの統合**
- **問題**: structlogのデフォルト形式とCloud Logging Sinkのフィルター条件が不一致
- **解決**: `logger.info("message", message="message", ...)`で明示的指定
- **学び**: インフラ設定とアプリケーションログ形式の事前検証が重要

#### **Docker Build環境での依存関係**
- **問題**: `pyproject.toml`でREADME.md参照だが、Dockerfileでコピーされていない
- **解決**: `COPY pyproject.toml uv.lock README.md ./`
- **学び**: ビルド環境とローカル環境の差異を常に考慮

#### **重複処理による安全性確保**
- **設計**: 1時間間隔で3時間分処理（2時間重複）
- **利点**: Gmail API遅延対応、処理失敗時自動復旧、取りこぼし防止
- **学び**: 重複処理は分散システムでの安全性向上に有効

### 🛡️ セキュリティ・運用

#### **個人情報保護の多層防御**
- **開発時**: ローカルでのみデバッグログ出力
- **本番時**: 個人情報の自動マスク
- **監視時**: 個人情報を含まないメトリクスのみ蓄積

#### **段階的実装の重要性**
1. **Phase 1**: 基盤構築（認証・API統合）
2. **Phase 2**: コア機能（航空券処理）
3. **Phase 2.5**: 機能拡張（カーシェア対応）
4. **Phase 3**: 運用改善（監視・最適化）
- **学び**: MVP優先、各フェーズでの完全検証、早期価値提供

### 💰 コスト最適化

#### **OpenAI API使用量の最適化**
1. **件名ベース事前判定** → 明らかな非予約メールを除外
2. **宣伝メールフィルタ** → パターンマッチングで除外
3. **処理済みラベル** → 重複処理防止
- **効果**: 月間コスト $15 → $9（40%削減）

#### **無料枠を活用した監視システム**
- **構成**: Cloud Logging → BigQuery → Looker Studio
- **コスト**: $0/月（無料枠内運用）
- **学び**: GCPの無料枠活用で高度な監視システムを低コスト構築

### 🧪 テスト・品質

#### **型安全性による品質向上**
- **技術**: Pydantic + mypy
- **効果**: 実行時エラー大幅削減、APIレスポンス構造明確化、リファクタリング安全性向上
- **学び**: 動的言語でも型システム活用で堅牢性大幅向上

#### **パフォーマンステストの重要性**
- **実装**: pytest-benchmarkでフィルタリング性能継続監視
- **効果**: リグレッション防止と最適化効果の定量化

### 🔄 CI/CD・運用

#### **Protected Branchとコード品質**
- **設定**: main branch protection + pre-commit hooks + automated deployment
- **学び**: コード品質自動化により手戻り削減、main branch保護で本番安定性確保

#### **インフラとアプリケーションの分離**
- **アプローチ**: アプリケーション（このリポジトリ）+ インフラ（別Terraformリポジトリ）
- **利点**: 変更影響範囲明確化、セキュリティ設定集約管理、開発高速化

### 📊 監視・可観測性

#### **多層監視アーキテクチャ**
1. **アプリケーション**: 構造化ログ
2. **インフラ**: Cloud Logging
3. **分析**: BigQuery
4. **可視化**: Looker Studio
5. **通知**: Slack

#### **運用メトリクスの設計**
- **成功率**: 実際の処理成功率（フィルタ結果除外）
- **処理時間**: 1通あたりの平均処理時間
- **フィルタ効果**: API呼び出し削減率
- **エラーパターン**: 同一エラーの頻発検知

### ✅ Do's / ❌ Don'ts

#### **推奨事項 ✅**
- 段階的実装によるリスク最小化
- 型システムの積極活用
- 外部API使用量の継続監視
- 多層防御によるセキュリティ確保
- インフラとアプリケーションの適切な分離

#### **避けるべき事項 ❌**
- 一括大容量バッチ処理
- デバッグログでの個人情報出力
- 単一層でのエラーハンドリング
- インフラ設定とアプリケーションの密結合
- 外部API依存部分での事前フィルタリング省略
