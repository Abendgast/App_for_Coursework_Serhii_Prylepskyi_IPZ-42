def create_account(client, email="owner@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Project Owner",
            "password": "a-very-long-test-password",
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a-very-long-test-password"},
    )
    assert login.status_code == 200
    return {
        "Authorization": f"Bearer {login.json()['access_token']}",
    }


def create_project(client, headers, name="Billing Service"):
    response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": name, "description": "Automated billing tests"},
    )
    assert response.status_code == 201
    return response.json()


def test_project_crud_and_one_time_project_key(client):
    headers = create_account(client)
    created = create_project(client, headers)
    project_id = created["id"]
    api_key = created["api_key"]

    assert api_key.startswith("ath_")
    assert created["runs_count"] == 0

    listed = client.get("/api/v1/projects", headers=headers)
    assert listed.status_code == 200
    assert [project["id"] for project in listed.json()] == [project_id]
    assert "api_key" not in listed.json()[0]

    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"name": "Billing API", "description": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Billing API"
    assert updated.json()["description"] is None

    details = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert details.status_code == 200
    assert details.json()["name"] == "Billing API"

    deleted = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}", headers=headers).status_code == 404


def test_project_can_be_replaced_with_put(client):
    headers = create_account(client)
    project = create_project(client, headers)

    replaced = client.put(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"name": "Billing API v2", "description": "Replaced project details"},
    )

    assert replaced.status_code == 200
    assert replaced.json()["name"] == "Billing API v2"
    assert replaced.json()["description"] == "Replaced project details"


def test_project_put_requires_all_replace_fields(client):
    headers = create_account(client)
    project = create_project(client, headers)

    response = client.put(
        f"/api/v1/projects/{project['id']}",
        headers=headers,
        json={"name": "Billing API v2"},
    )

    assert response.status_code == 422


def test_duplicate_project_name_returns_conflict(client):
    headers = create_account(client)
    assert create_project(client, headers)["name"] == "Billing Service"
    duplicate = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Billing Service"},
    )
    assert duplicate.status_code == 409


def test_project_names_are_scoped_to_the_owner(client):
    owner_headers = create_account(client, "first@example.com")
    other_headers = create_account(client, "second@example.com")
    first = create_project(client, owner_headers)
    second = create_project(client, other_headers)
    assert first["name"] == second["name"]
    assert first["id"] != second["id"]

    hidden = client.get(f"/api/v1/projects/{first['id']}", headers=other_headers)
    assert hidden.status_code == 404


def test_project_validation_and_authentication(client):
    unauthenticated = client.post("/api/v1/projects", json={"name": "No auth"})
    assert unauthenticated.status_code == 401

    too_long = client.post(
        "/api/v1/projects",
        headers=create_account(client),
        json={"name": "x" * 101},
    )
    assert too_long.status_code == 422
