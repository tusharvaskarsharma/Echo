import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from app.config import get_settings

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.settings = get_settings()
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.settings.pinecone_api_key)
        self.index_name = self.settings.pinecone_index
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
                    dimension=3072, # Using standard OpenAI dimensions for text-embedding-3-large
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.pinecone_environment
                    )
                )
        except Exception:
            logger.exception("Failed to check or create Pinecone index")
            raise

    def upsert_vectors(self, namespace: str, vectors: List[Dict[str, Any]]):
        """
        Upserts a list of vectors to Pinecone in batches.
        Expected vector format: {'id': 'vec1', 'values': [0.1...], 'metadata': {...}}
        Metadata Schema must include: user_id, session_id, memory_id, source, tags, importance, emotion, embedding_version.
        Namespace: Uses persona_id for strict isolation.
        """
        try:
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch, namespace=namespace)
                logger.info(f"Upserted batch of {len(batch)} vectors to Pinecone namespace '{namespace}'.")
        except Exception as e:
            logger.error(f"Failed to upsert to Pinecone: {e}")
            raise

    def query(self, namespace: str, vector: list[float], top_k: int = 12, filter: dict = None) -> list[dict]:
        """Queries Pinecone for similar vectors in a specific namespace."""
        try:
            response = self.index.query(
                namespace=namespace,
                vector=vector,
                top_k=top_k,
                filter=filter,
                include_metadata=True
            )
            return response.get("matches", [])
        except Exception as e:
            logger.error(f"Failed to query Pinecone: {e}")
            raise

    def update_metadata(self, namespace: str, vector_id: str, metadata_updates: dict):
        """Updates the metadata of an existing vector in Pinecone."""
        try:
            # Pinecone python client update command does support namespace
            self.index.update(
                id=vector_id,
                set_metadata=metadata_updates,
                namespace=namespace
            )
            logger.info(f"Updated metadata for vector {vector_id} in namespace '{namespace}'")
        except Exception as e:
            logger.error(f"Failed to update Pinecone metadata: {e}")
            raise

    def delete_vectors(self, namespace: str, ids: Optional[List[str]] = None, delete_all: bool = False):
        """Deletes specific vectors or all vectors in a namespace."""
        try:
            if delete_all:
                self.index.delete(delete_all=True, namespace=namespace)
                logger.info(f"Deleted all vectors in namespace '{namespace}'")
            elif ids:
                self.index.delete(ids=ids, namespace=namespace)
                logger.info(f"Deleted {len(ids)} vectors from namespace '{namespace}'")
        except Exception as e:
            logger.error(f"Failed to delete Pinecone vectors: {e}")
            raise
