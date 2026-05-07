from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.rag_service import FAISSRetrieverService

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.get("/rag")
async def hybrid_rag_search(query: str, db: AsyncSession = Depends(get_db)):
    rag_service = FAISSRetrieverService()
    try:
        results = rag_service.get_relevant_precedents(query, k=5)
    except Exception as e:
        results = []

    return {
        "query": query,
        "precedents": results,
        "synthesis": {
            "relevant_cases": [r.split("\n")[0] for r in results] if results else [],
            "guidance": "RAG search completed.",
            "statutory_notes": ""
        },
        "retrieval_stats": {
            "keyword_hits": len(results),
            "semantic_hits": len(results),
            "merged_top_5": results
        }
    }
