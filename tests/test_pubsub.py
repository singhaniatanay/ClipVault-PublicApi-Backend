"""Tests for the Pub/Sub service."""

import pytest
import json
import base64
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from google.cloud.pubsub_v1.publisher.exceptions import PublishError
from google.api_core.exceptions import ServiceUnavailable, DeadlineExceeded

from api.services.pubsub import PubSubService, init_pubsub_service, shutdown_pubsub_service, get_pubsub_service


class TestPubSubService:
    """Test cases for PubSubService class."""

    @pytest.fixture
    def pubsub_service(self):
        """Create a PubSubService instance for testing."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'PUBSUB_CLIP_EVENTS_TOPIC': 'test-clip-events',
            'PUBSUB_CLIP_EVENTS_DLQ_TOPIC': 'test-clip-events-dlq'
        }):
            service = PubSubService(raise_on_missing_env=False)
            return service

    @pytest.fixture
    def mock_publisher_client(self):
        """Mock Google Cloud Pub/Sub publisher client."""
        with patch('api.services.pubsub.pubsub_v1.PublisherClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            
            # Mock topic path creation
            mock_instance.topic_path.side_effect = lambda project, topic: f"projects/{project}/topics/{topic}"
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_initialize_success(self, pubsub_service, mock_publisher_client):
        """Test successful initialization of PubSub service."""
        await pubsub_service.initialize()
        
        assert pubsub_service._publisher is not None
        assert pubsub_service._topic_paths["clip_events"] == "projects/test-project/topics/test-clip-events"
        assert pubsub_service._topic_paths["clip_events_dlq"] == "projects/test-project/topics/test-clip-events-dlq"

    @pytest.mark.asyncio
    async def test_initialize_failure(self, pubsub_service):
        """Test failure during PubSub service initialization."""
        with patch('api.services.pubsub.pubsub_v1.PublisherClient', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await pubsub_service.initialize()

    def test_create_clip_created_message(self, pubsub_service):
        """Test creation of base64 encoded clip.created message."""
        clip_id = str(uuid4())
        source_url = "https://example.com/article"
        user_id = str(uuid4())
        correlation_id = str(uuid4())
        
        base64_message = pubsub_service._create_clip_created_message(
            clip_id=clip_id,
            source_url=source_url,
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        # Decode the base64 message to verify content
        decoded_bytes = base64.b64decode(base64_message)
        decoded_message = json.loads(decoded_bytes.decode('utf-8'))
        
        assert decoded_message["clip_id"] == clip_id
        assert decoded_message["source_url"] == source_url
        assert decoded_message["user_id"] == user_id
        assert "created_at" in decoded_message

    @pytest.mark.asyncio
    async def test_publish_clip_created_success(self, pubsub_service, mock_publisher_client):
        """Test successful publishing of clip.created event."""
        # Initialize the service
        await pubsub_service.initialize()
        
        # Mock successful publish
        mock_future = Mock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher_client.publish.return_value = mock_future
        
        clip_id = str(uuid4())
        source_url = "https://example.com/article"
        user_id = str(uuid4())
        
        result = await pubsub_service.publish_clip_created(
            clip_id=clip_id,
            source_url=source_url,
            user_id=user_id
        )
        
        assert result is True
        mock_publisher_client.publish.assert_called_once()
        
        # Verify the published message
        call_args = mock_publisher_client.publish.call_args
        topic_path, message_bytes = call_args[0]
        message_attrs = call_args[1]
        
        assert topic_path == "projects/test-project/topics/test-clip-events"
        
        # Parse the base64 encoded message
        base64_data = message_bytes.decode('utf-8')
        decoded_bytes = base64.b64decode(base64_data)
        message_data = json.loads(decoded_bytes.decode('utf-8'))
        assert message_data["clip_id"] == clip_id
        assert message_data["source_url"] == source_url
        assert message_data["user_id"] == user_id
        assert "created_at" in message_data
        
        # Check message attributes
        assert message_attrs["event_type"] == "clip.created"
        assert message_attrs["clip_id"] == clip_id
        assert message_attrs["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_publish_without_initialization(self, pubsub_service):
        """Test publishing fails when service is not initialized."""
        result = await pubsub_service.publish_clip_created(
            clip_id=str(uuid4()),
            source_url="https://example.com",
            user_id=str(uuid4())
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_service_unavailable_sends_to_dlq(self, pubsub_service, mock_publisher_client):
        """Test that ServiceUnavailable error sends message to DLQ."""
        await pubsub_service.initialize()
        
        # Mock publish failure and DLQ success
        mock_future = Mock()
        mock_future.result.side_effect = ServiceUnavailable("Service temporarily unavailable")
        
        mock_dlq_future = Mock()
        mock_dlq_future.result.return_value = "dlq-message-id"
        
        # First call fails, second call (DLQ) succeeds
        mock_publisher_client.publish.side_effect = [mock_future, mock_dlq_future]
        
        result = await pubsub_service.publish_clip_created(
            clip_id=str(uuid4()),
            source_url="https://example.com",
            user_id=str(uuid4())
        )
        
        assert result is False
        assert mock_publisher_client.publish.call_count == 2
        
        # Verify DLQ message
        dlq_call_args = mock_publisher_client.publish.call_args_list[1]
        dlq_topic_path, dlq_message_bytes = dlq_call_args[0]
        assert dlq_topic_path == "projects/test-project/topics/test-clip-events-dlq"
        
        dlq_message = json.loads(dlq_message_bytes.decode('utf-8'))
        assert dlq_message["error_reason"] == "503 Service temporarily unavailable"
        assert dlq_message["original_message"]["event_type"] == "clip.created"

    @pytest.mark.asyncio
    async def test_publish_permanent_failure_sends_to_dlq(self, pubsub_service, mock_publisher_client):
        """Test that permanent failures send message to DLQ."""
        await pubsub_service.initialize()
        
        # Mock publish failure and DLQ success
        mock_future = Mock()
        mock_future.result.side_effect = PublishError("Permanent failure")
        
        mock_dlq_future = Mock()
        mock_dlq_future.result.return_value = "dlq-message-id"
        
        mock_publisher_client.publish.side_effect = [mock_future, mock_dlq_future]
        
        result = await pubsub_service.publish_clip_created(
            clip_id=str(uuid4()),
            source_url="https://example.com",
            user_id=str(uuid4())
        )
        
        assert result is False
        assert mock_publisher_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_dlq_failure_is_logged(self, pubsub_service, mock_publisher_client):
        """Test that DLQ failures are properly logged."""
        await pubsub_service.initialize()
        
        # Mock both primary and DLQ publish failures
        mock_future = Mock()
        mock_future.result.side_effect = PublishError("Permanent failure")
        
        mock_dlq_future = Mock()
        mock_dlq_future.result.side_effect = Exception("DLQ also failed")
        
        mock_publisher_client.publish.side_effect = [mock_future, mock_dlq_future]
        
        with patch('api.services.pubsub.logger') as mock_logger:
            result = await pubsub_service.publish_clip_created(
                clip_id=str(uuid4()),
                source_url="https://example.com",
                user_id=str(uuid4())
            )
            
            assert result is False
            
            # Verify error logging for DLQ failure
            dlq_error_calls = [call for call in mock_logger.error.call_args_list 
                             if "Failed to send message to DLQ" in str(call)]
            assert len(dlq_error_calls) > 0

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, pubsub_service, mock_publisher_client):
        """Test health check when service is healthy."""
        await pubsub_service.initialize()
        
        health = await pubsub_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["publisher_initialized"] is True
        assert health["project_id"] == "test-project"
        assert health["topics_configured"] == 2

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, pubsub_service):
        """Test health check when service is not initialized."""
        health = await pubsub_service.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["error"] == "Publisher not initialized"

    @pytest.mark.asyncio
    async def test_close_service(self, pubsub_service, mock_publisher_client):
        """Test closing the PubSub service."""
        await pubsub_service.initialize()
        assert pubsub_service._publisher is not None
        
        await pubsub_service.close()
        assert pubsub_service._publisher is None


class TestGlobalServiceManagement:
    """Test cases for global service initialization and management."""

    @pytest.mark.asyncio
    async def test_init_and_shutdown_global_service(self):
        """Test initialization and shutdown of global service."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'PUBSUB_CLIP_EVENTS_TOPIC': 'test-clip-events',
            'PUBSUB_CLIP_EVENTS_DLQ_TOPIC': 'test-clip-events-dlq'
        }):
            with patch('api.services.pubsub.pubsub_v1.PublisherClient'):
                # Test initialization
                await init_pubsub_service()
                
                # Test that service is available
                service = get_pubsub_service()
                assert service is not None
                assert isinstance(service, PubSubService)
                
                # Test shutdown
                await shutdown_pubsub_service()

    def test_get_service_before_init_raises_error(self):
        """Test that getting service before initialization raises error."""
        with patch('api.services.pubsub._pubsub_service', None):
            with pytest.raises(RuntimeError, match="PubSubService not initialized"):
                get_pubsub_service()

    @pytest.mark.asyncio
    async def test_init_service_failure_propagates(self):
        """Test that initialization failures are properly propagated."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project'
        }):
            with patch('api.services.pubsub.PubSubService.initialize', side_effect=Exception("Init failed")):
                with pytest.raises(Exception, match="Init failed"):
                    await init_pubsub_service()


class TestEnvironmentConfiguration:
    """Test cases for environment variable handling."""

    def test_missing_project_id_raises_error(self):
        """Test that missing GOOGLE_CLOUD_PROJECT raises error."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT environment variable is required"):
                PubSubService(raise_on_missing_env=True)

    def test_default_topic_names(self):
        """Test default topic names when env vars not set."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project'
        }, clear=True):
            service = PubSubService(raise_on_missing_env=False)
            
            assert service.clip_events_topic == "clip-events"
            assert service.clip_events_dlq_topic == "clip-events-dlq"

    def test_custom_topic_names(self):
        """Test custom topic names from environment variables."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'PUBSUB_CLIP_EVENTS_TOPIC': 'custom-clips',
            'PUBSUB_CLIP_EVENTS_DLQ_TOPIC': 'custom-clips-dlq'
        }):
            service = PubSubService()
            
            assert service.clip_events_topic == "custom-clips"
            assert service.clip_events_dlq_topic == "custom-clips-dlq"


