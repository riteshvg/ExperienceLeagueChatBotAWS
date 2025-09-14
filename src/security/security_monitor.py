"""
Security Monitoring and Threat Detection
Monitors security events, logs threats, and detects anomalies
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event data structure"""
    timestamp: datetime
    event_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    source_ip: str
    user_agent: str
    details: Dict[str, Any]
    blocked: bool = False

@dataclass
class ThreatMetrics:
    """Threat detection metrics"""
    total_attempts: int = 0
    blocked_attempts: int = 0
    unique_ips: int = 0
    threat_types: Dict[str, int] = field(default_factory=dict)
    last_attack: Optional[datetime] = None

class SecurityMonitor:
    """Security monitoring and threat detection system"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events = deque(maxlen=max_events)
        self.ip_attempts = defaultdict(list)
        self.threat_metrics = ThreatMetrics()
        self.blocked_ips = set()
        
        # Rate limiting settings
        self.max_attempts_per_minute = 10
        self.max_attempts_per_hour = 100
        self.lockout_duration = timedelta(minutes=15)
    
    def log_security_event(self, 
                          event_type: str, 
                          severity: str, 
                          details: Dict[str, Any],
                          source_ip: str = "unknown",
                          user_agent: str = "unknown",
                          blocked: bool = False) -> None:
        """Log a security event"""
        
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            details=details,
            blocked=blocked
        )
        
        self.events.append(event)
        self._update_metrics(event)
        
        # Log to file
        logger.warning(f"Security Event: {event_type} | Severity: {severity} | IP: {source_ip} | Blocked: {blocked}")
    
    def monitor_input_validation(self, user_input: str, threats_detected: List[str], 
                               source_ip: str = "unknown", blocked: bool = False) -> None:
        """Monitor input validation failures"""
        
        if threats_detected:
            self.log_security_event(
                event_type="input_validation_failure",
                severity="high" if blocked else "medium",
                details={
                    "input_length": len(user_input),
                    "threats": threats_detected,
                    "input_sample": user_input[:100] + "..." if len(user_input) > 100 else user_input
                },
                source_ip=source_ip,
                blocked=blocked
            )
    
    def monitor_authentication_attempt(self, username: str, success: bool, 
                                     source_ip: str = "unknown", 
                                     user_agent: str = "unknown") -> bool:
        """
        Monitor authentication attempts and detect brute force
        
        Returns:
            True if attempt should be allowed, False if blocked
        """
        
        current_time = datetime.utcnow()
        
        # Record attempt
        self.ip_attempts[source_ip].append(current_time)
        
        # Clean old attempts
        cutoff_time = current_time - timedelta(hours=1)
        self.ip_attempts[source_ip] = [
            attempt for attempt in self.ip_attempts[source_ip] 
            if attempt > cutoff_time
        ]
        
        # Check rate limits
        recent_attempts = len([
            attempt for attempt in self.ip_attempts[source_ip]
            if attempt > current_time - timedelta(minutes=1)
        ])
        
        hourly_attempts = len(self.ip_attempts[source_ip])
        
        # Determine if this should be blocked
        should_block = (
            recent_attempts > self.max_attempts_per_minute or
            hourly_attempts > self.max_attempts_per_hour or
            source_ip in self.blocked_ips
        )
        
        if should_block:
            self.blocked_ips.add(source_ip)
        
        # Log the attempt
        self.log_security_event(
            event_type="authentication_attempt",
            severity="high" if should_block else ("medium" if not success else "low"),
            details={
                "username": username,
                "success": success,
                "recent_attempts": recent_attempts,
                "hourly_attempts": hourly_attempts
            },
            source_ip=source_ip,
            user_agent=user_agent,
            blocked=should_block
        )
        
        return not should_block
    
    def monitor_api_call(self, endpoint: str, method: str, status_code: int,
                        response_time: float, source_ip: str = "unknown") -> None:
        """Monitor API calls for suspicious activity"""
        
        severity = "low"
        
        # Detect suspicious patterns
        if status_code >= 500:
            severity = "medium"
        elif status_code == 403 or status_code == 401:
            severity = "medium"
        elif response_time > 10.0:  # Slow response might indicate attack
            severity = "medium"
        
        self.log_security_event(
            event_type="api_call",
            severity=severity,
            details={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time": response_time
            },
            source_ip=source_ip
        )
    
    def monitor_file_access(self, file_path: str, operation: str, 
                           source_ip: str = "unknown", allowed: bool = True) -> None:
        """Monitor file access attempts"""
        
        severity = "low" if allowed else "high"
        
        self.log_security_event(
            event_type="file_access",
            severity=severity,
            details={
                "file_path": file_path,
                "operation": operation,
                "allowed": allowed
            },
            source_ip=source_ip,
            blocked=not allowed
        )
    
    def get_threat_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get threat summary for the last N hours"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [event for event in self.events if event.timestamp > cutoff_time]
        
        # Count events by type and severity
        event_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        blocked_counts = defaultdict(int)
        unique_ips = set()
        
        for event in recent_events:
            event_counts[event.event_type] += 1
            severity_counts[event.severity] += 1
            if event.blocked:
                blocked_counts[event.event_type] += 1
            unique_ips.add(event.source_ip)
        
        return {
            "period_hours": hours,
            "total_events": len(recent_events),
            "unique_ips": len(unique_ips),
            "event_types": dict(event_counts),
            "severity_distribution": dict(severity_counts),
            "blocked_by_type": dict(blocked_counts),
            "most_active_ips": self._get_most_active_ips(recent_events),
            "threat_timeline": self._get_threat_timeline(recent_events)
        }
    
    def _get_most_active_ips(self, events: List[SecurityEvent], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most active IPs from events"""
        
        ip_counts = defaultdict(int)
        ip_threats = defaultdict(set)
        
        for event in events:
            ip_counts[event.source_ip] += 1
            ip_threats[event.source_ip].add(event.event_type)
        
        # Sort by activity
        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "ip": ip,
                "event_count": count,
                "threat_types": list(ip_threats[ip]),
                "is_blocked": ip in self.blocked_ips
            }
            for ip, count in sorted_ips[:top_n]
        ]
    
    def _get_threat_timeline(self, events: List[SecurityEvent]) -> List[Dict[str, Any]]:
        """Get threat timeline (hourly buckets)"""
        
        timeline = defaultdict(lambda: defaultdict(int))
        
        for event in events:
            hour_bucket = event.timestamp.replace(minute=0, second=0, microsecond=0)
            timeline[hour_bucket][event.event_type] += 1
        
        # Convert to list format
        timeline_list = []
        for hour, event_types in sorted(timeline.items()):
            timeline_list.append({
                "hour": hour.isoformat(),
                "events": dict(event_types),
                "total": sum(event_types.values())
            })
        
        return timeline_list
    
    def _update_metrics(self, event: SecurityEvent) -> None:
        """Update threat metrics"""
        
        self.threat_metrics.total_attempts += 1
        
        if event.blocked:
            self.threat_metrics.blocked_attempts += 1
        
        if event.event_type not in self.threat_metrics.threat_types:
            self.threat_metrics.threat_types[event.event_type] = 0
        self.threat_metrics.threat_types[event.event_type] += 1
        
        if event.severity in ['high', 'critical']:
            self.threat_metrics.last_attack = event.timestamp
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked"""
        return ip in self.blocked_ips
    
    def unblock_ip(self, ip: str) -> bool:
        """Unblock an IP address"""
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            logger.info(f"IP {ip} has been unblocked")
            return True
        return False
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of currently blocked IPs"""
        return list(self.blocked_ips)


# Global security monitor instance
security_monitor = SecurityMonitor()
