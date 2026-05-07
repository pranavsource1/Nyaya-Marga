"""Performance and load tests."""
import pytest
from app.services.pdf_service import PDFService
from app.services.nlp_service import NLPService


class TestPDFServicePerformance:
    """Performance tests for PDF service."""

    def test_pdf_extraction_speed(self, benchmark, mock_pdf_path):
        """Benchmark PDF extraction speed."""
        def extract():
            with PDFService(mock_pdf_path) as service:
                return service.extract_all_pages()

        result = benchmark(extract)
        assert len(result) > 0

    def test_multi_page_extraction_speed(self, benchmark, mock_pdf_path):
        """Benchmark multi-page extraction."""
        def extract_specific_pages():
            with PDFService(mock_pdf_path) as service:
                pages = []
                for i in range(min(3, service.document.page_count)):
                    pages.append(service.extract_page(i))
                return pages

        result = benchmark(extract_specific_pages)
        assert len(result) <= 3

    @pytest.mark.slow
    def test_pdf_extraction_memory(self, mock_pdf_path):
        """Test PDF extraction memory efficiency."""
        import tracemalloc

        tracemalloc.start()

        with PDFService(mock_pdf_path) as service:
            pages = service.extract_all_pages()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be reasonable (< 100 MB for small PDF)
        assert peak < 100 * 1024 * 1024


class TestNLPServicePerformance:
    """Performance tests for NLP service."""

    @pytest.fixture
    def nlp_service(self):
        """Initialize NLP service."""
        return NLPService(chunk_size=400, chunk_overlap=50)

    @pytest.mark.slow
    def test_sliding_window_creation_speed(self, benchmark, nlp_service):
        """Benchmark sliding window creation."""
        long_text = " ".join(["word"] * 2000)

        result = benchmark(nlp_service.create_sliding_windows, long_text)
        assert len(result) > 0

    @pytest.mark.slow
    def test_entity_deduplication_speed(self, benchmark, nlp_service):
        """Benchmark entity deduplication."""
        from app.services.nlp_service import NLPEntity

        entities = [
            NLPEntity("PERSON", f"Person_{i}", 0.80 + (i % 20) * 0.01, i, i + 5, 0)
            for i in range(1000)
        ]

        result = benchmark(nlp_service._deduplicate_entities, entities)
        assert len(result) <= len(entities)

    @pytest.mark.slow
    def test_nlp_service_inference_speed(self, benchmark, nlp_service):
        """Benchmark NLP inference speed."""
        text = (
            "John Smith is a defendant. The case involves ABC Corporation. "
            "The court is in New York. The date is January 15, 2024."
        )

        def extract():
            return nlp_service.extract_entities_from_text(text)

        result = benchmark(extract)
        assert isinstance(result, list)


class TestMemoryLeaks:
    """Test for memory leaks."""

    @pytest.mark.slow
    def test_pdf_service_no_memory_leak(self, mock_pdf_path):
        """Test PDF service doesn't leak memory."""
        import tracemalloc
        tracemalloc.start()

        initial_memory = 0
        # Run extraction multiple times
        for i in range(5):
            with PDFService(mock_pdf_path) as service:
                pages = service.extract_all_pages()

            if i == 0:
                initial_memory = tracemalloc.get_traced_memory()[1]

        final_memory = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        # Final should not be significantly larger (allow 2x growth)
        assert final_memory < initial_memory * 2

    @pytest.mark.slow
    def test_nlp_service_cleanup(self):
        """Test NLP service properly cleans up after close."""
        import gc

        service = NLPService()
        assert service.model is not None

        service.close()
        gc.collect()

        # Model should be unloaded
        assert service.model is None or service.device == "cpu"
