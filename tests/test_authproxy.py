import urllib.request

import asyncio
import pytest

from authproxy import AuthProxy
from aproxy import HTTPProxyProtocol

@pytest.fixture
def localip():
    with urllib.request.urlopen('https://diagnostic.opendns.com/myip') as resp:
        return resp.read().decode()

@pytest.mark.parameterize('protocol',["http", "https"])
def test_authproxy(localip, proxy_opener, protocol):
    with AuthProxy('localhost', 8080, '', '') as proxy:
        loop = asyncio.get_event_loop()
        parent_server = loop.create_server(HTTPProxyProtocol, 'localhost', 8080)
        server = loop.run_until_complete(parent_server)
        async with aio.http.ClientSession() as session:
            async with session.get('%s://diagnostic.opendns.com/myip' % protocol,
                                   proxy = 'http://localhost:8888') as resp:
            assert localip == resp.text()

