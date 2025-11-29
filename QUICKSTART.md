# Quick Start Guide

## Fastest Way to Run the Demo

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up database
python database_setup.py
# When prompted, enter 'y' to insert sample data

# 4. Run the demo
# Option A: Use the convenience script (recommended)
python run_demo.py

# Option B: Run directly from project root
python demo/main.py
```

That's it! The demo will show all test scenarios with full A2A communication logs.

## Verification

Before running the demo, you can verify everything is set up correctly:

```bash
python verify_setup.py
```

## What You'll See

The demo runs through:

1. **Part 1: Assignment Required Scenarios**
   - Scenario 1: Task Allocation
   - Scenario 2: Negotiation/Escalation
   - Scenario 3: Multi-Step Coordination

2. **Part 2: Test Scenarios**
   - Simple Query
   - Coordinated Query
   - Complex Query
   - Escalation
   - Multi-Intent

Each scenario shows:
- Detected scenario and intents
- Agent-to-agent communication logs
- A2A messages
- Final response

## Next Steps

- Read `README.md` for detailed documentation
- Explore the code in the `agents/` directory
- Try modifying queries in `demo/main.py`

