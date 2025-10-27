# Thin shim so the Lambda entrypoint can be referenced exactly as required by the AC.
# Keep your packaging script unchanged; this module simply re-exports the handler.

from ..handler import lambda_handler  # noqa: F401
