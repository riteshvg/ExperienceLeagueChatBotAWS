"""
Health check and status endpoints
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from app.models.schemas import HealthResponse, ConfigStatusResponse
from app.core.config import VERSION
from app.core.dependencies import get_settings, verify_aws_connection

router = APIRouter()

# Import chat service dependency (avoid circular import)
def get_chat_service():
    """Lazy import to avoid circular dependencies"""
    from app.core.dependencies import verify_aws_connection, get_settings
    from app.services.chat_service import ChatService
    aws_info = verify_aws_connection()
    settings = get_settings()
    return ChatService(aws_info["clients"], settings)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns API status and version
    """
    return HealthResponse(
        status="healthy",
        version=VERSION,
        timestamp=datetime.now()
    )


@router.get("/cache/stats")
async def get_cache_stats(
    chat_service = Depends(get_chat_service)
):
    """
    Get cache statistics
    """
    try:
        stats = chat_service.cache_service.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/cache/clear")
async def clear_cache(
    chat_service = Depends(get_chat_service)
):
    """
    Clear the cache
    """
    try:
        chat_service.cache_service.clear()
        return {
            "success": True,
            "message": "Cache cleared"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/sessions/stats")
async def get_session_stats(
    chat_service = Depends(get_chat_service)
):
    """
    Get session statistics
    """
    try:
        stats = chat_service.session_service.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/kb/update-date")
async def get_kb_update_date(
    settings = Depends(get_settings),
    aws_info: dict = Depends(verify_aws_connection)
):
    """
    Get the last update date of the Knowledge Base
    """
    try:
        import boto3
        
        kb_id = settings.bedrock_knowledge_base_id
        if not kb_id:
            return {
                "success": False,
                "error": "Knowledge Base not configured",
                "last_updated": None
            }
        
        bedrock_agent = boto3.client('bedrock-agent', region_name=settings.aws_default_region)
        
        # Get data sources
        response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
        data_sources = response.get('dataSourceSummaries', [])
        
        latest_date = None
        latest_job_id = None
        
        for ds in data_sources:
            ds_id = ds['dataSourceId']
            
            # Get latest ingestion job
            jobs_response = bedrock_agent.list_ingestion_jobs(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id,
                maxResults=1
            )
            
            if jobs_response.get('ingestionJobSummaries'):
                job = jobs_response['ingestionJobSummaries'][0]
                
                # Get job details to find completion date
                try:
                    job_detail = bedrock_agent.get_ingestion_job(
                        knowledgeBaseId=kb_id,
                        dataSourceId=ds_id,
                        ingestionJobId=job['ingestionJobId']
                    )
                    
                    job_info = job_detail.get('ingestionJob', {})
                    job_status = job_info.get('status', '')
                    
                    # Use endedAt if available, otherwise startedAt
                    if job_status == 'COMPLETE' and 'endedAt' in job_info:
                        job_date_str = job_info['endedAt']
                    else:
                        job_date_str = job_info.get('startedAt', '')
                    
                    if job_date_str:
                        # Parse date
                        if isinstance(job_date_str, str):
                            try:
                                job_date = datetime.fromisoformat(job_date_str.replace('Z', '+00:00'))
                            except:
                                job_date = datetime.fromisoformat(job_date_str)
                        else:
                            job_date = job_date_str
                        
                        # Track the latest date
                        if latest_date is None or job_date > latest_date:
                            latest_date = job_date
                            latest_job_id = job['ingestionJobId']
                except Exception:
                    # If we can't get job details, use startedAt from summary
                    started = job.get('startedAt', '')
                    if started:
                        try:
                            if isinstance(started, str):
                                job_date = datetime.fromisoformat(started.replace('Z', '+00:00'))
                            else:
                                job_date = started
                            
                            if latest_date is None or job_date > latest_date:
                                latest_date = job_date
                                latest_job_id = job['ingestionJobId']
                        except Exception:
                            pass
        
        if latest_date:
            # Format date for display
            formatted_date = latest_date.strftime('%Y-%m-%d')
            iso_date = latest_date.isoformat()
            
            return {
                "success": True,
                "last_updated": iso_date,
                "formatted_date": formatted_date,
                "job_id": latest_job_id
            }
        else:
            return {
                "success": False,
                "error": "No ingestion jobs found",
                "last_updated": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "last_updated": None
        }


@router.get("/config/status", response_model=ConfigStatusResponse)
async def config_status(
    aws_info: dict = Depends(verify_aws_connection)
):
    """
    Configuration status endpoint
    Returns current configuration status
    """
    app_settings = get_settings()
    
    return ConfigStatusResponse(
        aws_configured=True,
        knowledge_base_configured=app_settings.bedrock_knowledge_base_id is not None,
        database_configured=app_settings.database_url is not None,
        aws_account_id=aws_info.get("account_id"),
        knowledge_base_id=app_settings.bedrock_knowledge_base_id,
        region=app_settings.aws_default_region
    )

