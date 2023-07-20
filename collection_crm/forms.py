from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User

from collection_crm.lookups import EmailLookup
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from selectable.forms import AutoCompleteWidget

class UserProfileForm(ModelForm):
    """Profile details form edit"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

USER_LEVEL_CHOICES = (
    ('agent', 'Agent'),
    ('supervisor', 'Supervisor'),
    ('administrator', 'Administrator'),
)

class CreateUserForm(forms.Form):
    """Create user form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'form_create_new_user'
        self.helper.form_class = ''
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        super(CreateUserForm, self).__init__(*args, **kwargs)

    email = forms.CharField(
        required=True,
        label='Email',
        widget=AutoCompleteWidget(
            EmailLookup,
            attrs={
                'class': 'form-control',
                'placeholder': 'john.doe@callcenter.africa',
            }
        )
    )
    user_level = forms.ChoiceField(choices=USER_LEVEL_CHOICES,
                                    required=True,
                                    widget=forms.Select(
                                        attrs={
                                            'class': 'form-control',
                                        }
                                    ),)
    daily_target = forms.CharField(
        label='Daily Target',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }),
        required=False,
    )
    monthly_target = forms.CharField(
        label='Monthly Target',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }),
        required=False,
    )
