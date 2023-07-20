from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
import requests
import time
import datetime

from helpline.models import Hotdesk, Clock, IpAddress


def get_ip_address(request):
    request_headers = request.headers
    real_ip = request_headers.get("X-Real-Ip")
    user_ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
    if user_ip_address:
        ip = user_ip_address.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    ip = real_ip if real_ip else ip
    return ip


@receiver(user_logged_in)
def sig_user_logged_in(sender, user, request, **kwargs):
    """User logged in signal, add event to agent_session report
    Send the loggin details to external flow server for user creation
    """
    hot_desk = Hotdesk.objects.filter(
        user=user,
        status="Available",
        secret__isnull=False
    ).first()

    user_level = "Supervisor" if user.is_staff else "Agent"
    username = user.username
    t = time.localtime()
    current_time = time.strftime('%Y-%m-%d %H:%M:%S', t)
    real_ip =  get_ip_address(request)

    subject = "New Login on your Call Center Africa Account %s" % (user.username)
    user_agent = request.META['HTTP_USER_AGENT']

    description = f"""
    Dear {username},

    This email was generated because a new log-in has occurred for the account {username} on {current_time} originating from:

        IP: {real_ip}
        User-Agent: {user_agent}

    If you initiated this log-in, awesome! We just wanted to make sure it’s you.
    If you did NOT initiate this log-in, you should immediately change your password to ensure account security.

    Thanks,
    Call Center Africa Support Team
    """

    send_mail(
        subject,
        description,
        'security@zerxis.co.ke',
        [user.email],
        fail_silently=True,
    )

    try:
        ip_address = IpAddress.objects.get(ip_address=real_ip)
    except IpAddress.DoesNotExist:
        ip_address = IpAddress(
            user=user,
            ip_address=real_ip,
            pub_date=datetime.datetime.now(),
            user_data=user_agent,
        )
        ip_address.save()

    clock = Clock()
    clock.user = user
    clock.ip_address = ip_address
    clock.hl_clock = "Login"
    clock.hl_time = int(time.time())
    clock.save()


@receiver(user_logged_out)
def sig_user_logged_out(sender, user, request, **kwargs):
    """User logged out signal adds event to AgentSession
    Alert external system on event
    """
    if user:
        clock = Clock()
        clock.user = user
        clock.hl_clock = "Logout"
        clock.hl_time = int(time.time())
        clock.save()
        hot_desk = Hotdesk.objects.filter(
            user=user,
            status="Available",
            secret__isnull=False
        ).first()

        user_level = "Supervisor" if user.is_superuser else "Agent"

        data = {
            "username": user.username,
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": "%s %s" % (user.first_name, user.last_name),
            "extension": hot_desk,
            "user_level": user_level,
            "action": "logout",
            "api_key": "CHANGE_ME_SOMETIME!!",
            "ts": time.time()
        }
