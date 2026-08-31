import unittest

from academic_clipboard.privacy import sensitive_reason


class PrivacyTests(unittest.TestCase):
    def test_sensitive_patterns_are_blocked(self) -> None:
        values = (
            "-----BEGIN PRIVATE KEY-----\nsynthetic",
            "Authorization: Bearer synthetic-token-value",
            "password=synthetic-secret",
            "ghp_" + "a" * 30,
            "otp: 123456",
        )
        for value in values:
            with self.subTest(value=value):
                self.assertTrue(sensitive_reason(value))

    def test_research_content_is_not_blocked(self) -> None:
        values = (
            "10.1038/s41586-020-2649-2",
            "@article{demo, title={A Study}, year={2025}}",
            "The sample contains 123456 observations.",
        )
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(sensitive_reason(value), "")


if __name__ == "__main__":
    unittest.main()
