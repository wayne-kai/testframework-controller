import unittest
import pexpect
from mock import patch
from CiscoController import CiscoController
import CiscoConnection


class TestCiscoController(unittest.TestCase):

    def setUp(self):
        self.csc = CiscoController()
        self.csc.initialise_controller("127.0.0.1", "router")
        self.csc.set_database_ip("127.0.0.1", "127.0.0.1", "127.0.0.1")
        self.csc.set_credentials("user", "password", "enpassword")
        self.csc.set_config_credentials("super_user", "password", "enpassword")

    def test_set_default_protocol(self):
        self.assertEqual(self.csc.protocol, "telnet")

        self.csc.set_default_protocol("ssh")
        self.assertEqual(self.csc.protocol, "ssh")

        with self.assertRaises(ValueError):
            self.csc.set_default_protocol("dummy")

    @patch("CiscoController.CiscoConnection")
    def test_run_test_cmd(self, MockCiscoConnection):

        # Mock return values from CiscoConnection
        instance = MockCiscoConnection.return_value
        instance.after.side_effect = ["[confirm]", "[confirm]", self.csc.hostname+"#"]
        instance.before.side_effect = ["dummy_output_1", "dummy_output_2"]

        # Test sending dummy command with "[confirm]" interactive prompt
        test_cmd = self.csc.create_test_cmd("dummy")
        self.csc.run_test_cmd(test_cmd)
        instance.send.assert_called_with("n")
        instance.sendline.assert_called_with("dummy")
        instance.disconnect.assert_called()

    @patch("CiscoController.CiscoConnection")
    def test_run_test_cmd_fail(self, MockCiscoConnection):

        # Mock return values from CiscoConnection
        instance = MockCiscoConnection.return_value
        instance.after.side_effect = ["[confirm]", "[confirm]", self.csc.hostname+"#"]
        instance.before.side_effect = ["dummy_output_1", "dummy_output_2"]

        # Test sending dummy command with "[confirm]" interactive prompt
        test_cmd = self.csc.create_test_cmd("dummy")
        self.csc.add_test_cmd_criteria(test_cmd, should_contain="not in output")

        # Assert that exception is raised for failed test
        with self.assertRaises(ValueError):
            self.csc.run_test_cmd(test_cmd)

        instance.send.assert_called_with("n")
        instance.sendline.assert_called_with("dummy")
        instance.disconnect.assert_called()

    @patch("CiscoController.CiscoConnection")
    def test_run_test_cmd_exception(self, MockCiscoConnection):

        # Mock return values from CiscoConnection
        instance = MockCiscoConnection.return_value
        instance.sendline.side_effect = [pexpect.exceptions.EOF("generic error")]
        instance.after.side_effect = ["[confirm]", "[confirm]", self.csc.hostname+"#"]
        instance.before.side_effect = ["dummy_output_1", "dummy_output_2"]

        # Test sending dummy command with "[confirm]" interactive prompt
        test_cmd = self.csc.create_test_cmd("dummy")

        # Assert that exception is raised for failed test
        with self.assertRaises(pexpect.exceptions.EOF):
            self.csc.run_test_cmd(test_cmd)

        instance.sendline.assert_called_with("dummy")
        instance.disconnect.assert_called()

    @patch("CiscoController.CiscoConnection")
    def test_run_command_and_get_output(self, MockCiscoConnection):
        prompt = self.csc.hostname+"#"
        expected_output = "dummy_output"
        dummy_cmd = "dummy"

        # Mock return values from CiscoConnection
        instance = MockCiscoConnection.return_value
        instance.after.return_value = prompt
        instance.before.return_value = expected_output

        # Test sending dummy command with output
        output = self.csc.run_command_and_get_output(dummy_cmd)
        self.assertEqual(output, expected_output)
        instance.sendline.assert_called_with(dummy_cmd)
        instance.disconnect.assert_called()

