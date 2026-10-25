"""A normal img request must not poison the later CORS WebGL texture cache."""
import asyncio
from pathlib import Path
import sys
import unittest
from starlette.requests import Request
from starlette.responses import Response
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app import preserve_asset_cors_variant


class AssetCacheTests(unittest.TestCase):
    def test_static_asset_always_varies_on_origin_even_for_plain_image_request(self):
        async def check():
            async def next_handler(request):return Response(b'image',headers={'Vary':'Accept-Encoding'})
            request=Request({'type':'http','path':'/examples/new/generated.png','headers':[]})
            response=await preserve_asset_cors_variant(request,next_handler)
            vary={x.strip().lower() for x in response.headers['vary'].split(',')}
            self.assertEqual(vary,{'origin','accept-encoding'})
            self.assertNotIn('access-control-allow-origin',response.headers)
        asyncio.run(check())
