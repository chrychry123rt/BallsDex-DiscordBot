import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_panel.settings')
sys.path.insert(0, '/code')

django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Change password
username = sys.argv[1] if len(sys.argv) > 1 else 'admin'
password = sys.argv[2] if len(sys.argv) > 2 else 'newpassword123'

user = User.objects.get(username=username)
user.set_password(password)
user.save()
print(f"Password for user '{user.username}' changed to '{password}'")
