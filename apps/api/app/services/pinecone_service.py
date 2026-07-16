import logging
from typing import List, Dict, Any
from pinecone import Pinecone, ServerlessSpec
from app.config import get_settings

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.settings = get_settings()
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.settings.pinecone_api_key or "mock_key_for_demo")
        self.index_name = self.settings.pinecone_index_name
        
        # In a real production setting, checking index existence synchronously here 
        # is slow, but acceptable for this architecture phase.
        if self.settings.pinecone_api_key:
            self._ensure_index_exists()
            self.index = self.pc.Index(self.index_name)

    def _ensure_index_exists(self):
        """Creates the index if it doesn't exist."""
        try:
            existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index '{self.index_name}'...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=3072,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.pinecone_environment
                    )
                )
        except Exception as e:
            logger.error(f"Failed to check or create Pinecone index: {e}")

    def upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Upserts a list of vectors to Pinecone in batches.
        Expected format: [{'id': 'vec1', 'values': [0.1...], 'metadata': {...}}]
        """
        if not getattr(self, 'index', None):
            logger.warning("Pinecone index not initialized. Skipping upsert.")
            return

        try:
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                logger.info(f"Upserted batch of {len(batch)} vectors to Pinecone.")
        except Exception as e:
            logger.error(f"Failed to upsert to Pinecone: {e}")
            raise

    def query(self, vector: list[float], top_k: int = 12, filter: dict = None) -> list[dict]:
        """Queries Pinecone for similar vectors."""
        if not getattr(self, 'index', None):
            logger.warning("Pinecone index not initialized. Returning empty query results.")
            return []
            
        try:
            response = self.index.query(
                vector=vector,
                top_k=top_k,
                filter=filter,
                include_metadata=True
            )
            return response.get("matches", [])
        except Exception as e:
            logger.error(f"Failed to query Pinecone: {e}")
            raise

    def update_metadata(self, vector_id: str, metadata_updates: dict):
        """Updates the metadata of an existing vector in Pinecone."""
        if not getattr(self, 'index', None):
            logger.warning("Pinecone index not initialized. Skipping metadata update.")
            return

        try:
            self.index.update(
                id=vector_id,
                set_metadata=metadata_updates
            )
            logger.info(f"Updated metadata for vector {vector_id}")
        except Exception as e:
            logger.error(f"Failed to update Pinecone metadata: {e}")
            raise
