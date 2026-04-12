import httpx
import asyncio

async def main():
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.get("https://github.com/YagnaSuthar/EduTrack/graphs/contributors-data", headers=headers)
        print("Status:", r.status_code)
        try:
            print("Output:", r.json())
        except:
            print("Output:", r.text[:200])

asyncio.run(main())
