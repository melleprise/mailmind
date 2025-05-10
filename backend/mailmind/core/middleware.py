import logging

logger = logging.getLogger(__name__) # Or use 'mailmind.middleware' etc.

class LogHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log headers before the view is called
        auth_header = request.META.get('HTTP_AUTHORIZATION', 'Not Present')
        # Avoid logging sensitive headers like Cookie if not needed
        # You can customize which headers to log
        logger.debug(f"Request Path: {request.path}, Method: {request.method}, Authorization Header: {auth_header}")
        # logger.debug(f"All Request META: {request.META}") # Uncomment for more detail, potentially noisy

        response = self.get_response(request)

        # Optionally log something about the response too
        return response 