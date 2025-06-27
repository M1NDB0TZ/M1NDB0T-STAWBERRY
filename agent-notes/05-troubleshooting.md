# Backend Troubleshooting Guide

## Common Issues and Solutions

### Agent Connection Issues

#### Agent Not Joining Room
**Symptoms**: Agent service starts but never connects to LiveKit room
**Causes**:
- Incorrect LiveKit credentials
- Network connectivity issues
- LiveKit server not accessible

**Solutions**:
1. Verify environment variables in backend `.env`:
   ```bash
   echo $LIVEKIT_API_KEY
   echo $LIVEKIT_API_SECRET
   echo $LIVEKIT_URL
   ```

2. Test LiveKit credentials with CLI:
   ```bash
   lk room list --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
   ```

3. Check agent logs for connection errors:
   ```bash
   python basic-mindbot.py start --log-level DEBUG
   ```

#### Agent Disconnects Frequently
**Symptoms**: Agent joins but disconnects after short period
**Causes**:
- Network instability
- API rate limiting
- Resource constraints
- Memory leaks

**Solutions**:
1. Check system resources:
   ```bash
   htop  # Monitor CPU and memory usage
   ```

2. Monitor API usage in provider dashboards
3. Implement connection retry logic:
   ```python
   async def connect_with_retry(ctx: JobContext, max_retries=3):
       for attempt in range(max_retries):
           try:
               await ctx.connect()
               break
           except Exception as e:
               logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
               await asyncio.sleep(2 ** attempt)  # Exponential backoff
   ```

### Audio Processing Issues

#### Poor Speech Recognition
**Symptoms**: Agent doesn't respond to speech or responds incorrectly
**Causes**:
- VAD (Voice Activity Detection) sensitivity issues
- Deepgram API problems
- Network audio quality

**Solutions**:
1. Adjust VAD sensitivity:
   ```python
   vad=silero.VAD.load(
       min_speech_duration_ms=250,  # Reduce for faster detection
       min_silence_duration_ms=100   # Reduce for faster cutoff
   )
   ```

2. Test Deepgram connection:
   ```python
   # Add debugging to STT pipeline
   @session.stt.on("interim_transcript")
   def on_interim_transcript(transcript):
       logger.debug(f"Interim: {transcript.text}")
   ```

3. Monitor audio quality in logs

#### Agent Voice Output Issues
**Symptoms**: No audio output or poor quality TTS
**Causes**:
- OpenAI TTS API issues
- Audio codec problems
- Network bandwidth limitations

**Solutions**:
1. Test TTS directly:
   ```python
   from livekit.plugins import openai
   
   tts = openai.TTS(voice="fable")
   # Test TTS synthesis
   ```

2. Check OpenAI API status and usage
3. Monitor network bandwidth and latency

### API Issues

#### OpenAI Rate Limiting
**Symptoms**: Agent stops responding, rate limit errors in logs
**Solutions**:
1. Check OpenAI usage dashboard
2. Implement request queuing:
   ```python
   import asyncio
   from asyncio import Semaphore
   
   # Limit concurrent requests
   api_semaphore = Semaphore(5)
   
   async def call_openai_with_limit(prompt):
       async with api_semaphore:
           return await openai_client.chat.completions.create(...)
   ```

3. Upgrade to higher tier plan
4. Optimize prompt length and frequency

#### Deepgram API Errors
**Symptoms**: Speech recognition fails, transcription errors
**Solutions**:
1. Check Deepgram API status
2. Verify API key permissions
3. Test with different models:
   ```python
   stt=deepgram.STT(
       model="nova-3",      # Try different models
       language="en",       # Specify language
       smart_format=True,   # Enable smart formatting
       punctuate=True       # Enable punctuation
   )
   ```

### Performance Issues

#### High CPU Usage
**Symptoms**: System becomes slow during agent operation
**Causes**:
- Inefficient audio processing
- Too many concurrent operations
- Memory leaks

**Solutions**:
1. Monitor process CPU usage:
   ```bash
   top -p $(pgrep -f basic-mindbot)
   ```

2. Optimize audio buffer sizes:
   ```python
   # Adjust buffer sizes for performance
   AUDIO_BUFFER_SIZE = 1024  # Experiment with different sizes
   ```

3. Implement proper cleanup:
   ```python
   async def cleanup_session():
       """Clean up resources after session"""
       # Close connections, clear buffers, etc.
       logger.info("Session cleanup completed")
   
   ctx.add_shutdown_callback(cleanup_session)
   ```

#### Memory Leaks
**Symptoms**: Memory usage increases over time
**Solutions**:
1. Monitor memory usage:
   ```python
   import psutil
   import gc
   
   def log_memory_usage():
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024
       logger.info(f"Memory usage: {memory_mb:.2f} MB")
       
   # Call periodically
   ```

