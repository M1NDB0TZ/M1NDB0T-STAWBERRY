# MindBot Frontend API Integration Guide

This guide provides front-end developers with all the necessary information to interact with the MindBot API, including details on authentication, available endpoints, and how to switch between personas.

## 1. Authentication

All API requests must be authenticated using a JSON Web Token (JWT). The token should be included in the `Authorization` header of each request.

**Header Format:**

```
Authorization: Bearer <your_jwt_token>
```

### 1.1. Obtaining a JWT Token

To obtain a JWT token, the user must first authenticate with the authentication service. The authentication process is handled by the `AuthService`, which is responsible for user registration and login.

**Endpoint:** `POST /auth/login`

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "user_password"
}
```

**Response:**

```json
{
  "access_token": "your_jwt_token",
  "token_type": "bearer"
}
```

## 2. API Endpoints

The following sections describe the available API endpoints.

### 2.1. Subscriptions

#### Get Subscription Plans

- **Endpoint:** `GET /plans`
- **Description:** Retrieves a list of available subscription plans.
- **Response:**
  ```json
  {
    "plans": [
      {
        "id": "premium_monthly",
        "name": "Premium Monthly",
        "price": 19.99,
        "price_display": "$19.99/month",
        "currency": "usd",
        "interval": "month",
        "features": [
          "Access to all personas",
          "Ad-free experience",
          "Premium voice quality",
          "Create up to 3 custom personas",
          "Priority support"
        ]
      }
    ]
  }
  ```

#### Create a Subscription

- **Endpoint:** `POST /subscriptions`
- **Description:** Creates a new subscription for the authenticated user.
- **Request Body:**
  ```json
  {
    "plan_id": "premium_monthly",
    "payment_method_id": "pm_1234567890",
    "coupon_code": "WELCOME25"
  }
  ```
- **Response:**
  ```json
  {
    "subscription_id": "sub_1234567890",
    "client_secret": "pi_1234567890_secret_1234567890",
    "plan": "Premium Monthly",
    "amount": 19.99,
    "currency": "usd",
    "interval": "month"
  }
  ```

### 2.2. Time Cards

#### Get Time Card Packages

- **Endpoint:** `GET /packages`
- **Description:** Retrieves a list of available time card packages.
- **Response:**
  ```json
  {
    "packages": [
      {
        "id": "starter_1h",
        "name": "Starter Pack",
        "hours": 1,
        "price_cents": 999,
        "price_display": "$9.99",
        "bonus_minutes": 0,
        "total_minutes": 60,
        "total_hours": 1,
        "description": "Perfect for trying out MindBot - 1 hour of AI conversation time"
      }
    ]
  }
  ```

#### Purchase a Time Card

- **Endpoint:** `POST /time-cards/purchase`
- **Description:** Purchases a time card package for the authenticated user.
- **Request Body:**
  ```json
  {
    "package_id": "starter_1h",
    "payment_method_id": "pm_1234567890",
    "save_payment_method": true,
    "coupon_code": "WELCOME25"
  }
  ```
- **Response:**
  ```json
  {
    "payment_intent_id": "pi_1234567890",
    "client_secret": "pi_1234567890_secret_1234567890",
    "amount": 749,
    "amount_display": "$7.49",
    "original_price": 999,
    "original_price_display": "$9.99",
    "discount_percent": 25,
    "discount_amount": 250,
    "discount_display": "$2.50",
    "package": {
      "name": "Starter Pack",
      "hours": 1,
      "bonus_minutes": 0,
      "total_minutes": 60,
      "total_hours": 1
    },
    "time_card": {
      "id": "tc_1234567890",
      "activation_code": "TEST-CARD-12345678",
      "total_minutes": 60,
      "expires_at": "2026-06-27T12:00:00Z"
    }
  }
  ```

### 2.3. Personas

#### Get Available Personas

- **Endpoint:** `GET /personas`
- **Description:** Retrieves a list of available personas.
- **Response:**
  ```json
  [
    {
      "slug": "mindbot",
      "name": "MindBot",
      "summary": "General assistant",
      "voice": {
        "tts": "alloy",
        "style": "neutral"
      }
    },
    {
      "slug": "blaze",
      "name": "Blaze",
      "summary": "Cannabis guru",
      "voice": {
        "tts": "onyx",
        "style": "neutral"
      }
    }
  ]
  ```

#### Switch Persona

To switch to a different persona, you need to start a new LiveKit session with the desired persona's slug. The persona slug should be passed as a parameter when requesting a LiveKit token from the authentication service.

**Endpoint:** `POST /auth/livekit-token`

**Request Body:**

```json
{
  "persona_slug": "blaze"
}
```

**Response:**

```json
{
  "token": "livekit_token"
}
```

This token can then be used to connect to the LiveKit room and interact with the selected persona.
