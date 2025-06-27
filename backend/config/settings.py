"""
Centralized configuration management for MindBot services
Handles environment variables, validation, and service-specific settings
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, validator, Field
from pathlib import Path


class BaseConfig(BaseSettings):
    """Base configuration class with common settings"""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET", min_length=32)
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Database paths
    auth_db_path: str = Field(default="mindbot_users.db", env="AUTH_DB_PATH")
    time_db_path: str = Field(default="mindbot_time_tracking.db", env="TIME_DB_PATH")
    
    # Service URLs
    auth_service_url: str = Field(default="http://localhost:8000", env="AUTH_SERVICE_URL")
    time_service_url: str = Field(default="http://localhost:8001", env="TIME_SERVICE_URL")
    admin_service_url: str = Field(default="http://localhost:8002", env="ADMIN_SERVICE_URL")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()
    
    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        if cls.environment == 'production' and len(v) < 64:
            raise ValueError('JWT secret must be at least 64 characters in production')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class AuthServiceConfig(BaseConfig):
    """Configuration for Authentication Service"""
    
    # LiveKit
    livekit_api_key: str = Field(..., env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., env="LIVEKIT_API_SECRET")
    livekit_url: str = Field(..., env="LIVEKIT_URL")
    
    # Database
    database_path: str = Field(default="mindbot_users.db", env="DATABASE_PATH")
    
    # Token settings
    livekit_token_ttl_hours: int = Field(default=6, env="LIVEKIT_TOKEN_TTL_HOURS")
    
    # Rate limiting
    registration_rate_limit: int = Field(default=5, env="REGISTRATION_RATE_LIMIT")  # per hour
    login_rate_limit: int = Field(default=10, env="LOGIN_RATE_LIMIT")  # per minute
    
    @validator('livekit_url')
    def validate_livekit_url(cls, v):
        if not v.startswith(('ws://', 'wss://')):
            raise ValueError('LiveKit URL must start with ws:// or wss://')
        return v


class TimeServiceConfig(BaseConfig):
    """Configuration for Time Tracking Service"""
    
    # Stripe
    stripe_secret_key: str = Field(..., env="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(..., env="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    
    # Database
    database_path: str = Field(default="mindbot_time_tracking.db", env="DATABASE_PATH")
    
    # Time tracking settings
    minimum_session_minutes: int = Field(default=1, env="MINIMUM_SESSION_MINUTES")
    low_balance_threshold_minutes: int = Field(default=30, env="LOW_BALANCE_THRESHOLD_MINUTES")
    time_card_expiry_days: int = Field(default=365, env="TIME_CARD_EXPIRY_DAYS")
    
    # Payment settings
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    refund_window_days: int = Field(default=30, env="REFUND_WINDOW_DAYS")
    
    @validator('stripe_secret_key')
    def validate_stripe_key(cls, v):
        if cls.environment == 'production' and not v.startswith('sk_live_'):
            raise ValueError('Production environment requires live Stripe secret key')
        elif cls.environment != 'production' and not v.startswith('sk_test_'):
            raise ValueError('Non-production environment should use test Stripe secret key')
        return v


class AdminServiceConfig(BaseConfig):
    """Configuration for Admin Dashboard Service"""
    
    # Admin users
    admin_users: List[str] = Field(default=["admin@mindbot.ai"], env="ADMIN_USERS")
    
    # Database access
    time_db_path: str = Field(default="../time-service/mindbot_time_tracking.db", env="TIME_DB_PATH")
    auth_db_path: str = Field(default="../auth-service/mindbot_users.db", env="AUTH_DB_PATH")
    
    # Analytics settings
    default_analytics_days: int = Field(default=30, env="DEFAULT_ANALYTICS_DAYS")
    max_analytics_days: int = Field(default=365, env="MAX_ANALYTICS_DAYS")
    
    # Report settings
    max_user_report_limit: int = Field(default=1000, env="MAX_USER_REPORT_LIMIT")
    
    @validator('admin_users')
    def validate_admin_users(cls, v):
        if isinstance(v, str):
            v = [email.strip() for email in v.split(',')]
        
        for email in v:
            if '@' not in email:
                raise ValueError(f'Invalid admin email: {email}')
        
        return v


class AgentConfig(BaseConfig):
    """Configuration for Voice AI Agents"""
    
    # AI Service API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    deepgram_api_key: str = Field(..., env="DEEPGRAM_API_KEY")
    
    # LiveKit
    livekit_api_key: str = Field(..., env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., env="LIVEKIT_API_SECRET")
    livekit_url: str = Field(..., env="LIVEKIT_URL")
    
    # Agent settings
    agent_name: str = Field(default="MindBot", env="AGENT_NAME")
    max_concurrent_sessions: int = Field(default=100, env="MAX_CONCURRENT_SESSIONS")
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    
    # Voice processing
    vad_sensitivity: float = Field(default=0.5, env="VAD_SENSITIVITY")
    audio_buffer_size: int = Field(default=1024, env="AUDIO_BUFFER_SIZE")
    response_timeout_seconds: int = Field(default=30, env="RESPONSE_TIMEOUT_SECONDS")
    
    # LLM settings
    llm_model: str = Field(default="gpt-4.1-mini", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=150, env="LLM_MAX_TOKENS")
    
    # STT settings
    stt_model: str = Field(default="nova-3", env="STT_MODEL")
    stt_language: str = Field(default="multi", env="STT_LANGUAGE")
    
    # TTS settings
    tts_voice: str = Field(default="fable", env="TTS_VOICE")
    
    # Function calling
    max_function_calls_per_session: int = Field(default=10, env="MAX_FUNCTION_CALLS_PER_SESSION")
    function_timeout_seconds: int = Field(default=15, env="FUNCTION_TIMEOUT_SECONDS")
    
    @validator('vad_sensitivity')
    def validate_vad_sensitivity(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('VAD sensitivity must be between 0.0 and 1.0')
        return v
    
    @validator('llm_temperature')
    def validate_llm_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('LLM temperature must be between 0.0 and 2.0')
        return v


class SecurityConfig(BaseConfig):
    """Security-specific configuration"""
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # Security headers
    enable_security_headers: bool = Field(default=True, env="ENABLE_SECURITY_HEADERS")
    hsts_max_age: int = Field(default=31536000, env="HSTS_MAX_AGE")  # 1 year
    
    # Session security
    secure_cookies: bool = Field(default=True, env="SECURE_COOKIES")
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    
    # Input validation
    max_request_size_mb: int = Field(default=10, env="MAX_REQUEST_SIZE_MB")
    max_json_payload_mb: int = Field(default=1, env="MAX_JSON_PAYLOAD_MB")
    
    @validator('cors_origins')
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            v = [origin.strip() for origin in v.split(',')]
        
        for origin in v:
            if origin != "*" and not origin.startswith(('http://', 'https://')):
                raise ValueError(f'Invalid CORS origin: {origin}')
        
        return v


# Configuration factory
def get_config(service: str) -> BaseConfig:
    """
    Get configuration for specific service
    
    Args:
        service: Service name ('auth', 'time', 'admin', 'agent')
        
    Returns:
        Configuration instance for the service
    """
    config_map = {
        'auth': AuthServiceConfig,
        'time': TimeServiceConfig,
        'admin': AdminServiceConfig,
        'agent': AgentConfig,
        'security': SecurityConfig,
    }
    
    config_class = config_map.get(service)
    if not config_class:
        raise ValueError(f"Unknown service: {service}")
    
    return config_class()


# Environment validation
def validate_production_environment() -> List[str]:
    """
    Validate production environment requirements
    
    Returns:
        List of validation errors
    """
    errors = []
    
    try:
        # Check each service configuration
        services = ['auth', 'time', 'admin', 'agent']
        
        for service in services:
            try:
                config = get_config(service)
                
                # Production-specific checks
                if config.environment == 'production':
                    # JWT secret strength
                    if len(config.jwt_secret) < 64:
                        errors.append(f"{service}: JWT secret too weak for production")
                    
                    # Debug mode check
                    if config.debug:
                        errors.append(f"{service}: Debug mode should be disabled in production")
                    
                    # Log level check
                    if config.log_level == 'DEBUG':
                        errors.append(f"{service}: Debug logging should be disabled in production")
                        
            except Exception as e:
                errors.append(f"{service} configuration error: {e}")
                
    except Exception as e:
        errors.append(f"Configuration validation error: {e}")
    
    return errors


# Development helper
def create_development_env_file(filename: str = ".env.development") -> None:
    """
    Create a development environment file with default values
    
    Args:
        filename: Name of the environment file to create
    """
    env_content = """# MindBot Development Environment Configuration
