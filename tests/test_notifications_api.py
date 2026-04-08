import pytest


class TestNotificationsAPI:
    def test_register_device_token(self, client, auth_headers):
        response = client.post(
            "/api/notifications/device-token",
            headers=auth_headers,
            json={"token": "sample_device_token_12345", "platform": "android"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["registered"] is True
        assert data["platform"] == "android"

    def test_list_my_notifications(self, client, auth_headers):
        response = client.get("/api/notifications/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_send_notification_requires_admin_or_company(self, client, auth_headers):
        response = client.post(
            "/api/notifications/send",
            headers=auth_headers,
            json={
                "user_id": "some-user-id",
                "notification_type": "system",
                "title": "Unauthorized",
                "message": "This should be blocked",
            },
        )

        assert response.status_code == 403

    def test_admin_send_and_mark_read_flow(self, client, admin_auth_headers, auth_headers):
        me_response = client.get("/api/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        target_user_id = me_response.json()["id"]

        send_response = client.post(
            "/api/notifications/send",
            headers=admin_auth_headers,
            json={
                "user_id": target_user_id,
                "notification_type": "system",
                "title": "Dispatch Alert",
                "message": "Trip has been rerouted",
                "send_push": False,
            },
        )

        assert send_response.status_code == 200
        send_data = send_response.json()
        assert send_data["created"] is True
        assert send_data["ws_sent"] is True
        assert send_data["notification_id"]

        list_response = client.get("/api/notifications/me", headers=auth_headers)
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert len(items) >= 1

        notification_id = send_data["notification_id"]
        read_response = client.patch(
            f"/api/notifications/{notification_id}/read",
            headers=auth_headers,
        )

        assert read_response.status_code == 200
        read_data = read_response.json()
        assert read_data["id"] == notification_id
        assert read_data["is_read"] is True
