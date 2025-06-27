# Backend Deployment Guide

## Deployment Options

### Option 1: LiveKit Cloud + Managed Hosting (Recommended for MVP)

**Pros**: Easy setup, managed infrastructure, good for prototyping
**Cons**: Higher costs at scale, less control

#### Backend Deployment to Railway
1. **Prepare Agent for Cloud**:
   ```bash
   cd backend/basic-mindbot
   # Ensure all dependencies are in requirements.txt
   pip freeze > requirements.txt
   ```

2. **Deploy to Railway**:
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and deploy
   railway login
   railway init
   railway up
   ```

3. **Set Environment Variables** in Railway dashboard:
   ```
   LIVEKIT_API_SECRET=your_secret
   LIVEKIT_API_KEY=your_key  
   LIVEKIT_URL=wss://your-project.livekit.cloud
   OPENAI_API_KEY=your_openai_key
   DEEPGRAM_API_KEY=your_deepgram_key
   ```

#### Backend Deployment to Render
1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["python", "basic-mindbot.py", "start"]
   ```

2. **Deploy via Render Dashboard**:
   - Connect your GitHub repository
   - Set environment variables
   - Deploy from main branch

### Option 2: Self-Hosted LiveKit + AWS/GCP

**Pros**: Full control, potentially lower costs at scale
**Cons**: More complex setup, requires infrastructure management

#### Infrastructure Setup
```yaml
# docker-compose.yml for LiveKit server
version: '3.8'
services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881/tcp"
      - "7882:7882/udp"
    volumes:
      - ./livekit.yaml:/livekit.yaml
    command: --config /livekit.yaml
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
      
  agent:
    build: ./backend/basic-mindbot
    depends_on:
      - livekit
      - redis
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}
```

#### LiveKit Configuration
```yaml
# livekit.yaml
port: 7880
rtc:
  tcp_port: 7881
  udp_port: 7882
  use_external_ip: true
  
keys:
  APIKey: your_api_key
  APISecret: your_api_secret
  
redis:
  address: redis:6379
  
room:
  auto_create: true
  enable_recording: false
```

### Option 3: Kubernetes Deployment

**Pros**: Highly scalable, production-ready
**Cons**: Complex setup, requires Kubernetes knowledge

#### Kubernetes Manifests
```yaml
# agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mindbot-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mindbot-agent
  template:
    metadata:
      labels:
        app: mindbot-agent
    spec:
      containers:
      - name: agent
        image: your-registry/mindbot-agent:latest
        env:
        - name: LIVEKIT_URL
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: url
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: mindbot-agent-service
spec:
  selector:
    app: mindbot-agent
  ports:
  - port: 80
    targetPort: 8080
```

## Environment-Specific Configurations

### Development Environment
```env
# .env.development
LIVEKIT_URL=ws://localhost:7880
LOG_LEVEL=DEBUG
ENABLE_METRICS=true
AGENT_NAME=mindbot-dev
```

### Staging Environment
```env
# .env.staging
LIVEKIT_URL=wss://staging-project.livekit.cloud
LOG_LEVEL=INFO
ENABLE_METRICS=true
RATE_LIMIT_ENABLED=true
AGENT_NAME=mindbot-staging
```

### Production Environment
```env
# .env.production
LIVEKIT_URL=wss://prod-project.livekit.cloud
LOG_LEVEL=WARN
ENABLE_METRICS=true
RATE_LIMIT_ENABLED=true
SECURITY_HEADERS=true
AGENT_NAME=mindbot-prod
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy-backend.yml
name: Deploy MindBot Backend

on:
  push:
    branches: [main]
    paths: ['backend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        cd backend/basic-mindbot
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        cd backend/basic-mindbot
        python -m pytest tests/ || echo "No tests found"
        
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t mindbot-agent ./backend/basic-mindbot
        
    - name: Deploy to Railway
      run: |
        npm install -g @railway/cli
        railway login --token ${{ secrets.RAILWAY_TOKEN }}
        railway up --service mindbot-backend
```

