# Troubleshooting Guide

## Common Issues and Solutions

### Agent Connection Issues

#### Agent Not Joining Room
**Symptoms**: Frontend shows "connecting" but agent never appears
**Causes**:
- Incorrect LiveKit credentials
- Agent not running
- Network connectivity issues

**Solutions**:
1. Verify environment variables in backend `.env`
2. Check agent logs for connection errors
3. Test LiveKit credentials with CLI:
   ```bash
   lk room list --url $LIVEKIT_URL --api-key $LIVEKIT_API_KEY --api-secret $LIVEKIT_API_SECRET
   ```

#### Agent Disconnects Frequently
**Symptoms**: Agent joins but disconnects after short period
**Causes**:
- Network instability
- API rate limiting
- Resource constraints

**Solutions**:
1. Check system resources (CPU, memory)
2. Monitor API usage in provider dashboards
3. Implement exponential backoff for reconnections

### Audio Issues

#### No Audio Input
**Symptoms**: User can hear agent but agent doesn't respond to speech
**Causes**:
- Microphone permissions denied
- Incorrect audio device selection
- VAD (Voice Activity Detection) issues

**Solutions**:
1. Check browser microphone permissions
2. Test with different browsers (Chrome recommended)
3. Verify VAD sensitivity settings:
   ```python
   vad=silero.VAD.load(
       min_speech_duration_ms=250,
       min_silence_duration_ms=100
   )
   ```

#### Poor Audio Quality
**Symptoms**: Choppy or distorted audio
**Causes**:
- Network bandwidth limitations
- Audio codec issues
- System audio driver problems

**Solutions**:
1. Test network speed and stability
2. Check system audio settings
3. Monitor WebRTC stats in browser dev tools

#### Echo or Feedback
**Symptoms**: Agent hears its own voice
**Causes**:
- Acoustic echo not properly cancelled
- Speaker/microphone positioning

**Solutions**:
1. Use headphones during testing
2. Enable echo cancellation:
   ```python
   room_input_options=RoomInputOptions(
       noise_cancellation=noise_cancellation.BVC()
   )
   ```

### API Issues

#### OpenAI Rate Limiting
**Symptoms**: Agent stops responding, rate limit errors in logs
**Solutions**:
1. Check OpenAI usage dashboard
2. Implement request queuing
3. Upgrade to higher tier plan
4. Optimize prompt length and frequency

#### Deepgram Transcription Errors
**Symptoms**: Poor speech recognition accuracy
**Solutions**:
1. Check audio quality reaching Deepgram
2. Adjust model settings:
   ```python
   stt=deepgram.STT(
       model="nova-3",
       language="en",
       smart_format=True,
       punctuate=True
   )
   ```
3. Test with different microphones

### Frontend Issues

#### Connection Timeout
**Symptoms**: Frontend can't connect to LiveKit server
**Causes**:
- Incorrect server URL
- Network firewall blocking WebRTC
- CORS configuration issues

**Solutions**:
1. Verify LIVEKIT_URL format (must include wss://)
2. Test connection from different networks
3. Check browser network tab for failed requests

#### Transcription Not Displaying
**Symptoms**: Audio works but no text appears
**Causes**:
- Transcription not enabled
- React state management issues

**Solutions**:
1. Verify transcription is enabled:
   ```typescript
   room_output_options=RoomOutputOptions(
       transcription_enabled=True
   )
   ```
2. Check browser console for React errors

### Performance Issues

#### High CPU Usage
**Symptoms**: System becomes slow during agent operation
**Causes**:
- Inefficient audio processing
- Too many concurrent operations
- Memory leaks

**Solutions**:
1. Monitor process CPU usage
2. Implement proper cleanup in agent shutdown
3. Optimize audio buffer sizes

#### Memory Leaks
**Symptoms**: Memory usage increases over time
**Solutions**:
1. Implement proper cleanup:
   ```python
   ctx.add_shutdown_callback(log_usage)
   ```
2. Monitor memory usage patterns
3. Use memory profiling tools

### Development Environment Issues

#### Environment Variables Not Loading
**Symptoms**: "API key not found" errors
**Solutions**:
1. Check `.env` file location and format
2. Restart development server after changes
3. Verify variable names match exactly

#### Port Conflicts
**Symptoms**: "Port already in use" errors
**Solutions**:
1. Kill existing processes:
   ```bash
   lsof -ti:3000 | xargs kill -9  # Frontend
   lsof -ti:8080 | xargs kill -9  # Agent
   ```
2. Use different ports in configuration

## Debugging Tools

### Browser Developer Tools
- **Network Tab**: Monitor WebRTC connections
- **Console Tab**: Check for JavaScript errors
- **Application Tab**: Verify local storage and cookies

### Python Logging
Enable detailed logging in agent:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("basic-agent")
```

### LiveKit CLI Tools
Monitor rooms and participants:
```bash
# List active rooms
lk room list

# Get room info
lk room info <room_name>

# Monitor participant events
lk room join <room_name> --identity observer
```

### Network Diagnostics
Test WebRTC connectivity:
```bash
# Check UDP port accessibility
nc -u -v <livekit_host> 7882

# Test WebSocket connection
wscat -c wss://your-project.livekit.cloud
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

### Support Channels
- Community support via Discord/GitHub
- Enterprise support for LiveKit Cloud customers
- Professional services available