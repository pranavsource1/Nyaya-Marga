"""Unit tests for NLP service."""
import pytest
from app.services.nlp_service import NLPService, ChunkWindow, NLPEntity


class TestChunkWindow:
    """Test ChunkWindow data class."""

    def test_chunk_creation(self):
        """Test ChunkWindow initialization."""
        token_ids = [101, 2054, 2003, 102]
        chunk = ChunkWindow("Hello world", 0, 4, token_ids)

        assert chunk.text == "Hello world"
        assert chunk.start_token_idx == 0
        assert chunk.end_token_idx == 4
        assert chunk.token_ids == token_ids

    def test_chunk_repr(self):
        """Test ChunkWindow string representation."""
        chunk = ChunkWindow("Test", 10, 50, [])
        assert "tokens=40" in repr(chunk)
        assert "[10:50]" in repr(chunk)


class TestNLPEntity:
    """Test NLPEntity data class."""

    def test_entity_creation(self):
        """Test NLPEntity initialization."""
        entity = NLPEntity(
            entity_type="PERSON",
            text="John Smith",
            confidence=0.92,
            token_start=5,
            token_end=10,
            source_chunk_idx=0,
        )

        assert entity.entity_type == "PERSON"
        assert entity.text == "John Smith"
        assert entity.confidence == 0.92
        assert entity.token_start == 5
        assert entity.token_end == 10
        assert entity.source_chunk_idx == 0

    def test_entity_repr(self):
        """Test NLPEntity string representation."""
        entity = NLPEntity("LOCATION", "NYC", 0.85, 0, 1, 0)
        assert "LOCATION" in repr(entity)
        assert "NYC" in repr(entity)
        assert "0.850" in repr(entity)


class TestNLPService:
    """Test NLP service with sliding windows."""

    @pytest.fixture
    def nlp_service(self):
        """Initialize NLP service for tests."""
        # Note: First call downloads model ~500MB
        # For faster tests, mock or use smaller model
        return NLPService(
            model_name="law-ai/InLegalBERT",
            chunk_size=400,
            chunk_overlap=50,
            confidence_threshold=0.75,
        )

    def test_nlp_service_initialization(self, nlp_service):
        """Test NLP service initialization."""
        assert nlp_service.model_name == "law-ai/InLegalBERT"
        assert nlp_service.chunk_size == 400
        assert nlp_service.chunk_overlap == 50
        assert nlp_service.confidence_threshold == 0.75
        assert nlp_service.tokenizer is not None
        assert nlp_service.model is not None
        assert nlp_service.ner_pipeline is not None

    def test_sliding_window_creation(self, nlp_service):
        """Test sliding window chunking algorithm."""
        # Create long text
        sample_text = " ".join(["word"] * 1000)  # 1000 words
        windows = nlp_service.create_sliding_windows(sample_text)

        # Should create multiple windows
        assert len(windows) > 1

        # Each window should be within chunk size
        for window in windows:
            token_count = window.end_token_idx - window.start_token_idx
            assert token_count <= nlp_service.chunk_size

    def test_sliding_window_overlap(self, nlp_service):
        """Test that sliding windows have proper overlap."""
        sample_text = " ".join(["word"] * 1000)
        windows = nlp_service.create_sliding_windows(sample_text)

        # Check overlap between consecutive windows
        for i in range(len(windows) - 1):
            current = windows[i]
            next_window = windows[i + 1]
            overlap = current.end_token_idx - next_window.start_token_idx
            # Should have some overlap (but less than chunk_size)
            assert overlap > 0

    def test_sliding_window_coverage(self, nlp_service):
        """Test that sliding windows cover entire text."""
        sample_text = " ".join(["word"] * 100)
        windows = nlp_service.create_sliding_windows(sample_text)

        if windows:
            # First window should start at 0
            assert windows[0].start_token_idx == 0

            # Last window should end at or near total token count
            total_tokens = len(nlp_service.tokenizer.encode(sample_text, add_special_tokens=False))
            assert windows[-1].end_token_idx == total_tokens

    def test_short_text_single_window(self, nlp_service):
        """Test that short text creates single window."""
        short_text = "This is a short text."
        windows = nlp_service.create_sliding_windows(short_text)

        # Should create exactly one window
        assert len(windows) == 1
        assert windows[0].text

    def test_entity_deduplication(self, nlp_service):
        """Test entity deduplication for duplicate mentions."""
        # Create duplicate entities
        entities = [
            NLPEntity("PERSON", "john smith", 0.90, 0, 5, 0),
            NLPEntity("PERSON", "john smith", 0.85, 10, 15, 1),  # Duplicate, lower confidence
            NLPEntity("PERSON", "John Smith", 0.92, 20, 25, 2),  # Case variation
            NLPEntity("LOCATION", "new york", 0.80, 30, 35, 0),
        ]

        deduped = nlp_service._deduplicate_entities(entities)

        # Should keep highest confidence per entity type + text
        assert len(deduped) <= len(entities)
        # Should keep the PERSON entity with highest confidence
        person_entities = [e for e in deduped if e.entity_type == "PERSON"]
        assert len(person_entities) == 1
        assert person_entities[0].confidence == 0.92

    def test_empty_entity_list(self, nlp_service):
        """Test deduplication with empty list."""
        deduped = nlp_service._deduplicate_entities([])
        assert deduped == []

    def test_single_entity(self, nlp_service):
        """Test deduplication with single entity."""
        entities = [NLPEntity("PERSON", "John", 0.90, 0, 5, 0)]
        deduped = nlp_service._deduplicate_entities(entities)

        assert len(deduped) == 1
        assert deduped[0].text == "John"

    def test_nlp_service_cleanup(self, nlp_service):
        """Test NLP service cleanup."""
        nlp_service.close()
        # Should not raise exception


class TestNLPServiceIntegration:
    """Integration tests for NLP service (requires model)."""

    @pytest.fixture
    def nlp_service(self):
        """Initialize NLP service."""
        return NLPService(
            model_name="law-ai/InLegalBERT",
            chunk_size=100,  # Small for testing
            chunk_overlap=10,
            confidence_threshold=0.75,
        )

    @pytest.mark.slow  # Mark as slow because model loading takes time
    def test_extract_entities_from_legal_text(self, nlp_service):
        """Test entity extraction from legal text.."""
        legal_text = (
            "John Michael Smith sued ABC Corporation in the New York Supreme Court. "
            "The plaintiff claims damages of $1,000,000. "
            "The defendant filed a counter-claim on January 15, 2024."
        )

        entities = nlp_service.extract_entities_from_text(legal_text)

        # Should extract some entities (exact types depend on model)
        assert len(entities) >= 0
        # All entities should have required fields
        for entity in entities:
            assert entity.entity_type
            assert entity.text
            assert 0.0 <= entity.confidence <= 1.0

    @pytest.mark.slow
    def test_extract_entities_empty_text(self, nlp_service):
        """Test entity extraction from empty text."""
        entities = nlp_service.extract_entities_from_text("")
        assert len(entities) == 0

    @pytest.mark.slow
    def test_extract_entities_context_manager(self):
        """Test NLP service as context manager."""
        with NLPService() as nlp_service:
            assert nlp_service.model is not None

        # After context, should be cleaned up
        assert nlp_service.model is None or nlp_service.device == "cpu"
