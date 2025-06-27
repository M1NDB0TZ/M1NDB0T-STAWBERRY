# API Configuration Guide

## LiveKit Configuration

### Cloud Setup
1. Create account at [LiveKit Cloud](https://cloud.livekit.io)
2. Create new project
3. Navigate to Settings → Keys
4. Copy credentials:
   - API Key
   - API Secret
   - WebSocket URL (format: `wss://your-project.livekit.cloud`)

### Self-Hosted Setup
If using self-hosted LiveKit:
```yaml
# livekit.yaml
port: 7880
rtc:
  tcp_port: 7881
  udp_port: 7882
keys:
  APIKey: your_api_key
  APISecret: your_api_secret
```

## OpenAI Configuration

### API Key Setup
1. Sign up at [OpenAI Platform](https://platform.openai.com)
2. Navigate to API keys section
3. Create new secret key
4. Set usage limits and billing

### Model Configuration
Current models used:
- **LLM**: `gpt-4.1-mini` (optimized for speed)
- **TTS**: `fable` voice model
- **STT**: OpenAI Whisper (fallback option)

### Usage Optimization
```python
# Recommended settings for cost optimization
llm=openai.LLM(
    model="gpt-4.1-mini",  # Faster, cheaper than gpt-4
    store="True",         # Enable conversation storage
    temperature=0.7,      # Balance creativity and consistency
    max_tokens=150        # Limit response length
)
```

## Deepgram Configuration

### API Key Setup
1. Create account at [Deepgram Console](https://console.deepgram.com)
2. Navigate to API Keys
3. Create new key with appropriate scopes
4. Monitor usage in dashboard

### Model Configuration
```python
stt=deepgram.STT(
    model="nova-3",      # Latest model
    language="multi",    # Multi-language support
    punctuate=True,      # Auto punctuation
    profanity_filter=False,  # Adjust as needed
    redact=[]           # PII redaction options
)
```

### Language Support
Supported languages include:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- And many more...

## Environment Variable Management

### Backend Environment (.env)
```env
# LiveKit Configuration
LIVEKIT_API_SECRET="sk-xxx"
LIVEKIT_API_KEY="APIxxx"
LIVEKIT_URL="wss://your-project.livekit.cloud"

# AI Provider Keys
OPENAI_API_KEY="sk-xxx"
DEEPGRAM_API_KEY="xxx"

# Optional: Additional Providers
ELEVENLABS_API_KEY="xxx"  # Alternative TTS
CARTESIA_API_KEY="xxx"    # Alternative TTS
```

### Frontend Environment (.env.local)
```env
# LiveKit Configuration (Frontend)
LIVEKIT_API_KEY=APIxxx
LIVEKIT_API_SECRET=sk-xxx
LIVEKIT_URL=wss://your-project.livekit.cloud

# Optional: Custom Connection Endpoint
NEXT_PUBLIC_CONN_DETAILS_ENDPOINT=/api/connection-details
```

## Rate Limits & Quotas

### OpenAI Limits
- **Tier 1**: $100/month, 3 RPM
- **Tier 2**: $50+ spent, higher limits
- Monitor usage in OpenAI dashboard

### Deepgram Limits
- **Free Tier**: 45,000 minutes/month
- **Growth Plan**: Pay-as-you-go
- Monitor usage in Deepgram console

### LiveKit Limits
- **Community**: Free tier with limitations
- **Cloud**: Usage-based pricing
- Monitor in LiveKit Cloud dashboard

## Security Best Practices

### API Key Security
- Never commit API keys to version control
- Use environment variables or secret management
- Rotate keys regularly
- Monitor for unauthorized usage

### Access Control
```python
# Limit token permissions
grant: VideoGrant = {
    room: roomName,
    roomJoin: True,
    canPublish: True,      # Audio publishing
    canPublishData: True,  # Text/data
    canSubscribe: True,    # Receive audio
    canUpdateOwnMetadata: True,
    hidden: False,         # Visible participant
    recorder: False        # Not a recorder
}
```

### Network Security
- Use HTTPS/WSS in production
- Configure CORS properly
- Implement request rate limiting
- Monitor for abuse patterns

## Monitoring & Analytics

### LiveKit Analytics
- Session duration and quality metrics
- Participant connection statistics
- Media quality indicators
- Error rate monitoring

### Custom Metrics
```python
# Usage tracking in agent
usage_collector = metrics.UsageCollector()

@session.on("metrics_collected")
def _on_metrics_collected(ev: MetricsCollectedEvent):
    metrics.log_metrics(ev.metrics)
    usage_collector.collect(ev.metrics)
```

### Cost Monitoring
- Set up billing alerts in provider dashboards
- Implement usage tracking in application
- Monitor token consumption patterns
- Set up automated cost controls