# -*- coding: utf-8 -*-
"""Helpline forms"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.conf import settings

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from selectable.forms import AutoCompleteWidget

from helpline.models import HelplineUser,\
        Category, Address, Scheme,\
        Disposition, Break, Schedule,\
        Service

from helpline.lookups import AddressLookup, NameLookup,\
        PhoneLookup, RecipientLookup,\
        EmailLookup, PartnerLookup, SubCategoryLookup


class QueueLogForm(forms.Form):
    """Queue join form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'queue-log-form'
        self.helper.form_class = 'form-group'
        self.helper.form_method = 'post'
        self.helper.form_action = '#'
        self.helper.add_input(
            Submit('login', 'Login', css_class='pull-right')
            )

        super(QueueLogForm, self).__init__(*args, **kwargs)

    softphone = forms.CharField(
        label="Extension",
        widget=forms.TextInput(attrs={'placeholder': 'Enter Extention No',
                                      'required': 'true',
                                      'class': 'form-control'}),
        required=False)
    queue = forms.CharField(widget=forms.HiddenInput(), required=False)


QUEUE_PAUSE_REASON_CHOICES = (
    ('', '--'),
    ('Bio Break', 'Bio Break'),
    ('Tea Break', 'Tea Break'),
    ('System Issue TE', 'System Issue TE'),
    ('System Issue PC', 'System Issue PC'),
    ('Meeting', 'Meeting'),
    ('Lunch', 'Lunch'),
    ('End of Shift', 'End of Shift'),
    ('Consulting', 'Consulting'),
    ('Coaching', 'Coaching'),
    ('Other Break Reason', 'Other Break Reason'),
)

GENDER_CHOICES = (
    ('', '--'),
    ('MALE', 'Male'),
    ('FEMALE', 'Female'),
)


STATUS_CHOICES = (
    ('', '--'),
    ('Close', 'Close'),
    ('Pending', 'Pending'),
    ('Escalate', 'Escalate'),
    ('Transferred', 'Transferred'),
)

REFERRED_FROM_CHOICES = (
    ('--', '--'),
    ('Call Center', 'Call Center'),
    ('Facebook', 'Facebook'),
    ('Newspaper', 'Newspaper'),
    ('Friend', 'Friend'),
    ('Radio', 'Radio'),
    ('Other', 'Other'),
)


CASE_TYPE_CHOICES = (
    ('--', '--'),
    ('Claims', 'Claims'),
    ('Other', 'Other'),
)


