#!/bin/bash
# Production setup script for MindBot Voice Agent System

set -e  # Exit on any error

echo "🚀 MindBot Production Setup Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please don't run this script as root${NC}"
    exit 1
fi

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check system requirements
echo "🔍 Checking system requirements..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
REQUIRED_VERSION="3.11"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    print_status "Python $PYTHON_VERSION (>= $REQUIRED_VERSION required)"
else
    print_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check required tools
REQUIRED_TOOLS=("curl" "git" "docker" "docker-compose")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v $tool &> /dev/null; then
        print_status "$tool is installed"
    else
        print_error "$tool is required but not installed"
        exit 1
    fi
done

# Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p {logs,backups,ssl,monitoring,scripts}
mkdir -p backend/{shared,config,tests/{unit,integration,load}}

print_status "Directory structure created"

# Setup Python environment
echo ""
echo "🐍 Setting up Python environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip
print_status "pip upgraded"

# Install production requirements
echo ""
echo "📦 Installing production dependencies..."

# Install requirements for each service
cd backend

for service in auth-service time-service admin-dashboard basic-mindbot; do
    if [ -d "$service" ] && [ -f "$service/requirements.txt" ]; then
        echo "Installing requirements for $service..."
        pip install -r "$service/requirements.txt"
        print_status "$service requirements installed"
    fi
done

# Install additional production tools
pip install gunicorn prometheus-client structlog bandit safety pytest pytest-cov pytest-asyncio locust
print_status "Production tools installed"

cd ..

# Setup environment files
echo ""
echo "🔧 Setting up environment configuration..."

# Create production environment file
if [ ! -f ".env.prod" ]; then
    cat > .env.prod << 'EOF'
# MindBot Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security - CHANGE THESE IN PRODUCTION!
JWT_SECRET=CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_MIN_32_CHARS
ADMIN_USERS=admin@yourdomain.com

# Database Paths
AUTH_DB_PATH=/app/data/mindbot_users.db
TIME_DB_PATH=/app/data/mindbot_time_tracking.db

# LiveKit Configuration - ADD YOUR CREDENTIALS
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# Stripe Configuration - ADD YOUR CREDENTIALS
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# AI Service API Keys - ADD YOUR CREDENTIALS
OPENAI_API_KEY=sk-your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# Service URLs (update for your domain)
AUTH_SERVICE_URL=https://api.yourdomain.com/auth
TIME_SERVICE_URL=https://api.yourdomain.com/time
ADMIN_SERVICE_URL=https://api.yourdomain.com/admin
EOF

    print_warning "Created .env.prod - PLEASE UPDATE WITH YOUR ACTUAL CREDENTIALS!"
else
    print_status ".env.prod already exists"
fi

# Create systemd service files
echo ""
echo "🔧 Creating systemd service files..."

sudo mkdir -p /etc/systemd/system

# Auth service
sudo tee /etc/systemd/system/mindbot-auth.service > /dev/null << EOF
[Unit]
Description=MindBot Authentication Service
After=network.target

[Service]
Type=exec
User=$USER
WorkingDirectory=$(pwd)/backend/auth-service
Environment=PATH=$(pwd)/venv/bin
EnvironmentFile=$(pwd)/.env.prod
ExecStart=$(pwd)/venv/bin/gunicorn auth_server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Time service
sudo tee /etc/systemd/system/mindbot-time.service > /dev/null << EOF
[Unit]
Description=MindBot Time Tracking Service
After=network.target mindbot-auth.service

[Service]
Type=exec
User=$USER
WorkingDirectory=$(pwd)/backend/time-service
Environment=PATH=$(pwd)/venv/bin
EnvironmentFile=$(pwd)/.env.prod
ExecStart=$(pwd)/venv/bin/gunicorn time_server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Admin dashboard
sudo tee /etc/systemd/system/mindbot-admin.service > /dev/null << EOF
[Unit]
Description=MindBot Admin Dashboard
After=network.target mindbot-auth.service mindbot-time.service

[Service]
Type=exec
User=$USER
WorkingDirectory=$(pwd)/backend/admin-dashboard
Environment=PATH=$(pwd)/venv/bin
EnvironmentFile=$(pwd)/.env.prod
ExecStart=$(pwd)/venv/bin/gunicorn admin_server:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd service files created"

# Create nginx configuration
echo ""
echo "🌐 Creating nginx configuration..."

sudo tee /etc/nginx/sites-available/mindbot << 'EOF'
# MindBot API Gateway Configuration
upstream auth_backend {
    server 127.0.0.1:8000;
}

upstream time_backend {
    server 127.0.0.1:8001;
}

