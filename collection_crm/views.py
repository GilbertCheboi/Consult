# -*- coding: utf-8 -*-
"""Collection CRM views """

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt

from allauth.account.models import EmailAddress
from collection_crm.forms import UserProfileForm, CreateUserForm
from collection_crm.models import Survey, CollectionUser

from datetime import timedelta, datetime, date, time as datetime_time

from jsonview.decorators import json_view
from oauth2_provider.models import get_application_model

from two_factor.utils import default_device


@login_required
def home(request):
    """Collection CRM Landing page"""
    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )

    return render(
        request, "helpline/features.html", {}
    )


@login_required
def leads(request):
    """Collection CRM Leads Admin page"""
    collection_user = get_object_or_404(
        CollectionUser,
        user=request.user
    )
    my_leads = Survey.objects.all()[:5000]
    amount_paid_sum = my_leads.aggregate(
        Sum('amount_paid')
    ).get('amount_paid__sum')

    data = {
        'my_leads': my_leads,
        'collection_user': collection_user,
        'amount_paid_sum': amount_paid_sum,
    }

    return render(
        request, "collection_crm/leads.html", data
    )


@login_required
def search(request):
    """Collection CRM Leads Search page"""
    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )

    return render(
        request, "collection_crm/search.html", {}
    )


@login_required
def allocation(request):
    """Collection CRM Allocations page"""
    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )

    return render(
        request, "helpline/features.html", {}
    )


@login_required
def admin_dashboard(request):
    """Collection CRM Admin Dashbaord"""
    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )

    return render(
        request, "helpline/features.html", {}
    )


@login_required
def load_csv(request):
    """Collection CRM Load leads using CSV File"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "helpline/features.html", {}
    )


@login_required
def user_manager(request):
    """Collection CRM User Manager"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "helpline/features.html", {}
    )


@login_required
def not_contacted(request):
    """Collection CRM Not Contacted Leads List"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/not_contacted.html", {}
    )


@login_required
def call_status_report(request):
    """Collection CRM Call Status Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/call_status_report.html", {}
    )


@login_required
def attempts(request):
    """Collection CRM Call Attempts Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/attempts.html", {}
    )


@login_required
def delinquency_report(request):
    """Collection CRM Delinquency Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/delinquency_report.html", {}
    )


@login_required
def collection_summary(request):
    """Collection CRM Summary of Collections"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/collection_summary.html", {}
    )


@login_required
def collection_report(request):
    """Collection CRM Collections Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "helpline/features.html", {}
    )


@login_required
def agent_productivity_report(request):
    """Collection CRM Agent Productivity Report"""
    # call_user=christine.onsumu&fromdate=2022-08-01&todate=2022-08-08

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/agent_productivity_report.html", {}
    )


@login_required
def agent_productivity_report_details(request):
    """Collection CRM Agent Productivity Report Detailed View"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    username = request.GET.get("user")
    if username:
        user = get_object_or_404(User, username__iexact=username)

    data = {
        'content_user': user,
    }

    return render(
        request, "collection_crm/agent_productivity_report_details.html", data
    )


@login_required
def ptp_report(request):
    """Collection CRM Promise to Pay Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/ptp_report.html", {}
    )


@login_required
def allocation_summary(request):
    """Collection CRM Allocation Summary Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/allocation_summary.html", {}
    )


@login_required
def audit_view(request):
    """Collection CRM Audit Logs and View"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/audit_view.html", {}
    )


@login_required
def batch_history_download_loadcsv(request):
    """Collection CRM Download History in CSV"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/batch_history_download_loadcsv.html", {}
    )


@login_required
def batch_edit_loadcsv(request):
    """Collection CRM Batch edit using CSV"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/batch_edit_loadcsv.html", {}
    )


@login_required
def sms_outbound(request):
    """Collection CRM SMS Features"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "helpline/features.html", {}
    )


@json_view
@csrf_exempt
@login_required
def notification(request):
    """Collection CRM Notifications"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return {
        'result': False
    }


@login_required
def allocation(request):
    """Collection CRM Allocations"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/allocation.html", {}
    )


@login_required
def report(request):
    """Collection CRM Main Report"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/report.html", {}
    )


@login_required
def loadcsv(request):
    """Collection CRM Load CSV Leads"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/loadcsv.html", {}
    )


@login_required
def loadcsv(request):
    """Collection CRM Load CSV Leads"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    return render(
        request, "collection_crm/loadcsv.html", {}
    )


@login_required
def users(request):
    """Collection CRM Manage Users"""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    collection_users = CollectionUser.objects.using('collectiondb').all()

    data = {
        'collection_users': collection_users,
    }
    return render(
        request, "collection_crm/users.html", data
    )


@login_required
def user_profile(request, username):
    """User profiles view and edit."""

    collection_user = get_object_or_404(
        CollectionUser.objects.using('collectiondb'),
        user=request.user
    )
    form = UserProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
    username = username.strip("@")
    content_user = get_object_or_404(User, username__iexact=username)

    tfa_enabled = True if default_device(content_user) else False
    data = {}
    data['applications'] = get_application_model().objects.filter(user=request.user)
    data['is_owner'] = request.user == content_user
    data['content_user'] = content_user
    data['form'] = form
    data['tfa_enabled'] = tfa_enabled
    data['email_verfied'] = EmailAddress.objects.filter(
        user=request.user, verified=True).exists()

    return render(request, 'collection_crm/user_profile.html', data)


@login_required
def create_new_user(request):
    create_user_form = CreateUserForm()
    data = {
        'create_user_form': create_user_form,
    }
    return render(request, 'collection_crm/create_new_user.html', data)

@json_view
@login_required
def create_user(request):
    """Create a new user
    OR send an invitation if user not registered
    Redirect to user profile or ask to update if user exists"""
    create_user_form = CreateUserForm(request.POST or None)
    if create_user_form.is_valid():
        email = contact_form.cleaned_data.get('email')
        user_level = contact_form.cleaned_data.get('user_level')
        daily_target = contact_form.cleaned_data.get('daily_target')
        monthly_target = contact_form.cleaned_data.get('monthly_target')
        try:
            user = User.objects.get(email=email)
            collection_user, collection_user_created = CollectionUser.objects.get_or_create(
                user=user,

            )

            data = {'collection_user': collection_user}
        except User.DoesNotExist:
            data = {'action': 'send_invite', 'email': email}
