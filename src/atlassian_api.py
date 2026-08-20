import base64
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MEERKAT_DOMAIN = "https://id.atlassian.com/"  # This is your Cloud ID
USER_EMAIL = "kvanqa@sarao.ac.za"
API_TOKEN = "ATATT3xFfGF09_PQV8ukqRLFiYGf1W9C0wkVJMsAZ4665gLHK5l5a36E7IkIZfYGSLAEDVYGt2VEpmQbX1I1hF99Eb_BViMP0Xbk-PIv_cu0E1HtGYCP4R4SQNfBnI7gwLKtQsFD6jKDMuMTeLygHPUseM9_64soLElFdavAOKA-Z2O3rpxIrH0=2C7B5F2A"