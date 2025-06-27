#!/usr/bin/env python3
"""
Test script for MindBot Authentication Integration
Tests the complete flow from registration to LiveKit token generation
"""

import asyncio
import aiohttp
import json
from livekit import api
import os
from dotenv import load_dotenv

load_dotenv()

AUTH_SERVICE_URL = "http://localhost:8000"
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

class AuthTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_info = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_registration(self, email: str, password: str, full_name: str):
        """Test user registration"""
        print(f"🔐 Testing user registration for {email}...")
        
        data = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        
        async with self.session.post(f"{AUTH_SERVICE_URL}/auth/register", json=data) as response:
            if response.status == 200:
                result = await response.json()
                self.auth_token = result["access_token"]
                print(f"✅ Registration successful!")
                print(f"   JWT Token: {self.auth_token[:50]}...")
                print(f"   LiveKit Token: {result['livekit_token'][:50]}...")
                print(f"   LiveKit URL: {result['livekit_url']}")
                return result
            else:
                error = await response.text()
                print(f"❌ Registration failed: {error}")
                return None

    async def test_login(self, email: str, password: str):
        """Test user login"""
        print(f"🔑 Testing user login for {email}...")
        
        data = {
            "email": email,
            "password": password
        }
        
        async with self.session.post(f"{AUTH_SERVICE_URL}/auth/login", json=data) as response:
            if response.status == 200:
                result = await response.json()
                self.auth_token = result["access_token"]
                print(f"✅ Login successful!")
                print(f"   JWT Token: {self.auth_token[:50]}...")
                return result
            else:
                error = await response.text()
                print(f"❌ Login failed: {error}")
                return None

    async def test_get_user_info(self):
        """Test getting current user info"""
        print("👤 Testing get user info...")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return None
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(f"{AUTH_SERVICE_URL}/auth/me", headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                self.user_info = result
                print(f"✅ User info retrieved!")
                print(f"   ID: {result['id']}")
                print(f"   Email: {result['email']}")
                print(f"   Name: {result['full_name']}")
                print(f"   Created: {result['created_at']}")
                return result
            else:
                error = await response.text()
                print(f"❌ Get user info failed: {error}")
                return None

    async def test_get_room_token(self, room_name: str, participant_name: str = None):
        """Test getting room-specific LiveKit token"""
        print(f"🏠 Testing room token generation for room: {room_name}...")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return None
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        data = {
            "room_name": room_name,
            "participant_name": participant_name
        }
        
        async with self.session.post(f"{AUTH_SERVICE_URL}/auth/token", headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Room token generated!")
                print(f"   Room: {result['room_name']}")
                print(f"   Session ID: {result['session_id']}")
                print(f"   LiveKit Token: {result['livekit_token'][:50]}...")
                return result
            else:
                error = await response.text()
                print(f"❌ Room token generation failed: {error}")
                return None

    async def test_token_validation(self, livekit_token: str):
        """Test LiveKit token validation"""
        print("🔍 Testing LiveKit token validation...")
        
        try:
            # Decode token to check contents
            token = api.AccessToken.from_jwt(livekit_token)
            grants = token.grants
            
            print(f"✅ Token is valid!")
            print(f"   Identity: {token.identity}")
            print(f"   Name: {token.name}")
            print(f"   Room: {grants.room}")
            print(f"   Can Publish: {grants.can_publish}")
            print(f"   Can Subscribe: {grants.can_subscribe}")
            print(f"   Valid until: {token.ttl}")
            
            return True
        except Exception as e:
            print(f"❌ Token validation failed: {e}")
            return False

    async def test_health_check(self):
        """Test service health"""
        print("🏥 Testing service health...")
        
        async with self.session.get(f"{AUTH_SERVICE_URL}/health") as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Service is healthy!")
                print(f"   Status: {result['status']}")
                print(f"   Service: {result['service']}")
                return result
            else:
                print(f"❌ Health check failed")
                return None

async def run_comprehensive_test():
    """Run comprehensive authentication testing"""
    print("🚀 Starting MindBot Authentication Integration Tests")
    print("=" * 60)
    
    test_email = "test.user@mindbot.ai"
    test_password = "secure_test_password_123"
    test_name = "Test User"
    test_room = "test_voice_session_room"
    
    async with AuthTester() as tester:
        # 1. Test health check
        await tester.test_health_check()
        print()
        
        # 2. Test registration
        registration_result = await tester.test_registration(test_email, test_password, test_name)
        print()
        
        if registration_result:
            # 3. Test initial LiveKit token validation
            await tester.test_token_validation(registration_result["livekit_token"])
            print()
            
            # 4. Test getting user info
            await tester.test_get_user_info()
            print()
            
            # 5. Test room token generation
            room_token_result = await tester.test_get_room_token(test_room, "Test Participant")
            print()
            
            if room_token_result:
                # 6. Test room token validation
                await tester.test_token_validation(room_token_result["livekit_token"])
                print()
        
        # 7. Test login with existing user
        print("🔄 Testing login with existing credentials...")
        login_result = await tester.test_login(test_email, test_password)
        print()
        
        if login_result:
            # 8. Test another room token generation after login
            await tester.test_get_room_token("another_test_room")
            print()
    
    print("=" * 60)
    print("🎉 Authentication integration tests completed!")
    print()
    print("Next steps:")
    print("1. Start the auth service: python backend/auth-service/auth_server.py")
    print("2. Start the enhanced agent: python backend/basic-mindbot/enhanced-mindbot.py start")
    print("3. Use a client to connect with the generated LiveKit tokens")

async def test_simple_flow():
    """Simple test flow for quick validation"""
    print("🔧 Running simple authentication flow test...")
    
    async with aiohttp.ClientSession() as session:
        # Health check
        async with session.get(f"{AUTH_SERVICE_URL}/health") as response:
            if response.status == 200:
                print("✅ Auth service is running")
            else:
                print("❌ Auth service is not responding")
                return
        
        # Quick registration test
        data = {
            "email": "quick.test@mindbot.ai",
            "password": "testpass123",
            "full_name": "Quick Test"
        }
        
        async with session.post(f"{AUTH_SERVICE_URL}/auth/register", json=data) as response:
            if response.status == 200:
                result = await response.json()
                print("✅ Registration works")
                print(f"   Got JWT token: {result['access_token'][:30]}...")
                print(f"   Got LiveKit token: {result['livekit_token'][:30]}...")
            else:
                print(f"❌ Registration failed: {response.status}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        asyncio.run(test_simple_flow())
    else:
        asyncio.run(run_comprehensive_test())