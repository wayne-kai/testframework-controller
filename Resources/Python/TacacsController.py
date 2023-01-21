from VMController import VMController
from EsxiController import EsxiController
import logging
import time
from contextlib import contextmanager


class TacacsControllerError(Exception):
    """Errors in TacacsController."""


class TacacsController(object):
    """Controls a TACACS server VM."""

    TAC_PLUS_NAME = 'tac_plus'
    VALID_SERVICE_CMDS = (
        'start', 'stop', 'status', 'restart', 'reload', 'test')
    # Interval for polling a VM process' status
    POLLING_INTERVAL = 1

    def __init__(self):
        self.esxi_host = ''
        self.esxi_user = ''
        self.esxi_password = ''
        self.vm_host = ''
        self.vm_user = ''
        self.vm_password = ''
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def _init_esxi(self):
        """Initialize a EsxiController instance."""

        si = EsxiController()
        si.esxi_initialise(host=self.esxi_host,
                           user=self.esxi_user,
                           password=self.esxi_password)
        yield si
        si.esxi_disconnect()

    def _init_vmc(self, si):
        """Returns a new VMController instance for the TACACS VM."""
        vmc = VMController()
        self.logger.info('Connecting to VM "{:s}"'.format(self.vm_host))
        vmc.vmc_initialise(si=si.get_service_instance(),
                           vm=si.get_vm_from_name(self.vm_host),
                           user=self.vm_user,
                           pwd=self.vm_password,
                           interactive=False)
        return vmc

    def initialise_tacacs_controller(self,
                                     esxi_host,
                                     esxi_user,
                                     esxi_password,
                                     vm_host,
                                     vm_user,
                                     vm_password):
        self.esxi_host = esxi_host
        self.esxi_user = esxi_user
        self.esxi_password = esxi_password
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password

    def _get_tacacs_service_process(self, vmc):
        """Returns an instance of the tac_plus process.

        Returns None if process is not found."""
        return vmc.vm_find_process_name(self.TAC_PLUS_NAME)

    def _is_tacacs_service_running(self, vmc):
        """Returns True if tac_plus service is running, False otherwise."""
        return (self._get_tacacs_service_process(vmc) is not None)

    def is_tacacs_service_running(self):
        """Returns True if tac_plus service is running, False otherwise."""
        with self._init_esxi() as si:
            return self._get_tacacs_service_process(self._init_vmc(si))

    def get_tacacs_service_process(self):
        """Returns True if tac_plus service is running.

        Returns None if process is not found."""
        with self._init_esxi() as si:
            return self._get_tacacs_service_process(self._init_vmc(si))

    def ensure_tacacs_service_is_running(self):
        """Checks if Tacacs service is running and restart it if it is not."""
        with self._init_esxi() as si:
            vmc = self._init_vmc(si)
            if self._is_tacacs_service_running(vmc) is True:
                self.logger.info("Tacacs service is running")
            else:
                self.logger.warning("Tacacs service is not running")
                self.logger.info("Restarting Tacacs service")
                self._run_service_command(vmc, self.TAC_PLUS_NAME, 'restart')

                if self._is_tacacs_service_running(vmc) is True:
                    self.logger.warning("Tacacs service has been restarted")
                else:
                    raise TacacsControllerError(
                            "Tacacs service failed to start")

    def _run_service_command(self, vmc, service_name, command):
        """Run the command "service" with the given command on a service."""

        if command not in self.VALID_SERVICE_CMDS:
            raise ValueError('Invalid service command "%s"', command)

        self.logger.info('Sending %s command to service %s',
                         command,
                         service_name)

        # Call the 'service' command
        args = 'service {:s} {:s}'.format(service_name, command)
        pid = vmc.vm_run_program('/bin/env', args)

        self.logger.debug("Polling until the command finish running")

        exit_code = None
        while exit_code is None:
            proclist = vmc.vm_get_processinfo_list(pids=[pid])
            if len(proclist) != 1:
                # Unlikely to have multiple processes with the same PID, but
                # an error condition nonetheless
                raise TacacsControllerError("Expecting process pid {:d}, found"
                                            " {:d} processes with pid"
                                            "".format(pid, len(proclist)))

            exit_code = proclist[0].exitCode

            if exit_code is None:
                # Process is still running
                self.logger.debug("No exit code, sleeping")
                time.sleep(self.POLLING_INTERVAL)
            else:
                self.logger.debug(
                        "Exit code of PID {:d}: {:d}".format(pid, exit_code))

        if exit_code != 0:
            raise TacacsControllerError("Tacacs service failed to %s with code"
                                        " %d",
                                        command,
                                        exit_code)

    def _tacacs_service_command(self, command):
        with self._init_esxi() as si:
            vmc = self._init_vmc(si)
            self._run_service_command(vmc, self.TAC_PLUS_NAME, command)

    def start_tacacs_service(self):
        """Start the tac_plus service."""
        self.logger.info('Starting ' + self.TAC_PLUS_NAME)
        self._tacacs_service_command('start')

    def stop_tacacs_service(self):
        """Stop the tac_plus service."""
        self.logger.info('Stopping ' + self.TAC_PLUS_NAME)
        self._tacacs_service_command('stop')

    def restart_tacacs_service(self):
        """Restart the tac_plus service."""
        self.logger.info('Restarting ' + self.TAC_PLUS_NAME)
        self._tacacs_service_command('restart')
