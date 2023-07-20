from __future__ import unicode_literals

from selectable.base import ModelLookup
from selectable.decorators import login_required
from selectable.registry import registry

from django.contrib.auth.models import User
from collection_crm.models import CollectionUser

@login_required
class EmailLookup(ModelLookup):
    model = CollectionUser
    search_fields = ('user__email',)

    def get_item_value(self, item):
        return u"%s" % (item.user.email)

    def get_item_label(self, item):
        return u"%s %s, %s" % (item.user.first_name, item.user.last_name, item.user.email)

registry.register(EmailLookup)
