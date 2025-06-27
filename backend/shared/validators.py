"""
Common validation utilities for MindBot services
Provides reusable validation functions and Pydantic models
"""

import re
import secrets
import string
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, validator, Field, EmailStr


# Regular expressions for validation
PHONE_REGEX = re.compile(r'^\+?1?\d{9,15}$')
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')


# Base validation functions
def validate_email(email: str) -> bool:
    """Validate email format using basic regex"""
    email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return bool(email_regex.match(email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    return bool(PHONE_REGEX.match(phone))


def validate_strong_password(password: str) -> bool:
    """
    Validate strong password requirements:
    - At least 8 characters
    - At least one lowercase letter
    - At least one uppercase letter  
    - At least one digit
    - At least one special character
    """
    return bool(PASSWORD_REGEX.match(password))


def validate_username(username: str) -> bool:
    """Validate username format (alphanumeric, hyphens, underscores)"""
    return bool(USERNAME_REGEX.match(username))


def generate_secure_code(length: int = 12, include_special: bool = False) -> str:
    """
    Generate a secure random code
    
    Args:
        length: Length of the code
        include_special: Whether to include special characters
        
    Returns:
        Secure random code
    """
    alphabet = string.ascii_uppercase + string.digits
    if include_special:
        alphabet += "!@#$%^&*"
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def format_activation_code(code: str, separator: str = "-", group_size: int = 4) -> str:
    """
    Format activation code with separators
    
    Args:
        code: Raw code string
        separator: Separator character
        group_size: Size of each group
        
    Returns:
        Formatted code (e.g., "ABCD-EFGH-IJKL")
    """
    groups = [code[i:i+group_size] for i in range(0, len(code), group_size)]
    return separator.join(groups)


# Pydantic models for common validation
class BaseUser(BaseModel):
    """Base user model with common validation"""
    
    email: EmailStr = Field(..., description="Valid email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    
    @validator('full_name')
    def validate_full_name(cls, v):
        # Remove extra whitespace and validate
        name = ' '.join(v.split())
        if len(name.split()) < 1:
            raise ValueError('Full name must contain at least one word')
        if not re.match(r'^[a-zA-Z\s\'-\.]+$', name):
            raise ValueError('Full name contains invalid characters')
        return name


class StrongPassword(BaseModel):
    """Password validation model"""
    
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not validate_strong_password(v):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character'
            )
        return v


class UserRegistration(BaseUser, StrongPassword):
    """Complete user registration validation"""
    
    confirm_password: str = Field(..., description="Password confirmation")
    terms_accepted: bool = Field(..., description="Terms and conditions acceptance")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('terms_accepted')
    def terms_must_be_accepted(cls, v):
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class TimeCardValidation(BaseModel):
    """Time card validation model"""
    
    activation_code: str = Field(..., description="Time card activation code")
    
    @validator('activation_code')
    def validate_activation_code(cls, v):
        # Remove any separators and validate format
        code = v.replace('-', '').replace(' ', '').upper()
        
        if len(code) != 12:
            raise ValueError('Activation code must be 12 characters long')
        
        if not re.match(r'^[A-Z0-9]{12}$', code):
            raise ValueError('Activation code must contain only letters and numbers')
        
        return code


class PaymentValidation(BaseModel):
    """Payment validation model"""
    
    amount_cents: int = Field(..., gt=0, description="Payment amount in cents")
    currency: str = Field(default="usd", regex=r'^[a-z]{3}$', description="Currency code")
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    
    @validator('amount_cents')
    def validate_amount(cls, v):
        # Minimum $0.50, maximum $10,000
        if v < 50:
            raise ValueError('Minimum payment amount is $0.50')
        if v > 1000000:
            raise ValueError('Maximum payment amount is $10,000')
        return v


class SessionValidation(BaseModel):
    """Voice session validation model"""
    
    session_id: str = Field(..., min_length=1, max_length=100)
    room_name: str = Field(..., min_length=1, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=0, le=86400)  # Max 24 hours
    
    @validator('session_id', 'room_name')
    def validate_identifiers(cls, v):
        # Only alphanumeric, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Must contain only letters, numbers, hyphens, and underscores')
        return v


class AdminValidation(BaseModel):
    """Admin operation validation model"""
    
    admin_email: EmailStr = Field(..., description="Admin email address")
    action: str = Field(..., description="Admin action")
    target_user_id: Optional[int] = Field(None, description="Target user ID")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for action")
    
    @validator('action')
    def validate_admin_action(cls, v):
        allowed_actions = [
            'view_user', 'modify_balance', 'refund_payment', 
            'ban_user', 'unban_user', 'reset_password'
        ]
        if v not in allowed_actions:
            raise ValueError(f'Invalid admin action. Must be one of: {allowed_actions}')
        return v


class PricingTierValidation(BaseModel):
    """Pricing tier validation model"""
    
    name: str = Field(..., min_length=1, max_length=50)
    hours: int = Field(..., ge=1, le=1000)
    price_cents: int = Field(..., ge=50, le=10000000)  # $0.50 to $100,000
    bonus_minutes: int = Field(default=0, ge=0, le=60000)  # Max ~1000 hours bonus
    description: str = Field(..., max_length=200)
    active: bool = Field(default=True)
    
    @validator('name')
    def validate_tier_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-]+$', v):
            raise ValueError('Tier name can only contain letters, numbers, spaces, and hyphens')
        return v.strip()


# Validation helper functions
def validate_jwt_claims(claims: Dict[str, Any]) -> bool:
    """
    Validate JWT token claims
    
    Args:
        claims: JWT token claims dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['user_id', 'email', 'exp', 'iat']
    
    # Check required fields
    for field in required_fields:
        if field not in claims:
            return False
    
    # Check expiration
    exp_timestamp = claims.get('exp', 0)
    if datetime.utcnow().timestamp() > exp_timestamp:
        return False
    
    # Check user_id format
    user_id = claims.get('user_id')
    if not isinstance(user_id, (int, str)) or not str(user_id).isdigit():
        return False
    
    # Check email format
    email = claims.get('email', '')
    if not validate_email(email):
        return False
    
    return True


def validate_time_balance(balance_data: Dict[str, Any]) -> bool:
    """
    Validate time balance data structure
    
    Args:
        balance_data: Balance data dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['total_minutes', 'active_cards']
    
    for field in required_fields:
        if field not in balance_data:
            return False
    
    # Validate data types and ranges
    total_minutes = balance_data.get('total_minutes', 0)
    if not isinstance(total_minutes, (int, float)) or total_minutes < 0:
        return False
    
    active_cards = balance_data.get('active_cards', 0)
    if not isinstance(active_cards, int) or active_cards < 0:
        return False
    
    return True


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        input_string: Raw input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_string, str):
        return ""
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in input_string if ord(char) >= 32 or char in '\t\n\r')
    
    # Trim to max length
    sanitized = sanitized[:max_length]
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def validate_environment_variables(required_vars: List[str], env_dict: Dict[str, str]) -> List[str]:
    """
    Validate that required environment variables are set
    
    Args:
        required_vars: List of required variable names
        env_dict: Environment variables dictionary
        
    Returns:
        List of missing variables
    """
    missing = []
    
    for var in required_vars:
        value = env_dict.get(var)
        if not value or value.strip() == '':
            missing.append(var)
    
    return missing


