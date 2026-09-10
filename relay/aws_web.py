"""Lambda Function URL adapter; existing FastAPI routes retain cookie isolation."""

from mangum import Mangum

from .app import app

handler = Mangum(app, lifespan="off")
