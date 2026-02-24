"""
Advanced monitoring and metrics collection for ABOA system.
"""

import time
import asyncio
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from contextlib import asynccontextmanager

from aboa.core.config import get_settings
from aboa.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    unit: str
    tags: Dict[str, str]
    timestamp: datetime


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    uptime_seconds: float


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    requests_total: int
    requests_per_second: float
    response_time_avg: float
    response_time_p95: float
    error_rate: float
    active_connections: int
    database_connections: int
    cache_hit_rate: float


class MetricsCollector:
    """Collects and aggregates system and application metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.start_time = time.time()
        self.metrics_history: deque = deque(maxlen=max_history)
        self.request_times: deque = deque(maxlen=1000)
        self.request_count = 0
        self.error_count = 0
        self.active_connections = 0
        self._lock = threading.Lock()
        
        # Network baseline
        self._network_baseline = None
        self._last_network_check = None
        
    def record_request(self, duration: float, status_code: int):
        """Record a request with its duration and status code."""
        with self._lock:
            self.request_count += 1
            self.request_times.append(duration)
            
            if status_code >= 400:
                self.error_count += 1
    
    def increment_connections(self):
        """Increment active connection count."""
        with self._lock:
            self.active_connections += 1
    
    def decrement_connections(self):
        """Decrement active connection count."""
        with self._lock:
            self.active_connections = max(0, self.active_connections - 1)
    
    @asynccontextmanager
    async def track_connection(self):
        """Context manager to track active connections."""
        self.increment_connections()
        try:
            yield
        finally:
            self.decrement_connections()
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system resource metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = (memory.total - memory.available) / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        # Network metrics
        network = psutil.net_io_counters()
        if self._network_baseline is None:
            self._network_baseline = network
            self._last_network_check = time.time()
        
        # Process metrics
        process = psutil.Process()
        thread_count = process.num_threads()
        
        # System uptime
        uptime_seconds = time.time() - self.start_time
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_percent=disk.percent,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            process_count=len(psutil.pids()),
            thread_count=thread_count,
            uptime_seconds=uptime_seconds
        )
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        with self._lock:
            # Request metrics
            requests_total = self.request_count
            
            # Calculate requests per second (last minute)
            current_time = time.time()
            recent_requests = sum(1 for _ in self.request_times 
                                if current_time - _ < 60)
            requests_per_second = recent_requests / 60.0
            
            # Response time metrics
            if self.request_times:
                response_times = list(self.request_times)
                response_time_avg = sum(response_times) / len(response_times)
                response_times_sorted = sorted(response_times)
                p95_index = int(len(response_times_sorted) * 0.95)
                response_time_p95 = response_times_sorted[p95_index] if response_times_sorted else 0
            else:
                response_time_avg = 0
                response_time_p95 = 0
            
            # Error rate
            error_rate = (self.error_count / max(requests_total, 1)) * 100
            
            # Connection metrics
            active_connections = self.active_connections
            
        return ApplicationMetrics(
            requests_total=requests_total,
            requests_per_second=requests_per_second,
            response_time_avg=response_time_avg,
            response_time_p95=response_time_p95,
            error_rate=error_rate,
            active_connections=active_connections,
            database_connections=0,  # TODO: Implement database connection tracking
            cache_hit_rate=0.0  # TODO: Implement cache hit rate tracking
        )
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all current metrics."""
        system_metrics = self.get_system_metrics()
        app_metrics = self.get_application_metrics()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": asdict(system_metrics),
            "application": asdict(app_metrics)
        }
        
        # Store in history
        self.metrics_history.append(metrics)
        
        return metrics
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Get metrics summary for the specified duration."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not recent_metrics:
            return self.collect_metrics()
        
        # Calculate averages and trends
        cpu_values = [m["system"]["cpu_percent"] for m in recent_metrics]
        memory_values = [m["system"]["memory_percent"] for m in recent_metrics]
        response_times = [m["application"]["response_time_avg"] for m in recent_metrics]
        
        return {
            "period_minutes": duration_minutes,
            "data_points": len(recent_metrics),
            "system": {
                "cpu_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "cpu_max": max(cpu_values) if cpu_values else 0,
                "memory_avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                "memory_max": max(memory_values) if memory_values else 0,
            },
            "application": {
                "response_time_avg": sum(response_times) / len(response_times) if response_times else 0,
                "response_time_max": max(response_times) if response_times else 0,
                "total_requests": sum(m["application"]["requests_total"] for m in recent_metrics[-1:]),
                "error_rate_avg": sum(m["application"]["error_rate"] for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0,
            },
            "latest": recent_metrics[-1] if recent_metrics else None
        }


class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.settings = get_settings()
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "cpu_critical": 90.0,
            "cpu_warning": 70.0,
            "memory_critical": 90.0,
            "memory_warning": 70.0,
            "disk_critical": 95.0,
            "disk_warning": 80.0,
            "response_time_critical": 5.0,  # seconds
            "response_time_warning": 2.0,   # seconds
            "error_rate_critical": 10.0,    # percent
            "error_rate_warning": 5.0,      # percent
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts."""
        current_metrics = self.metrics_collector.collect_metrics()
        alerts = []
        
        system = current_metrics["system"]
        app = current_metrics["application"]
        
        # CPU alerts
        if system["cpu_percent"] >= self.alert_thresholds["cpu_critical"]:
            alerts.append({
                "level": "critical",
                "type": "cpu",
                "message": f"CPU usage critical: {system['cpu_percent']:.1f}%",
                "value": system["cpu_percent"],
                "threshold": self.alert_thresholds["cpu_critical"]
            })
        elif system["cpu_percent"] >= self.alert_thresholds["cpu_warning"]:
            alerts.append({
                "level": "warning",
                "type": "cpu",
                "message": f"CPU usage high: {system['cpu_percent']:.1f}%",
                "value": system["cpu_percent"],
                "threshold": self.alert_thresholds["cpu_warning"]
            })
        
        # Memory alerts
        if system["memory_percent"] >= self.alert_thresholds["memory_critical"]:
            alerts.append({
                "level": "critical",
                "type": "memory",
                "message": f"Memory usage critical: {system['memory_percent']:.1f}%",
                "value": system["memory_percent"],
                "threshold": self.alert_thresholds["memory_critical"]
            })
        elif system["memory_percent"] >= self.alert_thresholds["memory_warning"]:
            alerts.append({
                "level": "warning",
                "type": "memory",
                "message": f"Memory usage high: {system['memory_percent']:.1f}%",
                "value": system["memory_percent"],
                "threshold": self.alert_thresholds["memory_warning"]
            })
        
        # Disk alerts
        if system["disk_percent"] >= self.alert_thresholds["disk_critical"]:
            alerts.append({
                "level": "critical",
                "type": "disk",
                "message": f"Disk usage critical: {system['disk_percent']:.1f}%",
                "value": system["disk_percent"],
                "threshold": self.alert_thresholds["disk_critical"]
            })
        elif system["disk_percent"] >= self.alert_thresholds["disk_warning"]:
            alerts.append({
                "level": "warning",
                "type": "disk",
                "message": f"Disk usage high: {system['disk_percent']:.1f}%",
                "value": system["disk_percent"],
                "threshold": self.alert_thresholds["disk_warning"]
            })
        
        # Response time alerts
        if app["response_time_avg"] >= self.alert_thresholds["response_time_critical"]:
            alerts.append({
                "level": "critical",
                "type": "response_time",
                "message": f"Response time critical: {app['response_time_avg']:.2f}s",
                "value": app["response_time_avg"],
                "threshold": self.alert_thresholds["response_time_critical"]
            })
        elif app["response_time_avg"] >= self.alert_thresholds["response_time_warning"]:
            alerts.append({
                "level": "warning",
                "type": "response_time",
                "message": f"Response time high: {app['response_time_avg']:.2f}s",
                "value": app["response_time_avg"],
                "threshold": self.alert_thresholds["response_time_warning"]
            })
        
        # Error rate alerts
        if app["error_rate"] >= self.alert_thresholds["error_rate_critical"]:
            alerts.append({
                "level": "critical",
                "type": "error_rate",
                "message": f"Error rate critical: {app['error_rate']:.1f}%",
                "value": app["error_rate"],
                "threshold": self.alert_thresholds["error_rate_critical"]
            })
        elif app["error_rate"] >= self.alert_thresholds["error_rate_warning"]:
            alerts.append({
                "level": "warning",
                "type": "error_rate",
                "message": f"Error rate high: {app['error_rate']:.1f}%",
                "value": app["error_rate"],
                "threshold": self.alert_thresholds["error_rate_warning"]
            })
        
        # Add timestamp to alerts
        for alert in alerts:
            alert["timestamp"] = datetime.utcnow().isoformat()
        
        # Store in history
        if alerts:
            self.alert_history.extend(alerts)
            # Keep only last 100 alerts
            self.alert_history = self.alert_history[-100:]
        
        return alerts


# Global instances
_metrics_collector = None
_alert_manager = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(get_metrics_collector())
    return _alert_manager