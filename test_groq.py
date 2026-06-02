import asyncio
import logging
from app.config import get_settings
from app.decision.engine import _call_groq, _call_groq_stream

logging.basicConfig(level=logging.INFO)

async def test_groq():
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY is not set in the environment or .env file.")
        print("Please add 'GROQ_API_KEY=gsk_...' to your .env file to run this test.")
        return
        
    print(f"[OK] Found GROQ_API_KEY in configuration. Model: {settings.GROQ_MODEL}")
    prompt = "Hello Llama 3.1! Respond with a single short sentence confirming you are running via Groq."
    
    print("\n--- Testing Non-Streaming Call ---")
    try:
        response = await _call_groq(prompt)
        print("Groq Response:")
        print(response)
    except Exception as e:
        print(f"Exception during non-streaming call: {e}")
        
    print("\n--- Testing Streaming Call ---")
    try:
        print("Groq Stream Output: ", end="", flush=True)
        async for token in _call_groq_stream(prompt):
            print(token, end="", flush=True)
        print()
    except Exception as e:
        print(f"\nException during streaming call: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq())
