"""FAISS-based Retrieval Augmented Generation (RAG) service.

Loads local embeddings and searches for similar historical precedents
to augment LLM context for action plan generation.
"""
import logging
import os
from typing import List
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class FAISSRetrieverService:
    """Vector store retrieval service using FAISS and HuggingFace embeddings.

    Provides methods to initialize/load a FAISS index and retrieve
    similar historical judgments for context augmentation.
    """

    def __init__(self, embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the FAISS retriever service.

        Args:
            embeddings_model: HuggingFace model name for embeddings
        """
        self.embeddings_model_name = embeddings_model
        self.embeddings = None
        self.faiss_index = None
        self.metadata = []  # Stores text chunks corresponding to vectors

        logger.info(f"Initializing FAISSRetrieverService with model: {embeddings_model}")
        self._try_load_local_index()

    def _try_load_local_index(self):
        """Attempt to load a pre-built FAISS index from disk."""
        try:
            import faiss
            import pickle
            index_path = "data/rag_index/index.faiss"
            meta_path = "data/rag_index/metadata.pkl"
            
            if os.path.exists(index_path) and os.path.exists(meta_path):
                self.faiss_index = faiss.read_index(index_path)
                with open(meta_path, "rb") as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Successfully loaded local FAISS index with {len(self.metadata)} documents")
        except Exception as e:
            logger.warning(f"Could not load local FAISS index: {e}")

    def _load_embeddings(self):
        """Lazy load embeddings model on first use."""
        if self.embeddings is not None:
            return

        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            logger.info(f"Loading embeddings model: {self.embeddings_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embeddings_model_name
            )
            logger.info("Embeddings model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embeddings model: {e}", exc_info=True)
            raise

    def initialize_index_from_texts(self, texts: List[str]) -> None:
        """Initialize FAISS index from historical judgment texts.

        In production, these would be loaded from a document store.
        For now, we simulate indexing with example precedents.

        Args:
            texts: List of historical judgment texts to index
        """
        self._load_embeddings()

        if not texts:
            logger.warning("No texts provided to initialize index")
            return

        try:
            import faiss

            # Embed all texts
            logger.info(f"Embedding {len(texts)} documents...")
            embeddings = self.embeddings.embed_documents(texts)
            embeddings_array = np.array(embeddings).astype("float32")

            # Create FAISS index
            dimension = embeddings_array.shape[1]
            self.faiss_index = faiss.IndexFlatL2(dimension)
            self.faiss_index.add(embeddings_array)

            # Store metadata
            self.metadata = texts

            logger.info(f"FAISS index initialized with {len(texts)} documents")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}", exc_info=True)
            raise

    def get_relevant_precedents(self, query_text: str, k: int = 3) -> List[str]:
        """Retrieve top-k similar historical cases.

        Args:
            query_text: Query text (case summary or entity summary)
            k: Number of similar precedents to retrieve

        Returns:
            List of top-k similar historical judgment texts
        """
        self._load_embeddings()

        if self.faiss_index is None or len(self.metadata) == 0:
            logger.warning("FAISS index not initialized, using synthetic precedents")
            return self._get_synthetic_precedents()

        try:
            # Embed query
            query_embedding = self.embeddings.embed_query(query_text)
            query_array = np.array([query_embedding]).astype("float32")

            # Search
            distances, indices = self.faiss_index.search(query_array, min(k, len(self.metadata)))

            # Retrieve and return
            results = [self.metadata[idx] for idx in indices[0]]
            logger.info(f"Retrieved {len(results)} similar precedents")
            return results

        except Exception as e:
            logger.error(f"Error retrieving precedents: {e}", exc_info=True)
            return self._get_synthetic_precedents()

    def _get_synthetic_precedents(self) -> List[str]:
        """Return synthetic precedents for demonstration when index unavailable.

        Returns:
            List of example historical judgment texts
        """
        return [
            """JUDGMENT: ABC v. State of XYZ (Supreme Court 2020)
Bench: Justices A, B, C
Date: 15-03-2020
Issue: Statutory compliance with environmental regulations
Holding: Entities must file quarterly compliance reports within 30 days.
Penalty: ₹10 lakhs per violation, plus remediation costs.
Timeline: 90-day compliance window from judgment date.
Precedent Value: Establishes strict liability for regulatory violations.""",

            """JUDGMENT: DEF Corporation v. Ministry of Z (High Court 2021)
Bench: Justice X (Single)
Date: 10-07-2021
Issue: Administrative procedure compliance
Holding: All administrative actions must include stakeholder consultation.
Penalty: Administrative remedies plus potential financial penalties.
Timeline: 60 days from judgment for implementation.
Precedent Value: Sets standard for procedural fairness in administrative decisions.""",

            """JUDGMENT: GHI Ltd v. Regulatory Authority (Appellate Tribunal 2022)
Tribunal: Panel of 3 senior members
Date: 22-11-2022
Issue: Data protection obligations
Holding: Organizations must implement data protection frameworks per standards.
Penalty: Graduated penalties from ₹5 lakhs to ₹50 lakhs based on violation severity.
Timeline: 120 days for full compliance implementation.
Precedent Value: Clarifies proportionality in regulatory penalties.""",
        ]

    def set_index(self, faiss_index, metadata: List[str]) -> None:
        """Set pre-built FAISS index and metadata.

        Useful for loading a persisted index.

        Args:
            faiss_index: Pre-built FAISS index object
            metadata: Corresponding text chunks
        """
        self.faiss_index = faiss_index
        self.metadata = metadata
        logger.info(f"FAISS index set with {len(metadata)} documents")
