# MindBot Frontend Integration Flow

## User Journey Map

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│  Register/  │────►│ Purchase    │────►│ Choose      │────►│ Voice       │
│  Login      │     │ Time Cards  │     │ Persona     │     │ Session     │
│             │     │             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐           │
│             │     │             │     │             │           │
│ Upgrade     │◄────│ View        │◄────│ Rate        │◄──────────┘
│ Subscription│     │ Analytics   │     │ Experience  │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Registration & Login Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Registration│     │             │     │             │
│ Form        │────►│ JWT Token   │────►│ User        │
│             │     │ Generation  │     │ Dashboard   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                        ▲
      │                                        │
      │             ┌─────────────┐            │
      │             │             │            │
      └────────────►│ Login       │────────────┘
                    │ Form        │
                    │             │
                    └─────────────┘
```

## Time Card Purchase Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Package     │     │             │     │             │
│ Selection   │────►│ Stripe      │────►│ Activation  │
│             │     │ Payment     │     │ Confirmation│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │
                    ┌─────────────┐
                    │             │
                    │ Webhook     │
                    │ Processing  │
                    │             │
                    └─────────────┘
```

## Persona Selection Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Persona     │     │             │     │             │
│ Browse      │────►│ Persona     │────►│ Session     │
│             │     │ Details     │     │ Start       │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                        │
      │                                        │
      │             ┌─────────────┐            │
      │             │             │            │
      └────────────►│ Custom      │────────────┘
                    │ Persona     │
                    │ Creation    │
                    └─────────────┘
```

## Voice Session Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Session     │     │             │     │             │
│ Start       │────►│ LiveKit     │────►│ Voice       │
│             │     │ Connection  │     │ Interaction │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              │
                    ┌─────────────┐           │
                    │             │           │
                    │ Session End │◄──────────┘
                    │             │
                    └─────────────┘
```

## Subscription Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Plan        │     │             │     │             │
│ Selection   │────►│ Stripe      │────►│ Account     │
│             │     │ Subscription│     │ Upgrade     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           │
                    ┌─────────────┐
                    │             │
                    │ Webhook     │
                    │ Processing  │
                    │             │
                    └─────────────┘
```

## Ad Integration Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Ad Display  │     │             │     │             │
│ Trigger     │────►│ Ad Network  │────►│ Ad View     │
│             │     │ Request     │     │ Display     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              │
                    ┌─────────────┐           │
                    │             │           │
                    │ Reward      │◄──────────┘
                    │ Processing  │
                    └─────────────┘
```

## Custom Persona Creation Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Persona     │     │             │     │             │
│ Builder Form│────►│ AI-Generated│────►│ Persona     │
│             │     │ Configuration│    │ Preview     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              │
                    ┌─────────────┐           │
                    │             │           │
                    │ Save &      │◄──────────┘
                    │ Activate    │
                    └─────────────┘
```

## Analytics Dashboard Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Analytics   │     │             │     │             │
│ Dashboard   │────►│ Usage       │     │ Persona     │
│             │     │ Overview    │◄───►│ Analytics   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │             │     │             │
                    │ Time        │◄───►│ Subscription│
                    │ Analytics   │     │ Analytics   │
                    └─────────────┘     └─────────────┘
```

## Key UI Components

### Main App Shell

```javascript
function AppShell() {
  return (
    <div className="app-container">
      <Header />
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/personas" element={<PersonaBrowser />} />
          <Route path="/personas/:slug" element={<PersonaDetail />} />
          <Route path="/time-cards" element={<TimeCardManagement />} />
          <Route path="/sessions" element={<SessionHistory />} />
          <Route path="/subscription" element={<SubscriptionManagement />} />
          <Route path="/analytics" element={<UserAnalytics />} />
          <Route path="/settings" element={<UserSettings />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
```

### Auth Components

```javascript
function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await loginUser(email, password);
      navigate('/dashboard');
    } catch (error) {
      showErrorMessage(error.message);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit">Login</button>
      <p>Don't have an account? <Link to="/register">Register</Link></p>
    </form>
  );
}
```

### Persona Browser Component