2. Force garbage collection:
   ```python
   import gc
   gc.collect()  # Force garbage collection
   ```

3. Use memory profiling tools:
   ```bash
   pip install memory-profiler
   python -m memory_profiler basic-mindbot.py
   ```

### Environment Issues

#### Environment Variables Not Loading
**Symptoms**: "API key not found" errors
**Solutions**:
1. Check `.env` file location and format:
   ```bash
   cat .env  # Verify file contents
   ls -la .env  # Check file permissions
   ```

2. Verify variable loading:
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   print(f"OpenAI Key loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
   ```

3. Restart service after environment changes

#### Port Conflicts
**Symptoms**: "Port already in use" errors
**Solutions**:
1. Kill existing processes:
   ```bash
   # Find processes using ports
   lsof -ti:8080 | xargs kill -9
   
   # Or use netstat
   netstat -tulpn | grep :8080
   ```

2. Use different ports in configuration

## Debugging Tools

### Python Logging
Enable detailed logging:
```python
import logging

# Set up comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mindbot.log'),
        logging.StreamHandler()
    ]
)

# Log agent events
logger = logging.getLogger("mindbot-agent")

@session.on("agent_speech_committed")
def on_speech_committed(msg):
    logger.info(f"Agent spoke: {msg.transcript}")

@session.on("user_speech_committed") 
def on_user_speech(msg):
    logger.info(f"User said: {msg.transcript}")
```

### LiveKit CLI Tools
Monitor rooms and participants:
```bash
# List active rooms
lk room list --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET

# Get room info
lk room info <room_name> --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET

# Create test room
lk room create test-room --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
```

### Performance Monitoring
```python
# performance_monitor.py
import time
import psutil
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        
        result = await func(*args, **kwargs)
        
        end_time = time.time()
        end_cpu = psutil.cpu_percent()
        
        logger.info(f"{func.__name__} took {end_time - start_time:.2f}s, CPU: {end_cpu - start_cpu:.1f}%")
        return result
    return wrapper

# Use decorator on critical functions
@monitor_performance
async def process_user_speech(audio_data):
    # Process speech
    pass
```

### Network Diagnostics
Test connectivity:
```bash
# Test WebSocket connection
wscat -c $LIVEKIT_URL

# Test UDP connectivity (for LiveKit)
nc -u -v <livekit_host> 7882

# Check DNS resolution
nslookup your-project.livekit.cloud

# Test HTTPS connectivity
curl -I https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Error Recovery Strategies

### Graceful Error Handling
```python
async def robust_agent_entrypoint(ctx: JobContext):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            await main_agent_logic(ctx)
            break  # Success, exit retry loop
            
        except ConnectionError as e:
            logger.warning(f"Connection error (attempt {retry_count + 1}): {e}")
            retry_count += 1
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Send error notification
            await notify_error(e)
            break
    
    if retry_count >= max_retries:
        logger.error("Max retries exceeded, agent shutting down")
```

### Health Monitoring
```python
# health_monitor.py
import asyncio
from datetime import datetime, timedelta

class HealthMonitor:
    def __init__(self):
        self.last_activity = datetime.now()
        self.error_count = 0
        self.max_errors = 10
    
    async def start_monitoring(self):
        """Start health monitoring loop"""
        while True:
            await self.check_health()
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def check_health(self):
        """Check agent health and restart if needed"""
        now = datetime.now()
        
        # Check for activity timeout
        if now - self.last_activity > timedelta(minutes=5):
            logger.warning("Agent inactive for 5+ minutes")
        
        # Check error count
        if self.error_count > self.max_errors:
            logger.error("Too many errors, requesting restart")
            # Implement restart logic
    
    def record_activity(self):
        """Record agent activity"""
        self.last_activity = datetime.now()
    
    def record_error(self):
        """Record an error"""
        self.error_count += 1
```

## Getting Help

### Community Resources
- [LiveKit Discord](https://discord.gg/livekit)
- [GitHub Discussions](https://github.com/livekit/livekit/discussions)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/livekit)

### Documentation
- [LiveKit Docs](https://docs.livekit.io)
- [Agents Framework Guide](https://docs.livekit.io/agents)
- [API Reference](https://docs.livekit.io/home/server/managing-rooms/)

### Debugging Checklist
When reporting issues, include:
- [ ] Agent logs with DEBUG level enabled
- [ ] Environment variable configuration (without secrets)
- [ ] Network connectivity test results
- [ ] API provider status check
- [ ] System resource usage information
- [ ] Steps to reproduce the issue
- [ ] Expected vs actual behavior