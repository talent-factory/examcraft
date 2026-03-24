"""
List all registered API routes in the FastAPI app
"""

import asyncio
from main import app


async def list_routes():
    """List all routes after lifespan startup"""
    async with app.router.lifespan_context(app):
        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                methods = ", ".join(sorted(route.methods))
                routes.append(f"{methods:20} {route.path}")

        print("\n=== Registered API Routes ===\n")
        for route in sorted(routes):
            print(route)
        print(f"\nTotal routes: {len(routes)}")


if __name__ == "__main__":
    asyncio.run(list_routes())
