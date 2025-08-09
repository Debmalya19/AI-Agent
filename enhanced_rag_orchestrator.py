"""
Enhanced RAG Orchestrator with Explicit Priority Order:
1. RAG tool (vector database + embeddings)
2. Database search (SQL/Excel knowledge bases)
3. Web search (fallback)

This orchestrator provides a unified interface for all retrieval methods.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchPriority(Enum):
    RAG = 1
    DATABASE = 2
    WEB = 3

@dataclass
class RAGResult:
    """Standardized result structure for all retrieval methods"""
    content: str
    source: str
    confidence: float
    metadata: Dict[str, Any]
    search_method: str

class EnhancedRAGOrchestrator:
    """
    Main orchestrator that implements the priority-based search strategy
    """
    
    def __init__(self):
        self.rag_retriever = None
        self.database_searcher = None
        self.web_searcher = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all retrieval components"""
        self.rag_retriever = RAGRetriever()
        self.database_searcher = DatabaseSearcher()
        self.web_searcher = WebSearcher()
    
    def search(self, query: str, max_results: int = 5) -> List[RAGResult]:
        """
        Execute search with priority order:
        1. RAG tool
        2. Database search
        3. Web search
        """
        results = []
        
        # Priority 1: RAG tool
        logger.info("Attempting RAG retrieval...")
        rag_results = self.rag_retriever.search(query, max_results)
        if rag_results and rag_results[0].confidence > 0.7:
            logger.info("RAG retrieval successful")
            return rag_results
        
        # Priority 2: Database search
        logger.info("RAG failed, attempting database search...")
        db_results = self.database_searcher.search(query, max_results)
        if db_results and db_results[0].confidence > 0.5:
            logger.info("Database search successful")
            return db_results
        
        # Priority 3: Web search
        logger.info("Database search failed, attempting web search...")
        web_results = self.web_searcher.search(query, max_results)
        if web_results:
            logger.info("Web search successful")
            return web_results
        
        # Fallback
        logger.warning("All search methods failed")
        return [RAGResult(
            content="I'm sorry, I couldn't find relevant information for your query.",
            source="system",
            confidence=0.0,
            metadata={},
            search_method="fallback"
        )]

