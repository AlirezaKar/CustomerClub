from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.conf import settings
import random

# utils
from utils.functions import datetime


def generate_phone_number_verification_code():
    User= get_user_model()
    start= 10** (settings.PHONE_NUMBER_VERIFICATION_CODE_LENGTH- 1)
    end= (10** settings.PHONE_NUMBER_VERIFICATION_CODE_LENGTH)- 1
    phone_number_verification_code= random.randint(start, end)

    # ensure uniqueness among currently-active codes (ignoring NULLs)
    while User.objects.filter(phone_number_verification_code= phone_number_verification_code).first():
        phone_number_verification_code= random.randint(start, end)

    return phone_number_verification_code
