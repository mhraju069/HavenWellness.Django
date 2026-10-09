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
