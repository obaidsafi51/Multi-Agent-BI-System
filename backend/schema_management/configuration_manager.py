"""
Configuration management system with multi-source loading, validation, and hot-reload capabilities.
"""

import asyncio
import json
import os
import yaml
import time
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
from copy import deepcopy
import hashlib

logger = logging.getLogger(__name__)


class ConfigurationSource(str, Enum):
    """Sources for configuration data."""
    ENVIRONMENT = "environment"
    FILE = "file"
    DATABASE = "database"
    REMOTE = "remote"
    DEFAULT = "default"


class ConfigurationFormat(str, Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"
    TOML = "toml"


@dataclass
class ConfigurationChangeEvent:
    """Event representing a configuration change."""
    timestamp: datetime
    source: ConfigurationSource
    key_path: str
    old_value: Any
    new_value: Any
    user_id: Optional[str] = None
    change_reason: Optional[str] = None


@dataclass
class ConfigurationValidationError:
    """Configuration validation error."""
    key_path: str
    message: str
    severity: str = "error"
    suggested_value: Optional[Any] = None


@dataclass
class ConfigurationSnapshot:
    """Configuration snapshot for versioning."""
    version: str
    timestamp: datetime
    configuration: Dict[str, Any]
    checksum: str
    description: Optional[str] = None
    created_by: Optional[str] = None


class ConfigurationValidator:
    """Validates configuration values and structure."""
    
    def __init__(self):
        self.validation_rules: Dict[str, Dict[str, Any]] = {}
        self.custom_validators: Dict[str, Callable] = {}
    
    def add_validation_rule(
        self,
        key_path: str,
        rule_type: str,
        **kwargs
    ):
        """
        Add validation rule for a configuration key.
        
        Args:
            key_path: Configuration key path (e.g., "database.connection.timeout")
            rule_type: Type of validation (required, type, range, regex, custom)
            **kwargs: Rule-specific parameters
        """
        self.validation_rules[key_path] = {
            "type": rule_type,
            **kwargs
        }
    
    def add_custom_validator(self, name: str, validator_func: Callable):
        """Add custom validation function."""
        self.custom_validators[name] = validator_func
    
    def validate_configuration(
        self, 
        config: Dict[str, Any]
    ) -> List[ConfigurationValidationError]:
        """
        Validate entire configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for key_path, rule in self.validation_rules.items():
            try:
                value = self._get_nested_value(config, key_path)
                error = self._validate_value(key_path, value, rule)
                if error:
                    errors.append(error)
            except KeyError:
                if rule.get("required", False):
                    errors.append(ConfigurationValidationError(
                        key_path=key_path,
                        message=f"Required configuration key '{key_path}' is missing"
                    ))
        
        return errors
    
    def _get_nested_value(self, config: Dict[str, Any], key_path: str) -> Any:
        """Get value from nested configuration using dot notation."""
        keys = key_path.split('.')
        value = config
        
        for key in keys:
            value = value[key]
        
        return value
    
    def _validate_value(
        self,
        key_path: str,
        value: Any,
        rule: Dict[str, Any]
    ) -> Optional[ConfigurationValidationError]:
        """Validate a single value against a rule."""
        rule_type = rule["type"]
        
        try:
            if rule_type == "type":
                expected_type = rule["expected_type"]
                if not isinstance(value, expected_type):
                    return ConfigurationValidationError(
                        key_path=key_path,
                        message=f"Expected type {expected_type.__name__}, got {type(value).__name__}"
                    )
            
            elif rule_type == "range":
                min_val = rule.get("min")
                max_val = rule.get("max")
                
                if min_val is not None and value < min_val:
                    return ConfigurationValidationError(
                        key_path=key_path,
                        message=f"Value {value} is below minimum {min_val}",
                        suggested_value=min_val
                    )
                
                if max_val is not None and value > max_val:
                    return ConfigurationValidationError(
                        key_path=key_path,
                        message=f"Value {value} is above maximum {max_val}",
                        suggested_value=max_val
                    )
            
            elif rule_type == "regex":
                import re
                pattern = rule["pattern"]
                if not re.match(pattern, str(value)):
                    return ConfigurationValidationError(
                        key_path=key_path,
                        message=f"Value '{value}' does not match pattern '{pattern}'"
                    )
            
            elif rule_type == "custom":
                validator_name = rule["validator"]
                if validator_name in self.custom_validators:
                    validator = self.custom_validators[validator_name]
                    if not validator(value):
                        return ConfigurationValidationError(
                            key_path=key_path,
                            message=f"Custom validation failed for '{key_path}'"
                        )
        
        except Exception as e:
            return ConfigurationValidationError(
                key_path=key_path,
                message=f"Validation error: {str(e)}"
            )
        
        return None


class ConfigurationManager:
    """
    Configuration manager with multi-source loading, validation, hot-reload,
    versioning, and API endpoints support.
    """
    
    def __init__(
        self,
        config_dir: Optional[str] = None,
        environment: str = "production",
        enable_hot_reload: bool = True,
        enable_versioning: bool = True
    ):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            environment: Current environment (dev/staging/prod)
            enable_hot_reload: Enable hot reloading of configuration
            enable_versioning: Enable configuration versioning
        """
        self.config_dir = Path(config_dir or "./config")
        self.environment = environment
        self.enable_hot_reload = enable_hot_reload
        self.enable_versioning = enable_versioning
        
        # Configuration storage
        self._config: Dict[str, Any] = {}
        self._config_sources: Dict[str, ConfigurationSource] = {}
        self._config_checksums: Dict[str, str] = {}
        
        # Validation
        self.validator = ConfigurationValidator()
        
        # Versioning
        self._snapshots: List[ConfigurationSnapshot] = []
        self._current_version = "1.0.0"
        
        # Change tracking
        self._change_history: List[ConfigurationChangeEvent] = []
        self._change_callbacks: List[Callable] = []
        
        # Hot reload
        self._file_watchers: Dict[str, Any] = {}
        self._reload_tasks: Set[asyncio.Task] = set()
        
        # API configuration
        self._api_enabled = False
        self._api_auth_required = True
        
        logger.info(f"Configuration manager initialized for environment: {environment}")
    
    async def initialize(self):
        """Initialize configuration manager."""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup validation rules
        self._setup_default_validation_rules()
        
        # Load initial configuration
        await self.load_configuration()
        
        # Setup hot reload if enabled
        if self.enable_hot_reload:
            await self._setup_hot_reload()
        
        logger.info("Configuration manager initialization completed")
    
    def _setup_default_validation_rules(self):
        """Setup default validation rules for common configuration keys."""
        # Database configuration
        self.validator.add_validation_rule(
            "database.connection.timeout",
            "range",
            min=1,
            max=300
        )
        
        self.validator.add_validation_rule(
            "database.connection.max_retries",
            "type",
            expected_type=int
        )
        
        # Cache configuration
        self.validator.add_validation_rule(
            "cache.ttl",
            "range",
            min=60,
            max=86400
        )
        
        # MCP configuration
        self.validator.add_validation_rule(
            "mcp.server_url",
            "regex",
            pattern=r"^https?://.*"
        )
        
        # Environment validation
        self.validator.add_validation_rule(
            "environment",
            "custom",
            validator="validate_environment"
        )
        
        # Add custom validators
        self.validator.add_custom_validator(
            "validate_environment",
            lambda value: value in ["development", "test", "staging", "production"]
        )
    
    async def load_configuration(self, force_reload: bool = False) -> bool:
        """
        Load configuration from all sources.
        
        Args:
            force_reload: Force reload even if not changed
            
        Returns:
            True if configuration loaded successfully
        """
        try:
            new_config = {}
            
            # Load in priority order: defaults -> files -> environment -> remote
            await self._load_default_config(new_config)
            await self._load_file_config(new_config)
            await self._load_environment_config(new_config)
            await self._load_remote_config(new_config)
            
            # Validate configuration
            validation_errors = self.validator.validate_configuration(new_config)
            if validation_errors:
                error_messages = [f"{error.key_path}: {error.message}" for error in validation_errors]
                logger.error(f"Configuration validation failed: {error_messages}")
                return False
            
            # Check for changes
            config_changed = self._has_configuration_changed(new_config)
            
            if config_changed or force_reload:
                old_config = deepcopy(self._config)
                self._config = new_config
                
                # Create snapshot if versioning enabled
                if self.enable_versioning:
                    await self._create_snapshot("Configuration loaded")
                
                # Notify change callbacks
                await self._notify_configuration_changed(old_config, new_config)
                
                logger.info("Configuration loaded and updated")
            else:
                logger.debug("Configuration unchanged, no update needed")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    async def _load_default_config(self, config: Dict[str, Any]):
        """Load default configuration values."""
        defaults = {
            "environment": self.environment,
            "database": {
                "connection": {
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_delay": 1.0
                }
            },
            "cache": {
                "ttl": 300,
                "max_entries": 10000,
                "enable_distributed": False
            },
            "mcp": {
                "server_url": "http://localhost:8000",
                "connection_timeout": 30,
                "request_timeout": 60
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": 60,
                "health_check_interval": 30
            },
            "logging": {
                "level": "INFO",
                "format": "structured"
            }
        }
        
        self._merge_config(config, defaults, ConfigurationSource.DEFAULT)
    
    async def _load_file_config(self, config: Dict[str, Any]):
        """Load configuration from files."""
        # Load base configuration
        base_config_file = self.config_dir / "config.yaml"
        if base_config_file.exists():
            file_config = await self._load_config_file(base_config_file)
            if file_config:
                self._merge_config(config, file_config, ConfigurationSource.FILE)
        
        # Load environment-specific configuration
        env_config_file = self.config_dir / f"config.{self.environment}.yaml"
        if env_config_file.exists():
            env_config = await self._load_config_file(env_config_file)
            if env_config:
                self._merge_config(config, env_config, ConfigurationSource.FILE)
    
    async def _load_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from a single file."""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    logger.warning(f"Unsupported config file format: {file_path}")
                    return None
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
            return None
    
    async def _load_environment_config(self, config: Dict[str, Any]):
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to configuration keys
        env_mappings = {
            "ENVIRONMENT": "environment",
            "DB_CONNECTION_TIMEOUT": "database.connection.timeout",
            "DB_MAX_RETRIES": "database.connection.max_retries",
            "CACHE_TTL": "cache.ttl",
            "MCP_SERVER_URL": "mcp.server_url",
            "MONITORING_ENABLED": "monitoring.enabled",
            "LOG_LEVEL": "logging.level"
        }
        
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Type conversion
                if config_key.endswith('.timeout') or config_key.endswith('.ttl'):
                    value = int(value)
                elif config_key.endswith('.enabled'):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                self._set_nested_value(env_config, config_key, value)
        
        if env_config:
            self._merge_config(config, env_config, ConfigurationSource.ENVIRONMENT)
    
    async def _load_remote_config(self, config: Dict[str, Any]):
        """Load configuration from remote sources."""
        # This would implement loading from remote configuration services
        # For now, it's a placeholder
        pass
    
    def _merge_config(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any],
        source_type: ConfigurationSource
    ):
        """Merge source configuration into target."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value, source_type)
            else:
                target[key] = value
                self._config_sources[f"{key}"] = source_type
    
    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _has_configuration_changed(self, new_config: Dict[str, Any]) -> bool:
        """Check if configuration has changed."""
        new_checksum = self._calculate_checksum(new_config)
        old_checksum = self._calculate_checksum(self._config)
        return new_checksum != old_checksum
    
    def _calculate_checksum(self, config: Dict[str, Any]) -> str:
        """Calculate checksum for configuration."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    async def get_configuration(self, key_path: Optional[str] = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key_path: Configuration key path (None for entire config)
            
        Returns:
            Configuration value
        """
        if key_path is None:
            return deepcopy(self._config)
        
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                value = value[key]
            
            return deepcopy(value)
        except KeyError:
            raise KeyError(f"Configuration key '{key_path}' not found")
    
    async def set_configuration(
        self,
        key_path: str,
        value: Any,
        user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Set configuration value.
        
        Args:
            key_path: Configuration key path
            value: New value
            user_id: User making the change
            reason: Reason for the change
            
        Returns:
            True if set successfully
        """
        try:
            # Get old value for change tracking
            try:
                old_value = await self.get_configuration(key_path)
            except KeyError:
                old_value = None
            
            # Set new value
            keys = key_path.split('.')
            current = self._config
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            
            # Validate after setting
            validation_errors = self.validator.validate_configuration(self._config)
            if validation_errors:
                # Revert change
                if old_value is not None:
                    current[keys[-1]] = old_value
                else:
                    del current[keys[-1]]
                
                error_messages = [f"{error.key_path}: {error.message}" for error in validation_errors]
                logger.error(f"Configuration validation failed after update: {error_messages}")
                return False
            
            # Record change
            change_event = ConfigurationChangeEvent(
                timestamp=datetime.now(),
                source=ConfigurationSource.REMOTE,  # API update
                key_path=key_path,
                old_value=old_value,
                new_value=value,
                user_id=user_id,
                change_reason=reason
            )
            
            self._change_history.append(change_event)
            
            # Create snapshot if versioning enabled
            if self.enable_versioning:
                await self._create_snapshot(f"Updated {key_path}", user_id)
            
            # Notify callbacks
            await self._notify_configuration_changed({key_path: old_value}, {key_path: value})
            
            logger.info(f"Configuration updated: {key_path} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set configuration {key_path}: {e}")
            return False
    
    async def validate_configuration_change(
        self,
        key_path: str,
        value: Any
    ) -> List[ConfigurationValidationError]:
        """
        Validate a configuration change without applying it.
        
        Args:
            key_path: Configuration key path
            value: New value to validate
            
        Returns:
            List of validation errors
        """
        # Create temporary config with the change
        temp_config = deepcopy(self._config)
        self._set_nested_value(temp_config, key_path, value)
        
        # Validate the temporary config
        return self.validator.validate_configuration(temp_config)
    
    async def _create_snapshot(
        self,
        description: str,
        created_by: Optional[str] = None
    ) -> str:
        """Create configuration snapshot."""
        version = self._generate_next_version()
        checksum = self._calculate_checksum(self._config)
        
        snapshot = ConfigurationSnapshot(
            version=version,
            timestamp=datetime.now(),
            configuration=deepcopy(self._config),
            checksum=checksum,
            description=description,
            created_by=created_by
        )
        
        self._snapshots.append(snapshot)
        self._current_version = version
        
        # Keep only last 100 snapshots
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        
        logger.info(f"Created configuration snapshot: {version}")
        return version
    
    def _generate_next_version(self) -> str:
        """Generate next version number."""
        if not self._snapshots:
            return "1.0.0"
        
        latest_version = self._snapshots[-1].version
        parts = latest_version.split('.')
        patch = int(parts[2]) + 1
        
        return f"{parts[0]}.{parts[1]}.{patch}"
    
    async def rollback_to_version(self, version: str) -> bool:
        """
        Rollback configuration to a specific version.
        
        Args:
            version: Version to rollback to
            
        Returns:
            True if rollback successful
        """
        try:
            # Find snapshot
            snapshot = None
            for snap in self._snapshots:
                if snap.version == version:
                    snapshot = snap
                    break
            
            if not snapshot:
                logger.error(f"Configuration version {version} not found")
                return False
            
            # Apply rollback
            old_config = deepcopy(self._config)
            self._config = deepcopy(snapshot.configuration)
            
            # Create new snapshot for rollback
            await self._create_snapshot(f"Rollback to version {version}")
            
            # Notify callbacks
            await self._notify_configuration_changed(old_config, self._config)
            
            logger.info(f"Configuration rolled back to version {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback to version {version}: {e}")
            return False
    
    def add_change_callback(self, callback: Callable):
        """Add callback for configuration changes."""
        self._change_callbacks.append(callback)
    
    async def _notify_configuration_changed(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ):
        """Notify all callbacks about configuration changes."""
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_config, new_config)
                else:
                    callback(old_config, new_config)
            except Exception as e:
                logger.warning(f"Configuration change callback failed: {e}")
    
    async def _setup_hot_reload(self):
        """Setup hot reload for configuration files."""
        try:
            # This would implement file watching for hot reload
            # For now, it's a placeholder that sets up periodic checks
            task = asyncio.create_task(self._hot_reload_loop())
            self._reload_tasks.add(task)
            
            logger.info("Hot reload enabled for configuration files")
        except Exception as e:
            logger.warning(f"Failed to setup hot reload: {e}")
    
    async def _hot_reload_loop(self):
        """Hot reload monitoring loop."""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Check file modifications
                config_files = [
                    self.config_dir / "config.yaml",
                    self.config_dir / f"config.{self.environment}.yaml"
                ]
                
                should_reload = False
                for config_file in config_files:
                    if config_file.exists():
                        current_checksum = self._calculate_file_checksum(config_file)
                        cached_checksum = self._config_checksums.get(str(config_file))
                        
                        if current_checksum != cached_checksum:
                            self._config_checksums[str(config_file)] = current_checksum
                            should_reload = True
                
                if should_reload:
                    logger.info("Configuration file changed, reloading...")
                    await self.load_configuration(force_reload=True)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in hot reload loop: {e}")
                await asyncio.sleep(30)  # Wait longer after error
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate checksum for a file."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """Get configuration manager information."""
        return {
            "environment": self.environment,
            "current_version": self._current_version,
            "total_snapshots": len(self._snapshots),
            "hot_reload_enabled": self.enable_hot_reload,
            "versioning_enabled": self.enable_versioning,
            "change_history_count": len(self._change_history),
            "last_loaded": datetime.now().isoformat(),
            "configuration_sources": dict(self._config_sources)
        }
    
    def get_change_history(
        self,
        limit: int = 50,
        key_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Maximum number of changes to return
            key_path: Filter by specific key path
            
        Returns:
            List of change events
        """
        history = self._change_history
        
        if key_path:
            history = [change for change in history if change.key_path == key_path]
        
        # Sort by timestamp (newest first) and limit
        history = sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "timestamp": change.timestamp.isoformat(),
                "source": change.source,
                "key_path": change.key_path,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "user_id": change.user_id,
                "change_reason": change.change_reason
            }
            for change in history
        ]
    
    def get_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get configuration snapshots."""
        snapshots = sorted(self._snapshots, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "version": snapshot.version,
                "timestamp": snapshot.timestamp.isoformat(),
                "checksum": snapshot.checksum,
                "description": snapshot.description,
                "created_by": snapshot.created_by
            }
            for snapshot in snapshots
        ]
    
    async def backup_configuration(self, backup_path: Optional[str] = None) -> str:
        """
        Create configuration backup.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"config_backup_{timestamp}.json"
        
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "version": self._current_version,
            "environment": self.environment,
            "configuration": self._config,
            "snapshots": [
                {
                    "version": snap.version,
                    "timestamp": snap.timestamp.isoformat(),
                    "configuration": snap.configuration,
                    "description": snap.description,
                    "created_by": snap.created_by
                }
                for snap in self._snapshots
            ]
        }
        
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        logger.info(f"Configuration backup created: {backup_path}")
        return backup_path
    
    async def restore_configuration(self, backup_path: str) -> bool:
        """
        Restore configuration from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful
        """
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Restore configuration
            old_config = deepcopy(self._config)
            self._config = backup_data["configuration"]
            
            # Restore snapshots
            self._snapshots = []
            for snap_data in backup_data.get("snapshots", []):
                snapshot = ConfigurationSnapshot(
                    version=snap_data["version"],
                    timestamp=datetime.fromisoformat(snap_data["timestamp"]),
                    configuration=snap_data["configuration"],
                    checksum=self._calculate_checksum(snap_data["configuration"]),
                    description=snap_data.get("description"),
                    created_by=snap_data.get("created_by")
                )
                self._snapshots.append(snapshot)
            
            # Validate restored configuration
            validation_errors = self.validator.validate_configuration(self._config)
            if validation_errors:
                # Revert restore
                self._config = old_config
                error_messages = [f"{error.key_path}: {error.message}" for error in validation_errors]
                logger.error(f"Restored configuration validation failed: {error_messages}")
                return False
            
            # Create snapshot for restore
            await self._create_snapshot(f"Restored from backup: {backup_path}")
            
            # Notify callbacks
            await self._notify_configuration_changed(old_config, self._config)
            
            logger.info(f"Configuration restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore configuration from {backup_path}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown configuration manager."""
        # Cancel hot reload tasks
        for task in self._reload_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._reload_tasks:
            await asyncio.gather(*self._reload_tasks, return_exceptions=True)
        
        logger.info("Configuration manager shutdown completed")
