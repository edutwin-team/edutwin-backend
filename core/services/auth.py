from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction

User = get_user_model()


@transaction.atomic
def register_user(*, username: str, email: str, password: str):
    user = User(username=username, email=email)
    validate_password(password, user=user)

    try:
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
    except IntegrityError:
        raise ValueError("A user with this username already exists.")
