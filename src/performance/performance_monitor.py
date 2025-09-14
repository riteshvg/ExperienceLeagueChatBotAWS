"""
Performance monitoring and metrics for Streamlit chatbot
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OperationTiming:
    """Timing information for an operation"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, success: bool = True, error: str = None):
        """Finish timing the operation"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.operation_timings = deque(maxlen=max_history)
        self.active_operations = {}
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_duration': 0.0,
            'avg_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0
        }
        self.operation_stats = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'avg_duration': 0.0,
            'success_count': 0,
            'error_count': 0
        })
        self.lock = threading.Lock()
    
    def start_operation(self, operation: str, metadata: Dict[str, Any] = None) -> str:
        """Start timing an operation"""
        operation_id = f"{operation}_{int(time.time() * 1000)}_{id(operation)}"
        
        timing = OperationTiming(
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        with self.lock:
            self.active_operations[operation_id] = timing
        
        return operation_id
    
    def finish_operation(self, operation_id: str, success: bool = True, error: str = None):
        """Finish timing an operation"""
        with self.lock:
            if operation_id not in self.active_operations:
                logger.warning(f"⚠️ Operation {operation_id} not found in active operations")
                return
            
            timing = self.active_operations.pop(operation_id)
            timing.finish(success, error)
            
            # Add to history
            self.operation_timings.append(timing)
            
            # Update stats
            self._update_stats(timing)
    
    def _update_stats(self, timing: OperationTiming):
        """Update performance statistics"""
        if timing.duration is None:
            return
        
        # Update overall stats
        self.stats['total_operations'] += 1
        self.stats['total_duration'] += timing.duration
        
        if timing.success:
            self.stats['successful_operations'] += 1
        else:
            self.stats['failed_operations'] += 1
        
        # Update min/max duration
        if timing.duration < self.stats['min_duration']:
            self.stats['min_duration'] = timing.duration
        if timing.duration > self.stats['max_duration']:
            self.stats['max_duration'] = timing.duration
        
        # Update average duration
        self.stats['avg_duration'] = self.stats['total_duration'] / self.stats['total_operations']
        
        # Update operation-specific stats
        op_stats = self.operation_stats[timing.operation]
        op_stats['count'] += 1
        op_stats['total_duration'] += timing.duration
        op_stats['avg_duration'] = op_stats['total_duration'] / op_stats['count']
        
        if timing.success:
            op_stats['success_count'] += 1
        else:
            op_stats['error_count'] += 1
    
    def record_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        with self.lock:
            self.metrics_history.append(metric)
    
    def get_operation_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get statistics for a specific operation or all operations"""
        with self.lock:
            if operation:
                return dict(self.operation_stats.get(operation, {}))
            else:
                return {op: dict(stats) for op, stats in self.operation_stats.items()}
    
    def get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetric]:
        """Get recent metrics from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            return [metric for metric in self.metrics_history if metric.timestamp > cutoff_time]
    
    def get_recent_operations(self, minutes: int = 5) -> List[OperationTiming]:
        """Get recent operations from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            return [op for op in self.operation_timings if datetime.fromtimestamp(op.start_time) > cutoff_time]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            recent_ops = self.get_recent_operations(5)  # Last 5 minutes
            
            # Calculate recent performance
            recent_durations = [op.duration for op in recent_ops if op.duration is not None]
            recent_success_rate = (
                len([op for op in recent_ops if op.success]) / len(recent_ops)
                if recent_ops else 0
            )
            
            return {
                'overall_stats': dict(self.stats),
                'operation_stats': self.get_operation_stats(),
                'recent_performance': {
                    'operations_last_5min': len(recent_ops),
                    'avg_duration_last_5min': sum(recent_durations) / len(recent_durations) if recent_durations else 0,
                    'success_rate_last_5min': recent_success_rate,
                    'min_duration_last_5min': min(recent_durations) if recent_durations else 0,
                    'max_duration_last_5min': max(recent_durations) if recent_durations else 0
                },
                'active_operations': len(self.active_operations),
                'total_metrics_recorded': len(self.metrics_history)
            }
    
    def get_slow_operations(self, threshold_seconds: float = 5.0) -> List[OperationTiming]:
        """Get operations that took longer than threshold"""
        with self.lock:
            return [op for op in self.operation_timings if op.duration and op.duration > threshold_seconds]
    
    def get_failed_operations(self) -> List[OperationTiming]:
        """Get all failed operations"""
        with self.lock:
            return [op for op in self.operation_timings if not op.success]
    
    def clear_history(self):
        """Clear performance history"""
        with self.lock:
            self.metrics_history.clear()
            self.operation_timings.clear()
            self.operation_stats.clear()
            self.stats = {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0
            }

# Context manager for timing operations
class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, metadata: Dict[str, Any] = None):
        self.monitor = monitor
        self.operation = operation
        self.metadata = metadata
        self.operation_id = None
    
    def __enter__(self):
        self.operation_id = self.monitor.start_operation(self.operation, self.metadata)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        self.monitor.finish_operation(self.operation_id, success, error)

# Decorator for timing functions
def time_operation(operation_name: str = None, metadata: Dict[str, Any] = None):
    """Decorator to time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            with OperationTimer(global_monitor, op_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Global performance monitor
global_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor"""
    return global_monitor

def start_operation(operation: str, metadata: Dict[str, Any] = None) -> str:
    """Start timing an operation"""
    return global_monitor.start_operation(operation, metadata)

def finish_operation(operation_id: str, success: bool = True, error: str = None):
    """Finish timing an operation"""
    global_monitor.finish_operation(operation_id, success, error)

def record_metric(name: str, value: float, metadata: Dict[str, Any] = None):
    """Record a performance metric"""
    global_monitor.record_metric(name, value, metadata)

def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return global_monitor.get_performance_summary()

def get_slow_operations(threshold_seconds: float = 5.0) -> List[OperationTiming]:
    """Get slow operations"""
    return global_monitor.get_slow_operations(threshold_seconds)

def get_failed_operations() -> List[OperationTiming]:
    """Get failed operations"""
    return global_monitor.get_failed_operations()

# Performance monitoring utilities
class PerformanceAlert:
    """Performance alert system"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.alerts = []
        self.thresholds = {
            'max_duration': 10.0,  # seconds
            'min_success_rate': 0.8,  # 80%
            'max_memory_mb': 1024,  # MB
            'max_error_rate': 0.1  # 10%
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        alerts = []
        summary = self.monitor.get_performance_summary()
        
        # Check for slow operations
        slow_ops = self.monitor.get_slow_operations(self.thresholds['max_duration'])
        if slow_ops:
            alerts.append({
                'type': 'slow_operations',
                'message': f"{len(slow_ops)} operations exceeded {self.thresholds['max_duration']}s",
                'severity': 'warning',
                'data': slow_ops
            })
        
        # Check success rate
        recent_perf = summary['recent_performance']
        if recent_perf['success_rate_last_5min'] < self.thresholds['min_success_rate']:
            alerts.append({
                'type': 'low_success_rate',
                'message': f"Success rate {recent_perf['success_rate_last_5min']:.1%} below threshold",
                'severity': 'error',
                'data': recent_perf
            })
        
        # Check error rate
        failed_ops = self.monitor.get_failed_operations()
        if failed_ops and len(failed_ops) / max(summary['overall_stats']['total_operations'], 1) > self.thresholds['max_error_rate']:
            alerts.append({
                'type': 'high_error_rate',
                'message': f"Error rate {len(failed_ops)/summary['overall_stats']['total_operations']:.1%} above threshold",
                'severity': 'error',
                'data': failed_ops
            })
        
        return alerts
