"""
Chat service for processing queries with smart routing and knowledge base retrieval.
Adapts existing Streamlit logic for FastAPI backend.
"""
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, AsyncGenerator
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import SmartRouter and retrieve_documents_from_kb from app_streamlit.py
# Import helper functions from chat_helpers
import importlib.util
app_streamlit_path = project_root / "app_streamlit.py"
if not app_streamlit_path.exists():
    raise FileNotFoundError(
        f"app_streamlit.py not found at {app_streamlit_path}. "
        "This file is required for SmartRouter and retrieve_documents_from_kb."
    )
spec = importlib.util.spec_from_file_location("app_module", app_streamlit_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

SmartRouter = app_module.SmartRouter
retrieve_documents_from_kb = app_module.retrieve_documents_from_kb

# Import helper functions
from app.services.chat_helpers import (
    check_query_relevance,
    select_best_documents,
    process_document_content,
    invoke_bedrock_model,
    invoke_bedrock_model_stream
)

# Import cache and session services
from app.services.cache_service import CacheService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class ChatService:
    """Service for processing chat queries with caching and session management"""
    
    def __init__(self, aws_clients: dict, settings):
        self.aws_clients = aws_clients
        self.settings = settings
        self.smart_router = SmartRouter(haiku_only_mode=False)
        # Initialize cache and session services
        self.cache_service = CacheService(max_size=1000, default_ttl=3600)  # 1 hour TTL
        self.session_service = SessionService(max_sessions=1000, session_ttl=86400)  # 24 hour TTL
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate query before processing"""
        errors = []
        warnings = []
        
        if not query or not query.strip():
            errors.append("Query cannot be empty")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "is_relevant": False
            }
        
        if len(query) < 3:
            errors.append("Query must be at least 3 characters long")
        
        MAX_QUERY_LENGTH = 20000
        if len(query) > MAX_QUERY_LENGTH:
            errors.append(f"Query too long ({len(query)} characters). Maximum: {MAX_QUERY_LENGTH} characters")
        elif len(query) > MAX_QUERY_LENGTH * 0.8:
            warnings.append(f"Query is long ({len(query)} characters). Consider making it more specific")
        
        # Check relevance
        is_relevant = check_query_relevance(query)
        if not is_relevant:
            warnings.append("Query may not be relevant to Adobe Analytics, CJA, or AEP topics")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "is_relevant": is_relevant,
            "relevance_score": 1.0 if is_relevant else 0.5
        }
    
    def process_query(
        self,
        query: str,
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
        use_cache: bool = True,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Process a chat query with smart routing, caching, and conversation context
        
        Args:
            query: The user's query
            user_id: User identifier
            session_id: Session identifier for conversation history
            use_cache: Whether to use cache for responses
            include_context: Whether to include conversation history in LLM context
        """
        start_time = time.time()
        
        # Get or create session
        session = self.session_service.get_or_create_session(session_id, user_id)
        session_id = session.session_id
        
        # Validate query
        validation = self.validate_query(query)
        if not validation["valid"]:
            return {
                "success": False,
                "error": "; ".join(validation["errors"]),
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None,
                "processing_time": time.time() - start_time,
                "session_id": session_id,
                "from_cache": False
            }
        
        # Check cache
        if use_cache:
            cached_result = self.cache_service.get(query, user_id)
            if cached_result:
                logger.info(f"✅ Query served from cache")
                # Add user message to session
                session.add_message('user', query)
                # Add cached response to session
                session.add_message('assistant', cached_result.get('answer', ''), {
                    'model_used': cached_result.get('model_used'),
                    'from_cache': True,
                    'documents': cached_result.get('documents', []),
                    'source_links': cached_result.get('source_links', [])
                })
                cached_result["processing_time"] = time.time() - start_time
                cached_result["session_id"] = session_id
                cached_result["from_cache"] = True
                return cached_result
        
        # Get knowledge base ID
        kb_id = self.settings.bedrock_knowledge_base_id
        if not kb_id:
            return {
                "success": False,
                "error": "Knowledge Base not configured",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None,
                "processing_time": time.time() - start_time
            }
        
        try:
            # Step 1: Retrieve documents from Knowledge Base
            documents, retrieval_error = retrieve_documents_from_kb(
                query,
                kb_id,
                self.aws_clients['bedrock_agent'],
                max_results=3
            )
            
            if retrieval_error:
                return {
                    "success": False,
                    "error": f"Retrieval error: {retrieval_error}",
                    "documents": [],
                    "routing_decision": None,
                    "answer": "",
                    "model_used": None,
                    "processing_time": time.time() - start_time
                }
            
            # Step 2: Smart routing
            available_models = ["haiku", "sonnet", "opus"]
            routing_decision = self.smart_router.select_available_model(
                query, documents, available_models
            )
            
            # Step 3: Prepare context and extract source links
            context = ""
            source_links = []
            if documents:
                selected_docs = select_best_documents(documents, max_docs=3)
                context_parts = []
                for i, doc in enumerate(selected_docs, 1):
                    processed_content = process_document_content(doc)
                    if processed_content:
                        context_parts.append(f"Document {i}: {processed_content[:500]}...")
                context = "\n\n".join(context_parts)
                
                # Extract source links from documents
                from app.services.chat_helpers import extract_source_links
                source_links = extract_source_links(selected_docs)
            
            # Step 4: Prepare context with conversation history and source links
            # Get conversation context if enabled
            conversation_context = ""
            if include_context:
                conversation_context = self.session_service.get_conversation_context(
                    session_id,
                    max_tokens=1500  # Reserve space for document context
                )
                if conversation_context:
                    conversation_context = f"\n\nPrevious conversation:\n{conversation_context}\n"
            
            # Add instruction to include source links in response
            enhanced_context = context
            if source_links:
                links_text = "\n\nRelevant Experience League Articles:\n"
                for i, link in enumerate(source_links, 1):
                    links_text += f"{i}. {link['title']}: {link['url']}\n"
                enhanced_context = f"{context}\n\n{links_text}\n\nPlease provide a comprehensive answer and include references to these articles where relevant."
            
            # Combine conversation context with document context
            if conversation_context:
                enhanced_context = f"{conversation_context}\n\n{enhanced_context}"
                enhanced_context += "\n\nPlease provide a response that considers the conversation history above."
            
            answer, generation_error = invoke_bedrock_model(
                routing_decision['model_id'],
                query,
                self.aws_clients.get('bedrock_client') or self.aws_clients['bedrock'],
                enhanced_context
            )
            
            if generation_error:
                return {
                    "success": False,
                    "error": f"Generation error: {generation_error}",
                    "documents": documents,
                    "routing_decision": routing_decision,
                    "answer": "",
                    "model_used": routing_decision['model'],
                    "processing_time": time.time() - start_time
                }
            
            result = {
                "success": True,
                "error": None,
                "documents": documents,
                "routing_decision": routing_decision,
                "answer": answer,
                "model_used": routing_decision['model'],
                "processing_time": time.time() - start_time,
                "source_links": source_links,  # Include source links in response
                "session_id": session_id,
                "from_cache": False
            }
            
            # Add messages to session
            session.add_message('user', query)
            session.add_message('assistant', answer, {
                'model_used': routing_decision['model'],
                'documents': documents,
                'source_links': source_links,
                'routing_decision': routing_decision
            })
            
            # Cache result
            if use_cache:
                self.cache_service.set(query, result, user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None,
                "processing_time": time.time() - start_time,
                "session_id": session_id,
                "from_cache": False
            }
    
    async def process_query_stream(
        self,
        query: str,
        user_id: str = "anonymous",
        session_id: Optional[str] = None,
        use_cache: bool = True,
        include_context: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query with streaming response, caching, and conversation context
        
        Args:
            query: The user's query
            user_id: User identifier
            session_id: Session identifier for conversation history
            use_cache: Whether to check cache first
            include_context: Whether to include conversation history in LLM context
        """
        # Get or create session
        session = self.session_service.get_or_create_session(session_id, user_id)
        session_id = session.session_id
        
        # Validate query
        validation = self.validate_query(query)
        if not validation["valid"]:
            yield {
                "success": False,
                "error": "; ".join(validation["errors"]),
                "chunk": "",
                "is_complete": True,
                "model_used": None,
                "documents": [],
                "session_id": session_id,
                "from_cache": False
            }
            return
        
        # Check cache for streaming (return cached response as stream)
        if use_cache:
            cached_result = self.cache_service.get(query, user_id)
            if cached_result:
                logger.info(f"✅ Streaming cached response")
                # Add user message to session
                session.add_message('user', query)
                # Stream cached answer character by character for typing effect
                answer = cached_result.get('answer', '')
                for i, char in enumerate(answer):
                    yield {
                        "success": True,
                        "chunk": char,
                        "is_complete": False,
                        "model_used": cached_result.get('model_used'),
                        "documents": cached_result.get('documents', []) if i == 0 else [],
                        "source_links": cached_result.get('source_links', []) if i == 0 else [],
                        "session_id": session_id,
                        "from_cache": True
                    }
                    # Small delay for typing effect
                    import asyncio
                    await asyncio.sleep(0.01)
                
                # Add cached response to session
                session.add_message('assistant', answer, {
                    'model_used': cached_result.get('model_used'),
                    'from_cache': True,
                    'documents': cached_result.get('documents', []),
                    'source_links': cached_result.get('source_links', [])
                })
                
                # Final chunk
                yield {
                    "success": True,
                    "chunk": "",
                    "is_complete": True,
                    "model_used": cached_result.get('model_used'),
                    "documents": [],
                    "source_links": cached_result.get('source_links', []),
                    "session_id": session_id,
                    "from_cache": True
                }
                return
        
        # Run synchronous streaming in executor
        import asyncio
        loop = asyncio.get_event_loop()
        
        def sync_stream():
            """Synchronous streaming generator"""
            kb_id = self.settings.bedrock_knowledge_base_id
            if not kb_id:
                yield {
                    "success": False,
                    "error": "Knowledge Base not configured",
                    "chunk": "",
                    "is_complete": True,
                    "model_used": None,
                    "documents": []
                }
                return
            
            try:
                # Retrieve documents
                documents, retrieval_error = retrieve_documents_from_kb(
                    query,
                    kb_id,
                    self.aws_clients['bedrock_agent'],
                    max_results=3
                )
                
                if retrieval_error:
                    yield {
                        "success": False,
                        "error": f"Retrieval error: {retrieval_error}",
                        "chunk": "",
                        "is_complete": True,
                        "model_used": None,
                        "documents": []
                    }
                    return
                
                # Smart routing
                available_models = ["haiku", "sonnet", "opus"]
                routing_decision = self.smart_router.select_available_model(
                    query, documents, available_models
                )
                
                # Prepare context and extract source links
                context = ""
                source_links = []
                if documents:
                    selected_docs = select_best_documents(documents, max_docs=3)
                    context_parts = []
                    for i, doc in enumerate(selected_docs, 1):
                        processed_content = process_document_content(doc)
                        if processed_content:
                            context_parts.append(f"Document {i}: {processed_content[:500]}...")
                    context = "\n\n".join(context_parts)
                    
                    # Extract source links from documents
                    from app.services.chat_helpers import extract_source_links
                    source_links = extract_source_links(selected_docs)
                
                # Get conversation context if enabled
                conversation_context = ""
                if include_context:
                    conversation_context = self.session_service.get_conversation_context(
                        session_id,
                        max_tokens=1500  # Reserve space for document context
                    )
                    if conversation_context:
                        conversation_context = f"\n\nPrevious conversation:\n{conversation_context}\n"
                
                # Stream response
                full_answer = ""
                bedrock_client = self.aws_clients.get('bedrock_client') or self.aws_clients['bedrock']
                docs_sent = False
                
                # Enhance context with source links and conversation history
                enhanced_context = context
                if source_links:
                    links_text = "\n\nRelevant Experience League Articles:\n"
                    for i, link in enumerate(source_links, 1):
                        links_text += f"{i}. {link['title']}: {link['url']}\n"
                    enhanced_context = f"{context}\n\n{links_text}\n\nPlease provide a comprehensive answer and include references to these articles where relevant."
                
                # Combine conversation context with document context
                if conversation_context:
                    enhanced_context = f"{conversation_context}\n\n{enhanced_context}"
                    enhanced_context += "\n\nPlease provide a response that considers the conversation history above."
                
                for chunk, error in invoke_bedrock_model_stream(
                    routing_decision['model_id'],
                    query,
                    bedrock_client,
                    enhanced_context
                ):
                    if error:
                        yield {
                            "success": False,
                            "error": error,
                            "chunk": "",
                            "is_complete": True,
                            "model_used": routing_decision['model'],
                            "documents": documents
                        }
                        return
                    
                    if chunk:
                        full_answer += chunk
                        yield {
                            "success": True,
                            "chunk": chunk,
                            "is_complete": False,
                            "model_used": routing_decision['model'],
                            "documents": documents if not docs_sent else [],
                            "source_links": source_links if not docs_sent else []
                        }
                        docs_sent = True
                
                # Add messages to session
                session.add_message('user', query)
                session.add_message('assistant', full_answer, {
                    'model_used': routing_decision['model'],
                    'documents': documents,
                    'source_links': source_links,
                    'routing_decision': routing_decision
                })
                
                # Cache result
                if use_cache:
                    result_to_cache = {
                        "success": True,
                        "error": None,
                        "documents": documents,
                        "routing_decision": routing_decision,
                        "answer": full_answer,
                        "model_used": routing_decision['model'],
                        "source_links": source_links
                    }
                    self.cache_service.set(query, result_to_cache, user_id)
                
                # Final chunk with source links
                yield {
                    "success": True,
                    "chunk": "",
                    "is_complete": True,
                    "model_used": routing_decision['model'],
                    "documents": [],
                    "source_links": source_links,
                    "session_id": session_id,
                    "from_cache": False
                }
                
            except Exception as e:
                logger.error(f"❌ Streaming query processing failed: {e}")
                yield {
                    "success": False,
                    "error": f"Processing error: {str(e)}",
                    "chunk": "",
                    "is_complete": True,
                    "model_used": None,
                    "documents": []
                }
        
        # Run sync generator in executor and yield results
        sync_gen = sync_stream()
        while True:
            try:
                chunk = await loop.run_in_executor(None, lambda: next(sync_gen))
                yield chunk
                if chunk.get("is_complete"):
                    break
            except StopIteration:
                break
            except Exception as e:
                yield {
                    "success": False,
                    "error": f"Streaming error: {str(e)}",
                    "chunk": "",
                    "is_complete": True,
                    "model_used": None,
                    "documents": []
                }
                break

