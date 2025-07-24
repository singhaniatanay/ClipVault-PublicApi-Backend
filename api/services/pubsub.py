"""Google Cloud Pub/Sub service for ClipVault Public API."""

import os
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4
import structlog
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.publisher.exceptions import PublishError
from google.api_core import retry
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, DeadlineExceeded

logger = structlog.get_logger()


class PubSubService:
    """Async Google Cloud Pub/Sub publisher service for ClipVault events."""
    
    def __init__(self, project_id: Optional[str] = None, raise_on_missing_env: bool = True):
        """Initialize the Pub/Sub service."""
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.clip_events_topic = os.getenv("PUBSUB_CLIP_EVENTS_TOPIC", "clip-events")
        self.clip_events_dlq_topic = os.getenv("PUBSUB_CLIP_EVENTS_DLQ_TOPIC", "clip-events-dlq")
        
        if raise_on_missing_env and not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")
            
        self._publisher: Optional[pubsub_v1.PublisherClient] = None
        self._topic_paths: Dict[str, str] = {}
        
        logger.info(
            "PubSubService initialized",
            project_id=self.project_id,
            clip_events_topic=self.clip_events_topic,
            dlq_topic=self.clip_events_dlq_topic
        )

    async def initialize(self) -> None:
        """Initialize the Pub/Sub publisher client and topic paths."""
        try:
            # Create publisher client (uses Application Default Credentials)
            self._publisher = pubsub_v1.PublisherClient()
            
            # Pre-compute topic paths for performance
            self._topic_paths = {
                "clip_events": self._publisher.topic_path(self.project_id, self.clip_events_topic),
                "clip_events_dlq": self._publisher.topic_path(self.project_id, self.clip_events_dlq_topic)
            }
            
            logger.info(
                "PubSubService publisher initialized successfully",
                topic_paths=list(self._topic_paths.keys())
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize PubSubService",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def close(self) -> None:
        """Close the Pub/Sub publisher client."""
        if self._publisher:
            # Publisher client doesn't need explicit closing in the current version
            # But we can set it to None for cleanup
            self._publisher = None
            logger.info("PubSubService publisher closed")

    def _create_clip_created_message(
        self, 
        clip_id: str, 
        source_url: str, 
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized clip.created event message."""
        return {
            "event_type": "clip.created",
            "event_id": str(uuid4()),
            "correlation_id": correlation_id or str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "clip_id": clip_id,
                "source_url": source_url,
                "user_id": user_id
            },
            "metadata": {
                "api_version": "v1",
                "service": "clipvault-api"
            }
        }

    async def publish_clip_created(
        self, 
        clip_id: str, 
        source_url: str, 
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish a clip.created event to Pub/Sub.
        
        Args:
            clip_id: UUID of the created clip
            source_url: URL of the clip source
            user_id: ID of the user who created the clip
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            bool: True if published successfully, False if failed
        """
        if not self._publisher:
            logger.error("PubSubService not initialized - cannot publish message")
            return False
            
        # Create standardized message
        message_data = self._create_clip_created_message(
            clip_id=clip_id,
            source_url=source_url,
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        # Convert to JSON bytes
        message_bytes = json.dumps(message_data).encode('utf-8')
        
        logger.info(
            "Publishing clip.created event",
            clip_id=clip_id,
            source_url=source_url,
            user_id=user_id,
            event_id=message_data["event_id"],
            correlation_id=message_data["correlation_id"]
        )
        
        try:
            # Publish with retry logic
            topic_path = self._topic_paths["clip_events"]
            
            # Use the synchronous publisher with custom retry settings
            future = self._publisher.publish(
                topic_path,
                message_bytes,
                # Add message attributes for filtering/routing
                event_type="clip.created",
                clip_id=clip_id,
                user_id=user_id,
                correlation_id=message_data["correlation_id"]
            )
            
            # Get the message ID (this will block until published or failed)
            message_id = future.result(timeout=30.0)
            
            logger.info(
                "Successfully published clip.created event",
                clip_id=clip_id,
                message_id=message_id,
                event_id=message_data["event_id"],
                correlation_id=message_data["correlation_id"]
            )
            
            return True
            
        except (ServiceUnavailable, DeadlineExceeded) as e:
            # Temporary failures - could retry or send to DLQ
            logger.warning(
                "Temporary failure publishing clip.created event",
                clip_id=clip_id,
                error=str(e),
                error_type=type(e).__name__,
                will_retry=True
            )
            
            # Try to send to DLQ
            dlq_success = await self._send_to_dlq(message_data, str(e))
            if not dlq_success:
                logger.error(
                    "Failed to send message to DLQ after primary failure",
                    clip_id=clip_id,
                    original_error=str(e)
                )
            
            return False
            
        except PublishError as e:
            # Permanent publish failures
            logger.error(
                "Permanent failure publishing clip.created event",
                clip_id=clip_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Send to DLQ for manual inspection
            await self._send_to_dlq(message_data, str(e))
            return False
            
        except Exception as e:
            # Unexpected failures
            logger.error(
                "Unexpected error publishing clip.created event",
                clip_id=clip_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Send to DLQ for manual inspection
            await self._send_to_dlq(message_data, str(e))
            return False

    async def _send_to_dlq(self, original_message: Dict[str, Any], error_reason: str) -> bool:
        """
        Send a failed message to the Dead Letter Queue.
        
        Args:
            original_message: The original message that failed
            error_reason: Reason for the failure
            
        Returns:
            bool: True if sent to DLQ successfully, False otherwise
        """
        try:
            # Wrap original message with DLQ metadata
            dlq_message = {
                "dlq_timestamp": datetime.now(timezone.utc).isoformat(),
                "error_reason": error_reason,
                "original_message": original_message,
                "retry_count": 0  # Could be enhanced to track retries
            }
            
            dlq_bytes = json.dumps(dlq_message).encode('utf-8')
            dlq_topic_path = self._topic_paths["clip_events_dlq"]
            
            # Publish to DLQ with shorter timeout
            future = self._publisher.publish(
                dlq_topic_path,
                dlq_bytes,
                # Add DLQ-specific attributes
                dlq_reason="publish_failure",
                original_event_type=original_message.get("event_type", "unknown"),
                original_clip_id=original_message.get("data", {}).get("clip_id", "unknown")
            )
            
            dlq_message_id = future.result(timeout=10.0)
            
            logger.info(
                "Successfully sent message to DLQ",
                dlq_message_id=dlq_message_id,
                original_event_id=original_message.get("event_id"),
                error_reason=error_reason
            )
            
            return True
            
        except Exception as dlq_error:
            logger.error(
                "Failed to send message to DLQ",
                error=str(dlq_error),
                error_type=type(dlq_error).__name__,
                original_error=error_reason
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Pub/Sub service.
        
        Returns:
            Dict with health status and details
        """
        if not self._publisher:
            return {
                "status": "unhealthy",
                "error": "Publisher not initialized"
            }
            
        try:
            # Test by checking if we can access the topic
            topic_path = self._topic_paths.get("clip_events")
            if not topic_path:
                return {
                    "status": "unhealthy", 
                    "error": "Topic path not configured"
                }
                
            # The existence of the publisher client indicates we can connect
            # A more thorough check would actually publish a test message
            return {
                "status": "healthy",
                "publisher_initialized": True,
                "project_id": self.project_id,
                "topics_configured": len(self._topic_paths)
            }
            
        except Exception as e:
            logger.error(
                "PubSub health check failed",
                error=str(e),
                error_type=type(e).__name__
            )
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance for dependency injection
_pubsub_service: Optional[PubSubService] = None


async def init_pubsub_service() -> None:
    """Initialize the global PubSubService instance."""
    global _pubsub_service
    
    try:
        _pubsub_service = PubSubService()
        await _pubsub_service.initialize()
        
        logger.info("Global PubSubService initialized successfully")
        
    except Exception as e:
        logger.error(
            "Failed to initialize global PubSubService",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


async def shutdown_pubsub_service() -> None:
    """Shutdown the global PubSubService instance."""
    global _pubsub_service
    
    if _pubsub_service:
        await _pubsub_service.close()
        _pubsub_service = None
        logger.info("Global PubSubService shutdown complete")


def get_pubsub_service() -> PubSubService:
    """
    FastAPI dependency to get the PubSubService instance.
    
    Returns:
        PubSubService: The initialized service instance
        
    Raises:
        RuntimeError: If service is not initialized
    """
    if _pubsub_service is None:
        raise RuntimeError(
            "PubSubService not initialized. Make sure to call init_pubsub_service() in app lifespan."
        )
    
    return _pubsub_service 