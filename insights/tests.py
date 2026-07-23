from rest_framework import status

from config.factories import BaseAPITest, make_user


class InsightsIndexTests(BaseAPITest):
    url = "/api/insights/"

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_status_payload(self):
        self.client.force_login(make_user(email="insights@example.com"))
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {"app": "insights", "status": "working"})

    def test_post_is_not_allowed(self):
        self.client.force_login(make_user(email="insights2@example.com"))
        self.assertEqual(
            self.client.post(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