```javascript
function PersonaBrowser() {
  const [personas, setPersonas] = useState([]);
  const [filters, setFilters] = useState({
    category: '',
    adSupported: null,
    sortBy: 'rating'
  });
  
  useEffect(() => {
    async function fetchPersonas() {
      try {
        const response = await fetch(
          `/personas?user_tier=${userTier}&category=${filters.category}&ad_supported=${filters.adSupported}&sort_by=${filters.sortBy}`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
          }
        );
        
        const data = await response.json();
        setPersonas(data.personas);
      } catch (error) {
        console.error('Error fetching personas:', error);
      }
    }
    
    fetchPersonas();
  }, [filters, userTier]);
  
  return (
    <div className="persona-browser">
      <h1>Choose Your AI Companion</h1>
      
      <div className="filters">
        <CategoryFilter 
          selected={filters.category} 
          onChange={(category) => setFilters({...filters, category})} 
        />
        <SortDropdown 
          selected={filters.sortBy}
          onChange={(sortBy) => setFilters({...filters, sortBy})}
        />
        <AdSupportToggle 
          selected={filters.adSupported}
          onChange={(adSupported) => setFilters({...filters, adSupported})}
        />
      </div>
      
      <div className="persona-grid">
        {personas.map(persona => (
          <PersonaCard 
            key={persona.slug}
            persona={persona}
            onSelect={() => navigate(`/personas/${persona.slug}`)}
          />
        ))}
      </div>
      
      {userTier === 'premium' && (
        <button 
          className="create-persona-button"
          onClick={() => navigate('/personas/create')}
        >
          Create Custom Persona
        </button>
      )}
    </div>
  );
}
```

### Time Card Purchase Component