INTERVAL_CHOICES = (
    ('', '--'),
    ('hourly', 'Hourly'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
)

BUSINESS_PORTFOLIO_CHOICES = (
    ('', '--'),
    ('eBancasurance', 'eBancasurance'),
    ('General Insurance', 'General Insurance'),
    ('Healthcare', 'Healthcare'),
    ('Hospitality & Tourism', 'Hospitality & Tourism'),
    ('Human Capital Benefits', 'Human Capital Benefits'),
    ('Investment', 'Investment'),
    ('Pension', 'Pension'),
    ('Reinsurance', 'Reinsurance'),
)

AGE_GROUP_CHOICES = (
    ('', '--'),
    ('15-24', '15-24'),
    ('25-34', '25-34'),
    ('35-44', '35-44'),
    ('45-54', '45-54'),
    ('55-64', '55-64'),
    ('65+', '65+'),
)


INTERVENTIONS = (
    ('Counselling', 'counselling'),
    ('appropriate_referrals', 'Appropriate Referrals'),
    ('awareness', 'Awareness'),
    ('psychological_support', 'Psychological Support'),
    ('educational_support', 'Educational Support'),
    ('directed_to_telecom', 'Support Directed to Telecom Support'),
    ('report_to_olice', 'Report to Police'),
    ('medical_support', 'Medical Support'),
    ('legal_support', 'Legal Support'),
    ('basic_need_support', 'Basic Need Support'),
    ('resettlement', 'Resettlement'),
    ('others', 'Others'),
)


def get_pause_reasons():
    """Return list of break reasons."""
    return [("", "---------")] \
            + list(Break.objects.values_list(
                'name', 'name'
            ).distinct())


def get_categories():
    """Return list of categories."""
    return [("", "---------")] \
            + list(Category.objects.values_list(
                'hl_category', 'hl_category'
            ).distinct())


def get_sub_categories():
    """Return list of sub-categories."""
    return [("", "---------")] \
            + list(Category.objects.values_list(
                'hl_subcategory', 'hl_subcategory'
            ).distinct())


def get_sub_sub_categories():
    """Return list of sub-sub-categories."""
    return [("", "---------")] \
            + list(Category.objects.values_list(
                'hl_subsubcat', 'hl_subsubcat'
            ).distinct())


def get_schemes():
    """Return list of schemes."""
    return [("", "---------")] \
            + list(Scheme.objects.values_list(
                'name', 'name'
            ).order_by('name').distinct()) + [('Other', 'Other')]



def get_dispositions():
    """Return list of dispositions."""
    dynamic_dispositions = list(Disposition.objects.values_list(
        'value', 'value'
    ).order_by('value').distinct())
    # Check if there are values in the Dispositions model
    # If not use default Dispositions in settings only
    dispositions = settings.DISPOSITION_CHOICES + dynamic_dispositions
    return sorted(dispositions)


def get_agent_list(user):
    """Get list of agents/users in service"""
    agent_list = list(HelplineUser.objects.values_list(
        'user', 'user__username'
    ).order_by('user__username').distinct())

    return [("", "---------")] + agent_list


class ContactForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'contactDet'
        self.helper.form_class = 'contactDet'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        super(ContactForm, self).__init__(*args, **kwargs)

    case_number = forms.CharField(widget=forms.HiddenInput(), required=False)

    caller_name = forms.CharField(
        label='Contact Name',
        widget=AutoCompleteWidget(NameLookup,
                                  attrs={
                                      'class': 'form-control',
                                  }),
        required=False,
    )

    phone_number = forms.CharField(
        label='Phone Number',
        widget=AutoCompleteWidget(PhoneLookup,
                                  attrs={
                                      'class': 'form-control',
                                  }),
        required=False,
    )

    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }),
        required=False,
    )


class CaseActionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'caseAction'
        self.helper.form_class = 'caseAction'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        super(CaseActionForm, self).__init__(*args, **kwargs)

    case_number = forms.CharField(widget=forms.HiddenInput(), required=False)

    case_status = forms.ChoiceField(choices=STATUS_CHOICES,
                                    required=False,
                                    widget=forms.Select(
                                        attrs={
                                            'class': 'form-control',
                                            'onchange': "saveCaseAction();",
                                        }
                                    ),)


class DispositionForm(forms.Form):
    """Last case state form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'disposeDet'
        self.helper.form_class = 'disposeDet'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        super(DispositionForm, self).__init__(*args, **kwargs)

    case_number = forms.CharField(widget=forms.HiddenInput(), required=True)
    disposition = forms.ChoiceField(choices=settings.DISPOSITION_CHOICES, # Replace this with get_disposition() after migrations
                                    widget=forms.Select(attrs={
                                        'onchange': "saveContact();saveCaseDetail();saveCaseAction();disposeCase(this);",
                                        'class': 'form-control',
                                    }))


class CaseSearchForm(forms.Form):
    """Full text search form"""
    query = forms.CharField()


class MyAccountForm(ModelForm):
    """Profile details form edit"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class ServiceForm(ModelForm):
    """Profile details form edit"""
    class Meta:
        model = Service
        fields = ['name', 'managed']


