# Deployment Guide

## Deployment Options

### Option 1: LiveKit Cloud + Vercel (Recommended for MVP)

**Pros**: Easy setup, managed infrastructure, good for prototyping
**Cons**: Higher costs at scale, less control

#### Backend Deployment
1. **Prepare Agent for Cloud**:
   ```bash
   cd backend/basic-mindbot
   # Ensure all dependencies are in requirements.txt
   pip freeze > requirements.txt
   ```

2. **Deploy to Cloud Platform** (Railway, Render, or DigitalOcean):
   ```dockerfile
   # Use the provided dockerfile-example as reference
   FROM python:3.11-slim
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "basic-mindbot.py", "start"]
   ```

3. **Set Environment Variables** on your platform:
   ```
   LIVEKIT_API_SECRET=your_secret
   LIVEKIT_API_KEY=your_key  
   LIVEKIT_URL=wss://your-project.livekit.cloud
   OPENAI_API_KEY=your_openai_key
   DEEPGRAM_API_KEY=your_deepgram_key
   ```

#### Frontend Deployment
1. **Deploy to Vercel**:
   ```bash
   cd frontends/basic-frontend
   npm install -g vercel
   vercel
   ```

2. **Configure Environment Variables** in Vercel dashboard:
   ```
   LIVEKIT_API_KEY=your_key
   LIVEKIT_API_SECRET=your_secret
   LIVEKIT_URL=wss://your-project.livekit.cloud
   ```

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
  replicas: 2
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
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## Environment-Specific Configurations

### Development Environment
```env
# .env.development
LIVEKIT_URL=ws://localhost:7880
LOG_LEVEL=DEBUG
ENABLE_METRICS=true
```

### Staging Environment
```env
# .env.staging
LIVEKIT_URL=wss://staging-project.livekit.cloud
LOG_LEVEL=INFO
ENABLE_METRICS=true
RATE_LIMIT_ENABLED=true
```

### Production Environment
```env
# .env.production
LIVEKIT_URL=wss://prod-project.livekit.cloud
LOG_LEVEL=WARN
ENABLE_METRICS=true
RATE_LIMIT_ENABLED=true
SECURITY_HEADERS=true
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy MindBot

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
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
        python -m pytest tests/
        
    - name: Build Docker image
      run: |
        docker build -t mindbot-agent ./backend/basic-mindbot
        
    - name: Deploy to production
      # Add your deployment commands here
      run: echo "Deploy to production"

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'pnpm'
        
    - name: Install dependencies
      run: |
        cd frontends/basic-frontend
        pnpm install
        
    - name: Build application
      run: |
        cd frontends/basic-frontend
        pnpm build
        
    - name: Deploy to Vercel
      uses: amondnet/vercel-action@v20
      with:
        vercel-token: ${{ secrets.VERCEL_TOKEN }}
        vercel-org-id: ${{ secrets.ORG_ID }}
        vercel-project-id: ${{ secrets.PROJECT_ID }}
```

## Monitoring and Logging

### Application Monitoring
```python
# monitoring.py
import logging
from livekit.agents import metrics
import sentry_sdk

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
```

### Health Check Endpoints
```python
# health.py
from fastapi import FastAPI
import redis

app = FastAPI()

@app.get("/health")
async def health_check():
    try:
        # Check LiveKit connectivity
        # Check Redis connectivity  
        # Check API dependencies
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Security Considerations

### Production Security Checklist
- [ ] Use HTTPS/WSS in production
- [ ] Implement proper CORS policies
- [ ] Use secure API key storage (AWS Secrets Manager, etc.)
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerting
- [ ] Configure firewalls properly
- [ ] Use least-privilege access policies
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Implement input validation

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
- Implement usage limits
- Use cheaper models for non-critical operations
- Cache frequent responses
- Optimize audio quality vs. bandwidth

## Backup and Recovery

### Data Backup Strategy
- Regular database backups
- Configuration file versioning
- Log archival strategy
- Conversation history backup

### Disaster Recovery Plan
- Multi-region deployment
- Automated failover procedures
- Recovery time objectives (RTO)
- Recovery point objectives (RPO)
- Regular disaster recovery testing