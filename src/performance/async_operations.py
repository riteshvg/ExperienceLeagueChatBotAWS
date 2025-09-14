"""
Async operations and background processing for Streamlit chatbot performance
"""

import asyncio
import threading
import time
import logging
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BackgroundTask:
    """Background task definition"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 1  # 1=high, 2=medium, 3=low
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class AsyncOperationManager:
    """Manages async operations and background processing"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.PriorityQueue()
        self.running_tasks = {}
        self.completed_tasks = {}
        self.stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0
        }
        self._shutdown = False
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def _worker_loop(self):
        """Background worker loop for processing tasks"""
        while not self._shutdown:
            try:
                # Get task from queue (blocking with timeout)
                priority, task = self.task_queue.get(timeout=1.0)
                
                if task is None:  # Shutdown signal
                    break
                
                # Execute task
                self._execute_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Worker loop error: {e}")
    
    def _execute_task(self, task: BackgroundTask):
        """Execute a background task"""
        task_id = task.task_id
        start_time = time.time()
        
        try:
            logger.debug(f"🔄 Executing background task: {task_id}")
            
            # Execute the task
            result = task.func(*task.args, **task.kwargs)
            
            # Store result
            self.completed_tasks[task_id] = {
                'result': result,
                'status': 'completed',
                'execution_time': time.time() - start_time,
                'completed_at': datetime.now()
            }
            
            self.stats['tasks_completed'] += 1
            self.stats['total_execution_time'] += time.time() - start_time
            
            logger.debug(f"✅ Background task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Background task failed: {task_id} - {e}")
            
            self.completed_tasks[task_id] = {
                'result': None,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - start_time,
                'completed_at': datetime.now()
            }
            
            self.stats['tasks_failed'] += 1
        
        finally:
            # Remove from running tasks
            self.running_tasks.pop(task_id, None)
            self.task_queue.task_done()
    
    def submit_task(self, task_id: str, func: Callable, *args, priority: int = 2, **kwargs) -> bool:
        """Submit a background task"""
        if self._shutdown:
            return False
        
        task = BackgroundTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
        
        try:
            self.task_queue.put((priority, task))
            self.running_tasks[task_id] = task
            self.stats['tasks_submitted'] += 1
            logger.debug(f"📝 Background task submitted: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to submit task {task_id}: {e}")
            return False
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task"""
        return self.completed_tasks.get(task_id)
    
    def is_task_completed(self, task_id: str) -> bool:
        """Check if a task is completed"""
        return task_id in self.completed_tasks
    
    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is still running"""
        return task_id in self.running_tasks
    
    def wait_for_task(self, task_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Wait for a task to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            time.sleep(0.1)
        
        logger.warning(f"⏰ Task {task_id} timed out after {timeout}s")
        return None
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        tasks_to_remove = []
        for task_id, task_data in self.completed_tasks.items():
            if task_data['completed_at'].timestamp() < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            self.completed_tasks.pop(task_id, None)
        
        if tasks_to_remove:
            logger.info(f"🧹 Cleaned up {len(tasks_to_remove)} old tasks")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get operation manager statistics"""
        return {
            **self.stats,
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self.completed_tasks),
            'queue_size': self.task_queue.qsize(),
            'max_workers': self.max_workers,
            'avg_execution_time': (
                self.stats['total_execution_time'] / max(self.stats['tasks_completed'], 1)
            )
        }
    
    def shutdown(self):
        """Shutdown the operation manager"""
        self._shutdown = True
        self.task_queue.put((0, None))  # Shutdown signal
        self.executor.shutdown(wait=True)
        logger.info("🛑 Async operation manager shutdown")

# Global async operation manager
async_manager = AsyncOperationManager()

def run_async(func: Callable, *args, **kwargs) -> str:
    """Run a function asynchronously and return task ID"""
    task_id = f"task_{int(time.time() * 1000)}_{id(func)}"
    success = async_manager.submit_task(task_id, func, *args, **kwargs)
    return task_id if success else None

def get_async_result(task_id: str) -> Optional[Dict[str, Any]]:
    """Get result of an async operation"""
    return async_manager.get_task_result(task_id)

def wait_for_async(task_id: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
    """Wait for an async operation to complete"""
    return async_manager.wait_for_task(task_id, timeout)

# Background processing functions
def background_analytics_processing(analytics_data: List[Dict[str, Any]]):
    """Process analytics data in background"""
    try:
        from src.performance.database_pool import get_db_pool
        
        db_pool = get_db_pool()
        if db_pool:
            success = db_pool.batch_insert_analytics(analytics_data)
            logger.info(f"📊 Background analytics processing: {'Success' if success else 'Failed'}")
        else:
            logger.warning("⚠️ Database pool not available for background processing")
    except Exception as e:
        logger.error(f"❌ Background analytics processing failed: {e}")

def background_cache_cleanup():
    """Clean up expired cache entries in background"""
    try:
        from src.performance.cache_manager import cache_manager
        cache_manager.cleanup_expired()
        logger.debug("🧹 Background cache cleanup completed")
    except Exception as e:
        logger.error(f"❌ Background cache cleanup failed: {e}")

def background_model_warmup(model_name: str):
    """Warm up model in background"""
    try:
        # This would typically involve loading the model or making a test call
        logger.info(f"🔥 Warming up model: {model_name}")
        # Add model warmup logic here
        time.sleep(1)  # Simulate warmup time
        logger.info(f"✅ Model warmed up: {model_name}")
    except Exception as e:
        logger.error(f"❌ Model warmup failed for {model_name}: {e}")

# Utility functions for common async patterns
def process_query_async(query: str, model: str, **kwargs) -> str:
    """Process a query asynchronously"""
    def _process():
        # This would contain the actual query processing logic
        # For now, just simulate processing
        time.sleep(2)
        return {"query": query, "model": model, "result": "processed"}
    
    return run_async(_process, **kwargs)

def batch_analytics_async(analytics_data: List[Dict[str, Any]]) -> str:
    """Process analytics data asynchronously"""
    return run_async(background_analytics_processing, analytics_data, priority=3)

def cleanup_cache_async() -> str:
    """Clean up cache asynchronously"""
    return run_async(background_cache_cleanup, priority=3)

def warmup_model_async(model_name: str) -> str:
    """Warm up model asynchronously"""
    return run_async(background_model_warmup, model_name, priority=2)
