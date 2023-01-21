import re
import logging
import pexpect
import time
import os
from contextlib import contextmanager

from CiscoControllerLib import (
        get_router_running_image, process_copy_verify_firmware, process_delete_file, get_image_md5)
from Common import (spawn_and_print, expect_and_print, ping_wait)
from CiscoConnection import CiscoConnection
from CiscoConfigure import CiscoConfigure
from CiscoLogging import CiscoLogging
from CiscoCmdDescriptor import CiscoCmdDescriptor


class CiscoController(object):

    def __init__(self):

        self.router_ip = None
        self.hostname = None
        self.test_user = None
        self.password = None
        self.en_password = None
        self.conf_user = None
        self.conf_pass = None
        self.conf_en_pass = None
        self.output_file_path = None
        self.tacacs_ip = None
        self.syslog_ip = None
        self.snmp_ip = None

        self.protocol = "telnet"
        self.acl_config_protocol = None    # ACL's router configuring protocol
        self.acl_enabled = None    # If ACL test case is enabled

        self.default_timeout = 300
        self.memory_timeout = 1200
        self.reboot_timeout = 600
        self.firmware_timeout = 600

        # For describing expected output of cisco commands
        self.test_cmds_dscrptors = list()

        self.clog = None    # CiscoLogging class

        self.filesys_class = None

    def initialise_controller(self, router_ip, router_name):
        self.router_ip = router_ip
        self.hostname = router_name

    def set_database_ip(self, tacacs_ip, syslog_ip, snmp_ip):
        self.tacacs_ip = tacacs_ip
        self.syslog_ip = syslog_ip
        self.snmp_ip = snmp_ip

    def set_timeout(self, default, memory=None, reboot=None, firmware=None):
        if default:
            self.default_timeout = int(default)
        if memory:
            self.memory_timeout = int(memory)
        if reboot:
            self.reboot_timeout = int(reboot)
        if firmware:
            self.firmware_timeout = int(firmware)

    def set_credentials(self, test_user, test_pass, test_en_pass):
        self.password = test_pass
        self.test_user = test_user
        self.en_password = test_en_pass

    def set_config_credentials(self, config_user, config_pass, config_en_pass):
        self.conf_user = config_user
        self.conf_pass = config_pass
        self.conf_en_pass = config_en_pass

    def set_default_protocol(self, protocol):
        if protocol.lower() == "telnet" or protocol.lower() == "ssh":
            self.protocol = protocol
        else:
            raise ValueError("No such protocol: " + protocol)

    def set_config_protocol(self, protocol):
        if protocol.lower() == "telnet" or protocol.lower() == "ssh":
            self.acl_config_protocol = protocol
        else:
            raise ValueError("No such protocol: " + protocol)

    def set_acl_enabled(self, acl_enabled):
        self.acl_enabled = acl_enabled

    def set_filesystem_class(self, fs_class):
        self.filesys_class = fs_class

    def set_remote_commands(self, remote_commands):
        self.remote_commands = remote_commands

    @contextmanager
    def _get_conf_connection(self, protocol, acc_type=None):
        """
        Returns a CiscoConnection instance initialised with super user
        credentials.
        """
        if acc_type != None and acc_type.lower() == "legit":
            protocol = self.acl_config_protocol;
        elif self.acl_config_protocol != None:
            protocol = self.acl_config_protocol
        if protocol == None:
            protocol = self.protocol

        cconn = CiscoConnection(protocol,
                                self.router_ip,
                                self.conf_user,
                                self.conf_pass,
                                self.conf_en_pass,
                                self.hostname,
                                self.default_timeout)

        try:
            yield cconn
        finally:
            #   Close connection
            cconn.disconnect()

    @contextmanager
    def _get_connection(self, protocol, acc_type=None):
        """
        Returns a CiscoConnection instance initialised with normal credentials.
        """
        if acc_type != None and acc_type.lower() == "legit":
            protocol = self.acl_config_protocol;
        elif self.acl_config_protocol != None:
            protocol = self.acl_config_protocol
        if protocol == None:
            protocol = self.protocol

        cconn = CiscoConnection(protocol,
                                self.router_ip,
                                self.test_user,
                                self.password,
                                self.en_password,
                                self.hostname,
                                self.default_timeout)

        try:
            yield cconn
        finally:
            #   Close connection
            cconn.disconnect()

    def start_tracking_logs(self, log_check_list, protocol=None):

        # Connect and login
        with self._get_conf_connection(protocol) as cconn:

            self.clog = CiscoLogging(self.tacacs_ip, self.syslog_ip, self.snmp_ip)
            self.clog.logging_start(cconn, log_check_list)

    def retrieve_logs(self, log_check_list, protocol=None):

        # Additional sleep to allow time for SNMP to be flush out
        logging.debug("### SNMP Flush out before retrieving log (experimental)  ###")
        logging.debug("Waiting for SNMP to flush itself...")
        time.sleep(120)
        logging.debug("Waiting for SNMP to flush itself... DONE")

        # Connect and login
        with self._get_conf_connection(protocol) as cconn:
            self.clog.logging_retrieve(cconn, log_check_list, self.test_user)

    def get_log_output(self, log_type):

        log_output = ""

        if log_type.lower() == "buffered":
            log_output = self.clog.get_buffered_log()
        elif log_type.lower() == "tacacs access":
            log_output = self.clog.get_tacacs_access_log()
        elif log_type.lower() == "tacacs account":
            log_output = self.clog.get_tacacs_accounting_log()
        elif log_type.lower() == "syslog":
            log_output = self.clog.get_syslog_log()
        elif log_type.lower() == "snmp":
            log_output = self.clog.get_snmp_log()
        elif log_type.lower() == "history all":
            log_output = self.clog.get_history_all_log()
        elif log_type.lower() == "archive log":
            log_output = self.clog.get_archive_log()

        if log_output:
            log_output = log_output.strip()

        return log_output

    def create_test_cmd(self, cmd):
        return CiscoCmdDescriptor(cmd)

    def add_test_cmd_criteria(self,
                              test_cmd,
                              should_contain=None,
                              should_not_contain=None,
                              should_begin_with=None,
                              should_end_with=None,
                              should_match_regex=None,
                              should_be_empty=None):

        test_cmd.add_criteria(should_contain,
                              should_not_contain,
                              should_begin_with,
                              should_end_with,
                              should_match_regex,
                              should_be_empty)

    def run_cmd_until_next_shell(self, cconn, cmd, no_shell_prompt=False):

        #   Send test cmd with return carriage
        cconn.sendline(cmd)

        cmd_out = ""
        if no_shell_prompt == False:

            #   Governs the failsafe mechanism for the while loop below
            noOfLoopsOccurred = 0
            maxNoOfLoops = 10

            #   Loop until the next command line shell of the Cisco device has
            #   been reached
            while (noOfLoopsOccurred == 0) or (re.match("{}[^\s]*#".format(self.hostname), cconn.after()) is None):

                cconn.expectline(("(\[[yY]es\/[nN]o\]|{}[^\s]*#|\[confirm\])").format(self.hostname))

                #   Concat all the outputs into one variable
                #   till the point before the command shell is hit again
                #   NOTE:   cconn.before() gives the string from the
                #           start / previous expect() until the next expect string
                #           (not inclusive)
                cmd_out += cconn.before()

                #   Perform additional command send to get the execution
                #   to end with a command line shell instead of prompts
                #   NOTE:   .lower() to make the case insensitive for string
                #           comparison
                if "[yes/no]" in cconn.after().lower():
                    cconn.sendline("n")
                elif "[confirm]" in cconn.after().lower():
                    cconn.send("n")

                #   Failsafe mechanism for this loop in case it goes into an
                #   infinite loop
                noOfLoopsOccurred += 1
                if noOfLoopsOccurred > maxNoOfLoops:
                    logging.debug("Looping has exceeded {} times".format(maxNoOfLoops))
                    break

        return cmd_out

    def run_test_cmd(self, test_cmd, protocol=None, acc_type=None):

        #   Connect and login
        with self._get_connection(protocol, acc_type) as cconn:
            #   Loop until the next command line shell of the Cisco device has
            #   been reached
            cmd_out = self.__run_cmd_until_next_shell(cconn, test_cmd.cmd)

            retmsg = ""
            # Parse output and remove the cmd entered
            if cmd_out.startswith(test_cmd.cmd):
                cmd_out = cmd_out[len(test_cmd.cmd):].lstrip('\r\n')

            errmsg = test_cmd.parse_cmd_output(cmd_out)
            if len(errmsg) == 0:
                retmsg = "\n[+][{}] succeed\n".format(test_cmd.cmd)
                logging.info(retmsg)
            else:
                retmsg = "\n[-][{}] failed\n{}\nout[{}]".format(test_cmd.cmd, errmsg, cmd_out)
                logging.info(retmsg)
                logging.debug("run_test_cmd for {} failed, output: {}".format(test_cmd.cmd, cmd_out))
                raise ValueError("run_test_cmd failed: " + retmsg)

    def run_command_and_get_output(self,
                                   cmd,
                                   protocol=None,
                                   no_shell_prompt=False, acc_type=None):

        #   Connect and login
        with self._get_connection(protocol, acc_type) as cconn:

            #   len of <"hostname><"'>'|'#'"><"cmd"> more than 78 characters ->
            #   cmds will be truncated
            if (len(self.hostname) + 1 + len(cmd)) > 78:
                logging.info(cmd+"\n")

            return self.__run_cmd_until_next_shell(cconn, cmd)

    def run_commands_list(self,
                          cmds_list,
                          protocol=None,
                          no_shell_prompt=False):

        all_cmd_out = []

        #   Connect and login
        with self._get_connection(protocol) as cconn:

            # execute the test commands
            for cmd in cmds_list:
                # len of <"hostname><"'>'|'#'"><"cmd"> more than 78 characters ->
                #  cmds will be truncated

                if (len(self.hostname) + 1 + len(cmd)) > 78:
                    logging.info(cmd+"\n")

                cmd_out = self.__run_cmd_until_next_shell(cconn, cmd, no_shell_prompt)
                all_cmd_out.append(cmd_out)
                logging.debug('cmd_out: {:s}'.format(cmd_out))
                    
                if(no_shell_prompt == True):
                    time.sleep(1)

            if(no_shell_prompt == True):
                cconn.expect_hostname()            
                logging.info(cconn.before()+"\n")

        return all_cmd_out

    def cisco_delete_file(self, router_file_path, protocol=None):

        # Connect and login
        with self._get_connection(protocol) as cconn:

            cconn.sendline("delete " + router_file_path)
            cconn.expectline("Delete filename \[\S*\]?")
            cconn.sendline()
            cconn.expectline("Delete \S*? \[confirm]")
            cconn.sendline()

    def cisco_view_file(self, router_file_path, protocol=None):

        # Connect and login
        with self._get_connection(protocol) as cconn:

            return self.__run_cmd_until_next_shell(cconn,
                                                   "more {:s}".format(router_file_path))

    def run_script(self, path, cmd_args=[], expect_status=None):

        script_dir = os.path.dirname(os.path.abspath(path))
        logging.debug('script_dir: {:s}'.format(script_dir))

        original_dir = os.getcwd()
        logging.debug('original_dir: {:s}'.format(original_dir))

        #   Change to script directory
        os.chdir(script_dir)

        # append basename to top of the list
        child = spawn_and_print("sh", [os.path.basename(path)] + cmd_args)

        #   This was added specifically for running memory injection script
        #   so that expect script will print out the status
        #   instead of waiting for the entire injection to complete
        while child.after != pexpect.EOF:
            expect_and_print(child, [pexpect.EOF], self.memory_timeout)

        #   Change back to original directory
        os.chdir(original_dir)

        #   Close the child's process
        child.close()

        if child.exitstatus > 0:
            raise ValueError(
                    "Run script: script exit with an error code {}"
                    "".format(child.exitstatus))

        return 0

    def reboot(self, protocol=None):
        """Reboot using "user" credential"""

        # Connect and login
        # Reboot should be using config-user for now
        with self._get_conf_connection(protocol) as cconn:

            cconn.sendline("reload")
            cconn.expectline("(Proceed with reload\?|System configuration has been modified)")
            if "System configuration" in cconn.after():
                cconn.sendline("n")
                cconn.expectline("Proceed with reload\?")

            # Proceed with reload
            cconn.sendline("y")
            cconn.expectline(pexpect.EOF)

        # Wait for the router to reboot
        print("\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n")
        # wait for 10s for the router to reboot. We need this because router
        # can still be pinged
        time.sleep(10)
        ping_wait(self.router_ip, self.reboot_timeout)

        return 0

    def replace_firmware(self,
                         ftp_firmware_path,
                         protocol=None):
        logging.info("Replacing firmware")

        # Connect and login
        with self._get_conf_connection(protocol) as cconn:
            # Get path of firmware running image
            image_path = get_router_running_image(cconn)

            # Get the local path based on the src firmware_path
            base_name = os.path.basename(ftp_firmware_path) 
            local_dst_path = "flash:" + base_name

            # Delete the running image             
            process_delete_file(cconn, self.filesys_class, image_path)

            # Copy the firmware and verify
            process_copy_verify_firmware(cconn,
                                         self.filesys_class,
                                         ftp_firmware_path,
                                         local_dst_path,
                                         cconn.hostname,
                                         self.firmware_timeout)

    def replace_running_config(self, replace_path, protocol=None):

        # Connect and login
        with self._get_conf_connection(protocol) as cconn:
            cconfig = CiscoConfigure(cconn, self.filesys_class)
            cconfig.configure_replace_running(replace_path)

    def replace_startup_config(self, replace_path, protocol=None):

        # Connect and login
        with self._get_conf_connection(protocol) as cconn:
            cconfig = CiscoConfigure(cconn, self.filesys_class)
            cconfig.configure_replace_startup(replace_path)

    # Types of configure:
    #  1. CONF_RESET
    #  2. CONF_LOCAL_UIDPASS_ADMIN
    #  3. CONF_LOCAL_UIDPASS_USR
    #  4. CONF_LOCAL_PASS_ADMIN
    #  5. CONF_LOCAL_PASS_USR
    #  6. CONF_LOCAL_NOUIDPASS_ADMIN
    #  7. CONF_LOCAL_NOUIDPASS_USR
    #  8. CONF_REMOTE_UIDPASS_ADMIN
    #  9. CONF_REMOTE_UIDPASS_USR
    def configure(self, config_option, acc_type=None):
        # Connect and login
        with self._get_conf_connection(self.protocol, acc_type) as cconn:
            cconfig = CiscoConfigure(cconn, self.filesys_class)

            logging.debug('config_option: {:s}'.format(config_option))

            logging.info("\n**************************\n" + config_option + "\n**************************\n")

            #   Check to make sure that the test_user variable has been set
            if self.test_user.strip() == "":
                raise ValueError("Configure Router: Test Credential not set.")

            if config_option == "CONF_RESET":
                cconfig.configure_login_auth_reset(self.test_user,
                                                   self.syslog_ip,
                                                   self.tacacs_ip)
            elif config_option == "CONF_ACL":
                cconfig.configure_acl(self.remote_commands)
            elif config_option == "CONF_ACL_RESET":
                cconfig.configure_acl_reset(self.remote_commands)
            else:
                auth_type = ""
                login_type = ""
                admin = 0

                # Set Authentication type
                if "_LOCAL" in config_option:
                    auth_type = "local"
                elif "_REMOTE" in config_option:
                    auth_type = "remote"
                else:
                    logging.info("[-]ERROR: CONFIG unknown authentication type")
                    raise ValueError("Configure Router: Unknown auth type\n")

                # Set login type
                if "_UIDPASS" in config_option:
                    login_type = "LOGINLOCAL"
                elif "_PASS" in config_option:
                    login_type = "PASSONLY"
                elif "_NOUIDPASS" in config_option:
                    login_type = "NOLOGIN"
                else:
                    logging.info("[-]ERROR: CONFIG unknown login type")
                    raise ValueError("Configure Router: Unknown login type\n")

                # set privilege type
                if "_ADMIN" in config_option:
                    admin = 1
                elif "_USR" in config_option:
                    admin = 0
                else:
                    logging.info("[-]ERROR: CONFIG not _ADMIN or _USR")
                    raise ValueError("Configure Router: Unknown privilege type\n")

                cconfig.configure_login_auth(
                        auth_type, login_type, admin, self.test_user)

            # to verify output
            cconn.sendline_and_expect_hostname("show run")

            # commit config changes
            cconfig.commit()

        time.sleep(1)   # Give some time for the logs to generate

        return 0

    #   Change the function to private
    __run_cmd_until_next_shell = run_cmd_until_next_shell