```javascript
function TimeCardPurchase() {
  const [packages, setPackages] = useState([]);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [couponCode, setCouponCode] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  useEffect(() => {
    async function fetchPackages() {
      try {
        const response = await fetch('/time/pricing');
        const data = await response.json();
        setPackages(data.pricing_tiers);
      } catch (error) {
        console.error('Error fetching packages:', error);
      }
    }
    
    fetchPackages();
  }, []);
  
  const handlePurchase = async () => {
    if (!selectedPackage || !paymentMethod) return;
    
    setIsProcessing(true);
    
    try {
      const result = await purchaseTimeCard(
        selectedPackage.id, 
        paymentMethod.id,
        couponCode
      );
      
      if (result.success) {
        showSuccessMessage(
          `Successfully purchased ${result.package.name}!`
        );
        navigate('/time-cards');
      }
    } catch (error) {
      showErrorMessage(`Payment failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  return (
    <div className="time-card-purchase">
      <h1>Purchase Time Cards</h1>
      
      <div className="package-selection">
        {packages.map(pkg => (
          <PackageOption
            key={pkg.id}
            package={pkg}
            isSelected={selectedPackage?.id === pkg.id}
            onSelect={() => setSelectedPackage(pkg)}
          />
        ))}
      </div>
      
      <div className="payment-section">
        <h2>Payment Method</h2>
        <StripeCardElement
          onChange={(e) => setPaymentMethod(e.complete ? e.element : null)}
        />
        
        <div className="coupon-section">
          <input
            type="text"
            value={couponCode}
            onChange={(e) => setCouponCode(e.target.value)}
            placeholder="Coupon Code (Optional)"
          />
          <button onClick={validateCoupon}>Apply</button>
        </div>
        
        <button 
          className="purchase-button"
          disabled={!selectedPackage || !paymentMethod || isProcessing}
          onClick={handlePurchase}
        >
          {isProcessing ? 'Processing...' : `Purchase ${selectedPackage?.name || 'Package'}`}
        </button>
      </div>
    </div>
  );
}
```

### Voice Session Component

```javascript
function VoiceSession({ personaSlug }) {
  const [room, setRoom] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [enableAds, setEnableAds] = useState(true);
  const [timeBalance, setTimeBalance] = useState(null);
  const [persona, setPersona] = useState(null);
  
  useEffect(() => {
    async function startSession() {
      setIsConnecting(true);
      
      try {
        const session = await startPersonaSession(personaSlug, enableAds);
        
        setRoom(session.room);
        setPersona(session.persona);
        setTimeBalance(session.time_balance);
        setIsConnected(true);
        
        // Setup event listeners
        session.room.on('trackSubscribed', handleTrackSubscribed);
        session.room.on('disconnected', handleDisconnect);
        
      } catch (error) {
        console.error('Session error:', error);
        showErrorMessage(`Failed to connect: ${error.message}`);
      } finally {
        setIsConnecting(false);
      }
    }
    
    startSession();
    
    return () => {
      // Cleanup on unmount
      if (room) {
        room.disconnect();
      }
    };
  }, [personaSlug, enableAds]);
  
  // Handle speech events
  useEffect(() => {
    if (!room) return;
    
    const handleSpeech = (transcript) => {
      setTranscript(transcript);
      setIsSpeaking(true);
    };
    
    const handleSpeechEnd = () => {
      setIsSpeaking(false);
    };
    
    // Set up speech event listeners
    // (Implementation depends on LiveKit details)
    
    return () => {
      // Remove listeners
    };
  }, [room]);
  
  // Show ad if needed based on session configuration
  const showAdIfNeeded = async () => {
    if (!enableAds) return;
    
    try {
      const adResult = await showAdForReward('video');
      
      if (adResult.reward_earned) {
        showRewardMessage(adResult.message);
      }
    } catch (error) {
      console.error('Ad error:', error);
    }
  };
  
  const endSession = async () => {
    try {
      if (room) {
        await room.disconnect();
      }
      
      navigate('/sessions');
    } catch (error) {
      console.error('Error ending session:', error);
    }
  };
  
  return (
    <div className="voice-session">
      <div className="session-header">
        <div className="persona-info">
          <h1>{persona?.name || 'AI Assistant'}</h1>
          <p>{persona?.summary || 'Loading...'}</p>
        </div>
        
        <div className="session-controls">
          <button 
            className="end-session-button"
            onClick={endSession}
          >
            End Session
          </button>
          
          <div className="time-balance">
            {timeBalance && (
              <span>{timeBalance.total_minutes} minutes remaining</span>
            )}
          </div>
        </div>
      </div>
      
      <div className="conversation-area">
        <div className="transcript">
          <p>{transcript || 'Start speaking to begin conversation...'}</p>
        </div>
        
        <div className={`agent-status ${isSpeaking ? 'speaking' : ''}`}>
          {isSpeaking ? 'Speaking...' : 'Listening...'}
        </div>
        
        {enableAds && (
          <div className="ad-section">
            <button onClick={showAdIfNeeded}>
              Watch ad for 5 free minutes
            </button>
          </div>
        )}
      </div>
      
      <div className="microphone-status">
        {isConnected ? 'Microphone active' : 'Connecting...'}
      </div>
    </div>
  );
}
```

### Subscription Management Component

```javascript
function SubscriptionManagement() {
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  useEffect(() => {
    async function fetchData() {
      try {
        // Get plans
        const plansResponse = await fetch('/plans');
        const plansData = await plansResponse.json();
        setPlans(plansData.plans);
        
        // Get current subscription
        const subResponse = await fetch('/subscriptions/current', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (subResponse.ok) {
          const subData = await subResponse.json();
          setCurrentSubscription(subData);
        }
      } catch (error) {
        console.error('Error fetching subscription data:', error);
      }
    }
    
    fetchData();
  }, []);
  
  const handleSubscribe = async (planId) => {
    setIsProcessing(true);
    
    try {
      // Get or create payment method
      const paymentMethod = await getPaymentMethod();
      
      if (!paymentMethod) {
        throw new Error('Payment method required');
      }
      
      // Subscribe to plan
      const result = await subscribeToPlan(planId);
      
      if (result.success) {
        showSuccessMessage(`Successfully subscribed to ${result.subscription.plan}!`);
        setCurrentSubscription(result.subscription);
      }
    } catch (error) {
      showErrorMessage(`Subscription failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) {
      return;
    }
    
    setIsProcessing(true);
    
    try {
      const response = await fetch('/subscriptions/cancel', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      const data = await response.json();
      
      if (response.ok && data.cancelled) {
        showSuccessMessage(data.message);
        setCurrentSubscription({
          ...currentSubscription,
          cancel_at_period_end: true
        });
      } else {
        throw new Error(data.detail || 'Cancellation failed');
      }
    } catch (error) {
      showErrorMessage(`Error: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  return (
    <div className="subscription-management">
      <h1>Subscription Management</h1>
      
      {currentSubscription ? (
        <div className="current-subscription">
          <h2>Current Plan: {currentSubscription.plan_name}</h2>
          <p>Status: {currentSubscription.status}</p>
          <p>Renews: {new Date(currentSubscription.current_period_end).toLocaleDateString()}</p>
          
          {currentSubscription.cancel_at_period_end ? (
            <p className="cancellation-notice">
              Your subscription will end on {new Date(currentSubscription.current_period_end).toLocaleDateString()}
            </p>
          ) : (
            <button 
              className="cancel-button"
              onClick={handleCancel}
              disabled={isProcessing}
            >
              Cancel Subscription
            </button>
          )}
          
          <h3>Features</h3>
          <ul className="feature-list">
            {currentSubscription.features.map((feature, index) => (
              <li key={index}>{feature}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="subscription-plans">
          <h2>Choose a Plan</h2>
          
          {plans.map(plan => (
            <div className="plan-card" key={plan.id}>
              <h3>{plan.name}</h3>
              <p className="price">{plan.price_display}</p>
              
              <ul className="feature-list">
                {plan.features.map((feature, index) => (
                  <li key={index}>{feature}</li>
                ))}
              </ul>
              
              <button
                className="subscribe-button"
                onClick={() => handleSubscribe(plan.id)}
                disabled={isProcessing}
              >
                Subscribe Now
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```