class RAGRetriever:
    """RAG tool using FAISS vector store"""
    
    def __init__(self):
        self.vectorstore = None
        self.retriever = None
        self._setup_vectorstore()
    
    def _setup_vectorstore(self):
        """Initialize FAISS vector store with documents"""
        try:
            # Load knowledge base
            loader = TextLoader("data/knowledge.txt")
            documents = loader.load()
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,
                chunk_overlap=50
            )
            split_docs = text_splitter.split_documents(documents)
            
            # Create embeddings and vector store
            embedding = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
            self.vectorstore = FAISS.from_documents(split_docs, embedding)
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 5}
            )
            
            logger.info("RAG retriever initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG retriever: {e}")
    
    def search(self, query: str, max_results: int = 5) -> List[RAGResult]:
        """Search using RAG (vector similarity)"""
        try:
            if not self.retriever:
                return []
            
            docs = self.retriever.get_relevant_documents(query)
            results = []
            
            for doc in docs[:max_results]:
                # Calculate confidence based on similarity
                confidence = self._calculate_confidence(doc, query)
                
                result = RAGResult(
                    content=doc.page_content,
                    source=doc.metadata.get('source', 'knowledge.txt'),
                    confidence=confidence,
                    metadata=doc.metadata,
                    search_method="rag"
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def _calculate_confidence(self, doc: Document, query: str) -> float:
        """Calculate confidence score for RAG results"""
        try:
            # Simple confidence based on document length and query overlap
            content_lower = doc.page_content.lower()
            query_lower = query.lower()
            
            # Count matching words
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            
            if not query_words:
                return 0.0
            
            overlap = len(query_words.intersection(content_words))
            confidence = min(overlap / len(query_words), 1.0)
            
            return confidence
            
        except Exception:
            return 0.5

class DatabaseSearcher:
    """Database search using Excel knowledge bases"""
    
    def __init__(self):
        self.knowledge_bases = {
            'customer': 'data/customer_knowledge_base.xlsx',
            'support': 'data/customer_support_knowledge_base.xlsx'
        }
    
    def search(self, query: str, max_results: int = 5) -> List[RAGResult]:
        """Search through Excel knowledge bases"""
        results = []
        
        for kb_name, file_path in self.knowledge_bases.items():
            try:
                kb_results = self._search_knowledge_base(file_path, query, max_results)
                results.extend(kb_results)
            except Exception as e:
                logger.error(f"Failed to search {kb_name} knowledge base: {e}")
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:max_results]
    
    def _search_knowledge_base(self, file_path: str, query: str, max_results: int) -> List[RAGResult]:
        """Search a specific Excel knowledge base"""
        try:
            xls = pd.ExcelFile(file_path)
            results = []
            
            # Search through all sheets
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                
                # Search in relevant columns
                for _, row in df.iterrows():
                    content = self._extract_content_from_row(row)
                    if content and self._is_relevant(content, query):
                        confidence = self._calculate_relevance_score(content, query)
                        
                        result = RAGResult(
                            content=str(content),
                            source=f"{file_path}#{sheet_name}",
                            confidence=confidence,
                            metadata={"sheet": sheet_name, "row": row.to_dict()},
                            search_method="database"
                        )
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base {file_path}: {e}")
            return []
    
    def _extract_content_from_row(self, row: pd.Series) -> str:
        """Extract searchable content from a DataFrame row"""
        content_parts = []
        
        for col in row.index:
            if pd.notna(row[col]) and str(row[col]).strip():
                content_parts.append(f"{col}: {row[col]}")
        
        return " | ".join(content_parts)
    
    def _is_relevant(self, content: str, query: str) -> bool:
        """Check if content is relevant to query"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        # Simple keyword matching
        return len(query_words.intersection(content_words)) > 0
    
    def _calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score for database results"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        score = overlap / len(query_words)
        
        # Bonus for exact phrase matches
        if query.lower() in content.lower():
            score += 0.3
        
        return min(score, 1.0)

class WebSearcher:
    """Web search as fallback"""
    
    def __init__(self):
        self.search_api_key = os.getenv("SEARCH_API_KEY")
    
    def search(self, query: str, max_results: int = 5) -> List[RAGResult]:
        """Perform web search"""
        try:
            # Use the existing search tool from your tools.py
            from tools import search_tool
            
            search_results = search_tool.run(query)
            
            if not search_results:
                return []
            
            # Parse search results
            results = []
            for i, result in enumerate(search_results[:max_results]):
                result_obj = RAGResult(
                    content=result.get('snippet', ''),
                    source=result.get('link', 'web_search'),
                    confidence=0.6 - (i * 0.1),  # Decreasing confidence for lower results
                    metadata=result,
                    search_method="web"
                )
                results.append(result_obj)
            
            return results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

# Global orchestrator instance
rag_orchestrator = EnhancedRAGOrchestrator()

def search_with_priority(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Main function to use the RAG system with priority order
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
    
    Returns:
        List of search results with metadata
    """
    results = rag_orchestrator.search(query, max_results)
    
    # Convert to JSON-serializable format
    return [
        {
            "content": result.content,
            "source": result.source,
            "confidence": result.confidence,
            "search_method": result.search_method,
            "metadata": result.metadata
        }
        for result in results
    ]

if __name__ == "__main__":
    # Test the orchestrator
    test_query = "How do I reset my BT router?"
    results = search_with_priority(test_query)
    
    print(f"\nSearch results for: {test_query}")
    print("-" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['search_method'].upper()}] Confidence: {result['confidence']:.2f}")
        print(f"   Source: {result['source']}")
        print(f"   Content: {result['content'][:100]}...")
        print()
