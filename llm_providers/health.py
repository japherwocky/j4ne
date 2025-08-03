"""
Health monitoring for LLM providers.

This module provides utilities for monitoring the health and status of LLM providers.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from llm_providers.base import LLMProvider
from llm_providers.registry import ProviderRegistry
from llm_providers.config import ProviderConfig

logger = logging.getLogger(__name__)


class ProviderHealthMonitor:
    """Monitor the health of LLM providers."""
    
    def __init__(self, registry: ProviderRegistry, config: ProviderConfig):
        """
        Initialize the health monitor.
        
        Args:
            registry: Provider registry instance
            config: Provider configuration instance
        """
        self.registry = registry
        self.config = config
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_check: Optional[datetime] = None
    
    def check_provider_health(self, provider: LLMProvider) -> Dict[str, Any]:
        """
        Check the health of a specific provider.
        
        Args:
            provider: The provider to check
            
        Returns:
            Health status dictionary
        """
        try:
            health_result = provider.health_check()
            
            # Add timestamp
            health_result['timestamp'] = datetime.now().isoformat()
            health_result['provider_name'] = provider.name
            
            # Store in history
            if provider.name not in self.health_history:
                self.health_history[provider.name] = []
            
            self.health_history[provider.name].append(health_result)
            
            # Keep only last 10 health checks
            if len(self.health_history[provider.name]) > 10:
                self.health_history[provider.name] = self.health_history[provider.name][-10:]
            
            return health_result
            
        except Exception as e:
            logger.error(f"Error checking health for provider {provider.name}: {str(e)}")
            error_result = {
                'status': 'error',
                'error': f"Health check failed: {str(e)}",
                'provider': provider.name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store error in history
            if provider.name not in self.health_history:
                self.health_history[provider.name] = []
            self.health_history[provider.name].append(error_result)
            
            return error_result
    
    def check_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Check the health of all configured providers.
        
        Returns:
            Dictionary mapping provider names to health status
        """
        results = {}
        configured_providers = self.config.get_available_providers()
        
        # Ensure providers are registered
        self.registry._ensure_providers_registered()
        
        for provider_name in configured_providers:
            provider_config = self.config.get_provider_config(provider_name)
            if not provider_config:
                results[provider_name] = {
                    'status': 'error',
                    'error': 'No configuration found',
                    'provider': provider_name,
                    'timestamp': datetime.now().isoformat()
                }
                continue
            
            # Try to create provider for health check
            provider = self.registry.create_provider(provider_name, provider_config)
            if not provider:
                results[provider_name] = {
                    'status': 'error',
                    'error': 'Failed to initialize provider',
                    'provider': provider_name,
                    'timestamp': datetime.now().isoformat()
                }
                continue
            
            results[provider_name] = self.check_provider_health(provider)
        
        self.last_check = datetime.now()
        return results
    
    def get_provider_history(self, provider_name: str) -> List[Dict[str, Any]]:
        """
        Get health check history for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            List of health check results
        """
        return self.health_history.get(provider_name, [])
    
    def get_provider_uptime(self, provider_name: str, hours: int = 24) -> float:
        """
        Calculate provider uptime percentage over the specified period.
        
        Args:
            provider_name: Name of the provider
            hours: Number of hours to look back
            
        Returns:
            Uptime percentage (0.0 to 1.0)
        """
        history = self.get_provider_history(provider_name)
        if not history:
            return 0.0
        
        # Filter history to the specified time period
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_checks = []
        
        for check in history:
            try:
                check_time = datetime.fromisoformat(check['timestamp'])
                if check_time >= cutoff_time:
                    recent_checks.append(check)
            except (KeyError, ValueError):
                continue
        
        if not recent_checks:
            return 0.0
        
        # Calculate uptime
        healthy_checks = sum(1 for check in recent_checks if check.get('status') == 'healthy')
        return healthy_checks / len(recent_checks)
    
    def get_summary_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive health summary report.
        
        Returns:
            Summary report dictionary
        """
        current_health = self.check_all_providers()
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'total_providers': len(current_health),
            'healthy_providers': sum(1 for h in current_health.values() if h.get('status') == 'healthy'),
            'unhealthy_providers': sum(1 for h in current_health.values() if h.get('status') != 'healthy'),
            'current_provider': self.registry.get_current_provider_name(),
            'provider_details': current_health,
            'uptime_24h': {}
        }
        
        # Calculate 24-hour uptime for each provider
        for provider_name in current_health.keys():
            summary['uptime_24h'][provider_name] = self.get_provider_uptime(provider_name, 24)
        
        return summary
    
    def is_provider_healthy(self, provider_name: str) -> bool:
        """
        Check if a provider is currently healthy.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if healthy, False otherwise
        """
        history = self.get_provider_history(provider_name)
        if not history:
            return False
        
        latest_check = history[-1]
        return latest_check.get('status') == 'healthy'
    
    def get_unhealthy_providers(self) -> List[str]:
        """
        Get a list of currently unhealthy providers.
        
        Returns:
            List of provider names that are unhealthy
        """
        unhealthy = []
        configured_providers = self.config.get_available_providers()
        
        for provider_name in configured_providers:
            if not self.is_provider_healthy(provider_name):
                unhealthy.append(provider_name)
        
        return unhealthy
    
    async def continuous_monitoring(self, interval_minutes: int = 5) -> None:
        """
        Run continuous health monitoring in the background.
        
        Args:
            interval_minutes: Minutes between health checks
        """
        logger.info(f"Starting continuous health monitoring (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                logger.debug("Running scheduled health check")
                self.check_all_providers()
                
                # Log any unhealthy providers
                unhealthy = self.get_unhealthy_providers()
                if unhealthy:
                    logger.warning(f"Unhealthy providers detected: {', '.join(unhealthy)}")
                
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

