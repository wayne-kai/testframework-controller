import logging
import re


class CiscoConfigure:

    def __init__(self, cisco_conn, fs_class):
        self.cconn = cisco_conn
        self.filesys_class = fs_class
        self.last_cli_shell = ""
        self.conf_mode_cmd_list = []

    def check_curr_conf_mode(self, cmd):
        
        logging.debug("Checking if the cli shell is configuration mode now...")

        if re.match(self.cconn.hostname + "\([\s\S]*\)#", self.cconn.after()):
                            
            if self.last_cli_shell == "":
                self.last_cli_shell = self.cconn.after()
                self.conf_mode_cmd_list.append(cmd)
                logging.debug("Last CLI Shell: {}".format(self.cconn.after()))

            else:

                if self.last_cli_shell != self.cconn.after():
                    
                    self.last_cli_shell = self.cconn.after()

                    if cmd != "exit":
                        self.conf_mode_cmd_list.append(cmd)
                    else:
                        self.conf_mode_cmd_list = self.conf_mode_cmd_list[:-1]

                logging.debug("last CLI Shell: {}".format(self.cconn.after()))

            logging.debug("Configuration Mode Command Entered:\n")
            for cmd in self.conf_mode_cmd_list:

                logging.debug("[+] {}".format(cmd))

        elif re.match(self.cconn.hostname + "#", self.cconn.after()):

            self.last_cli_shell = ""
            self.conf_mode_cmd_list = []

    def rerun_conf_mode_cmds(self):

        expectstr = "" + self.cconn.hostname + "[\s\S]*#"

        for cmd in self.conf_mode_cmd_list:

            self.cconn.sendline(cmd)
            self.cconn.expectline(expectstr)

    def conf_sendline_expect(self, cmd):
        """Automatic handling of authorization failed by re-login."""
        expectstr = "(back to no aaa new-model is not supported|Authorization failed|" + self.cconn.hostname + "[\s\S]*[#|>])"

        self.cconn.sendline(cmd)
        self.cconn.expectline(expectstr)

        self.check_curr_conf_mode(cmd)

        logging.debug("conn.after() = {}".format(self.cconn.after()))

        while self.cconn.hostname not in self.cconn.after():
            reconnected = False

            if "Authorization failed" in self.cconn.after():
                # Reconnect and try
                if reconnected:
                    raise ValueError("CiscoConfigure: Authorization failed\n")
                else:
                    self.cconn.reconnect_and_login()
                    reconnect = True
                    self.rerun_conf_mode_cmds()
                    self.cconn.sendline(cmd)
            # no aaa new-model might prompt to confirm in some versions
            elif "back to no aaa new-model is not supported" in self.cconn.after(): 
                self.cconn.sendline("y")

            self.cconn.expectline(expectstr)

    def configure_replace_running(self, replace_path):
        self.cconn.sendline("configure replace " + replace_path)
        self.cconn.expectline("sure you want to proceed. ?")
        self.conf_sendline_expect("yes")

    def configure_replace_startup(self, replace_path):
        self.cconn.sendline("copy {:s} startup".format(replace_path))
        self.cconn.expectline("Destination filename")
        self.conf_sendline_expect(" ")

    def verify_config(self, conf_list):

        conf_out = ""

        logging.debug("Check configuration...")

        self.cconn.sendline("do show run")
        self.cconn.expectline("(" + self.cconn.hostname + "\(config\)#|--More--)")
        conf_out += self.cconn.before()

        logging.debug("Ran do show run...")

        while "(config)#" not in self.cconn.after():
            #   Accumulate the output
            conf_out += self.cconn.before()

            self.cconn.sendline()
            self.cconn.expectline("(\(config\)#|--More--)")

        logging.debug("conf_out:[{}]".format(conf_out))
        for conf in conf_list:
            if conf.lower() == "password password":
                if re.match("[\s\S]*line vty[\s\S]+password[\s\S]*", conf_out) is None:
                    raise ValueError(
                            "password password Configure Error: Failed to configure in : {}".format(conf))
            elif "aaa accounting" in conf.lower():
                m = re.search("aaa accounting (.+?) start-stop group tacacs+", conf.lower())
                if m:

                    #   Extract the different part of the aaa accounting
                    #   configuration
                    found = m.group(1)

                    #   Try to match the aaa accounting setup for two
                    #   different versions of display
                    if re.match("[\s\S]*aaa accounting " + found + "[\t\r\n ]*(action-type )?start-stop[\t\r\n ]*group tacacs+[\s\S]*", conf_out) is None:
                        logging.debug("conf_out:[{}]".format(conf_out))
                        raise ValueError(
                                "aaa accounting Configure Error: Failed to "
                                "configure in : {}".format(conf))
            else:
                if conf.startswith("no") is False:
                    if conf not in conf_out:
                        logging.debug("conf_out:[{}]".format(conf_out))
                        raise ValueError(
                                "Configure Error: Failed to configure in : {}"
                                "".format(conf))

    def set_vty_lines_priv(self, start_line, end_line, is_admin):

        priv_conf_list = []

        self.conf_sendline_expect(
                "line vty {} {}".format(start_line, end_line))

        if is_admin:
            priv_conf_list.append("privilege level 15")
        else:
            priv_conf_list.append("no privilege level 15")

        for priv_conf in priv_conf_list:
            self.conf_sendline_expect(priv_conf)

        # Exiting line config
        self.conf_sendline_expect("exit")
        self.verify_config(priv_conf_list)

    def conf_login_priv(self, is_admin, username):
        # For both Telnet & SSH
        self.conf_sendline_expect("no username " + username)

        if is_admin:
            self.conf_sendline_expect(
                    "username " + username + " privilege 15 password 0 password")
        else:
            self.conf_sendline_expect(
                    "username " + username + " privilege 0 password 0 password")

        # For Telnet
        self.set_vty_lines_priv(0, 4, is_admin)

        # For SSH
        self.set_vty_lines_priv(5, 15, is_admin)

    def conf_login_type(self, login_type):

        login_conf_list = []

        # Login using username configuration data
        if login_type == "LOGINLOCAL":
            # to reference the username command
            login_conf_list.append("login local")
            login_conf_list.append("no password")
        # Login using VTY password checking
        elif login_type == "PASSONLY":
            # only use for local scenario
            login_conf_list.append("password password")
            login_conf_list.append("login")     # login for passwd only
        # No Login required
        elif login_type == "NOLOGIN":
            login_conf_list.append("no login ")
            login_conf_list.append("no password")

        self.conf_sendline_expect("line vty 0 4")

        for login_conf in login_conf_list:
            self.conf_sendline_expect(login_conf)

        # Exiting line config
        self.conf_sendline_expect("exit")

        self.verify_config(login_conf_list)

    def conf_connection_channel(self):

        logging.info("Configuring for comms connection")

        self.conf_telnet()
        self.conf_ssh()

    def conf_telnet(self):

        logging.info("Configuring for Telnet connection")

        config_local_telnet_commands = [
                    "line vty 0 4",
                    "transport input telnet"]

        for cmd in config_local_telnet_commands:
            self.conf_sendline_expect(cmd)

        # Exiting line config
        self.conf_sendline_expect("exit")
        self.verify_config(config_local_telnet_commands)

    def conf_ssh(self):

        logging.info("Configuring for SSH connection")

        config_local_ssh_commands = [
                    "line vty 5 15",
                    "transport input ssh"]

        # Set domain name
        self.cconn.sendline("ip domain-name testnet")
        self.cconn.expectline(self.cconn.hostname + "\(config\)#")
        self.cconn.sendline("do show run | include ip domain name")
        self.cconn.expectline("(" + self.cconn.hostname + "\(config\)#|ip domain name)")

        # ip domain name should be displayed first
        if self.cconn.hostname + "(config)#" in self.cconn.after():
            raise ValueError("Fail to set domain name. Unable to process with configuration for SSH")
        # ip domain found!
        else:
            # Configure SSH in config terminal
            #  Resynchronized to the config prompt
            self.cconn.expectline(self.cconn.hostname + "\(config\)#")

            self.cconn.sendline("crypto key generate rsa")
            self.cconn.expectline("(" + self.cconn.hostname + "\(config\)#|How many bits in the modulus|Do you really want to replace them)")

            if self.cconn.hostname + "(config)#" in self.cconn.after():
                logging.info("Firmware has no crypto module so SSH does not exist")
            else: 
                logging.info("Firmware has crypto module so SSH exists")

                if "How many bits in the modulus" in self.cconn.after():
                    self.conf_sendline_expect("2048")
                elif "Do you really want to replace them" in self.cconn.after():
                    self.conf_sendline_expect("no")

                self.conf_sendline_expect("ip ssh version 2")
                self.conf_sendline_expect("ip ssh dh min size 4096")

                for cmd in config_local_ssh_commands:
                    self.conf_sendline_expect(cmd)

                # Exiting line config
                self.conf_sendline_expect("exit")
                self.verify_config(config_local_ssh_commands)

    def conf_local_auth(self):
        config_local_telnet_commands = [
                    "line vty 0 4",
                    "login local"]

        config_local_ssh_commands = [
                    "line vty 5 15",
                    "login local"]

        self.conf_sendline_expect("no aaa new-model")

        for cmd in config_local_telnet_commands:
            self.conf_sendline_expect(cmd)

        # Exiting line config
        self.conf_sendline_expect("exit")
        self.verify_config(config_local_telnet_commands)

        for cmd in config_local_ssh_commands:
            self.conf_sendline_expect(cmd)

        # Exiting line config
        self.conf_sendline_expect("exit")
        self.verify_config(config_local_ssh_commands)

    def conf_remote_auth(self):

        config_remote_commands = [
                "aaa new-model",
                "aaa authentication login default group tacacs+ local-case",
                "aaa authentication enable default group tacacs+ enable",
                "aaa authorization config-commands",
                "aaa authorization exec default group tacacs+ if-authenticated",
                "aaa authorization commands 1 default group tacacs+ if-authenticated",
                "aaa authorization commands 15 default group tacacs+ if-authenticated",
                "aaa accounting exec default start-stop group tacacs+",
                "aaa accounting commands 1 default start-stop group tacacs+",
                "aaa accounting commands 15 default start-stop group tacacs+"
                ]

        for cmd in config_remote_commands:
            self.conf_sendline_expect(cmd)

        self.verify_config(config_remote_commands)

    def configure_login_auth(self, auth_type, login_type, admin, username):
        """Enter configuration mode."""
        self.conf_sendline_expect("config terminal")

        self.conf_login_priv(admin, username)
        self.conf_connection_channel()

        if auth_type == "local":
            self.conf_local_auth()
            self.conf_login_type(login_type)
        else:
            self.conf_remote_auth()

        self.end_config()

    def commit(self):
        """Write config to file."""
        # Filesystem B cannot write to memory
        # Bug in c3845-advipservicesk9-mz.124-11.T1
        #  cannot make config changes after write memory
        if self.filesys_class != "B":
            self.conf_sendline_expect("write memory")

    def end_config(self):
        """Exit from configuration mode."""
        self.conf_sendline_expect("exit")
        # Reconnect before proceeding. New configuration might require
        # username/password pair
        self.cconn.reconnect_and_login()

    def configure_login_auth_reset(self,
                                   username,
                                   syslog_IP,
                                   tacacs_IP,
                                   tacacs_pass="password"):

        config_reset_commands = [
            "logging message-counter syslog",
            "logging trap debugging",
            "logging buffered debugging",
            "logging console debugging",
            "logging monitor debugging",
            "logging origin-id hostname",
            "logging " + syslog_IP,
            "service password-encryption",      # this is needed for ssh
            "login on-failure log",
            "login on-success log",
            "archive",
                "log config",
                    "logging enable",
                    "logging size 500",
                    "notify syslog contenttype plaintext",
                    "hidekeys",
                    "exit",
                "exit",
            "aaa new-model",
            "aaa authentication login default group tacacs+ local-case",
            "aaa authentication enable default group tacacs+ enable",
            "aaa authorization config-commands",
            "aaa authorization exec default group tacacs+ if-authenticated",
            "aaa authorization commands 1 default group tacacs+ if-authenticated",
            "aaa authorization commands 15 default group tacacs+ if-authenticated",
            "aaa accounting exec default start-stop group tacacs+",
            "aaa accounting commands 1 default start-stop group tacacs+",
            "aaa accounting commands 15 default start-stop group tacacs+"
            "tacacs-server host " + tacacs_IP,
            "tacacs-server directed-request",
            "tacacs-server key " + tacacs_pass,
            "no username " + username,
            "username " + username + " password 0 password",
            "line vty 0 4",
                "exec-timeout 2 0",
                "logging synchronous",
                "no password",
                "no privilege level 15",
                "transport input telnet",
                "exit",
            "line vty 5 15",
                "exec-timeout 2 0",
                "logging synchronous",
                "no privilege level 15",
                "transport input ssh"]

        # Enter configuration mode
        self.conf_sendline_expect("configure terminal")

        for cmd in config_reset_commands:
            self.conf_sendline_expect(cmd)

        self.conf_sendline_expect("exit")
        self.verify_config(config_reset_commands)

        self.end_config()

    def configure_acl(self, remote_commands):
        
        config_remote_commands = remote_commands
        logging.debug("Configuring ACLs")

        self.conf_sendline_expect("config terminal")

        for cmd in config_remote_commands:
            self.conf_sendline_expect(cmd)
        
        # To exit from aaa conf mode
        self.conf_sendline_expect("exit")
        #child = self.cconn.reconnect_and_login()
        #self.verify_config(config_remote_commands)

    def configure_acl_reset(self, remote_commands):
        
        config_remote_commands = remote_commands

        self.conf_sendline_expect("config terminal")

        for cmd in config_remote_commands:
            self.conf_sendline_expect(cmd)
        
        # To exit from aaa conf mode
        self.conf_sendline_expect("exit")
        #child = self.cconn.reconnect_and_login()
        #self.verify_config(config_remote_commands)
