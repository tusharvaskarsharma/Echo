import logging
from typing import List, Dict
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()

    async def retrieve_memories(self, question: str, subject_id: str, allowed_consent_levels: List[str]) -> List[Dict]:
        """
        Retrieves relevant memories based on semantic similarity.
        Filters by subject_id and consent_level.
        """
        # Embed question
        embeddings = await self.embedding_service.embed_texts([question])
        if not embeddings:
            logger.warning("Failed to embed question.")
            return []
            
        question_vector = embeddings[0]
        
        # Build metadata filter
        metadata_filter = {
            "subject_id": {"$eq": subject_id},
            "consent_level": {"$in": allowed_consent_levels}
        }
        
        # Query pinecone
        matches = self.pinecone_service.query(
            namespace=subject_id,
            vector=question_vector,
            top_k=12,
            filter=metadata_filter
        )
        
        grounded_matches = [
            match for match in matches
            if match.get("score", 0.0) >= 0.72 and match.get("metadata", {}).get("content")
        ]
        if not grounded_matches:
            logger.info("No consent-allowed memory met the 0.72 retrieval threshold.")
            return []

        return [match["metadata"] for match in grounded_matches]
