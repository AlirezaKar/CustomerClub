import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Check if admin exists, create if not
phone = '09106165392'  # Your desired phone number
if not User.objects.filter(phone_number=phone).exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        phone_number='09106165392'
    )
    print("✅ Superuser created")
else:
    print("⚠️ User with this phone already exists")