# DO NOT USE THESE VALUES IN PRODUCTION!

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Security (CHANGE IN PRODUCTION!)
JWT_SECRET=development-jwt-secret-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database Paths
AUTH_DB_PATH=mindbot_users.db
TIME_DB_PATH=mindbot_time_tracking.db

# LiveKit Configuration (ADD YOUR TEST CREDENTIALS)
LIVEKIT_API_KEY=your_test_livekit_api_key
LIVEKIT_API_SECRET=your_test_livekit_api_secret
LIVEKIT_URL=wss://your-test-project.livekit.cloud

# Stripe Configuration (ADD YOUR TEST CREDENTIALS)
STRIPE_SECRET_KEY=sk_test_your_test_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_test_webhook_secret

# AI Service API Keys (ADD YOUR CREDENTIALS)
OPENAI_API_KEY=sk-your_test_openai_api_key
DEEPGRAM_API_KEY=your_test_deepgram_api_key

# Service URLs
AUTH_SERVICE_URL=http://localhost:8000
TIME_SERVICE_URL=http://localhost:8001
ADMIN_SERVICE_URL=http://localhost:8002

# Admin Configuration
ADMIN_USERS=admin@localhost,dev@localhost

# Agent Configuration
AGENT_NAME=MindBot-Dev
MAX_CONCURRENT_SESSIONS=10
VAD_SENSITIVITY=0.5
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.7

# Security Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT_PER_MINUTE=120
SECURE_COOKIES=false
"""
    
    with open(filename, 'w') as f:
        f.write(env_content)
    
    print(f"Development environment file created: {filename}")
    print("Remember to update it with your actual API credentials!")


# Usage example
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "validate":
            errors = validate_production_environment()
            if errors:
                print("❌ Production environment validation failed:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print("✅ Production environment validation passed")
        
        elif sys.argv[1] == "create-dev-env":
            create_development_env_file()
        
        else:
            service = sys.argv[1]
            try:
                config = get_config(service)
                print(f"✅ {service} service configuration loaded successfully")
                print(f"Environment: {config.environment}")
                print(f"Debug: {config.debug}")
                print(f"Log Level: {config.log_level}")
            except Exception as e:
                print(f"❌ Error loading {service} configuration: {e}")
                sys.exit(1)
    else:
        print("Usage:")
        print("  python settings.py validate              # Validate production environment")
        print("  python settings.py create-dev-env        # Create development .env file")
        print("  python settings.py [auth|time|admin|agent] # Test service configuration")