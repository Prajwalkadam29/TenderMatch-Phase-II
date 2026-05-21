import asyncio
import httpx
async def t():
    async with httpx.AsyncClient() as client:
        login_data = {"username": "eval@tendermatch-research.internal", "password": "EvalSecure2026!"}
        res = await client.post("http://localhost:8000/auth/token", data=login_data)
        print(res.status_code, res.text)
asyncio.run(t())
