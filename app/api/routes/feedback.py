"""
Feedback endpoints.

This module provides endpoints for users to submit feedback on sentiment predictions.
This feedback is used to monitor model performance and trigger active learning workflows.
"""

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
):
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
    logger = get_contextual_logger(
        __name__,
        endpoint="feedback",
        prediction_id=payload.prediction_id,
    )

    logger.info("Received feedback submission")

    try:
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
            "prediction_id": payload.prediction_id
        }

    except Exception as e:
        logger.error(
            "Error processing feedback request",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error processing feedback",
        )
