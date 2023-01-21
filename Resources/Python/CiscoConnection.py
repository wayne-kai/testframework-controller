import logging
import time
from Common import spawn_and_print, expect_and_print, expect_eof


class CiscoConnection:

    def __init__(self,
                 protocol,
                 IP,
                 username,
                 password,
                 en_password,
                 hostname,
                 default_timeout=None,
                 set_terminate_len0=True):

        self.protocol = protocol
        self.IP = IP
        self.username = username
        self.password = password
        self.en_password = en_password
        self.hostname = hostname

        self.cisco_process = None

        self.default_timeout = default_timeout
        self.set_terminate_len0 = set_terminate_len0

        self.connect_and_login()

    def connect(self):
        """Start an interactive session."""

        logging.info(
                "Connecting to {:s} with username '{:s}' over {:s} protocol"
                "".format(self.IP, self.username, self.protocol))
        logging.debug("timeout:{:d}".format(self.default_timeout))

        if self.protocol.lower() == 'telnet':
            # Telnet
            self.cisco_process = spawn_and_print(
                    "telnet", [self.IP], timeout=self.default_timeout)

            self.sendline()
            peek_data = self.cisco_process.read_nonblocking(
                    size=1000, timeout=-1)

            if "Connection refused" in peek_data:
                logging.debug("Retrying telnet connect")
                time.sleep(2)
                self.cisco_process = spawn_and_print(
                        "telnet", [self.IP], timeout=self.default_timeout)

            logging.debug("before[{:s}]".format(self.before()))
            logging.debug("after[{:s}]".format(self.after()))

        elif self.protocol.lower() == 'ssh':
            # SSH Refresh RSA key
            self.cisco_process_rm_key = spawn_and_print(
                "ssh-keygen",
                [
                    "-R",
                    self.IP
                ],
                timeout=self.default_timeout
            )

            # SSH connect
            self.cisco_process = spawn_and_print(
                    'ssh',
                    [
                        self.username + '@' + self.IP,
                        '-o',
                        'KexAlgorithms=diffie-hellman-group14-sha1,diffie-hellman-group1-sha1'
                    ],
                    timeout=self.default_timeout)

        else:
            # Invalid protocol type
            raise ValueError(
                    'Invalid protocol type "{:s}"'.format(self.protocol))

    def login(self):
        """
        Func with logic to know whether to enter username.

        For Cisco IOS login, we have 6 different cases depending on the
        configuration of the router

           1. Require     Username,   login_pass, en_pass
           2. Require     Username,   login_pass,
           3. Require                 login_pass, en_pass
           4. Require                 login_pass
           5. Require                             en_pass
           6. Not required
        """

        self.handle_user_login()
        self.handle_en()

        if self.set_terminate_len0:
            # Set terminal length 0 -> so cmd output will not have paging
            self.sendline("terminal length 0")
            self.expectline(self.hostname + "#")

    def disconnect(self):
        """Exit from router login."""
        self.cisco_process.sendline("exit")
        logging.debug("Disconnecting from router...")
        expect_eof(self.cisco_process)
        self.cisco_process.close()

    def connect_and_login(self):
        """Connect and login."""
        self.connect()
        self.login()

    def reconnect_and_login(self):
        """Reconnect and login."""
        logging.debug("Attempting to relogin")

        # exit from router login
        self.disconnect()

        # connect and login
        self.connect_and_login()

        logging.debug("Relogin done!")

    def send(self, string=""):
        """Send a string."""
        self.cisco_process.send(string)

    def send_and_expect_hostname(self, string="", timeout=None):
        """Send a string and wait for the prompt."""
        self.send(string)
        self.expect_hostname(timeout)

    def sendline(self, string=""):
        """Send a line."""
        logging.debug("sendline: {}".format(string))
        self.cisco_process.sendline(string)

    def sendline_and_expect_hostname(self, string="", timeout=None):
        """Send a line and wait for the prompt."""
        self.sendline(string)
        self.expect_hostname(timeout)

    def expectline(self, expect_string, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        logging.debug("expectline timeout: {}".format(timeout))
        expect_and_print(self.cisco_process, expect_string, timeout)

    def expect_hostname(self, timeout=None):
        self.expectline(self.hostname + "[^\s]*#", timeout)

    def after(self):
        return self.cisco_process.after

    def before(self):
        return self.cisco_process.before

    def handle_user_login(self):
        """Handle user login."""

        self.expectline(
                "(\(yes\/no\)\?|Username:|Password:|" + self.hostname + ")")

        # Enter yes if prompt to continue
        logging.debug("handle_user_login:" + self.after())
        if "(yes/no)?" in self.after():
            self.sendline("yes")
            self.expectline("(Username:|Password:|" + self.hostname + ")")

        # If no login is required. Send something to syn with the rest of the
        # code
        if self.hostname in self.after():
            self.sendline()     # send empty line
        else:
            # If there is username, input the username
            if "Username:" in self.after():
                self.sendline(self.username)
                self.expectline("Password: ")

            # Enter the password
            self.sendline(self.password)
            # Print the password for checking. By default Password will not be
            # echoed
            logging.info(self.password)

        # Prompt will be expected in handle_en func

    # Func with logic to know whether to 'en' to get admin rights
    # Second part of login process, see handle_login func
    def handle_en(self):
        """Turn on privileged commands."""

        # Expect '#' for default priviledge acc. or '>' for default
        # non-privilege acc.
        # We need to add '>' & '#' with hostname to syn to the next full
        # prompt
        self.expectline(
                "(% Authentication failed|% Login invalid|" + self.hostname + "#|" + self.hostname + ">)")

        # If login failed
        if "%" in self.after():
            raise ValueError("Incorrect Login Credential!\n")

        # If is non-priviledge: <enable>
        elif ">" in self.after():

            self.sendline("enable")
            self.expectline("Password:")

            # print to log file for report generation
            logging.debug("Entered password:\"" + self.en_password + "\"")

            # Enter enable password
            self.sendline(self.en_password)
            self.expectline("#|Enable rejected|Password:[\S\s]*")

            # Note that GK will print out "Password:" instead of
            # "Enable Accepted".
            # Added the chec for "#" to be sure that it is a success

            if "Enable rejected" in self.after() or ("Password:" in self.after() and "#" not in self.after()):
                raise ValueError("Incorrect Enable Password!\n")
