#!/usr/bin/env python3
""""Test the DeepSeek Gateway with a given API key."""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI


def test_gateway(api_key: str, base_url: str = "http://127.0.0.1:8000/v1"):
    client = OpenAI(api_key=api_key, base_url=base_url)

    print("=" * 50)
    print("1. Test /v1/models")
    print("=" * 50)
    try:
        models = client.models.list()
        for m in models.data:
            print(f"  - {m.id}")
    except Exception as e:
        print(f"  FAIL: {e}")

    print()
    print("=" * 50)
    print("2. Test /v1/chat/completions (non-streaming)")
    print("=" * 50)
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Say hello in one short sentence."}],
        )
        print(f"  Reply: {response.choices[0].message.content}")
        print(f"  Model: {response.model}")
        if hasattr(response, 'usage'):
            print(f"  Tokens: {response.usage}")
    except Exception as e:
        print(f"  FAIL: {e}")

    print()
    print("=" * 50)
    print("3. Test streaming")
    print("=" * 50)
    try:
        stream = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "Count from 1 to 5."}],
            stream=True,
        )
        print("  Stream: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
    except Exception as e:
        print(f"  FAIL: {e}")

    print()
    print("All tests done!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <API_KEY>")
        print("Example: python test_client.py sk-gateway-xxxx")
        sys.exit(1)

    test_gateway(sys.argv[1])