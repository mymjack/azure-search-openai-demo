"""Retriever wrapper for Azure Cognitive Search."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Extra, root_validator

from langchain.schema import BaseRetriever, Document

from vdbutils.retriever import Retriever


class AzureCognitiveSearchRetriever(BaseRetriever, BaseModel):
    """Wrapper around Azure Cognitive Search."""


    def get_relevant_documents(self, query: str) -> List[Document]:
        search_results = self._search(query)

        return [
            Document(page_content=result.pop(self.content_key), metadata=result)
            for result in search_results
        ]
