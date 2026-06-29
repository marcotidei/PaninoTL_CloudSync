import unittest
from unittest import mock

import requests

import main


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.auth = {"AUTH_TOKEN": "token", "USER_ID": "user"}

    @mock.patch("requests.get")
    def test_auth_refreshes_after_unauthorized_response(self, get):
        get.return_value.status_code = 401

        self.assertTrue(main.auth_needs_refresh(self.auth))

    @mock.patch("requests.get")
    def test_valid_auth_is_reused(self, get):
        get.return_value.status_code = 200

        self.assertFalse(main.auth_needs_refresh(self.auth))

    @mock.patch("requests.get")
    def test_network_failure_does_not_force_browser_login(self, get):
        get.side_effect = requests.ConnectionError("offline")

        self.assertFalse(main.auth_needs_refresh(self.auth))


if __name__ == "__main__":
    unittest.main()
