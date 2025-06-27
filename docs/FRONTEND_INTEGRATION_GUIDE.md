# 🖥️ MindBot Frontend Integration Guide

This guide provides comprehensive instructions for integrating a frontend application with the MindBot API platform.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication Integration](#authentication-integration)
3. [Time Card System](#time-card-system)
4. [Voice Session Implementation](#voice-session-implementation)
5. [Persona System](#persona-system)
6. [Subscription Management](#subscription-management)
7. [Ad Integration](#ad-integration)
8. [Analytics Display](#analytics-display)
9. [Responsive Design Considerations](#responsive-design-considerations)
10. [Mobile App Integration](#mobile-app-integration)

## Getting Started

### Required Libraries

```json
// package.json dependencies
{
  "dependencies": {
    "@stripe/react-stripe-js": "^2.3.0",
    "@stripe/stripe-js": "^2.1.5",
    "livekit-client": "^1.13.2",
    "jwt-decode": "^3.1.2",
    "axios": "^1.5.0",
    "react": "^18.2.0",
    "react-router-dom": "^6.15.0"
  }
}
```

### API Base URLs

```javascript
// config.js
const config = {
  API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  AUTH_API: '/auth',
  TIME_API: '/time',
  PERSONA_API: '/personas',
  SUBSCRIPTION_API: '/subscriptions',
  ADS_API: '/ads',
  ANALYTICS_API: '/analytics',
  STRIPE_PUBLIC_KEY: process.env.REACT_APP_STRIPE_PUBLIC_KEY
};

export default config;
```

### API Client Setup

```javascript
// api/client.js
import axios from 'axios';
import config from '../config';

const apiClient = axios.create({
  baseURL: config.API_BASE_URL
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors by redirecting to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

## Authentication Integration

### User Authentication Flow

```javascript
// auth/authService.js
import apiClient from '../api/client';
import jwtDecode from 'jwt-decode';

export const register = async (email, password, fullName) => {
  const response = await apiClient.post('/auth/register', {
    email,
    password,
    full_name: fullName
  });
  
  const { access_token, livekit_token, livekit_url } = response.data;
  
  // Store tokens
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('livekit_token', livekit_token);
  localStorage.setItem('livekit_url', livekit_url);
  
  // Decode and store user info
  const decoded = jwtDecode(access_token);
  localStorage.setItem('user_info', JSON.stringify({
    id: decoded.user_id,
    email: decoded.email,
    fullName: decoded.full_name
  }));
  
  return response.data;
};

export const login = async (email, password) => {
  const response = await apiClient.post('/auth/login', {
    email,
    password
  });
  
  const { access_token, livekit_token, livekit_url } = response.data;
  
  // Store tokens
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('livekit_token', livekit_token);
  localStorage.setItem('livekit_url', livekit_url);
  
  // Decode and store user info
  const decoded = jwtDecode(access_token);
  localStorage.setItem('user_info', JSON.stringify({
    id: decoded.user_id,
    email: decoded.email,
    fullName: decoded.full_name
  }));
  
  return response.data;
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('livekit_token');
  localStorage.removeItem('livekit_url');
  localStorage.removeItem('user_info');
  
  window.location.href = '/login';
};

export const getCurrentUser = () => {
  const userInfoString = localStorage.getItem('user_info');
  if (!userInfoString) return null;
  
  return JSON.parse(userInfoString);
};

export const isAuthenticated = () => {
  const token = localStorage.getItem('access_token');
  if (!token) return false;
  
  try {
    const decoded = jwtDecode(token);
    const currentTime = Date.now() / 1000;
    
    return decoded.exp > currentTime;
  } catch (error) {
    return false;
  }
};
```

### Auth Context Provider

```jsx
// auth/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { isAuthenticated, getCurrentUser } from './authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Check authentication on mount
    const checkAuth = () => {
      if (isAuthenticated()) {
        setUser(getCurrentUser());
      }
      setLoading(false);
    };
    
    checkAuth();
  }, []);
  
  const value = {
    user,
    isAuthenticated: !!user,
    loading
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### Protected Route Component

```jsx
// auth/ProtectedRoute.jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  return children;
};
```

## Time Card System

### Time Card Service

```javascript
// services/timeCardService.js
import apiClient from '../api/client';
import { loadStripe } from '@stripe/stripe-js';
import config from '../config';

const stripePromise = loadStripe(config.STRIPE_PUBLIC_KEY);

export const getPricingTiers = async () => {
  const response = await apiClient.get('/time/pricing');
  return response.data.pricing_tiers;
};

export const purchaseTimeCard = async (packageId, paymentMethodId, couponCode = null) => {
  // Create payment intent
  const response = await apiClient.post('/time/purchase', {
    package_id: packageId,
    payment_method_id: paymentMethodId,
    save_payment_method: true,
    coupon_code: couponCode
  });
  
  const { client_secret, payment_intent_id } = response.data;
  
  // Initialize Stripe
  const stripe = await stripePromise;
  
  // Confirm payment
  const result = await stripe.confirmCardPayment(client_secret);
  
  if (result.error) {
    throw new Error(result.error.message);
  }
  
  if (result.paymentIntent.status === 'succeeded') {
    return {
      success: true,
      payment_intent_id: payment_intent_id,
      time_card: response.data.time_card,
      package: response.data.package
    };
  } else {
    throw new Error('Payment failed with status: ' + result.paymentIntent.status);
  }
};

export const activateTimeCard = async (activationCode) => {
  const response = await apiClient.post('/time/activate', {
    activation_code: activationCode
  });
  
  return response.data;
};

export const getTimeBalance = async () => {
  const response = await apiClient.get('/time/balance');
  return response.data;
};

export const getSessionHistory = async (limit = 50) => {
  const response = await apiClient.get(`/time/sessions?limit=${limit}`);
  return response.data.sessions;
};
```

### Time Balance Component

```jsx
// components/TimeBalance.jsx
import React, { useState, useEffect } from 'react';
import { getTimeBalance } from '../services/timeCardService';
import { Link } from 'react-router-dom';

export const TimeBalance = () => {
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchBalance = async () => {
      try {
        const data = await getTimeBalance();
        setBalance(data.balance);
      } catch (err) {
        setError('Failed to load balance');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchBalance();
  }, []);
  
  if (loading) return <div className="loading">Loading balance...</div>;
  if (error) return <div className="error">{error}</div>;
  
  const isLowBalance = balance.total_minutes < 30;
  
  return (
    <div className={`time-balance ${isLowBalance ? 'low-balance' : ''}`}>
      <h3>Time Balance</h3>
      <div className="balance-amount">
        <span className="hours">{balance.total_hours}</span> hours
        <span className="minutes">({balance.total_minutes} minutes)</span>
      </div>
      
      <div className="active-cards">
        {balance.active_cards} active card{balance.active_cards !== 1 ? 's' : ''}
      </div>
      
      {balance.next_expiration && (
        <div className="expiration">
          Next expiration: {new Date(balance.next_expiration).toLocaleDateString()}
        </div>
      )}
      
      {isLowBalance && (
        <div className="low-balance-warning">
          Your balance is running low! 
          <Link to="/time-cards/purchase" className="purchase-link">
            Purchase More Time
          </Link>
        </div>
      )}
    </div>
  );
};
```

### Time Card Purchase Component

```jsx
// components/TimeCardPurchase.jsx
import React, { useState, useEffect } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { getPricingTiers, purchaseTimeCard } from '../services/timeCardService';

export const TimeCardPurchase = () => {
  const [packages, setPackages] = useState([]);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [couponCode, setCouponCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const stripe = useStripe();
  const elements = useElements();
  
  useEffect(() => {
    const fetchPackages = async () => {
      try {
        const tiers = await getPricingTiers();
        setPackages(tiers);
        setLoading(false);
      } catch (err) {
        setError('Failed to load packages');
        setLoading(false);
      }
    };
    
    fetchPackages();
  }, []);
  
  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements || !selectedPackage) {
      return;
    }
    
    setProcessing(true);
    setError(null);
    
    try {
      const cardElement = elements.getElement(CardElement);
      
      // Create payment method
      const { paymentMethod, error } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });
      
      if (error) {
        throw new Error(error.message);
      }
      
      // Purchase time card
      const result = await purchaseTimeCard(
        selectedPackage.id,
        paymentMethod.id,
        couponCode || null
      );
      
      if (result.success) {
        setSuccess({
          package: result.package,
          timeCard: result.time_card
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  };
  
  if (loading) return <div className="loading">Loading packages...</div>;
  
  if (success) {
    return (
      <div className="success-message">
        <h2>Purchase Successful!</h2>
        <p>You've purchased the {success.package.name} package:</p>
        <ul>
          <li>{success.package.hours} hours of conversation time</li>
          {success.package.bonus_minutes > 0 && (
            <li>Plus {success.package.bonus_minutes} bonus minutes</li>
          )}
          <li>Total: {success.package.total_minutes} minutes ({success.package.total_hours} hours)</li>
        </ul>
        <p>Your time card is ready to use!</p>
        <button onClick={() => window.location.href = '/personas'}>
          Start Conversation
        </button>
      </div>
    );
  }
  
  return (
    <div className="time-card-purchase">
      <h2>Purchase Time Cards</h2>
      
      <div className="package-selection">
        {packages.map(pkg => (
          <div 
            key={pkg.id}
            className={`package ${selectedPackage?.id === pkg.id ? 'selected' : ''}`}
            onClick={() => setSelectedPackage(pkg)}
          >
            <h3>{pkg.name}</h3>
            <div className="price">{pkg.price_display}</div>
            <div className="hours">{pkg.hours} hours</div>
            {pkg.bonus_minutes > 0 && (
              <div className="bonus">+ {pkg.bonus_minutes} bonus minutes</div>
            )}
            <div className="description">{pkg.description}</div>
          </div>
        ))}
      </div>
      
      {selectedPackage && (
        <form onSubmit={handleSubmit} className="payment-form">
          <h3>Payment Details</h3>
          
          <div className="card-element-container">
            <CardElement />
          </div>
          
          <div className="coupon-container">
            <input
              type="text"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value)}
              placeholder="Coupon Code (Optional)"
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button 
            type="submit" 
            disabled={!stripe || processing || !selectedPackage}
            className="purchase-button"
          >
            {processing ? 'Processing...' : `Purchase ${selectedPackage.name} - ${selectedPackage.price_display}`}
          </button>
        </form>
      )}
    </div>
  );
};
```

## Voice Session Implementation

### LiveKit Integration Service

```javascript
// services/livekitService.js
import { Room, RoomEvent } from 'livekit-client';

export class VoiceSessionManager {
  constructor() {
    this.room = null;
    this.audioElements = {};
    this.onStateChange = null;
    this.onTranscript = null;
    this.onSessionEnd = null;
  }
  
  async connect(url, token, roomName) {
    try {
      // Create room instance
      this.room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioEnabled: true,
        videoEnabled: false
      });
      
      // Set up event listeners
      this.room.on(RoomEvent.ParticipantConnected, this._handleParticipantConnected.bind(this));
      this.room.on(RoomEvent.ParticipantDisconnected, this._handleParticipantDisconnected.bind(this));
      this.room.on(RoomEvent.Disconnected, this._handleDisconnect.bind(this));
      this.room.on(RoomEvent.TrackSubscribed, this._handleTrackSubscribed.bind(this));
      this.room.on(RoomEvent.TrackUnsubscribed, this._handleTrackUnsubscribed.bind(this));
      this.room.on(RoomEvent.DataReceived, this._handleDataReceived.bind(this));
      
      // Connect to room
      await this.room.connect(url, token);
      console.log(`Connected to room: ${roomName}`);
      
      // Enable microphone
      await this.room.localParticipant.enableMicrophone();
      
      // Notify state change
      if (this.onStateChange) {
        this.onStateChange('connected');
      }
      
      return true;
    } catch (error) {
      console.error('LiveKit connection error:', error);
      
      if (this.onStateChange) {
        this.onStateChange('error', error.message);
      }
      
      throw error;
    }
  }
  
  async disconnect() {
    try {
      if (this.room) {
        await this.room.disconnect();
        
        // Cleanup audio elements
        Object.values(this.audioElements).forEach(audio => {
          audio.srcObject = null;
          audio.remove();
        });
        
        this.audioElements = {};
        this.room = null;
        
        // Notify state change
        if (this.onStateChange) {
          this.onStateChange('disconnected');
        }
        
        // Trigger session end
        if (this.onSessionEnd) {
          this.onSessionEnd();
        }
      }
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
  }
  
  // Private event handlers
  
  _handleParticipantConnected(participant) {
    console.log('Participant connected:', participant.identity);
    
    if (this.onStateChange) {
      this.onStateChange('participant_connected', participant.identity);
    }
  }
  
  _handleParticipantDisconnected(participant) {
    console.log('Participant disconnected:', participant.identity);
    
    if (this.onStateChange) {
      this.onStateChange('participant_disconnected', participant.identity);
    }
  }
  
  _handleDisconnect() {
    console.log('Disconnected from room');
    
    // Cleanup
    Object.values(this.audioElements).forEach(audio => {
      audio.srcObject = null;
    });
    
    if (this.onStateChange) {
      this.onStateChange('disconnected');
    }
    
    if (this.onSessionEnd) {
      this.onSessionEnd();
    }
  }
  
  _handleTrackSubscribed(track, publication, participant) {
    if (track.kind === 'audio') {
      // Create audio element
      const audioElement = new Audio();
      audioElement.srcObject = new MediaStream([track.mediaStreamTrack]);
      audioElement.play().catch(error => console.error('Error playing audio:', error));
      
      // Store reference
      this.audioElements[participant.identity] = audioElement;
    }
  }
  
  _handleTrackUnsubscribed(track, publication, participant) {
    if (track.kind === 'audio' && this.audioElements[participant.identity]) {
      this.audioElements[participant.identity].srcObject = null;
      delete this.audioElements[participant.identity];
    }
  }
  
  _handleDataReceived(data, participant) {
    try {
      const message = JSON.parse(new TextDecoder().decode(data));
      
      // Handle transcript messages
      if (message.type === 'transcript' && this.onTranscript) {
        this.onTranscript(message.text, participant.identity);
      }
    } catch (error) {
      console.error('Error processing data message:', error);
    }
  }
}
```

### Voice Session Component

```jsx
// components/VoiceSession.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VoiceSessionManager } from '../services/livekitService';
import { startPersonaSession } from '../services/personaService';

export const VoiceSession = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  
  const [sessionState, setSessionState] = useState('initializing'); // initializing, connecting, connected, error, ended
  const [sessionInfo, setSessionInfo] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [enableAds, setEnableAds] = useState(true);
  const [sessionDuration, setSessionDuration] = useState(0);
  const [estimatedCost, setEstimatedCost] = useState(0);
  
  const sessionManagerRef = useRef(new VoiceSessionManager());
  const durationTimerRef = useRef(null);
  
  useEffect(() => {
    const startSession = async () => {
      try {
        setSessionState('connecting');
        
        // Start persona session
        const sessionData = await startPersonaSession(slug, enableAds);
        setSessionInfo(sessionData);
        
        // Set up event handlers
        const sessionManager = sessionManagerRef.current;
        
        sessionManager.onStateChange = (state, data) => {
          setSessionState(state);
          console.log('Session state change:', state, data);
        };
        
        sessionManager.onTranscript = (text, identity) => {
          setTranscript(text);
          setIsSpeaking(true);
          
          // Reset speaking after delay
          setTimeout(() => setIsSpeaking(false), 500);
        };
        
        sessionManager.onSessionEnd = () => {
          // Stop duration timer
          if (durationTimerRef.current) {
            clearInterval(durationTimerRef.current);
          }
          
          setSessionState('ended');
          navigate('/sessions/summary', { 
            state: { 
              duration: sessionDuration,
              cost: estimatedCost,
              persona: sessionInfo.persona
            }
          });
        };
        
        // Connect to LiveKit
        await sessionManager.connect(
          sessionData.livekit_url, 
          sessionData.livekit_token,
          sessionData.room_name
        );
        
        setSessionState('connected');
        
        // Start duration timer
        durationTimerRef.current = setInterval(() => {
          setSessionDuration(prev => {
            const newDuration = prev + 1;
            
            // Calculate estimated cost (in minutes)
            const costPerMinute = sessionData.estimated_cost_per_minute || 1;
            const newCost = Math.ceil(newDuration / 60) * costPerMinute;
            setEstimatedCost(newCost);
            
            return newDuration;
          });
        }, 1000);
        
      } catch (error) {
        console.error('Session initialization error:', error);
        setSessionState('error');
      }
    };
    
    startSession();
    
    // Cleanup function
    return () => {
      const sessionManager = sessionManagerRef.current;
      if (sessionManager) {
        sessionManager.disconnect();
      }
      
      if (durationTimerRef.current) {
        clearInterval(durationTimerRef.current);
      }
    };
  }, [slug, enableAds, navigate]);
  
  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
  };
  
  const handleEndSession = () => {
    if (window.confirm('Are you sure you want to end this session?')) {
      sessionManagerRef.current.disconnect();
    }
  };
  
  if (sessionState === 'initializing' || sessionState === 'connecting') {
    return (
      <div className="voice-session-loading">
        <h2>Connecting to {slug}...</h2>
        <div className="loader"></div>
      </div>
    );
  }
  
  if (sessionState === 'error') {
    return (
      <div className="voice-session-error">
        <h2>Connection Error</h2>
        <p>Unable to start voice session. Please try again later.</p>
        <button onClick={() => navigate('/personas')}>
          Back to Personas
        </button>
      </div>
    );
  }
  
  return (
    <div className="voice-session">
      <div className="session-header">
        <div className="persona-info">
          <h2>{sessionInfo?.persona.name || 'AI Assistant'}</h2>
          <p className="persona-summary">
            {sessionInfo?.persona.summary || ''}
          </p>
        </div>
        
        <div className="session-controls">
          <div className="session-stats">
            <div className="duration">
              Duration: {formatDuration(sessionDuration)}
            </div>
            <div className="cost">
              Estimated cost: {estimatedCost} minutes
            </div>
          </div>
          
          <button 
            className="end-session-button"
            onClick={handleEndSession}
          >
            End Session
          </button>
        </div>
      </div>
      
      <div className="conversation-container">
        <div className={`conversation-status ${isSpeaking ? 'speaking' : 'listening'}`}>
          {isSpeaking ? 'Speaking...' : 'Listening...'}
        </div>
        
        <div className="transcript">
          {transcript || 'Start speaking to begin conversation...'}
        </div>
        
        <div className="audio-visualizer">
          {/* Audio wave visualization would go here */}
        </div>
      </div>
      
      {sessionInfo?.ads_enabled && (
        <div className="ad-banner">
          <button className="watch-ad-button">
            Watch ad for 50% off next 5 minutes
          </button>
        </div>
      )}
    </div>
  );
};
```

## Persona System

### Persona Service

```javascript
// services/personaService.js
import apiClient from '../api/client';

export const getAvailablePersonas = async (filters = {}) => {
  const {
    userTier = 'free',
    category = '',
    adSupported = null,
    sortBy = 'rating',
    limit = 20
  } = filters;
  
  let url = `/personas?user_tier=${userTier}&sort_by=${sortBy}&limit=${limit}`;
  
  if (category) {
    url += `&category=${category}`;
  }
  
  if (adSupported !== null) {
    url += `&ad_supported=${adSupported}`;
  }
  
  const response = await apiClient.get(url);
  return response.data.personas;
};

export const getPersonaDetails = async (slug) => {
  const response = await apiClient.get(`/personas/${slug}`);
  return response.data;
};

export const createCustomPersona = async (personaData) => {
  const response = await apiClient.post('/personas/custom', personaData);
  return response.data;
};

export const startPersonaSession = async (slug, enableAds = true, qualityPreference = 'standard') => {
  const response = await apiClient.post(`/personas/${slug}/session`, {
    room_name: null, // Let the API generate a room name
    enable_ads: enableAds,
    quality_preference: qualityPreference
  });
  
  return response.data;
};

export const ratePersona = async (slug, rating, feedback = null) => {
  const url = `/personas/${slug}/rate?rating=${rating}`;
  
  if (feedback) {
    url += `&feedback=${encodeURIComponent(feedback)}`;
  }
  
  const response = await apiClient.post(url);
  return response.data;
};

export const getPersonaCategories = async () => {
  const response = await apiClient.get('/categories');
  return response.data.categories;
};

export const getPersonaAnalytics = async () => {
  const response = await apiClient.get('/analytics/personas');
  return response.data;
};
```

### Persona Browser Component

```jsx
// components/PersonaBrowser.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAvailablePersonas, getPersonaCategories } from '../services/personaService';
import { PersonaCard } from './PersonaCard';
import { CategoryFilter } from './CategoryFilter';

export const PersonaBrowser = () => {
  const navigate = useNavigate();
  
  const [personas, setPersonas] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    category: '',
    adSupported: null,
    sortBy: 'rating'
  });
  
  // User tier would come from user context/state
  const userTier = 'premium'; // Mock value for example
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch categories
        const categoriesData = await getPersonaCategories();
        setCategories(categoriesData);
        
        // Fetch personas
        const personasData = await getAvailablePersonas({
          userTier,
          ...filters
        });
        setPersonas(personasData);
      } catch (err) {
        setError('Failed to load personas');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [filters, userTier]);
  
  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };
  
  const handlePersonaSelect = (slug) => {
    navigate(`/personas/${slug}`);
  };
  
  if (loading) return <div className="loading">Loading personas...</div>;
  if (error) return <div className="error">{error}</div>;
  
  return (
    <div className="persona-browser">
      <h1>Choose Your AI Companion</h1>
      
      <div className="filters">
        <CategoryFilter
          categories={categories}
          selected={filters.category}
          onChange={(value) => handleFilterChange('category', value)}
        />
        
        <div className="sort-filter">
          <label>Sort by: </label>
          <select
            value={filters.sortBy}
            onChange={(e) => handleFilterChange('sortBy', e.target.value)}
          >
            <option value="rating">Top Rated</option>
            <option value="cost">Lowest Cost</option>
            <option value="popularity">Most Popular</option>
          </select>
        </div>
        
        {userTier === 'free' && (
          <div className="ad-filter">
            <label>
              <input
                type="checkbox"
                checked={filters.adSupported === true}
                onChange={(e) => handleFilterChange('adSupported', e.target.checked ? true : null)}
              />
              Show Ad-Supported
            </label>
          </div>
        )}
      </div>
      
      <div className="personas-grid">
        {personas.map(persona => (
          <PersonaCard
            key={persona.slug}
            persona={persona}
            onSelect={() => handlePersonaSelect(persona.slug)}
          />
        ))}
      </div>
      
      {personas.length === 0 && (
        <div className="no-results">
          No personas found with the selected filters.
        </div>
      )}
      
      {userTier === 'premium' && (
        <div className="create-persona">
          <button
            className="create-persona-button"
            onClick={() => navigate('/personas/create')}
          >
            Create Custom Persona
          </button>
          <p>As a Premium member, you can create your own custom AI personas!</p>
        </div>
      )}
      
      {userTier === 'free' && (
        <div className="premium-upsell">
          <h3>Want to access all personas?</h3>
          <p>Upgrade to Premium to unlock all personas and remove ads!</p>
          <button
            className="upgrade-button"
            onClick={() => navigate('/subscription')}
          >
            Upgrade Now
          </button>
        </div>
      )}
    </div>
  );
};
```

### Persona Detail Component

```jsx
// components/PersonaDetail.jsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPersonaDetails } from '../services/personaService';
import { getTimeBalance } from '../services/timeCardService';
import { StarRating } from './StarRating';

export const PersonaDetail = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  
  const [persona, setPersona] = useState(null);
  const [timeBalance, setTimeBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch persona details
        const personaData = await getPersonaDetails(slug);
        setPersona(personaData);
        
        // Get user's time balance
        const balanceData = await getTimeBalance();
        setTimeBalance(balanceData.balance);
      } catch (err) {
        setError('Failed to load persona details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [slug]);
  
  const handleStartSession = () => {
    // Check if user has time balance
    if (timeBalance.total_minutes <= 0) {
      navigate('/time-cards/purchase', { 
        state: { redirectAfter: `/personas/${slug}` } 
      });
      return;
    }
    
    // Start voice session
    navigate(`/sessions/start/${slug}`);
  };
  
  if (loading) return <div className="loading">Loading persona details...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!persona) return <div className="not-found">Persona not found</div>;
  
  return (
    <div className="persona-detail">
      <div className="persona-header">
        <h1>{persona.name}</h1>
        <div className="persona-rating">
          <StarRating rating={persona.rating} />
          <span className="rating-value">{persona.rating.toFixed(1)}</span>
        </div>
      </div>
      
      <div className="persona-summary">
        <p>{persona.summary}</p>
      </div>
      
      <div className="persona-details">
        <div className="detail-row">
          <div className="detail-label">Category:</div>
          <div className="detail-value">{persona.category}</div>
        </div>
        
        <div className="detail-row">
          <div className="detail-label">Personality:</div>
          <div className="detail-value">{persona.persona}</div>
        </div>
        
        <div className="detail-row">
          <div className="detail-label">Purpose:</div>
          <div className="detail-value">{persona.purpose}</div>
        </div>
        
        {persona.age_restriction && (
          <div className="detail-row age-restriction">
            <div className="detail-label">Age Restriction:</div>
            <div className="detail-value">{persona.age_restriction}+</div>
          </div>
        )}
        
        <div className="detail-row">
          <div className="detail-label">Cost:</div>
          <div className="detail-value">
            {persona.cost_multiplier === 1.0 ? (
              'Standard rate'
            ) : persona.cost_multiplier < 1.0 ? (
              `${100 - persona.cost_multiplier * 100}% discount`
            ) : (
              `${persona.cost_multiplier.toFixed(1)}x rate`
            )}
          </div>
        </div>
        
        <div className="detail-row">
          <div className="detail-label">Ad-Supported:</div>
          <div className="detail-value">{persona.ad_supported ? 'Yes' : 'No'}</div>
        </div>
        
        <div className="detail-row">
          <div className="detail-label">Tools:</div>
          <div className="detail-value tools-list">
            {persona.tools.map(tool => (
              <span key={tool} className="tool-badge">{tool}</span>
            ))}
          </div>
        </div>
      </div>
      
      <div className="session-start-panel">
        <div className="time-balance-info">
          <h3>Your Time Balance</h3>
          <div className="balance">{timeBalance.total_hours} hours ({timeBalance.total_minutes} minutes)</div>
          
          <div className="cost-estimate">
            <h4>Estimated Cost</h4>
            <p>{Math.ceil(persona.cost_multiplier)} minute per minute of conversation</p>
            <p className="small">({persona.estimated_cost_per_hour}/hour)</p>
          </div>
        </div>
        
        <button 
          className="start-session-button"
          onClick={handleStartSession}
          disabled={timeBalance.total_minutes <= 0}
        >
          Start Conversation
        </button>
        
        {timeBalance.total_minutes <= 0 && (
          <div className="no-balance-warning">
            You need to purchase time cards before starting a conversation.
          </div>
        )}
        
        {persona.premium_features.length > 0 && (
          <div className="premium-features">
            <h4>Premium Features</h4>
            <ul>
              {persona.premium_features.map((feature, index) => (
                <li key={index}>{feature}</li>
              ))}
            </ul>
            <p className="premium-note">
              Requires Premium subscription to access
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
```

## Subscription Management

### Subscription Service

```javascript
// services/subscriptionService.js
import apiClient from '../api/client';
import { loadStripe } from '@stripe/stripe-js';
import config from '../config';

const stripePromise = loadStripe(config.STRIPE_PUBLIC_KEY);

export const getSubscriptionPlans = async () => {
  const response = await apiClient.get('/plans');
  return response.data.plans;
};

export const getCurrentSubscription = async () => {
  try {
    const response = await apiClient.get('/subscriptions/current');
    return response.data;
  } catch (error) {
    if (error.response && error.response.status === 404) {
      return null; // No subscription
    }
    throw error;
  }
};

export const createSubscription = async (planId, paymentMethodId, couponCode = null) => {
  // Create subscription
  const response = await apiClient.post('/subscriptions', {
    plan_id: planId,
    payment_method_id: paymentMethodId,
    coupon_code: couponCode
  });
  
  const { client_secret } = response.data;
  
  // Initialize Stripe
  const stripe = await stripePromise;
  
  // Confirm subscription payment
  const result = await stripe.confirmCardPayment(client_secret);
  
  if (result.error) {
    throw new Error(result.error.message);
  }
  
  return {
    success: true,
    subscription: response.data
  };
};

export const cancelSubscription = async () => {
  const response = await apiClient.post('/subscriptions/cancel');
  return response.data;
};

export const getUserSubscriptionInfo = async () => {
  const response = await apiClient.get('/user/subscription');
  return response.data;
};
```

### Subscription Management Component

```jsx
// components/SubscriptionManagement.jsx
import React, { useState, useEffect } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { 
  getSubscriptionPlans, 
  getCurrentSubscription,
  createSubscription,
  cancelSubscription
} from '../services/subscriptionService';

export const SubscriptionManagement = () => {
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [couponCode, setCouponCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const stripe = useStripe();
  const elements = useElements();
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch subscription plans
        const plansData = await getSubscriptionPlans();
        setPlans(plansData);
        
        // Fetch current subscription
        const subscription = await getCurrentSubscription();
        setCurrentSubscription(subscription);
      } catch (err) {
        setError('Failed to load subscription data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  const handleSubscribe = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements || !selectedPlan) {
      return;
    }
    
    setProcessing(true);
    setError(null);
    
    try {
      const cardElement = elements.getElement(CardElement);
      
      // Create payment method
      const { paymentMethod, error } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });
      
      if (error) {
        throw new Error(error.message);
      }
      
      // Create subscription
      const result = await createSubscription(
        selectedPlan.id,
        paymentMethod.id,
        couponCode || null
      );
      
      if (result.success) {
        setSuccess({
          plan: result.subscription.plan,
          nextBilling: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString() // Mock next billing date
        });
        setCurrentSubscription(result.subscription);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  };
  
  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your current billing period.')) {
      return;
    }
    
    setProcessing(true);
    
    try {
      await cancelSubscription();
      
      // Update subscription state
      setCurrentSubscription({
        ...currentSubscription,
        cancel_at_period_end: true
      });
      
      setSuccess({
        message: 'Your subscription has been cancelled and will end at the end of your current billing period.'
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  };
  
  if (loading) return <div className="loading">Loading subscription information...</div>;
  
  return (
    <div className="subscription-management">
      <h1>Subscription Management</h1>
      
      {success && (
        <div className="success-message">
          {success.message || `Successfully subscribed to ${success.plan}! Your next billing date is ${success.nextBilling}.`}
        </div>
      )}
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {currentSubscription ? (
        <div className="current-subscription">
          <h2>Your Subscription</h2>
          
          <div className="subscription-details">
            <div className="detail-row">
              <div className="detail-label">Plan:</div>
              <div className="detail-value">{currentSubscription.plan_name}</div>
            </div>
            
            <div className="detail-row">
              <div className="detail-label">Status:</div>
              <div className="detail-value">{currentSubscription.status}</div>
            </div>
            
            <div className="detail-row">
              <div className="detail-label">Billing Period Ends:</div>
              <div className="detail-value">
                {new Date(currentSubscription.current_period_end).toLocaleDateString()}
              </div>
            </div>
            
            {currentSubscription.cancel_at_period_end ? (
              <div className="cancellation-notice">
                Your subscription will end on {new Date(currentSubscription.current_period_end).toLocaleDateString()}.
                <button 
                  className="reactivate-button"
                  onClick={() => {/* Implement reactivation */}}
                >
                  Reactivate Subscription
                </button>
              </div>
            ) : (
              <button 
                className="cancel-button"
                onClick={handleCancelSubscription}
                disabled={processing}
              >
                {processing ? 'Processing...' : 'Cancel Subscription'}
              </button>
            )}
          </div>
          
          <div className="subscription-features">
            <h3>Your Plan Features</h3>
            <ul>
              {currentSubscription.features.map((feature, index) => (
                <li key={index} className="feature-item">
                  <span className="feature-tick">✓</span> {feature}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="subscription-upgrade">
            <h3>Looking for More?</h3>
            {currentSubscription.plan.includes('Premium') ? (
              <div className="upgrade-option">
                <p>Consider upgrading to our Exclusive plan for unlimited custom personas and the highest quality experience.</p>
                <button 
                  className="upgrade-button"
                  onClick={() => {/* Implement plan change */}}
                >
                  Upgrade to Exclusive
                </button>
              </div>
            ) : (
              <p>You're already on our top tier plan! Enjoy all the premium features.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="subscription-plans">
          <h2>Choose a Subscription Plan</h2>
          
          <div className="plans-container">
            {plans.map(plan => (
              <div 
                key={plan.id}
                className={`plan-card ${selectedPlan?.id === plan.id ? 'selected' : ''}`}
                onClick={() => setSelectedPlan(plan)}
              >
                <h3>{plan.name}</h3>
                <div className="price">{plan.price_display}</div>
                
                <ul className="feature-list">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      <span className="feature-tick">✓</span> {feature}
                    </li>
                  ))}
                </ul>
                
                <button
                  className="select-plan-button"
                  onClick={() => setSelectedPlan(plan)}
                >
                  {selectedPlan?.id === plan.id ? 'Selected' : 'Select Plan'}
                </button>
              </div>
            ))}
          </div>
          
          {selectedPlan && (
            <form onSubmit={handleSubscribe} className="subscription-form">
              <h3>Payment Details</h3>
              
              <div className="card-element-container">
                <CardElement />
              </div>
              
              <div className="coupon-container">
                <input
                  type="text"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value)}
                  placeholder="Coupon Code (Optional)"
                />
              </div>
              
              <button 
                type="submit" 
                disabled={!stripe || processing || !selectedPlan}
                className="subscribe-button"
              >
                {processing ? 'Processing...' : `Subscribe to ${selectedPlan.name} for ${selectedPlan.price_display}`}
              </button>
              
              <p className="subscription-terms">
                By subscribing, you agree to the terms of service. You can cancel anytime.
              </p>
            </form>
          )}
        </div>
      )}
    </div>
  );
};
```

## Ad Integration

### Ad Service

```javascript
// services/adService.js
import apiClient from '../api/client';

export const getAdConfiguration = async () => {
  const response = await apiClient.get('/ads/config');
  return response.data;
};

export const recordAdView = async (adId, personaSlug, viewDuration, completed = false, interacted = false) => {
  const response = await apiClient.post('/ads/view', {
    ad_id: adId,
    persona_slug: personaSlug,
    view_duration: viewDuration,
    completion: completed,
    interaction: interacted
  });
  
  return response.data;
};

// Example ad display function (implementation would depend on ad network)
export const displayAd = async (adType = 'video') => {
  return new Promise((resolve, reject) => {
    console.log(`Displaying ${adType} ad...`);
    
    // Simulate ad display
    setTimeout(() => {
      resolve({
        adId: `${adType}_${Date.now()}`,
        viewDuration: adType === 'video' ? 30 : 10,
        completed: true,
        interacted: false
      });
    }, 1000);
  });
};
```

### Ad Component

```jsx
// components/AdDisplay.jsx
import React, { useState, useEffect } from 'react';
import { displayAd, recordAdView } from '../services/adService';

export const AdDisplay = ({ adType = 'video', personaSlug, onRewardEarned, onClose }) => {
  const [adState, setAdState] = useState('loading'); // loading, playing, completed, error
  const [countdown, setCountdown] = useState(0);
  const [reward, setReward] = useState(null);
  
  useEffect(() => {
    let countdownTimer;
    
    const showAd = async () => {
      try {
        setAdState('loading');
        
        // Simulate ad loading
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Display ad
        const adResult = await displayAd(adType);
        setAdState('playing');
        
        // Set countdown based on ad type
        const duration = adResult.viewDuration;
        setCountdown(duration);
        
        // Start countdown
        countdownTimer = setInterval(() => {
          setCountdown(prev => {
            if (prev <= 1) {
              clearInterval(countdownTimer);
              handleAdCompleted(adResult);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
        
      } catch (error) {
        console.error('Error displaying ad:', error);
        setAdState('error');
      }
    };
    
    showAd();
    
    return () => {
      if (countdownTimer) {
        clearInterval(countdownTimer);
      }
    };
  }, [adType, personaSlug]);
  
  const handleAdCompleted = async (adResult) => {
    try {
      setAdState('completed');
      
      // Record ad view
      const rewardData = await recordAdView(
        adResult.adId,
        personaSlug,
        adResult.viewDuration,
        true,
        adResult.interacted
      );
      
      // Set reward info
      setReward(rewardData);
      
      // Notify parent component
      if (onRewardEarned && rewardData.reward_earned) {
        onRewardEarned(rewardData);
      }
    } catch (error) {
      console.error('Error recording ad view:', error);
    }
  };
  
  return (
    <div className={`ad-display ad-${adType} ad-state-${adState}`}>
      <div className="ad-container">
        {adState === 'loading' && (
          <div className="ad-loading">
            <div className="loader"></div>
            <p>Loading advertisement...</p>
          </div>
        )}
        
        {adState === 'playing' && (
          <div className="ad-player">
            <div className="ad-content">
              {/* Ad content would be displayed here */}
              <div className="mock-ad">
                <h3>Advertisement</h3>
                <div className="ad-visual"></div>
                <p>This is a simulated {adType} advertisement</p>
              </div>
            </div>
            
            <div className="ad-controls">
              <div className="ad-countdown">
                Skip in {countdown} seconds
              </div>
            </div>
          </div>
        )}
        
        {adState === 'completed' && reward && (
          <div className="ad-completed">
            <div className="reward-message">
              <h3>Thank You!</h3>
              <p>{reward.message}</p>
              
              {reward.reward_earned && (
                <div className="reward-details">
                  {reward.cost_reduction_percentage && (
                    <p>You've earned a {reward.cost_reduction_percentage}% discount on your next session!</p>
                  )}
                  
                  {reward.time_reward && (
                    <p>You've earned {reward.time_reward} free minutes!</p>
                  )}
                </div>
              )}
              
              <button 
                className="close-button"
                onClick={onClose}
              >
                Continue
              </button>
            </div>
          </div>
        )}
        
        {adState === 'error' && (
          <div className="ad-error">
            <p>Sorry, there was an error displaying this advertisement.</p>
            <button 
              className="close-button"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
```

## Analytics Display

### Analytics Service

```javascript
// services/analyticsService.js
import apiClient from '../api/client';

export const getUserAnalytics = async () => {
  const response = await apiClient.get('/user/analytics');
  return response.data;
};

export const getPersonaAnalytics = async () => {
  const response = await apiClient.get('/analytics/personas');
  return response.data;
};

// Helper function for chart formatting
export const formatChartData = (data, type = 'pie') => {
  if (type === 'pie') {
    return {
      labels: Object.keys(data),
      datasets: [{
        data: Object.values(data),
        backgroundColor: [
          '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
          '#FF9F40', '#8AC249', '#EA4C89', '#00D1B2', '#3298DC'
        ]
      }]
    };
  }
  
  if (type === 'bar') {
    return {
      labels: Object.keys(data),
      datasets: [{
        label: 'Usage',
        data: Object.values(data),
        backgroundColor: '#36A2EB'
      }]
    };
  }
  
  // Default line chart
  return {
    labels: Object.keys(data),
    datasets: [{
      label: 'Data',
      data: Object.values(data),
      borderColor: '#36A2EB',
      tension: 0.1,
      fill: false
    }]
  };
};
```

### User Analytics Dashboard

```jsx
// components/UserAnalytics.jsx
import React, { useState, useEffect } from 'react';
import { Pie, Bar, Line } from 'react-chartjs-2';
import { getUserAnalytics, getPersonaAnalytics, formatChartData } from '../services/analyticsService';

export const UserAnalytics = () => {
  const [userAnalytics, setUserAnalytics] = useState(null);
  const [personaAnalytics, setPersonaAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch user analytics
        const userData = await getUserAnalytics();
        setUserAnalytics(userData);
        
        // Fetch persona analytics
        const personaData = await getPersonaAnalytics();
        setPersonaAnalytics(personaData);
      } catch (err) {
        setError('Failed to load analytics');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  if (loading) return <div className="loading">Loading analytics...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!userAnalytics || !personaAnalytics) return <div className="error">No data available</div>;
  
  return (
    <div className="user-analytics">
      <h1>Your Analytics Dashboard</h1>
      
      <div className="analytics-summary">
        <div className="summary-card">
          <h3>Total Sessions</h3>
          <div className="summary-value">{userAnalytics.usage.total_sessions}</div>
        </div>
        
        <div className="summary-card">
          <h3>Time Used</h3>
          <div className="summary-value">{userAnalytics.usage.total_hours_used} hours</div>
        </div>
        
        <div className="summary-card">
          <h3>Remaining Balance</h3>
          <div className="summary-value">{userAnalytics.balance.total_hours} hours</div>
        </div>
        
        <div className="summary-card">
          <h3>Total Spent</h3>
          <div className="summary-value">{userAnalytics.payments.total_spent_display}</div>
        </div>
      </div>
      
      <div className="analytics-row">
        <div className="analytics-card">
          <h3>Persona Usage</h3>
          <div className="chart-container">
            <Pie 
              data={formatChartData(
                personaAnalytics.popular_personas.reduce((acc, p) => {
                  acc[p.name] = p.usage_percent;
                  return acc;
                }, {}), 
                'pie'
              )} 
              options={{ responsive: true }}
            />
          </div>
        </div>
        
        <div className="analytics-card">
          <h3>Category Usage</h3>
          <div className="chart-container">
            <Bar 
              data={formatChartData(personaAnalytics.category_usage, 'bar')} 
              options={{ responsive: true }}
            />
          </div>
        </div>
      </div>
      
      <div className="analytics-row">
        <div className="analytics-card full-width">
          <h3>Session History</h3>
          <div className="chart-container">
            {/* This would use actual session data in production */}
            <Line 
              data={{
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                  label: 'Session Minutes',
                  data: [45, 70, 65, 90],
                  borderColor: '#36A2EB',
                  tension: 0.1,
                  fill: false
                }]
              }} 
              options={{ responsive: true }}
            />
          </div>
        </div>
      </div>
      
      <div className="persona-recommendations">
        <h3>Recommended For You</h3>
        <div className="recommendations-list">
          {personaAnalytics.persona_recommendations.map((rec, index) => (
            <div key={index} className="recommendation-card">
              <h4>{rec.name}</h4>
              <p>{rec.reason}</p>
              <button onClick={() => navigate(`/personas/${rec.slug}`)}>
                Try Now
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Responsive Design Considerations

### Breakpoints

```css
/* styles/breakpoints.css */
:root {
  --breakpoint-xs: 0;
  --breakpoint-sm: 576px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 992px;
  --breakpoint-xl: 1200px;
}

/* Media query mixins */
@mixin for-phone-only {
  @media (max-width: 575.98px) { @content; }
}

@mixin for-tablet-portrait-up {
  @media (min-width: 576px) { @content; }
}

@mixin for-tablet-landscape-up {
  @media (min-width: 768px) { @content; }
}

@mixin for-desktop-up {
  @media (min-width: 992px) { @content; }
}

@mixin for-large-desktop-up {
  @media (min-width: 1200px) { @content; }
}

/* Responsive layout classes */
.row {
  display: flex;
  flex-wrap: wrap;
}

.col-12 {
  flex: 0 0 100%;
  max-width: 100%;
}

@media (min-width: 576px) {
  .col-sm-6 {
    flex: 0 0 50%;
    max-width: 50%;
  }
}

@media (min-width: 768px) {
  .col-md-4 {
    flex: 0 0 33.333333%;
    max-width: 33.333333%;
  }
  
  .col-md-6 {
    flex: 0 0 50%;
    max-width: 50%;
  }
}

@media (min-width: 992px) {
  .col-lg-3 {
    flex: 0 0 25%;
    max-width: 25%;
  }
  
  .col-lg-4 {
    flex: 0 0 33.333333%;
    max-width: 33.333333%;
  }
}
```

### Responsive Component Examples

```jsx
// components/ResponsiveLayout.jsx
import React from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';

export const ResponsiveLayout = ({ children }) => {
  const isDesktop = useMediaQuery('(min-width: 992px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 991px)');
  const isMobile = useMediaQuery('(max-width: 767px)');
  
  return (
    <div className={`app-layout ${isDesktop ? 'desktop' : isTablet ? 'tablet' : 'mobile'}`}>
      {isMobile ? (
        <MobileLayout>{children}</MobileLayout>
      ) : (
        <DesktopLayout>{children}</DesktopLayout>
      )}
    </div>
  );
};

const MobileLayout = ({ children }) => (
  <div className="mobile-layout">
    <div className="mobile-header">
      <MobileNavToggle />
      <MobileLogo />
    </div>
    
    <div className="mobile-content">
      {children}
    </div>
    
    <div className="mobile-footer">
      <MobileNavigation />
    </div>
  </div>
);

const DesktopLayout = ({ children }) => (
  <div className="desktop-layout">
    <div className="sidebar">
      <Logo />
      <Navigation />
      <TimeBalanceWidget />
    </div>
    
    <div className="main-content">
      <TopBar />
      <div className="content-area">
        {children}
      </div>
    </div>
  </div>
);
```

### Media Query Hook

```javascript
// hooks/useMediaQuery.js
import { useState, useEffect } from 'react';

export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);
  
  useEffect(() => {
    const media = window.matchMedia(query);
    
    if (media.matches !== matches) {
      setMatches(media.matches);
    }
    
    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    
    return () => media.removeEventListener('change', listener);
  }, [matches, query]);
  
  return matches;
};
```

## Mobile App Integration

### React Native Integration

```javascript
// MindBotAPI.js - React Native API Client
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LivekitClient } from '@livekit/react-native-client';

class MindBotAPI {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.accessToken = null;
  }
  
  async initialize() {
    // Load token from storage
    try {
      this.accessToken = await AsyncStorage.getItem('access_token');
    } catch (error) {
      console.error('Error loading token:', error);
    }
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }
    
    const config = {
      ...options,
      headers
    };
    
    const response = await fetch(url, config);
    
    // Handle 401 - Unauthorized
    if (response.status === 401) {
      await this._handleUnauthorized();
      throw new Error('Authentication required');
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'API request failed');
    }
    
    return data;
  }
  
  async _handleUnauthorized() {
    // Clear tokens
    this.accessToken = null;
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('livekit_token');
    await AsyncStorage.removeItem('livekit_url');
    
    // Navigate to login (you would need to implement this with your navigation system)
    // For example: navigation.navigate('Login');
  }
  
  // Auth methods
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    
    await this._storeAuthData(data);
    
    return data;
  }
  
  async register(email, password, fullName) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        full_name: fullName
      })
    });
    
    await this._storeAuthData(data);
    
    return data;
  }
  
  async _storeAuthData(data) {
    this.accessToken = data.access_token;
    
    await AsyncStorage.setItem('access_token', data.access_token);
    await AsyncStorage.setItem('livekit_token', data.livekit_token);
    await AsyncStorage.setItem('livekit_url', data.livekit_url);
  }
  
  // Persona methods
  async getPersonas(filters = {}) {
    let url = '/personas';
    const queryParams = new URLSearchParams();
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value);
      }
    });
    
    const queryString = queryParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
    
    return this.request(url);
  }
  
  async getPersonaDetails(slug) {
    return this.request(`/personas/${slug}`);
  }
  
  async startPersonaSession(slug, options = {}) {
    return this.request(`/personas/${slug}/session`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }
  
  // LiveKit integration
  async connectToVoiceSession(sessionData) {
    const livekitClient = new LivekitClient();
    
    await livekitClient.connect(
      sessionData.livekit_url,
      sessionData.livekit_token
    );
    
    return {
      client: livekitClient,
      sessionId: sessionData.session_id
    };
  }
  
  // Time card methods
  async getTimeBalance() {
    return this.request('/time/balance');
  }
  
  async purchaseTimeCard(packageId, paymentMethodId, options = {}) {
    return this.request('/time/purchase', {
      method: 'POST',
      body: JSON.stringify({
        package_id: packageId,
        payment_method_id: paymentMethodId,
        ...options
      })
    });
  }
  
  // Subscription methods
  async getSubscriptionPlans() {
    return this.request('/plans');
  }
  
  async getCurrentSubscription() {
    return this.request('/subscriptions/current');
  }
  
  async createSubscription(planId, paymentMethodId, options = {}) {
    return this.request('/subscriptions', {
      method: 'POST',
      body: JSON.stringify({
        plan_id: planId,
        payment_method_id: paymentMethodId,
        ...options
      })
    });
  }
}

