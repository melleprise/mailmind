import asyncio
from aioimaplib import aioimaplib
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test():
    client = aioimaplib.IMAP4_SSL('imap.gmail.com', timeout=30)
    logger.debug("Connecting to IMAP server...")
    await client.wait_hello_from_server()
    logger.debug("Connected, attempting login...")
    await client.login('fwylapi@gmail.com', 'ifkmdinmknpfvexn')
    logger.debug("Login successful, selecting INBOX...")
    await client.select('INBOX')
    logger.debug("INBOX selected, searching...")
    await client.search('ALL')
    logger.debug("Search completed")
    await client.logout()

if __name__ == "__main__":
    asyncio.run(test()) 