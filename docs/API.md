# 🔧 API Specifications

Gmail Calendar Syncの内部API仕様とサービスインターフェースドキュメント

## 📋 目次

- [Service APIs](#service-apis)
- [Data Models](#data-models)
- [Processing Interfaces](#processing-interfaces)
- [Integration Patterns](#integration-patterns)
- [Error Handling](#error-handling)
- [Usage Examples](#usage-examples)

## Service APIs

### 1. Gmail Client API

#### メール取得
```python
def get_all_supported_emails(
    self,
    since_days: Optional[int] = None,
    since_hours: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[EmailMessage]:
    """
    期間指定でサポート対象メールを取得

    Args:
        since_days: 過去N日間（後方互換性）
        since_hours: 過去N時間（推奨）
        start_date: 開始日（YYYY-MM-DD）
        end_date: 終了日（YYYY-MM-DD）

    Returns:
        EmailMessage のリスト

    Priority:
        1. 絶対日付指定 (start_date/end_date) - 最優先
        2. 時間単位指定 (since_hours) - 推奨
        3. 日単位指定 (since_days) - 後方互換性
    """
```

#### ラベル操作
```python
def add_label(self, email_id: str, label_name: str) -> None:
    """
    メールにラベルを追加

    Args:
        email_id: Gmail メールID
        label_name: 追加するラベル名
    """

def remove_label(self, email_id: str, label_name: str) -> None:
    """
    メールからラベルを削除（テスト用）

    Args:
        email_id: Gmail メールID
        label_name: 削除するラベル名
    """
```

### 2. Calendar Client API

#### イベント作成・更新
```python
def create_or_update_event(
    self,
    event_data: CalendarEventData,
    duplicate_check_field: str
) -> str:
    """
    重複検出付きでカレンダーイベントを作成/更新

    Args:
        event_data: カレンダーイベントデータ
        duplicate_check_field: 重複検出用フィールド（確認番号/予約番号）

    Returns:
        作成/更新されたイベントID

    Logic:
        1. duplicate_check_fieldで既存イベント検索
        2. 見つかった場合: 更新
        3. 見つからない場合: 新規作成
    """
```

#### イベント検索・削除
```python
def search_events_by_summary(self, search_term: str) -> List[Dict]:
    """
    サマリー文字列でイベントを検索

    Args:
        search_term: 検索文字列

    Returns:
        マッチしたイベントのリスト
    """

def delete_event(self, event_id: str) -> None:
    """
    イベントを削除（テスト用）

    Args:
        event_id: 削除するイベントID
    """
```

### 3. OpenAI Client API

#### 航空券情報抽出
```python
def extract_flight_info(self, email_content: str) -> Dict[str, Any]:
    """
    航空券メールから予約情報を抽出

    Args:
        email_content: メール本文

    Returns:
        構造化された航空券情報

    Output Format:
        {
            "confirmation_code": str | null,
            "booking_reference": str,
            "passenger_name": str,
            "outbound_segments": [FlightSegment, ...],
            "return_segments": [FlightSegment, ...]
        }
    """
```

#### カーシェア情報抽出
```python
def extract_carshare_info(self, email_content: str) -> Dict[str, Any]:
    """
    カーシェアメールから予約情報を抽出

    Args:
        email_content: メール本文

    Returns:
        構造化されたカーシェア情報

    Output Format:
        {
            "provider": "TIMES_CAR" | "MITSUI_CARSHARE",
            "booking_reference": str,
            "user_name": str,
            "station": {
                "station_name": str,
                "address": str | null
            },
            "start_datetime": "YYYY-MM-DDTHH:MM:SS",
            "end_datetime": "YYYY-MM-DDTHH:MM:SS",
            "status": "RESERVED" | "CHANGED" | "CANCELLED" | "COMPLETED"
        }
    """
```

## Data Models

### 1. EmailMessage

```python
class EmailMessage(BaseModel):
    """Gmail API から取得されるメール情報"""

    id: str                    # Gmail メールID
    subject: str               # 件名
    body: str                  # 本文
    domain: str                # 送信元ドメイン
    datetime: datetime         # 受信日時（日本時間）

    # 計算プロパティ
    @property
    def is_promotional(self) -> bool:
        """プロモーションメールかどうか判定"""
        promotional_patterns = [
            "キャンペーン", "お知らせ", "メンテナンス",
            "プレゼント", "特典", "ポイント", "割引"
        ]
        return any(pattern in self.subject for pattern in promotional_patterns)
```

### 2. FlightBooking

```python
class FlightSegment(BaseModel):
    """航空便セグメント情報"""

    flight_number: str         # 便名（例: "NH006"）
    departure_airport: str     # 出発空港コード
    arrival_airport: str       # 到着空港コード
    departure_datetime: datetime  # 出発日時
    arrival_datetime: datetime    # 到着日時
    seat_number: Optional[str] = None  # 座席番号

class FlightBooking(BaseModel):
    """航空券予約情報"""

    confirmation_code: Optional[str] = None  # 確認番号（優先）
    booking_reference: str                   # 予約番号（フォールバック）
    passenger_name: str                      # 搭乗者名
    outbound_segments: List[FlightSegment]   # 往路便
    return_segments: List[FlightSegment] = []  # 復路便（片道の場合は空）

    # 計算プロパティ
    @property
    def unique_identifier(self) -> str:
        """重複検出用の一意識別子"""
        return self.confirmation_code or self.booking_reference

    @property
    def total_segments(self) -> int:
        """総セグメント数"""
        return len(self.outbound_segments) + len(self.return_segments)
```

### 3. CarShareBooking

```python
class CarShareProvider(str, Enum):
    """カーシェアプロバイダー"""
    TIMES_CAR = "TIMES_CAR"
    MITSUI_CARSHARE = "MITSUI_CARSHARE"

class CarShareStatus(str, Enum):
    """カーシェア予約ステータス"""
    RESERVED = "RESERVED"    # 予約済み
    CHANGED = "CHANGED"      # 変更済み
    CANCELLED = "CANCELLED"  # キャンセル済み
    COMPLETED = "COMPLETED"  # 利用完了

class StationInfo(BaseModel):
    """ステーション情報"""
    station_name: str              # ステーション名
    address: Optional[str] = None  # 住所

class CarShareBooking(BaseModel):
    """カーシェア予約情報"""

    provider: CarShareProvider     # プロバイダー
    booking_reference: str         # 予約番号
    user_name: str                # 利用者名
    station: StationInfo          # ステーション情報
    start_datetime: datetime      # 利用開始日時
    end_datetime: datetime        # 利用終了日時
    status: CarShareStatus = CarShareStatus.RESERVED  # ステータス

    # 計算プロパティ
    @property
    def duration_hours(self) -> float:
        """利用時間（時間単位）"""
        delta = self.end_datetime - self.start_datetime
        return delta.total_seconds() / 3600

    @property
    def status_emoji(self) -> str:
        """ステータス絵文字"""
        return {
            CarShareStatus.RESERVED: "🚗",
            CarShareStatus.CHANGED: "🔄",
            CarShareStatus.CANCELLED: "❌",
            CarShareStatus.COMPLETED: "✅"
        }[self.status]
```

### 4. ProcessingResult

```python
class EmailType(str, Enum):
    """メール種別"""
    FLIGHT = "FLIGHT"
    CAR_SHARE = "CAR_SHARE"

class ProcessingResult(BaseModel):
    """メール処理結果"""

    email_id: str                           # 処理対象メールID
    email_type: EmailType                   # メール種別
    success: bool                           # 処理成功フラグ
    extracted_data: Optional[Dict] = None   # 抽出されたデータ
    error_message: Optional[str] = None     # エラーメッセージ
    processing_time: Optional[float] = None # 処理時間（秒）

    # 計算プロパティ
    @property
    def is_promotional_skip(self) -> bool:
        """プロモーションスキップかどうか"""
        return not self.success and self.error_message == "Skipped promotional email"

    @property
    def is_no_info_found(self) -> bool:
        """情報なしかどうか"""
        no_info_messages = [
            "No flight information found in email",
            "No car sharing information found in email"
        ]
        return not self.success and self.error_message in no_info_messages
```

## Processing Interfaces

### 1. BaseEmailProcessor

```python
class BaseEmailProcessor(ABC):
    """メール処理基底クラス"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.openai_client = OpenAIClient(settings)
        self.calendar_client = CalendarClient(settings)

    @abstractmethod
    def can_process(self, email: EmailMessage) -> bool:
        """
        このプロセッサーでメールを処理できるかチェック

        Args:
            email: 判定対象メール

        Returns:
            処理可能な場合 True
        """

    @abstractmethod
    def process(self, email: EmailMessage) -> ProcessingResult:
        """
        メール処理を実行

        Args:
            email: 処理対象メール

        Returns:
            処理結果
        """

    def should_process_with_ai(self, email: EmailMessage) -> bool:
        """
        AI解析を実行すべきかの判定（スマートフィルタリング）

        Args:
            email: 判定対象メール

        Returns:
            AI解析すべき場合 True
        """
        return not email.is_promotional
```

### 2. EmailProcessorFactory

```python
class EmailProcessorFactory:
    """プロセッサーファクトリー"""

    def __init__(self, settings: Settings):
        self._processors = [
            FlightEmailProcessor(settings),
            CarShareEmailProcessor(settings),
            # 新しいプロセッサーをここに追加
        ]

    def get_processor(self, email: EmailMessage) -> Optional[BaseEmailProcessor]:
        """
        メールに適したプロセッサーを取得

        Args:
            email: 処理対象メール

        Returns:
            適切なプロセッサー（見つからない場合 None）
        """
        for processor in self._processors:
            if processor.can_process(email):
                return processor
        return None
```

## Integration Patterns

### 1. OAuth2 認証フロー

```python
def get_access_token(self) -> str:
    """
    リフレッシュトークンからアクセストークンを取得

    Returns:
        有効なアクセストークン

    Raises:
        GmailCalendarSyncError: 認証に失敗した場合
    """
    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        raise GmailCalendarSyncError(f"Failed to get access token: {e}")
```

### 2. 重複検出パターン

```python
def find_existing_event(self, unique_id: str, search_scope_days: int = 30) -> Optional[str]:
    """
    確認番号/予約番号で既存イベントを検索

    Args:
        unique_id: 検索する一意識別子
        search_scope_days: 検索範囲（日数）

    Returns:
        既存イベントID（見つからない場合 None）
    """
    # 過去30日間のイベントを検索
    time_min = (datetime.now() - timedelta(days=search_scope_days)).isoformat() + "Z"
    time_max = (datetime.now() + timedelta(days=365)).isoformat() + "Z"

    events = self.service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        q=unique_id,  # 確認番号/予約番号で検索
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    for event in events.get("items", []):
        if unique_id in event.get("summary", ""):
            return event["id"]

    return None
```

### 3. エラーハンドリングパターン

```python
def safe_api_call(self, api_func: Callable, *args, **kwargs) -> Any:
    """
    安全なAPI呼び出しラッパー

    Args:
        api_func: 呼び出すAPI関数
        *args, **kwargs: API関数の引数

    Returns:
        API呼び出し結果

    Raises:
        GmailCalendarSyncError: 回復不能なエラーの場合
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return api_func(*args, **kwargs)
        except httpx.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
                continue
            elif e.response.status_code >= 500:  # Server error
                if attempt == max_retries - 1:
                    raise GmailCalendarSyncError(f"Server error after {max_retries} attempts: {e}")
                time.sleep(1)
                continue
            else:
                raise GmailCalendarSyncError(f"API error: {e}")
        except Exception as e:
            raise GmailCalendarSyncError(f"Unexpected error: {e}")

    raise GmailCalendarSyncError(f"Max retries ({max_retries}) exceeded")
```

## Error Handling

### 1. カスタム例外

```python
class GmailCalendarSyncError(Exception):
    """Gmail Calendar Sync固有のエラー"""
    pass

class AuthenticationError(GmailCalendarSyncError):
    """認証エラー"""
    pass

class DataExtractionError(GmailCalendarSyncError):
    """データ抽出エラー"""
    pass

class CalendarIntegrationError(GmailCalendarSyncError):
    """カレンダー連携エラー"""
    pass
```

### 2. エラー分類

| エラー種別 | 対応方法 | 例 |
|-----------|---------|---|
| 認証エラー | トークン再取得 | OAuth2トークン期限切れ |
| レート制限 | 指数バックオフ | API呼び出し頻度過多 |
| データ不正 | スキップ・ログ出力 | メール形式不明 |
| ネットワークエラー | リトライ | 一時的な接続障害 |
| システムエラー | 処理中断 | 設定不備・権限不足 |

### 3. ログ出力パターン

```python
# 成功ログ
logger.info(
    "Email processed successfully",
    email_id=email.id,
    email_type=email_type.value,
    processing_time=processing_time,
    extracted_data_keys=list(extracted_data.keys())
)

# 警告ログ
logger.warning(
    "Email processing failed",
    email_id=email.id,
    error_type=type(e).__name__,
    error_message=str(e),
    email_subject=email.subject[:100]
)

# エラーログ
logger.error(
    "Unexpected error processing email",
    email_id=email.id,
    error=str(e),
    traceback=traceback.format_exc()
)
```

## Usage Examples

### 1. 基本的な使用方法

```python
# 設定読み込み
settings = get_settings()

# クライアント初期化
gmail_client = GmailClient(settings)
calendar_client = CalendarClient(settings)
processor_factory = EmailProcessorFactory(settings)

# メール取得・処理
emails = gmail_client.get_all_supported_emails(since_hours=8)
for email in emails:
    processor = processor_factory.get_processor(email)
    if processor:
        result = processor.process(email)
        if result.success:
            print(f"✅ Processed: {email.subject}")
        else:
            print(f"❌ Failed: {result.error_message}")
```

### 2. 期間指定実行

```python
# 時間単位指定（推奨）
emails = gmail_client.get_all_supported_emails(since_hours=3)

# 絶対日付指定
emails = gmail_client.get_all_supported_emails(
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# 日単位指定（後方互換性）
emails = gmail_client.get_all_supported_emails(since_days=7)
```

### 3. カスタムプロセッサー実装

```python
class HotelEmailProcessor(BaseEmailProcessor):
    """ホテル予約メール専用プロセッサー"""

    def can_process(self, email: EmailMessage) -> bool:
        return email.domain in ["booking.com", "hotels.com"]

    def process(self, email: EmailMessage) -> ProcessingResult:
        try:
            # スマートフィルタリング
            if not self.should_process_with_ai(email):
                return ProcessingResult(
                    email_id=email.id,
                    email_type=EmailType.HOTEL,
                    success=False,
                    error_message="Skipped promotional email"
                )

            # AI解析
            extracted_data = self.openai_client.extract_hotel_info(email.body)

            # カレンダーイベント作成
            event_data = self._create_hotel_event_data(extracted_data)
            event_id = self.calendar_client.create_or_update_event(
                event_data,
                extracted_data["confirmation_code"]
            )

            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.HOTEL,
                success=True,
                extracted_data=extracted_data
            )

        except Exception as e:
            return ProcessingResult(
                email_id=email.id,
                email_type=EmailType.HOTEL,
                success=False,
                error_message=str(e)
            )
```

### 4. テスト・デバッグ用途

```python
# デバッグ実行
import logging
logging.basicConfig(level=logging.DEBUG)

# 最近1時間のメールのみテスト
emails = gmail_client.get_all_supported_emails(since_hours=1)

# 特定メールの処理詳細確認
for email in emails:
    print(f"Subject: {email.subject}")
    print(f"Domain: {email.domain}")
    print(f"Is Promotional: {email.is_promotional}")

    processor = processor_factory.get_processor(email)
    if processor:
        result = processor.process(email)
        print(f"Result: {result}")
```

---

📚 実装の詳細とサンプルコードは [examples/](examples/) ディレクトリを参照してください。
