from django.utils import translation

class LanguageMiddleware:
    """
    Middleware to dynamically activate language preference (en, nl, de)
    based on query parameter (?lang=nl/de/en) or Accept-Language / lang request headers.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.GET.get('lang') or request.headers.get('Accept-Language') or request.headers.get('lang')
        if lang:
            lang = str(lang).lower().strip()
            if 'nl' in lang:
                translation.activate('nl')
                request.LANGUAGE_CODE = 'nl'
            elif 'de' in lang:
                translation.activate('de')
                request.LANGUAGE_CODE = 'de'
            else:
                translation.activate('en')
                request.LANGUAGE_CODE = 'en'
        else:
            translation.activate('en')
            request.LANGUAGE_CODE = 'en'

        response = self.get_response(request)
        return response


class ForceHttpsMiddleware:
    """
    Middleware to force request scheme to HTTPS so that all serializer
    file/image fields and build_absolute_uri calls always generate https:// URLs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Support both ASGI (Uvicorn/Daphne) and WSGI (Gunicorn)
        if hasattr(request, 'scope'):
            request.scope['scheme'] = 'https'
        if hasattr(request, 'environ'):
            request.environ['wsgi.url_scheme'] = 'https'
            request.environ['HTTP_X_FORWARDED_PROTO'] = 'https'

        # Force request.scheme and request.is_secure()
        request.scheme = 'https'
        request.is_secure = lambda: True

        # Monkey-patch build_absolute_uri for this request to always enforce https
        original_build_absolute_uri = request.build_absolute_uri

        def forced_build_absolute_uri(location=None):
            uri = original_build_absolute_uri(location)
            if uri and uri.startswith('http://'):
                uri = 'https://' + uri[7:]
            return uri

        request.build_absolute_uri = forced_build_absolute_uri

        response = self.get_response(request)
        return response

