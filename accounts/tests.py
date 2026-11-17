from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Role

User = get_user_model()


class RegistrationTests(TestCase):
    def setUp(self):
        self.viewer_role = Role.objects.get_or_create(name=Role.VIEWER, defaults={"description": "Viewer"})[0]
        self.admin_role = Role.objects.get_or_create(name=Role.ADMINISTRATOR, defaults={"description": "Administrator"})[0]

    def test_public_registration_creates_general_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newviewer",
                "email": "newviewer@example.com",
                "first_name": "New",
                "last_name": "Viewer",
                "role": str(self.viewer_role.pk),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newviewer")
        self.assertEqual(user.role, self.viewer_role)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_public_registration_creates_admin_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newadmin",
                "email": "newadmin@example.com",
                "first_name": "New",
                "last_name": "Admin",
                "role": str(self.admin_role.pk),
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newadmin")
        self.assertEqual(user.role, self.admin_role)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
