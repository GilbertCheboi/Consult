# views.py

import logging
from django.shortcuts import render, redirect
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import AccessToken

logger = logging.getLogger('console_logger')

def calendly_auth(request):
    print('hello')
    params = {
        'response_type': 'code',
        'client_id': settings.CALENDLY_CLIENT_ID,
        'redirect_uri': settings.CALENDLY_REDIRECT_URI,
    }
    auth_url = f'https://auth.calendly.com/oauth/authorize?{"&".join(f"{key}={value}" for key, value in params.items())}'
    print(params)
    return redirect(auth_url)


def calendly_callback(request):
    full_path = request.get_full_path()
    print(full_path)
    code = request.GET.get('code')
    print(code)
    if code:
        params = {
            'grant_type': 'authorization_code',
            'client_id': settings.CALENDLY_CLIENT_ID,
            'client_secret': settings.CALENDLY_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.CALENDLY_REDIRECT_URI,
        }
        response = requests.post('https://auth.calendly.com/oauth/token', data=params)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            # Save the access token to the user or session for future API calls
            # Redirect the user to the success page or render a template with success message
            return redirect('calendly:get_user_events')  # Replace with your success view name
        else:
            # Handle the error case, redirect to an error view or render a template with error message
            return redirect('calendly:error_view')  # Replace with your error view name
    else:
        # Handle the case where 'code' parameter is missing in the request
        # Redirect to an error view or render a template with error message
        return redirect('calendly:success_view')  # Replace with your error view name


@login_required
def get_user_events(request):
    # Get the user's access token from the session or wherever you stored it
    user = request.user
    try:
        access_token = AccessToken.objects.get(user=user).token
    except AccessToken.DoesNotExist:
        # If the access token doesn't exist, obtain it from Calendly OAuth flow
        access_token = ...
        AccessToken.objects.create(user=user, token=access_token)

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get('https://api.calendly.com/scheduled_events', headers=headers)

    if response.status_code == 200:
        data = response.json()
        events = data.get('data', [])
        # Process the events data as per your requirements
        logger.debug(events)
        return render(request, 'helpline/home_dashboard.html', {'events': events})
    else:
        # Handle the error case
        return redirect('calendly:error_view')

def error_view(request):
    return render(request, 'error.html')


def success_view(request):
    return render(request, 'success.html')
