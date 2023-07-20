from django import forms

from crispy_forms.helper import FormHelper

class UpdateForm(forms.Form):
    """Status update form"""
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'status'
        self.helper.form_class = 'statusUpdateForm'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        super(UpdateForm, self).__init__(*args, **kwargs)
    in_reply_to = forms.CharField(
        widget=forms.HiddenInput(), required=False
    )
    status = forms.CharField(widget=forms.Textarea(
        attrs={
            "rows":"3",
            "class":"form-control"
        }),required=True)
