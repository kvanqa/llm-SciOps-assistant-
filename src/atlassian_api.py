import base64
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MEERKAT_DOMAIN = "https://id.atlassian.com/"  # This is your Cloud ID
USER_EMAIL = "kvanqa@sarao.ac.za"

API_TOKEN = "ATATT3xFfGF0mRfoNUgEFQD9QgZeTShaquV6EHfOaXnHnT4QATlj95ZhcPLHp1fnte_DuNQ2FHFMjhvMWHY9fxpmIFOJQgzxd64k16AJPOtsh-qBTj8q4W2-TV9ioVj5yuZwUvJje9RigXWSj2vK18D6-ntaRfFctAyhRBUXyYZT4WIsuH18xh0=E7F02BCD"