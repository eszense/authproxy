import urllib.request
import asyncio

import pytest
import aiohttp

from authproxy import AuthProxy
from aproxy import HTTPProxyProtocol


@pytest.fixture
def localip():
    with urllib.request.urlopen('https://diagnostic.opendns.com/myip') as resp:
        return resp.read().decode()

@pytest.mark.parametrize('protocol',["http", "https"])
def test_authproxy(localip, protocol):

    async def test_authproxy_async(localip, protocol):
        async with aiohttp.ClientSession() as session:
            async with session.get('%s://diagnostic.opendns.com/myip' % protocol,
                                   proxy = 'http://localhost:8888') as resp:
                assert localip == await resp.text()

    with AuthProxy('localhost', 8080, '', '') as proxy:

        loop = asyncio.get_event_loop()
        parent_server = loop.create_server(HTTPProxyProtocol, 'localhost', 8080)
        server = loop.run_until_complete(parent_server)
        loop.run_until_complete(test_authproxy_async(localip, protocol))
        server.close()

