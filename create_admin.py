import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

try:
    if not User.objects.filter(username='admin@oceango.com').exists():
        u = User(
            username='admin@oceango.com', 
            email='admin@oceango.com', 
            role='admin', 
            phone='+1234567890', 
            name='Admin User'
        )
        u.set_password('password123')
        u.is_superuser = True
        u.is_staff = True
        u.save()
        print("Success: User 'admin@oceango.com' with password 'password123' created!")
    else:
        print("Info: User 'admin@oceango.com' already exists.")
except Exception as e:
    print(f"Error creating user: {e}")
