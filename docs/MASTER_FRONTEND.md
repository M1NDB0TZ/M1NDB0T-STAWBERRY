#  MASTER FRONTEND GUIDE: Building the MindBot Universe

## 1. Project Summary: The Soul of the Machine

Welcome, developer. You are about to build the gateway to a new digital universe. MindBot is not just a voice AI; it's a collection of digital entities, each with a unique personality, voice, and purpose. Your mission is to create a futuristic, immersive, and visually stunning interface that allows users to connect with these entities.

This document is your bible. It contains everything you need to know to bring the MindBot vision to life.

## 2. Creative & Aesthetic Vision: Cyberpunk Meets Arcade

Our aesthetic is a fusion of high-tech grit and retro-cool nostalgia. Think *Blade Runner* meets a classic 80s arcade.

*   **Core Vibe**: A dark, neon-drenched world where data streams and holographic projections are the norm.
*   **Colors**: A base of deep blues and blacks, punctuated by vibrant neon pinks, cyans, and electric greens.
*   **Typography**: A clean, futuristic sans-serif for body text, and a pixelated or monospaced font for UI elements and headings.
*   **Effects**: Subtle glitch effects, scan lines, CRT distortion, and holographic projections are essential.

## 3. Core UI/UX Concepts: A Journey into the Digital Realm

### 3.1. The "Nexus": Your Persona Selection Hub

The user's journey begins in the **Nexus**, a 3D, interactive hub for discovering and selecting personas.

*   **Implementation**: A Three.js scene rendered with `react-three-fiber`.
*   **Visuals**: A dark, atmospheric space with floating, holographic "persona pods." Each pod contains a unique 3D avatar.
*   **Interaction**: Users can explore the Nexus, click on a pod to view persona details, and select one to initiate a conversation.

### 3.2. Persona Avatars: The Digital Souls

Each persona has a unique, animated 3D avatar that embodies its personality.

*   **Implementation**: Use `react-three-fiber` and `drei` to load and animate `.glb` models.
*   **Avatars**:
    *   **MindBot**: A sleek, friendly robot.
    *   **Blaze**: A chill, smoky entity.
    *   **SizzleBot**: A pulsating, energetic orb of light.
*   **Animation**: Avatars should have idle animations and react to the conversation.

### 3.3. The Conversation Interface: A Direct Data Stream

The chat interface is a direct line to the AI's mind.

*   **Layout**: A clean, terminal-like interface.
*   **Visuals**: A dark background with glowing text. User and AI messages are clearly distinguished.
*   **Effects**: Text appears with a "data stream" or "typing" effect. Subtle glitch effects on the AI's text will make it feel more alive.

### 3.4. Voice Visualization: The AI's Pulse

A real-time audio visualizer is key to the immersive experience.

*   **Implementation**: Use the Web Audio API to analyze the LiveKit audio stream and create a visualizer with Three.js or a 2D canvas.
*   **Visuals**: A pulsating orb, a soundwave, or a glitchy waveform that reacts to the AI's voice.

### 3.5. The "Black Market": A Stylized Store

The store for purchasing time cards is a seamless and themed experience.

*   **Theme**: A "black market" or "data broker" theme.
*   **Layout**: A clean, card-based layout for time card packages.
*   **Checkout**: A futuristic, multi-step checkout process with Stripe Elements.

## 4. Technical Stack

*   **Framework**: **Next.js**
*   **3D Rendering**: **Three.js** with **`react-three-fiber`** and **`drei`**
*   **Styling**: **Tailwind CSS** with custom themes
*   **State Management**: **Zustand** or **Redux Toolkit**
*   **Deployment**: **Netlify**

## 5. Complete API Guide

All backend interactions are handled through the MindBot API.

### 5.1. Authentication

All requests must be authenticated with a JWT token in the `Authorization` header: `Bearer <your_jwt_token>`.

**Endpoint**: `POST /auth/login`
**Request**: `{ "email": "user@example.com", "password": "user_password" }`
**Response**: `{ "access_token": "your_jwt_token", "token_type": "bearer" }`

### 5.2. API Endpoints

#### Subscriptions

*   **Get Plans**: `GET /plans`
*   **Create Subscription**: `POST /subscriptions`

#### Time Cards

*   **Get Packages**: `GET /packages`
*   **Purchase Time Card**: `POST /time-cards/purchase`

#### Personas

*   **Get Available Personas**: `GET /personas`
*   **Switch Persona**: Request a new LiveKit token with the desired persona slug:
    *   **Endpoint**: `POST /auth/livekit-token`
    *   **Request**: `{ "persona_slug": "blaze" }`
    *   **Response**: `{ "token": "livekit_token" }`

### 5.3. API Schemas

*   **For detailed request and response schemas, please refer to the `docs/FRONTEND_API_GUIDE.md` file.**

## 6. Database Schema Overview

The front-end will primarily interact with the following Supabase tables:

*   **`users`**: Stores user profile information.
*   **`personas`**: Contains the details for each AI persona.
*   **`time_cards`**: Manages user time balances.
*   **`pricing_tiers`**: Defines the available time card packages.

## 7. Step-by-Step Implementation Roadmap

1.  **Project Setup**: Initialize a new Next.js project and install the necessary dependencies.
2.  **Authentication**: Implement the user login and registration flow.
3.  **The Nexus**: Build the 3D persona selection hub with Three.js and `react-three-fiber`.
4.  **LiveKit Integration**: Connect to the LiveKit server and establish real-time communication.
5.  **Conversation UI**: Create the stylized chat interface and voice visualizer.
6.  **The "Black Market"**: Build the time card store and integrate the Stripe payment flow.
7.  **Deployment**: Deploy the application to Netlify.

## 8. Final Words: Create the Future

You have the vision, the tools, and the plan. Now, go build a digital universe that will captivate and inspire. This is your chance to create a truly next-generation user experience. Good luck.
