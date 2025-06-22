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
    cost_usd: float = Field(..., description="Estimated cost in USD")
    success: bool = Field(..., description="Whether the API call was successful")
    error_message: str | None = Field(None, description="Error message if failed")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the API call"
    )

    @property
    def cost_per_1k_tokens_prompt(self) -> float:
        """Cost per 1K prompt tokens for gpt-3.5-turbo."""
        return 0.0015  # $0.0015 per 1K tokens as of 2024

    @property
    def cost_per_1k_tokens_completion(self) -> float:
        """Cost per 1K completion tokens for gpt-3.5-turbo."""
        return 0.002  # $0.002 per 1K tokens as of 2024

    def calculate_cost(self) -> float:
        """Calculate the estimated cost in USD."""
        prompt_cost = (self.usage.prompt_tokens / 1000) * self.cost_per_1k_tokens_prompt
        completion_cost = (
            self.usage.completion_tokens / 1000
        ) * self.cost_per_1k_tokens_completion
        return prompt_cost + completion_cost

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
