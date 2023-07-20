from helpline.models import Hotdesk
from plans.validators import ModelCountValidator


class MaxHotdesksValidator(ModelCountValidator):
    code = 'MAX_HOTDESK_COUNT'
    model = Hotdesk

    def get_queryset(self, user):
        return super(MaxHotdesksValidator, self).get_queryset(user).filter(
            user=user
        )


max_hotdesk_validator = MaxHotdesksValidator()
