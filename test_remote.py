import httpx
import json

async def check_schema():
    base_url = "https://mujeebsystem.duckdns.org"
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{base_url}/openapi.json")
        if r.status_code == 200:
            openapi = r.json()
            schemas = openapi.get("components", {}).get("schemas", {})
            tts_request = schemas.get("TTSRequest", {})
            print(f"TTSRequest schema properties: {json.dumps(tts_request, indent=2)}")
        else:
            print(f"Failed to get openapi.json: {r.status_code}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_schema())