class ReportFilterForm(forms.Form):
    """Simple report filter form for dashboard reports"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        user = kwargs.pop('user', None)
        super(ReportFilterForm, self).__init__(*args, **kwargs)
        dynamic_agent_list = get_agent_list(user)
        self.fields['agent'].choices = dynamic_agent_list
    datetime_range = forms.CharField(
        label='Choose Date and time Range:',
        widget=forms.TextInput(attrs={'class': 'form-control pull-right',
                                      'name': 'datetimerange',
                                      'id': 'datetimerange',
                                      'width': '200px'}),
        required=False,
    )
    agent = forms.ChoiceField(
        label='Agent:',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control pull-right',
                                   'id': 'agent',
                                   'name': 'agent'}))

    interval = forms.ChoiceField(choices=INTERVAL_CHOICES,
                                 label='Interval:',
                                 required=False,
                                 widget=forms.Select(
                                     attrs={
                                         'class': 'form-control pull-right',
                                         'id': 'interval',
                                         'name': 'interval',
                                     }
                                 ),)
    category = forms.ChoiceField(choices=[],
                                 label='Category:',
                                 required=False,
                                 widget=forms.Select(
                                     attrs={
                                         'class': 'form-control pull-right',
                                         'id': 'category',
                                         'name': 'category',
                                     }
                                 ),)

    queueid = forms.CharField(widget=forms.HiddenInput(), required=True)

    case_status = forms.ChoiceField(choices=STATUS_CHOICES,
                                    required=False,
                                    widget=forms.Select(
                                        attrs={
                                            'class': 'form-control',
                                        }
                                    ),)

    interventions = forms.ChoiceField(choices=INTERVENTIONS,
                                    required=False,
                                    widget=forms.Select(
                                        attrs={
                                            'class': 'form-control',
                                        }
                                    ),)

class LoginForm(forms.Form):
    username = forms.CharField(label="Username", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'username'}))
    password = forms.CharField(label="Password", max_length=30,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'name': 'password'}))


class QueuePauseForm(forms.Form):
    """Queue pause form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'queue-pause-form'
        self.helper.form_class = 'form-group'
        self.helper.form_method = 'post'
        self.helper.form_action = '#'

        super(QueuePauseForm, self).__init__(*args, **kwargs)

    reason = forms.ChoiceField(
        label='Reason',
        widget=forms.Select(
            attrs={
                'class': 'form-control',
                'id': 'pause-reason'
            }
        ),
        choices=[],
        required=False
    )


class ContactSearchForm(forms.Form):
    """Contact search form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'contact-search-form'
        self.helper.form_class = 'contact-search-form'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        super(ContactSearchForm, self).__init__(*args, **kwargs)
    query = forms.CharField(
        required=False,
        label='Search contacts',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Contact name or phone number',
            }
        )
    )


class InviteForm(forms.Form):
    """Invite form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'invite-form'
        self.helper.form_class = 'invite-form'
        self.helper.form_method = 'post'
        self.helper.form_action = ''

        super(InviteForm, self).__init__(*args, **kwargs)
    email = forms.CharField(
        required=False,
        label='Email',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'john.doe@callcenter.africa',
            }
        )
    )


class CaseDetailForm(forms.Form):
    """Legacy Call Form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'caseDet'
        self.helper.form_class = 'caseDet'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        super(CaseDetailForm, self).__init__(*args, **kwargs)

    case_number = forms.CharField(widget=forms.HiddenInput(), required=True)
    category = forms.ChoiceField(
        required=False,
        choices=get_categories,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
            }
        ),
    )

    sub_category = forms.ChoiceField(
        required=False,
        choices=get_sub_categories,
        widget=forms.Select(
            attrs={
                'class': 'form-control',
            }
        ),)

    comment = forms.CharField(
        label='Description',
        widget=forms.Textarea(
            attrs={'col': '30',
                   'rows': '7',
                   'class': 'form-control',
                   'id': 'txtComment'}

        ),
        required=False,
    )

class GetRecordsForm(forms.Form):
    """Get CDR Data form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        super(GetRecordsForm, self).__init__(*args, **kwargs)

    agent = forms.ChoiceField(
        label='Agent:',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control pull-right',
                                   'id': 'agent',
                                   'name': 'agent'}))
    channel = forms.CharField(
        required=True,
        label='Extension',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Channel',
            }
        )
    )

    direction = forms.CharField(
        required=True,
        label='Direction',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Direction',
            }
        )
    )
    start = forms.CharField(
        required=True,
        label='Start',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Start',
            }
        )
    )
    end = forms.CharField(
        required=True,
        label='End',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'End',
            }
        )
    )


class EmailLoginForm(forms.Form):
    """ Email login verfication step"""
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }),
        required=True,
    )