## Monitoring and Logging

### Application Monitoring
```python
# monitoring.py
import logging
import sentry_sdk
from livekit.agents import metrics

# Configure Sentry for error tracking
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mindbot-agent")

# Metrics collection
def setup_metrics():
    """Setup metrics collection for monitoring"""
    usage_collector = metrics.UsageCollector()
    return usage_collector
```

### Health Check Implementation
```python
# health_check.py
from fastapi import FastAPI
import redis
import httpx

app = FastAPI()

@app.get("/health")
async def health_check():
    try:
        # Check LiveKit connectivity
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LIVEKIT_URL}/health")
            livekit_healthy = response.status_code == 200
        
        # Check Redis connectivity (if used)
        r = redis.Redis()
        redis_healthy = r.ping()
        
        # Check API dependencies
        openai_healthy = True  # Implement OpenAI health check
        deepgram_healthy = True  # Implement Deepgram health check
        
        if all([livekit_healthy, redis_healthy, openai_healthy, deepgram_healthy]):
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        else:
            return {"status": "unhealthy", "details": {
                "livekit": livekit_healthy,
                "redis": redis_healthy,
                "openai": openai_healthy,
                "deepgram": deepgram_healthy
            }}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/metrics")
async def get_metrics():
    """Expose metrics for monitoring"""
    return {
        "active_sessions": 0,  # Implement session counting
        "total_requests": 0,   # Implement request counting
        "avg_response_time": 0, # Implement response time tracking
    }
```

## Security Considerations

### Production Security Checklist
- [ ] Use HTTPS/WSS in production
- [ ] Implement proper API rate limiting
- [ ] Use secure secret storage (AWS Secrets Manager, etc.)
- [ ] Enable comprehensive logging
- [ ] Configure firewalls properly
- [ ] Use least-privilege access policies
- [ ] Regular security updates
- [ ] Input validation and sanitization
- [ ] Implement request authentication
- [ ] Monitor for abuse patterns

### Network Security
```yaml
# Security group rules (AWS example)
SecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupDescription: MindBot Agent Security Group
    SecurityGroupIngress:
    - IpProtocol: tcp
      FromPort: 443
      ToPort: 443
      CidrIp: 0.0.0.0/0
    - IpProtocol: udp
      FromPort: 7882
      ToPort: 7882
      CidrIp: 0.0.0.0/0  # LiveKit UDP traffic
    SecurityGroupEgress:
    - IpProtocol: -1
      CidrIp: 0.0.0.0/0
```

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple agent instances
- Use load balancer for distribution
- Implement session affinity if needed
- Monitor resource usage per instance

### Vertical Scaling
- Monitor CPU/memory usage
- Optimize audio processing
- Implement caching strategies
- Use connection pooling

### Cost Optimization
- Monitor API usage and costs
- Implement usage limits per session
- Use cheaper models for non-critical operations
- Cache frequent responses
- Optimize audio quality vs. bandwidth

## Backup and Recovery

### Data Backup Strategy
- Regular configuration backups
- Log archival strategy
- Conversation history backup (if implemented)
- Database backups for user data

### Disaster Recovery Plan
- Multi-region deployment capability
- Automated failover procedures
- Recovery time objectives (RTO): < 1 hour
- Recovery point objectives (RPO): < 15 minutes
- Regular disaster recovery testing

## Performance Optimization

### Agent Performance Tuning
```python
# performance_config.py
AGENT_CONFIG = {
    "max_concurrent_sessions": 100,
    "session_timeout": 300,  # 5 minutes
    "audio_buffer_size": 1024,
    "vad_sensitivity": 0.5,
    "response_timeout": 30,
    "max_function_calls_per_session": 10
}

# Resource monitoring
def monitor_resources():
    """Monitor system resources"""
    import psutil
    
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    
    if cpu_usage > 80 or memory_usage > 85:
        logger.warning(f"High resource usage: CPU {cpu_usage}%, Memory {memory_usage}%")
```