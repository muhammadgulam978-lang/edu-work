from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def remember_authorization(sender, request, user, **kwargs):
    from .identity import authorization_fingerprint
    request.session['authorization_fingerprint'] = authorization_fingerprint(user)
