def register(client, email="dev@example.com", password="correct-horse-battery"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Test Developer",
            "password": password,
        },
    )


def login(client, email="dev@example.com", password="correct-horse-battery"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_read_current_user(client):
    registered = register(client)
    assert registered.status_code == 201
    user = registered.json()
    assert user["email"] == "dev@example.com"
    assert user["display_name"] == "Test Developer"
    assert "password" not in user
    assert "hashed_password" not in user

    authenticated = login(client)
    assert authenticated.status_code == 200
    token = authenticated.json()["access_token"]
    assert authenticated.json()["token_type"] == "bearer"
    assert authenticated.json()["expires_in"] == 1800

    current = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert current.status_code == 200
    assert current.json()["id"] == user["id"]
    assert current.json()["email"] == user["email"]


def test_registration_normalizes_email(client):
    response = register(client, email="Developer@Example.com")
    assert response.status_code == 201
    assert response.json()["email"] == "developer@example.com"


def test_duplicate_registration_returns_conflict(client):
    assert register(client).status_code == 201
    response = register(client, email="DEV@example.com")
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


def test_invalid_email_is_rejected(client):
    response = register(client, email="not-an-email")
    assert response.status_code == 422


def test_short_password_is_rejected(client):
    response = register(client, password="short")
    assert response.status_code == 422


def test_wrong_password_returns_generic_unauthorized(client):
    assert register(client).status_code == 201
    response = login(client, password="a-different-long-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_unknown_email_returns_same_unauthorized_response(client):
    response = login(client, email="unknown@example.com")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_protected_endpoint_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_rejects_malformed_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