upstream admin_backend {
    server 127.0.0.1:8002;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;

server {
    listen 80;
    server_name api.yourdomain.com;  # CHANGE THIS

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;  # CHANGE THIS

    # SSL Configuration - UPDATE WITH YOUR CERTIFICATES
    ssl_certificate /etc/ssl/certs/mindbot.crt;
    ssl_certificate_key /etc/ssl/private/mindbot.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Auth service
    location /auth/ {
        limit_req zone=auth_limit burst=5 nodelay;
        proxy_pass http://auth_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Time service
    location /time/ {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://time_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin service (restrict access)
    location /admin/ {
        limit_req zone=auth_limit burst=5 nodelay;
        
        # IP whitelist - ADD YOUR ADMIN IPs
        # allow 192.168.1.0/24;
        # deny all;
        
        proxy_pass http://admin_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

print_status "Nginx configuration created"

# Setup log rotation
echo ""
echo "📝 Setting up log rotation..."

sudo tee /etc/logrotate.d/mindbot << 'EOF'
/var/log/mindbot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        systemctl reload nginx
        systemctl restart mindbot-auth mindbot-time mindbot-admin
    endscript
}
EOF

sudo mkdir -p /var/log/mindbot
print_status "Log rotation configured"

# Create monitoring script
echo ""
echo "📊 Creating monitoring script..."

cat > monitoring/health_check.sh << 'EOF'
#!/bin/bash
# MindBot Health Check Script

SERVICES=("mindbot-auth" "mindbot-time" "mindbot-admin")
ENDPOINTS=("http://localhost:8000/health" "http://localhost:8001/health" "http://localhost:8002/health")

for i in "${!SERVICES[@]}"; do
    service="${SERVICES[$i]}"
    endpoint="${ENDPOINTS[$i]}"
    
    # Check service status
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        systemctl restart $service
    fi
    
    # Check HTTP endpoint
    if curl -f -s $endpoint > /dev/null; then
        echo "✅ $service endpoint is responding"
    else
        echo "❌ $service endpoint is not responding"
    fi
done

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ Disk usage is ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEM_USAGE -gt 80 ]; then
    echo "⚠️ Memory usage is ${MEM_USAGE}%"
fi
EOF

chmod +x monitoring/health_check.sh
print_status "Health check script created"

# Setup cron job for monitoring
echo ""
echo "⏰ Setting up monitoring cron job..."

(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/monitoring/health_check.sh >> /var/log/mindbot/health.log 2>&1") | crontab -
print_status "Monitoring cron job added (runs every 5 minutes)"

# Create backup script
echo ""
echo "💾 Creating backup script..."

cat > scripts/backup.sh << 'EOF'
#!/bin/bash
# MindBot Backup Script

BACKUP_DIR="/backup/mindbot/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup databases
cp backend/auth-service/mindbot_users.db $BACKUP_DIR/ 2>/dev/null || echo "No auth database found"
cp backend/time-service/mindbot_time_tracking.db $BACKUP_DIR/ 2>/dev/null || echo "No time database found"

# Backup configuration
cp .env.prod $BACKUP_DIR/

# Backup logs
cp -r /var/log/mindbot $BACKUP_DIR/logs/ 2>/dev/null || echo "No logs found"

# Compress backup
tar -czf $BACKUP_DIR.tar.gz -C $(dirname $BACKUP_DIR) $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

echo "Backup created: $BACKUP_DIR.tar.gz"

# Keep only last 7 days of backups
find /backup/mindbot/ -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x scripts/backup.sh

# Setup daily backup cron job
(crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/scripts/backup.sh >> /var/log/mindbot/backup.log 2>&1") | crontab -
print_status "Backup script and daily cron job created"

# Create deployment script
echo ""
echo "🚀 Creating deployment script..."

cat > scripts/deploy.sh << 'EOF'
#!/bin/bash
# MindBot Deployment Script

set -e

echo "🚀 Deploying MindBot Services..."

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r backend/auth-service/requirements.txt
pip install -r backend/time-service/requirements.txt
pip install -r backend/admin-dashboard/requirements.txt

# Run tests
echo "🧪 Running tests..."
cd backend
python -m pytest tests/ -v
cd ..

# Backup current databases
./scripts/backup.sh

# Reload systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart mindbot-auth mindbot-time mindbot-admin

# Wait for services to start
sleep 10

# Health check
./monitoring/health_check.sh

echo "✅ Deployment completed successfully!"
EOF

chmod +x scripts/deploy.sh
print_status "Deployment script created"

# Final instructions
echo ""
echo "🎉 Production setup completed!"
echo "=============================="
echo ""
print_warning "IMPORTANT: Complete these manual steps:"
echo ""
echo "1. 📝 Update .env.prod with your actual credentials:"
echo "   - LiveKit API keys"
echo "   - Stripe API keys"  
echo "   - OpenAI and Deepgram API keys"
echo "   - Change JWT_SECRET to a secure random string"
echo ""
echo "2. 🔒 Setup SSL certificates in /etc/ssl/certs/ and /etc/ssl/private/"
echo ""
echo "3. 🌐 Update nginx configuration with your domain name:"
echo "   sudo nano /etc/nginx/sites-available/mindbot"
echo ""
echo "4. 🔧 Enable nginx site:"
echo "   sudo ln -s /etc/nginx/sites-available/mindbot /etc/nginx/sites-enabled/"
echo "   sudo nginx -t"
echo "   sudo systemctl restart nginx"
echo ""
echo "5. 🚀 Start MindBot services:"
echo "   sudo systemctl enable mindbot-auth mindbot-time mindbot-admin"
echo "   sudo systemctl start mindbot-auth mindbot-time mindbot-admin"
echo ""
echo "6. ✅ Verify everything is working:"
echo "   ./monitoring/health_check.sh"
echo ""
print_status "Production setup script completed!"
print_warning "Remember to secure your server and keep your API keys safe!"