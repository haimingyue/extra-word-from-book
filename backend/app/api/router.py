from fastapi import APIRouter

from app.api.routes.analysis import router as analysis_router
from app.api.routes.auth import router as auth_router
from app.api.routes.books import router as books_router
from app.api.routes.vocab_test import router as vocab_test_router
from app.api.routes.vocabularies import router as vocabularies_router


api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(books_router, prefix="/books", tags=["books"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_router.include_router(vocabularies_router, prefix="/vocabularies", tags=["vocabularies"])
api_router.include_router(vocab_test_router, prefix="/vocab-test", tags=["vocab-test"])
