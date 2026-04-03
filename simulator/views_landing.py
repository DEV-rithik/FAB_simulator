"""Landing page view — public, no auth required."""

from django.shortcuts import render


def landing(request):
    """Render the public landing page.

    The template decides where the CTA button points based on
    {{ user.is_authenticated }}, which Django injects automatically via the
    'django.contrib.auth.context_processors.auth' context processor.
    """
    return render(request, 'landing.html')