export default new MindBotAPI('https://api.mindbot.ai');
```

### React Native Component Example

```jsx
// MobilePersonaBrowser.js
import React, { useState, useEffect } from 'react';
import { 
  View, Text, FlatList, TouchableOpacity, 
  StyleSheet, ActivityIndicator, Image 
} from 'react-native';
import MindBotAPI from '../api/MindBotAPI';

const MobilePersonaBrowser = ({ navigation }) => {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const fetchPersonas = async () => {
      try {
        const data = await MindBotAPI.getPersonas({
          user_tier: 'premium', // Would come from user context
          sort_by: 'rating'
        });
        
        setPersonas(data.personas);
      } catch (err) {
        setError('Failed to load personas');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPersonas();
  }, []);
  
  const handlePersonaPress = (slug) => {
    navigation.navigate('PersonaDetails', { slug });
  };
  
  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Loading personas...</Text>
      </View>
    );
  }
  
  if (error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity 
          style={styles.retryButton}
          onPress={() => {
            setLoading(true);
            setError(null);
            fetchPersonas();
          }}
        >
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }
  
  const renderPersonaItem = ({ item }) => (
    <TouchableOpacity 
      style={styles.personaCard}
      onPress={() => handlePersonaPress(item.slug)}
    >
      <View style={styles.personaHeader}>
        <Text style={styles.personaName}>{item.name}</Text>
        <View style={styles.ratingContainer}>
          <Text style={styles.ratingText}>{item.rating.toFixed(1)}</Text>
          <Text style={styles.ratingStar}>★</Text>
        </View>
      </View>
      
      <Text style={styles.personaSummary}>{item.summary}</Text>
      
      <View style={styles.personaMeta}>
        <Text style={styles.categoryBadge}>{item.category}</Text>
        
        {item.ad_supported && (
          <Text style={styles.adBadge}>Ad-Supported</Text>
        )}
      </View>
      
      <View style={styles.costContainer}>
        <Text style={styles.costLabel}>
          Cost: {item.cost_multiplier === 1.0 
            ? 'Standard' 
            : `${item.cost_multiplier.toFixed(1)}x`}
        </Text>
      </View>
    </TouchableOpacity>
  );
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Choose Your AI Companion</Text>
      
      <FlatList
        data={personas}
        renderItem={renderPersonaItem}
        keyExtractor={item => item.slug}
        contentContainerStyle={styles.listContainer}
        numColumns={1}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 16
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333'
  },
  listContainer: {
    paddingBottom: 20
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666'
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  errorText: {
    fontSize: 16,
    color: '#e74c3c',
    marginBottom: 16
  },
  retryButton: {
    backgroundColor: '#3498db',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 5
  },
  retryButtonText: {
    color: 'white',
    fontWeight: 'bold'
  },
  personaCard: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 16,
    marginBottom: 16,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2
  },
  personaHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8
  },
  personaName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333'
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center'
  },
  ratingText: {
    fontSize: 16,
    color: '#666',
    marginRight: 4
  },
  ratingStar: {
    fontSize: 16,
    color: '#f39c12'
  },
  personaSummary: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12
  },
  personaMeta: {
    flexDirection: 'row',
    marginBottom: 8
  },
  categoryBadge: {
    backgroundColor: '#e0e0e0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    fontSize: 12,
    color: '#333',
    marginRight: 8
  },
  adBadge: {
    backgroundColor: '#3498db',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    fontSize: 12,
    color: 'white'
  },
  costContainer: {
    marginTop: 8
  },
  costLabel: {
    fontSize: 14,
    color: '#666'
  }
});

export default MobilePersonaBrowser;
```