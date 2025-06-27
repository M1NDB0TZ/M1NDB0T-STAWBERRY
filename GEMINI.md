# MindBot Project Overview for Gemini

This `GEMINI.md` file provides a concise overview of the MindBot project, designed to help the Gemini agent quickly understand its purpose, architecture, and how to interact with it.

## 1. Project Goal

MindBot is a sophisticated, production-ready Voice AI platform that offers a monetized conversational AI assistant. Its core functionality revolves around:
- **Voice AI Agent**: An AI assistant capable of natural language conversations.
- **Time-Based Billing**: Users purchase "time cards" to interact with the AI, with usage tracked and deducted from their balance.
- **Payment System**: Integrated with Stripe for secure payment processing and automatic time card activation via webhooks.
- **Database Backend**: Utilizes Supabase (PostgreSQL) for managing users, time cards, payment history, and voice session data.

## 2. Architecture Overview

The system follows a modular, service-oriented architecture, primarily focused on the `production-agent` which encapsulates the core logic.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   Supabase       │◄──►│   Stripe        │
│   (Web/Mobile)  │    │   Database       │    │   Payments      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LiveKit       │◄──►│   Production     │◄──►│   Webhook       │
│   Server        │    │   Voice Agent    │    │   Server        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Key Components:**
- **LiveKit Server**: Manages real-time WebRTC connections for voice communication.
- **Voice AI Agent**: Handles AI conversation, context management, and time tracking.
- **Payment Webhook Server**: Processes Stripe webhooks for payment events and time card activation.
- **Supabase**: Primary data store for all persistent data.
- **Stripe**: External payment gateway.

## 3. Technology Stack

- **Backend Language**: Python 3.11+
- **Frameworks**:
    -   **LiveKit Agents**: For building the Voice AI Agent.
    -   **FastAPI**: For the Payment Webhook Server.
-   **AI/ML**: OpenAI GPT-4.1-mini (LLM), Deepgram Nova-3 (STT).
-   **Database**: Supabase (PostgreSQL).
-   **Payments**: Stripe.
-   **Real-time Communication**: LiveKit (WebRTC).
-   **Configuration**: Pydantic BaseSettings.
-   **Logging**: Structured logging with `structlog`.
-   **Deployment**: Docker, Docker Compose.

## 4. Key Directories and Files (Post-Refactoring)

The project has been refactored to consolidate core logic into the `backend/production-agent` directory.

-   `backend/production-agent/`: The main application directory.
    -   `main.py`: The central entry point for launching both the LiveKit Agent and the FastAPI Webhook Server.
    -   `agent/`: Contains the LiveKit Voice AI Agent logic.
        -   `mindbot_agent.py`: The `ProductionMindBotAgent` class.
        -   `main.py`: Entrypoint for the LiveKit agent worker.
    -   `api/`: Contains the FastAPI application for the webhook server and API endpoints.
        -   `webhook.py`: The FastAPI app and its routes.
    -   `services/`: Contains client modules for external services.
        -   `supabase_client.py`: Interactions with Supabase.
        -   `stripe_manager.py`: Interactions with Stripe.
    -   `core/`: Core utilities and configuration.
        -   `settings.py`: Centralized Pydantic-based configuration.
        -   `logging_config.py`: Structured logging setup.
    -   `Dockerfile`: Dockerfile for building the production agent image.
    -   `requirements.txt`: Python dependencies.
    -   `.env.example`: Template for environment variables.
    -   `launch_script.sh`: A convenience script for local development.
-   `supabase/migrations/`: SQL migration scripts for the Supabase database schema.
-   `docker-compose.yml`: Docker Compose configuration for local development.

## 5. How to Run/Develop

The recommended way to run the project locally is using Docker Compose:

1.  **Prerequisites**: Ensure Docker Desktop is installed and running. You will also need API keys for Supabase, Stripe, LiveKit, OpenAI, and Deepgram.
2.  **Environment Setup**:
    -   Navigate to `backend/production-agent/`.
    -   Copy `env.example` to `.env` and populate it with your API keys and configuration.
    -   Set up your Supabase database using the SQL scripts in `supabase/migrations/`.
    -   For local Stripe webhooks, use the Stripe CLI: `stripe listen --forward-to localhost:8003/webhooks/stripe`. Copy the `whsec_` secret to your `.env`.
3.  **Run with Docker Compose**: From the project root directory (`Z:/GIT/2045/M1NDB0TZ/M1NDB0T-STAWBERRY/`), run:
    ```bash
    docker-compose up --build
    ```
    This will build the Docker image and start the MindBot application and a local PostgreSQL database.

Alternatively, you can run directly from the `backend/production-agent/` directory using the `launch_script.sh` (requires Python 3.11+ and `pip install -r requirements.txt`):
```bash
./launch_script.sh
```

## 6. Improvements Made (by Gemini)

This project has undergone significant refactoring to enhance its structure, maintainability, and developer experience:
-   **Code Consolidation**: All core backend services are now unified under `backend/production-agent/`.
-   **Modularization**: The main application logic has been broken down into smaller, more manageable modules (`agent/`, `api/`, `services/`, `core/`).
-   **Centralized Configuration**: Adopted Pydantic `BaseSettings` for robust environment variable management.
-   **Structured Logging**: Integrated `structlog` for improved log analysis.
-   **Enhanced DX**: Provided `docker-compose.yml` for easier local setup and updated `launch_script.sh`.

## 7. Future Roadmap

The project has a detailed `IMPROVEMENTS_ROADMAP.md` and `agent-notes/06-feature-roadmap.md` outlining future enhancements, including:
-   Advanced analytics and monitoring.
-   Frontend integration SDK.
-   Multiple voice personalities.
-   Agent memory system.
-   Subscription models.
-   Enterprise features (SSO, white-labeling).

This `GEMINI.md` should serve as a quick reference for future interactions with the MindBot project.
