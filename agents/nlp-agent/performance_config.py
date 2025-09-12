"""
Performance configuration settings for the NLP Agent.
Centralized configuration for all performance optimization parameters.
"""

from typing import Dict, Any

class PerformanceConfig:
    """Centralized performance configuration"""
    
    # WebSocket Connection Settings
    WEBSOCKET_CONFIG = {
        "initial_reconnect_delay": 0.5,      # Fast initial reconnection
        "max_reconnect_delay": 30.0,         # Reasonable max delay
        "connection_timeout": 6.0,           # Quick connection timeout detection
        "request_timeout": 15.0,             # Reasonable request timeout
        "heartbeat_interval": 20.0,          # Frequent heartbeats for quick detection
        "health_check_interval": 45.0,       # Regular health checks
        "ping_timeout": 5.0,                 # Quick ping timeout
        "enable_request_batching": True,
        "batch_size": 5,
        "batch_timeout": 0.1
    }
    
    # Performance Optimizer Settings
    OPTIMIZER_CONFIG = {
        "memory_cache_size": 1500,           # Large memory cache for speed
        "semantic_cache_size": 800,          # Good semantic cache size
        "query_cache_size": 400,             # Adequate query result cache
        "schema_cache_ttl": 900,             # 15 minutes - schemas don't change often
        "context_cache_ttl": 450,            # 7.5 minutes - context can change
        "semantic_similarity_threshold": 0.85, # Balanced precision/recall
        "enable_request_deduplication": True,
        "enable_response_prediction": True
    }
    
    # Query Processing Settings
    QUERY_CONFIG = {
        "fast_path_enabled": True,           # Enable fast-path optimization
        "simple_query_max_words": 10,       # Max words for simple queries
        "cache_ttl_simple": 600,             # 10 minutes for simple queries
        "cache_ttl_complex": 300,            # 5 minutes for complex queries
        "cache_ttl_time_based": 1800,        # 30 minutes for historical queries
        "cache_ttl_current": 60              # 1 minute for current data queries
    }
    
    # Circuit Breaker Settings
    CIRCUIT_BREAKER_CONFIG = {
        "threshold": 5,                      # Failures before opening
        "timeout": 60.0,                     # Timeout before retry
        "max_concurrent_requests": 100       # Max concurrent requests
    }
    
    # Monitoring Settings
    MONITORING_CONFIG = {
        "performance_analysis_interval": 180, # 3 minutes
        "cache_cleanup_interval": 60,        # 1 minute
        "memory_optimization_interval": 1800, # 30 minutes
        "cache_warming_interval": 900,       # 15 minutes
        "max_response_time_history": 1000,   # Keep last 1000 response times
        "performance_alert_threshold": 5.0   # Alert if avg response > 5s
    }
    
    # Environment-specific overrides
    ENVIRONMENT_OVERRIDES = {
        "development": {
            "semantic_similarity_threshold": 0.80,  # Lower for more matches
            "cache_ttl_simple": 300,                # Shorter TTL for dev
            "health_check_interval": 30.0           # More frequent checks
        },
        "production": {
            "semantic_similarity_threshold": 0.88,  # Higher for precision
            "cache_ttl_simple": 900,                # Longer TTL for prod
            "memory_cache_size": 2000               # Larger cache for prod
        }
    }
    
    @classmethod
    def get_config(cls, environment: str = "development") -> Dict[str, Any]:
        """Get complete configuration with environment overrides"""
        config = {
            "websocket": cls.WEBSOCKET_CONFIG.copy(),
            "optimizer": cls.OPTIMIZER_CONFIG.copy(),
            "query": cls.QUERY_CONFIG.copy(),
            "circuit_breaker": cls.CIRCUIT_BREAKER_CONFIG.copy(),
            "monitoring": cls.MONITORING_CONFIG.copy()
        }
        
        # Apply environment-specific overrides
        if environment in cls.ENVIRONMENT_OVERRIDES:
            overrides = cls.ENVIRONMENT_OVERRIDES[environment]
            
            # Apply overrides to relevant sections
            for key, value in overrides.items():
                if key in cls.OPTIMIZER_CONFIG:
                    config["optimizer"][key] = value
                elif key in cls.WEBSOCKET_CONFIG:
                    config["websocket"][key] = value
                elif key in cls.QUERY_CONFIG:
                    config["query"][key] = value
        
        return config
    
    @classmethod
    def get_websocket_config(cls, environment: str = "development") -> Dict[str, Any]:
        """Get WebSocket-specific configuration"""
        return cls.get_config(environment)["websocket"]
    
    @classmethod
    def get_optimizer_config(cls, environment: str = "development") -> Dict[str, Any]:
        """Get optimizer-specific configuration"""
        return cls.get_config(environment)["optimizer"]
    
    @classmethod
    def print_config(cls, environment: str = "development"):
        """Print current configuration for debugging"""
        import json
        config = cls.get_config(environment)
        print(f"Performance Configuration for {environment}:")
        print(json.dumps(config, indent=2))

# Performance monitoring thresholds
class PerformanceThresholds:
    """Performance thresholds for alerts and optimizations"""
    
    # Response time thresholds (in seconds)
    RESPONSE_TIME_EXCELLENT = 1.0
    RESPONSE_TIME_GOOD = 2.0
    RESPONSE_TIME_ACCEPTABLE = 5.0
    RESPONSE_TIME_POOR = 10.0
    
    # Cache hit rate thresholds
    CACHE_HIT_RATE_EXCELLENT = 0.8
    CACHE_HIT_RATE_GOOD = 0.6
    CACHE_HIT_RATE_ACCEPTABLE = 0.4
    CACHE_HIT_RATE_POOR = 0.2
    
    # Connection stability thresholds
    CONNECTION_FAILURES_LOW = 2
    CONNECTION_FAILURES_MEDIUM = 5
    CONNECTION_FAILURES_HIGH = 10
    
    @classmethod
    def get_response_time_category(cls, response_time: float) -> str:
        """Categorize response time performance"""
        if response_time <= cls.RESPONSE_TIME_EXCELLENT:
            return "excellent"
        elif response_time <= cls.RESPONSE_TIME_GOOD:
            return "good"
        elif response_time <= cls.RESPONSE_TIME_ACCEPTABLE:
            return "acceptable"
        else:
            return "poor"
    
    @classmethod
    def get_cache_hit_category(cls, hit_rate: float) -> str:
        """Categorize cache hit rate performance"""
        if hit_rate >= cls.CACHE_HIT_RATE_EXCELLENT:
            return "excellent"
        elif hit_rate >= cls.CACHE_HIT_RATE_GOOD:
            return "good"
        elif hit_rate >= cls.CACHE_HIT_RATE_ACCEPTABLE:
            return "acceptable"
        else:
            return "poor"
    
    @classmethod
    def should_alert(cls, response_time: float, hit_rate: float, failures: int) -> bool:
        """Determine if performance alert should be triggered"""
        return (
            response_time > cls.RESPONSE_TIME_POOR or
            hit_rate < cls.CACHE_HIT_RATE_POOR or
            failures > cls.CONNECTION_FAILURES_HIGH
        )

if __name__ == "__main__":
    # Print configurations for different environments
    print("=== Development Configuration ===")
    PerformanceConfig.print_config("development")
    
    print("\n=== Production Configuration ===")
    PerformanceConfig.print_config("production")