# Rate limiting validation
class RateLimitValidation:
    """Rate limiting validation for API endpoints"""
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = {}  # {client_id: [timestamps]}
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if client is within rate limits
        
        Args:
            client_id: Unique client identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Get client's request history
        client_requests = self.requests.get(client_id, [])
        
        # Remove old requests outside the window
        client_requests = [req_time for req_time in client_requests if req_time > window_start]
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add current request
        client_requests.append(now)
        self.requests[client_id] = client_requests
        
        return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """Get number of remaining requests for client"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        client_requests = self.requests.get(client_id, [])
        current_count = len([req for req in client_requests if req > window_start])
        
        return max(0, self.max_requests - current_count)


# Usage examples and tests
if __name__ == "__main__":
    # Test password validation
    print("Testing password validation:")
    passwords = [
        "weak",  # Too weak
        "StrongPassword123!",  # Strong
        "nouppercasehere123!",  # No uppercase
        "NOLOWERCASEHERE123!",  # No lowercase
    ]
    
    for pwd in passwords:
        print(f"'{pwd}': {validate_strong_password(pwd)}")
    
    print("\nTesting activation code generation:")
    code = generate_secure_code(12)
    formatted = format_activation_code(code)
    print(f"Generated: {code} -> Formatted: {formatted}")
    
    print("\nTesting Pydantic validation:")
    try:
        user = UserRegistration(
            email="test@example.com",
            full_name="John Doe",
            password="StrongPassword123!",
            confirm_password="StrongPassword123!",
            terms_accepted=True
        )
        print(f"Valid user: {user.email}")
    except Exception as e:
        print(f"Validation error: {e}")