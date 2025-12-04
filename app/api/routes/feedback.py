"""
Feedback endpoints.

This module provides endpoints for users to submit feedback on sentiment predictions.
This feedback is used to monitor model performance and trigger active learning workflows.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.requests import FeedbackRequest
from app.core.dependencies import get_feedback_service
from app.core.logging import get_contextual_logger
from app.services.feedback_service import FeedbackService

router = APIRouter()


@router.post(
    "/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit prediction feedback",
    description="Submit user feedback (corrections) for a specific sentiment prediction.",
)
async def submit_feedback(
    payload: FeedbackRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> Dict[str, Any]:
    """Submit feedback for a prediction.

    Accepts user feedback including the corrected label and optional comments.
    This data is published to the feedback system for analysis and model retraining.

    Args:
        payload: The feedback data matching FeedbackRequest schema.
        feedback_service: The feedback service instance.

    Returns:
        A success message.

    Raises:
        HTTPException: If the feedback submission fails.
    """
    # We create the logger first to ensure we have context even if subsequent steps fail
    # Note: validation errors are handled by global exception handler before this point
    prediction_id_str = str(payload.prediction_id)
    logger = get_contextual_logger(
        __name__,
        endpoint="feedback",
        prediction_id=prediction_id_str,
    )

    logger.info("Received feedback submission")

    # Use service to submit feedback
    # Service handles its own exceptions and returns False on failure
    success = await feedback_service.submit_feedback(payload)
    
    if not success:
        logger.error("Failed to submit feedback to downstream systems")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback system unavailable",
        )

    logger.info(
        "Feedback submitted successfully",
        corrected_label=payload.corrected_label
    )
    
    return {
        "status": "success",
        "message": "Feedback received and queued for processing",
        "prediction_id": prediction_id_str
    }
