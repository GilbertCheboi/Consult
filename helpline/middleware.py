class SetRemoteAddrMiddleware:
    """Set REMOTE_ADDR based on the HTTP_X_REAL_IP
    When ehind a proxy and trust the HTTP_X_REAL_IP Header"""
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        try:
            request.META['REMOTE_ADDR'] = request.META['HTTP_X_REAL_IP']
        except KeyError:
            # You could place a valid IP in REMOTE_ADDR
            # request.META['REMOTE_ADDR'] = '127.0.0.1'
            pass

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
