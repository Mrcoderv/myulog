from mangum import Mangum

from .http import app

# API Gateway/Lambda entrypoint
lambda_handler = Mangum(app)
