from django.utils import translation
from rest_framework.fields import ImageField as DRFImageField, FileField as DRFFileField


def _force_https(url):
    """Convert any http:// URL to https://."""
    if url and isinstance(url, str) and url.startswith('http://'):
        return 'https://' + url[7:]
    return url


# ── Globally patch DRF ImageField & FileField to always return https:// ──────
_original_image_to_representation = DRFImageField.to_representation
_original_file_to_representation = DRFFileField.to_representation


def _https_image_to_representation(self, value):
    return _force_https(_original_image_to_representation(self, value))


def _https_file_to_representation(self, value):
    return _force_https(_original_file_to_representation(self, value))


DRFImageField.to_representation = _https_image_to_representation
DRFFileField.to_representation = _https_file_to_representation
# ─────────────────────────────────────────────────────────────────────────────


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
    Works with both ASGI (Uvicorn) and WSGI (Gunicorn).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ASGI: set scope scheme (ASGIRequest.scheme reads from scope)
        if hasattr(request, 'scope'):
            request.scope['scheme'] = 'https'

        # WSGI: set environ scheme
        if hasattr(request, 'environ'):
            request.environ['wsgi.url_scheme'] = 'https'
            request.environ['HTTP_X_FORWARDED_PROTO'] = 'https'

        # Force is_secure() — scheme is already handled via scope/environ above
        request.is_secure = lambda: True

        # Patch build_absolute_uri as a final safety net
        original_build_absolute_uri = request.build_absolute_uri

        def forced_build_absolute_uri(location=None):
            return _force_https(original_build_absolute_uri(location))

        request.build_absolute_uri = forced_build_absolute_uri

        response = self.get_response(request)
        return response
