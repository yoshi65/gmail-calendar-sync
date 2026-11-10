"""OpenAI API usage metrics models."""

from datetime import datetime

from pydantic import BaseModel, Field


class OpenAIUsage(BaseModel):
    """OpenAI API usage metrics."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens used")


class OpenAIMetrics(BaseModel):
    """Complete OpenAI API call metrics."""

    model: str = Field(..., description="Model used for the API call")
    email_type: str = Field(
        ..., description="Type of email processed (flight/carshare)"
    )
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    usage: OpenAIUsage = Field(..., description="Token usage information")
    cost_usd: float | None = Field(
        None,
        description="Uncached standard-rate estimate in USD; null for unknown pricing",
    )
    success: bool = Field(..., description="Whether the API call was successful")
    error_message: str | None = Field(None, description="Error message if failed")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the API call"
    )

    @property
    def cost_per_1k_tokens_prompt(self) -> float | None:
        """Standard uncached rates; unknown models are not estimated."""
        if self.model != "gpt-5.6-terra":
            return None
        return 0.004 if self.usage.prompt_tokens > 272_000 else 0.002

    @property
    def cost_per_1k_tokens_completion(self) -> float | None:
        """Standard output rate matching the request context tier."""
        if self.model != "gpt-5.6-terra":
            return None
        return 0.018 if self.usage.prompt_tokens > 272_000 else 0.012

    def calculate_cost(self) -> float | None:
        """Estimate uncached cost, not the billed amount (pricing: 2026-11-10)."""
        input_rate = self.cost_per_1k_tokens_prompt
        output_rate = self.cost_per_1k_tokens_completion
        if input_rate is None or output_rate is None:
            return None
        return (
            self.usage.prompt_tokens * input_rate
            + self.usage.completion_tokens * output_rate
        ) / 1000

    @classmethod
    def create_from_response(
        cls,
        model: str,
        email_type: str,
        processing_time_ms: float,
        response,
        success: bool = True,
        error_message: str | None = None,
    ) -> "OpenAIMetrics":
        """Create OpenAIMetrics from OpenAI API response."""
        if success and response and hasattr(response, "usage"):
            usage = OpenAIUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        else:
            # Default values for failed calls
            usage = OpenAIUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )

        metrics = cls(
            model=model,
            email_type=email_type,
            processing_time_ms=processing_time_ms,
            usage=usage,
            cost_usd=0.0,  # Will be calculated next
            success=success,
            error_message=error_message,
        )

        # Calculate cost
        metrics.cost_usd = metrics.calculate_cost()
        return metrics
