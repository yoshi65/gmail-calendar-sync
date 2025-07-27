# 📚 Gmail Calendar Sync Documentation

Gmail Calendar Syncプロジェクトの包括的なドキュメントへようこそ。

## 📖 ドキュメント一覧

### 🏗️ システム設計
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - システムアーキテクチャと設計思想
- **[API.md](API.md)** - API仕様とサービスインターフェース
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Cloud Run デプロイメントガイド

### 📋 運用・保守
- **[CHANGELOG.md](CHANGELOG.md)** - バージョン履歴と変更点
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - よくある問題と解決方法
- **[PERFORMANCE.md](PERFORMANCE.md)** - パフォーマンス最適化ガイド

### 🎨 ビジュアル資料
- **[diagrams/](diagrams/)** - システム図・データフロー図
  - `architecture.mmd` - システム全体アーキテクチャ
  - `data-flow.mmd` - データフロー詳細
  - `deployment.mmd` - デプロイメント構成

### 💡 実装例
- **[examples/](examples/)** - 設定例・サンプルコード
  - `configuration/` - 環境別設定例
  - `email-samples/` - サポート対象メール例
  - `notebooks/` - Jupyter ノートブック

### 🔧 API仕様
- **[api/](api/)** - OpenAPI仕様書
  - `openai.yml` - OpenAI API統合仕様
  - `gmail.yml` - Gmail API使用パターン
  - `calendar.yml` - Calendar API操作仕様

## 🚀 クイックナビゲーション

### 開発者向け
- 新規開発者: [ARCHITECTURE.md](ARCHITECTURE.md) → [API.md](API.md)
- 運用担当者: [DEPLOYMENT.md](DEPLOYMENT.md) → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- 拡張開発: [examples/](examples/) → [API.md](API.md)

### 問題解決
- 実行エラー: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- パフォーマンス: [PERFORMANCE.md](PERFORMANCE.md)
- デプロイ問題: [DEPLOYMENT.md](DEPLOYMENT.md)

## 📝 ドキュメント更新ガイドライン

1. **正確性**: 実装と同期した内容を維持
2. **完全性**: 新機能追加時は関連ドキュメントも更新
3. **可読性**: 図表・例を積極的に活用
4. **検索性**: 適切なヘッダー・リンクを設置

## 🔗 関連リンク

- **[メインREADME](../README.md)** - プロジェクト概要・セットアップ
- **[CLAUDE.md](../CLAUDE.md)** - 開発知見・教訓
- **[GitHub Issues](https://github.com/yoshi65/gmail-calendar-sync/issues)** - 既知の問題・要望

---

📧 質問・提案は [Issues](https://github.com/yoshi65/gmail-calendar-sync/issues) でお気軽にどうぞ！
