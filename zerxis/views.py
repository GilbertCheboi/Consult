"""Social media managemnt app for MyHelpline"""
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import Http404
from django.shortcuts import render
from django.template.context_processors import csrf
from django.template.loader import render_to_string

from allauth.socialaccount.models import SocialToken, SocialAccount,\
        SocialApp

from bleach.linkifier import Linker

from crispy_forms.utils import render_crispy_form

from jsonview.decorators import json_view

from six.moves.urllib.parse import urlparse

import tweepy

from zerxis.forms import UpdateForm


@login_required
def social_dashboard(request):
    """Social media dashboard"""
    return render(
        request, 'zerxis/dashboard.html',
        {}
    )


@login_required
def twitter_home(request, uid=None):
    """Home view, displays login mechanism"""
    update_form = UpdateForm()
    return render(
        request, 'zerxis/twitter_home.html',
        {"uid": uid,
         "update_form": update_form}
    )


@login_required
def facebook_home(request):
    """Home view, displays login mechanism"""
    return render(
        request, 'zerxis/facebook_home.html',
        {}
    )


@login_required
@json_view
def twitter_home_timeline(request, uid=None):
    """Return home timeline without base tempplate"""
    data = {}
    api = get_api(request, uid=uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    try:
        home_timeline = api.home_timeline(tweet_mode='extended')
        linkify_twitter_statuses(home_timeline, uid)
        data['timeline'] = home_timeline
        data['timeline_title'] = "Home"
        data['uid'] = uid
        timeline_html = render_to_string(
            'zerxis/twitter_timeline.html',
            data, request
        )
    except tweepy.RateLimitError:
        timeline_html = "Rate limit"

    return {'timeline_html': timeline_html}


@json_view
@login_required
def twitter_mentions_timeline(request, uid=None):
    """Return home timeline without base tempplate"""
    data = {}
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    try:
        mentions_timeline = api.mentions_timeline(tweet_mode='extended')
        linkify_twitter_statuses(mentions_timeline, uid)
        data['timeline'] = mentions_timeline
        data['uid'] = uid
        data['timeline_title'] = "Mentions"
        timeline_html = render_to_string(
            'zerxis/twitter_timeline.html',
            data, request
        )
    except tweepy.RateLimitError:
       timeline_html = "Rate Limit"

    return {'timeline_html': timeline_html}


@login_required
@json_view
def twitter_user_timeline(request, uid=None):
    """Return home timeline without base tempplate"""
    data = {}
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    try:
        user_timeline = api.user_timeline(tweet_mode='extended')
        linkify_twitter_statuses(user_timeline, uid)
        data['timeline'] = user_timeline
        data['timeline_title'] = "User"
        data['uid'] = uid
        timeline_html = render_to_string(
            'zerxis/twitter_timeline.html',
            data, request
        )
    except tweepy.RateLimitError:
        timeline_html = "Rate Limit"

    return {'timeline_html': timeline_html}


@login_required
@json_view
def twitter_user_friends(request, user_name=None, uid=None):
    """Return list of twitter following given a screen_name"""
    data = {}
    api = get_api(request, uid)
    if not api:
        return {'twitter_users_html': 'Connect a twitter account..'}
    try:
        twitter_friends_list = api.friends(screen_name=user_name)
        linkify_twitter_profiles(twitter_friends_list, uid)
        data['twitter_users'] = twitter_friends_list
        data['uid'] = uid
        twitter_users_html = render_to_string(
            'zerxis/twitter_userlist.html',
            data, request
        )
    except tweepy.RateLimitError:
        twitter_users_html = "Rate Limit"

    return {'twitter_users_html': twitter_users_html}



@login_required
@json_view
def twitter_user_followers(request, user_name=None, uid=None):
    """Return list of twitter followers given a screen_name"""
    data = {}
    api = get_api(request, uid)
    if not api:
        return {'twitter_users_html': 'Connect a twitter account..'}
    try:
        twitter_followers_list = api.followers(screen_name=user_name)
        linkify_twitter_profiles(twitter_followers_list, uid)
        data['twitter_users'] = twitter_followers_list
        data['uid'] = uid
        twitter_users_html = render_to_string(
            'zerxis/twitter_userlist.html',
            data, request
        )
    except tweepy.RateLimitError:
        twitter_users_html = "Rate Limit"

    return {'twitter_users_html': twitter_users_html}



@login_required
def done(request):
    """Login complete view, displays user data"""
    ctx = {
        'version': 'VERSION',
        'last_login': request.session.get('social_auth_last_login_backend')
    }
    return render(request,
                  'zerxis/home.html', ctx)


def error(request):
    """Error view"""
    return render(request,
                  'bs/zerxis/error.html', {'version': 'VERSION'})


def logout(request):
    """Logs out user"""
    pass


def login(request):
    """Login a user through a social account"""
    pass


def search(request, uid=None):
    query = request.GET.get('q')
    if not query:
        raise Http404(_("Search term not found"))

    """Get user twitter stream"""
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    statuses = api.search(q=query, tweet_mode='extended')
    linkify_twitter_statuses(statuses, uid)

    return render(request,
                  'zerxis/twitter_search_results.html', {
                      'title': 'Twitter Search | %s' % (query),
                      'truncate': True,
                      'query': query,
                      'twitter_user': query,
                      'statuses': statuses,
                      'uid': uid,
                  })


def form(request):
    if request.method == 'POST' and request.POST.get('username'):
        pass
    return render(request,
        'bs/zerxis/form.html', {})


def form2(request):
    if request.method == 'POST' and request.POST.get('first_name'):
        pass
    return render(request, 'bs/zerxis/form2.html', {})


def set_target(attrs, new=False):
    """Set link target to _blank if not current site"""
    site = Site.objects.get_current()
    current_site_domain = site.domain
    p = urlparse(attrs[(None, 'href')])
    if p.netloc not in ['callcenter.africa', current_site_domain]:
        attrs[(None, 'target')] = '_blank'
        attrs[(None, 'class')] = 'external'
    else:
        attrs.pop((None, 'target'), None)
    return attrs


def linkify_twitter_statuses(statuses, uid=None):
    """Use custom links for twitter profiles"""
    for status in statuses:
        tweet = status.full_text
        for url in status.entities['urls']:
            tweet = tweet.replace(url['url'], url['expanded_url'])
        linker = Linker(callbacks=[set_target])
        tweet = linker.linkify(tweet)

        tweet = re.sub(
            r'(\.|\A|\s)@(\w+)',
            r'\1<a href="/helpline/social/twitter/user/\2/{}/">@\2</a>'.format(uid),
            tweet
        )
        status.full_text = re.sub(
            r'(\A|\s)#(\w+)',
            r'\1<a href="/helpline/social/twitter/search/{}/?q=%23\2">#\2</a>'.format(uid),
            tweet
        )
    return statuses



def linkify_twitter_profiles(twitter_profiles, uid=None):
    """Use custom links for twitter profiles"""
    for profile in twitter_profiles:
        description = profile.description
        description = re.sub(
            r'(\.|\A|\s)@(\w+)',
            r'\1<a href="/helpline/social/twitter/user/\2/{}/">@\2</a>'.format(uid),
           description
        )
        profile.description = re.sub(
            r'(\A|\s)#(\w+)',
            r'\1<a href="/helpline/social/twitter/search/{}/?q=%23\2">#\2</a>'.format(uid),
           description
        )
    return twitter_profiles


@login_required
def twitter_user_stream(request, user_name=None, uid=None):
    """Get user twitter stream"""
    if not user_name:
        raise Http404(_("Username not found"))

    update_form = UpdateForm()
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    twitter_user = api.get_user(user_name)
    statuses = api.user_timeline(id=user_name, tweet_mode='extended')
    linkify_twitter_statuses(statuses, uid)

    return render(request,
                  'zerxis/twitter_userstream.html', {
                      'title': 'Twitter',
                      'truncate': True,
                      'text': user_name,
                      'twitter_user': twitter_user,
                      'update_form': update_form,
                      'statuses': statuses,
                      'uid': uid,
                  })


@login_required
def user_directs(request, uid):
    form = UpdateForm()
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}
    statuses = api.list_direct_messages()

    return render(request,
        'zerxis/twitter_dms.html', {
            'title': 'Zerxis - Directs',
            'statuses': statuses,
            'form': form,
            'uid':uid
        },)


