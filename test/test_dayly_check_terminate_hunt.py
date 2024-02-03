import asyncio
from historic.main import dayly_check_terminate_hunt

async def test_dayly_check_terminate_hunt():
    await dayly_check_terminate_hunt()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_dayly_check_terminate_hunt())