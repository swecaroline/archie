from aiohttp import web

async def handle_health(request):
    return web.Response(text="Archie is OK")

async def setup_hook():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = 8080
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server running internally on port {port}")