@login_required
def user_mentions(request, uid):
    form = UpdateForm()
    api = get_api(request, uid)
    if not api:
        return {'timeline_html': 'Connect a twitter account..'}

    statuses = api.mentions_timeline()
    linkify_twitter_statuses(statuses, uid)
    return render(request,
                  'zerxis/twitter_mentions.html',
                  {
                      'title': 'Zerxis - Mentions',
                      'statuses': statuses,
                      'form': form,
                      'uid': uid
                  })


def get_api(request=None, uid=None):
    """Get twitter API credentials"""

    social_app = SocialApp.objects.get(id=1)

    try:
        social_account = SocialAccount.objects.get(uid=uid)
        # TODO Security, maek sure that the user is allowed to access this account
    except SocialAccount.DoesNotExist:
        raise Http404("Social account not found %s" % (uid))
    try:
        social_token = SocialToken.objects.get(account=social_account)
    except SocialToken.DoesNotExist:
        raise Http404("Social token missing")

    consumer_key = social_app.client_id
    consumer_secret = social_app.secret
    access_token = social_token.token
    access_token_secret = social_token.token_secret

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api


@json_view
@login_required
def post_tweet(request, uid):
    """Update twitter status"""
    update_form = UpdateForm(request.POST or None)
    if update_form.is_valid():
        in_reply_to = request.POST.get('in_reply_to')
        status = request.POST['status']
        api = get_api(request, uid=uid)

        # tweet
        try:
            res = api.update_status(status, in_reply_to_status_id=in_reply_to)
            success = True
            message = res
        except tweepy.TweepError as e:
            success = False
            message = e.args[0][0]['message']

        return {'success': success, 'message': message}
    else:
        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(update_form, context=ctx)
        return {'success': False, 'update_form_html': form_html}


@json_view
@login_required
def like_tweet(request, uid):
    """Lika a tweet given a uid for an account"""
    if request.is_ajax and request.POST.get('id'):
        api = get_api(request, uid=uid)
        tweet_id = request.POST.get('id')
        try:
            status = api.create_favorite(tweet_id)
            success = True
        except tweepy.TweepError as e:
            success = False
            status = e.args[0][0]['message']

        return {
            'success': success,
            'status': status,
            'tweet_id': tweet_id
        }



@json_view
@login_required
def ajax_get_helpdesk_queues(request):
    """Accept ajax request for helpdesk queues"""
    return {'data': 'data'}
