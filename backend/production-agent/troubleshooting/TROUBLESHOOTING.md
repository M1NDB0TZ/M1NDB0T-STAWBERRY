# MindBot Troubleshooting Guide

This guide provides instructions on how to use the debugging and testing tools for the MindBot agent.

## 1. Debug Mode

The MindBot agent has a debug mode that can be enabled to provide more verbose logging and access to the agent's internal state.

### 1.1. Enabling Debug Mode

To enable debug mode, set the `DEBUG_MODE` environment variable to `true` in your `.env` file:

```
DEBUG_MODE=true
```

### 1.2. Accessing Agent State

When debug mode is enabled, you can use the `get_agent_state` function tool to get a snapshot of the agent's current state. This can be useful for debugging issues with user context, session information, or configuration.

**Example Usage:**

```
get_agent_state()
```

## 2. Health Checks

The `health_check.py` script can be used to verify connectivity to all external services (Supabase, Stripe, LiveKit, etc.).

### 2.1. Running Health Checks

To run the health checks, execute the following command from the `backend/production-agent` directory:

```
python -m troubleshooting.health_check
```

The script will output a status report indicating whether each service is healthy.

## 3. Agent Testing

The `test_agent.py` script can be used to run a simulated session with the `ProductionMindBotAgent`. This allows for testing the agent's core functionalities in an isolated environment.

### 3.1. Running the Agent Test

To run the agent test, execute the following command from the `backend/production-agent` directory:

```
python -m troubleshooting.test_agent
```

The script will simulate a user interaction with the agent and report on the success or failure of the test.