class TestMessageFormat:
    """Test cases for message format validation."""

    @pytest.fixture
    def pubsub_service(self):
        """Create a PubSubService instance for testing."""
        with patch.dict('os.environ', {
            'GOOGLE_CLOUD_PROJECT': 'test-project'
        }):
            return PubSubService(raise_on_missing_env=False)

    def test_message_has_required_fields(self, pubsub_service):
        """Test that generated base64 messages have all required fields when decoded."""
        base64_message = pubsub_service._create_clip_created_message(
            clip_id="test-clip-id",
            source_url="https://example.com",
            user_id="test-user-id"
        )
        
        # Decode the base64 message
        decoded_bytes = base64.b64decode(base64_message)
        message = json.loads(decoded_bytes.decode('utf-8'))
        
        # Required fields in the decoded message
        required_fields = ["clip_id", "source_url", "user_id", "created_at"]
        for field in required_fields:
            assert field in message

    def test_message_timestamp_format(self, pubsub_service):
        """Test that message created_at timestamp is in ISO format."""
        base64_message = pubsub_service._create_clip_created_message(
            clip_id="test-clip-id",
            source_url="https://example.com",
            user_id="test-user-id"
        )
        
        # Decode the base64 message
        decoded_bytes = base64.b64decode(base64_message)
        message = json.loads(decoded_bytes.decode('utf-8'))
        
        # Should be able to parse as ISO datetime
        timestamp = datetime.fromisoformat(message["created_at"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None

    def test_correlation_id_generation(self, pubsub_service):
        """Test that base64 message generation works with or without correlation ID."""
        # Test without correlation ID
        base64_message1 = pubsub_service._create_clip_created_message(
            clip_id="test-clip-id",
            source_url="https://example.com",
            user_id="test-user-id"
        )
        # Should still generate a valid base64 message
        decoded_bytes1 = base64.b64decode(base64_message1)
        message1 = json.loads(decoded_bytes1.decode('utf-8'))
        assert message1["clip_id"] == "test-clip-id"
        
        # Test with correlation ID (currently not stored in the data payload, but method should still work)
        custom_correlation_id = "custom-correlation-123"
        base64_message2 = pubsub_service._create_clip_created_message(
            clip_id="test-clip-id",
            source_url="https://example.com",
            user_id="test-user-id",
            correlation_id=custom_correlation_id
        )
        # Should still generate a valid base64 message
        decoded_bytes2 = base64.b64decode(base64_message2)
        message2 = json.loads(decoded_bytes2.decode('utf-8'))
        assert message2["clip_id"] == "test-clip-id" 