from mangum import Mangum

from .http import app  # your FastAPI app is defined here

# AWS Lambda entrypoint
lambda_handler = Mangum(app)
