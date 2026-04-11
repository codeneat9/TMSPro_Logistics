from backend.services.auth import AuthService


class TestAuthService:
    """Unit tests for AuthService."""

    def test_hash_password(self):
        password = "MySecurePassword123!"
        hashed = AuthService.hash_password(password)

        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password(self):
        password = "MySecurePassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True
        assert AuthService.verify_password("WrongPassword", hashed) is False

    def test_create_access_token(self):
        token = AuthService.create_access_token(
            data={"sub": "123", "email": "test@example.com", "role": "customer"}
        )

        assert token
        assert isinstance(token, str)

    def test_create_refresh_token(self):
        token = AuthService.create_refresh_token(data={"sub": "123"})

        assert token
        assert isinstance(token, str)

    def test_verify_token(self):
        token = AuthService.create_access_token(
            data={"sub": "123", "email": "test@example.com", "role": "customer"}
        )
        payload = AuthService.verify_token(token)

        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "customer"

    def test_verify_invalid_token(self):
        payload = AuthService.verify_token("invalid.token.here")
        assert payload is None

    def test_register_user(self, db_session):
        user = AuthService.register_user(
            db=db_session,
            email="newuser@example.com",
            password="SecurePassword123!",
            full_name="John Doe",
            phone="+1234567890",
        )

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "John Doe"

    def test_register_duplicate_email(self, db_session):
        email = "duplicate@example.com"

        AuthService.register_user(
            db=db_session,
            email=email,
            password="SecurePassword123!",
            full_name="John Doe",
            phone="+1234567890",
        )

        user = AuthService.register_user(
            db=db_session,
            email=email,
            password="AnotherPassword123!",
            full_name="Jane Doe",
            phone="+1234567891",
        )

        assert user is None

    def test_authenticate_user(self, db_session):
        email = "authtest@example.com"
        password = "SecurePassword123!"

        AuthService.register_user(
            db=db_session,
            email=email,
            password=password,
            full_name="Auth Test",
            phone="+1234567890",
        )

        user = AuthService.authenticate_user(db=db_session, email=email, password=password)

        assert user is not None
        assert user.email == email

    def test_authenticate_wrong_password(self, db_session):
        email = "wrongpass@example.com"
        password = "SecurePassword123!"

        AuthService.register_user(
            db=db_session,
            email=email,
            password=password,
            full_name="Wrong Pass",
            phone="+1234567890",
        )

        user = AuthService.authenticate_user(db=db_session, email=email, password="WrongPassword")
        assert user is None

    def test_authenticate_nonexistent_user(self, db_session):
        user = AuthService.authenticate_user(
            db=db_session,
            email="nonexistent@example.com",
            password="password",
        )
        assert user is None
