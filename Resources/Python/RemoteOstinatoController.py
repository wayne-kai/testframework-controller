from VMController import VMController
from EsxiController import EsxiController
import logging
import time
import os


class RemoteOstinatoControllerError(Exception):
    """Exceptions thrown by the remote Ostinato controller."""
    pass


class RemoteOstinatoController(object):
    """Remote Ostinato controller. Controls an Ostinato drone over ESXI."""

    ROBOT_LIBRARY_VERSION = "1.0.0"

    user_home_dir = '/home/user'
    ostinato_pyenv_path = os.path.join(user_home_dir, 'pyenv', 'ostinato')
    ostinatocontroller_name = "OstinatoController.py"
    bash_path = '/usr/bin/bash'
    ostinatocontroller_path = os.path.join(user_home_dir, ostinatocontroller_name)
    stdout_log_path = '/tmp/OstinatoController-stdout.log'
    stderr_log_path = '/tmp/OstinatoController-stderr.log'

    def __init__(self):
        self.esxi_host = ''
        self.esxi_user = ''
        self.esxi_password = ''
        self.vm_host = ''
        self.vm_user = ''
        self.vm_password = ''

    def _init_esxi(self):
        """Initialize a EsxiController instance."""

        si = EsxiController()
        si.esxi_initialise(host=self.esxi_host,
                           user=self.esxi_user,
                           password=self.esxi_password)
        return si

    def _init_vmc(self, si, testnet):
        """
        Returns a new VMController instance for the test VM within the testnet
        network.
        """
        vm_name = self.vm_host.format(testnet)
        logging.info('Connecting to VM "{:s}"'.format(vm_name))
        vm = si.get_vm_from_name(vm_name)
        vmc = VMController()
        vmc.vmc_initialise(
                si=si.get_service_instance(),
                vm=vm,
                user=self.vm_user,
                pwd=self.vm_password,
                interactive=False)

        return vmc

    def initialise_remote_traffic_generator(
            self, esxi_host, esxi_user, esxi_password, vm_host, vm_user,
            vm_password):
        self.esxi_host = esxi_host
        self.esxi_user = esxi_user
        self.esxi_password = esxi_password
        self.vm_host = vm_host
        self.vm_user = vm_user
        self.vm_password = vm_password

    def initialise_generator_in_network(self, network):
        """Initialise Ostinato Controller on VM inside network."""
        si = self._init_esxi()

        # Get path of this script
        this_file_pathname = os.path.realpath(__file__)
        this_file_dir = os.path.dirname(this_file_pathname)
        local_script_path = os.path.join(this_file_dir, 'OstinatoController.py')
        if not os.path.exists(local_script_path):
            raise RemoteOstinatoControllerError(
                    "Ostinato controller not found at " + local_script_path)

        try:
            vmc = self._init_vmc(si, network)
            logging.info("Uploading %s to the VM", local_script_path)
            vmc.vm_upload_file(local_script_path, self.ostinatocontroller_path)
            logging.info("Successfully uploaded %s to the VM", local_script_path)
        finally:
            si.esxi_disconnect()

    def _remote_run_script(self, source_network, args):
        arguments = '-c "source {:s} && python {:s} {:s} 1> {:s} 2> {:s}"'.format(
                os.path.join(self.ostinato_pyenv_path, 'bin', 'activate'),
                self.ostinatocontroller_path,
                ' '.join(args),
                self.stdout_log_path,
                self.stderr_log_path)

        si = self._init_esxi()

        try:
            vmc = self._init_vmc(si, source_network)

            logging.info('Executing "{:s} {:s}" on guest'.format(
                    self.bash_path, arguments))
            pid = vmc.vm_run_program(self.bash_path, arguments)

            logging.debug("PID: {}".format(pid))

            # Wait for process to end
            exit_code = None
            while exit_code is None:
                time.sleep(1)

                # Obtain ProcessInfo of a single process with the PID
                process_info_list = vmc.vm_get_processinfo_list(pids=[pid])
                logging.debug(
                        "Processes with PID {:d}\n{:s}".format(
                            pid, process_info_list))

                if len(process_info_list) == 1:
                    process_info = process_info_list[0]
                else:
                    raise RemoteOstinatoControllerError(
                            "Error executing {:s} on guest\n"
                            "Processes:\n{:s}"
                            "".format(self.ostinatocontroller_path,
                                      process_info_list))

                logging.debug("Exit code of process {:d}: {}"
                              "".format(process_info.pid,
                                        process_info.exitCode))
                exit_code = process_info_list[0].exitCode

            stdout_log = vmc.vm_read_file(self.stdout_log_path)
            stderr_log = vmc.vm_read_file(self.stderr_log_path)

            logging.info(
                "{:s} executed on guest\n"
                "Exit code: {}\n"
                "stdout:\n{:s}\n"
                "stderr:\n{:s}".format(
                        self.ostinatocontroller_path, exit_code, stdout_log,
                        stderr_log))

            if exit_code != 0:
                raise RemoteOstinatoControllerError(
                        "Error executing {:s} on guest\n"
                        "Exit code: {}\n"
                        "Output:\n{:s}\n"
                        "Error:\n{:s}".format(
                            self.ostinatocontroller_path,
                            exit_code,
                            stdout_log,
                            stderr_log))
        finally:
            si.esxi_disconnect()

    def configure_traffic_generator(self, source_network, port_id, target_host, packets_per_burst=None):
        """Configure the network generator to transmit to a host."""

        args = ['configure']
        if packets_per_burst:
            args.append('--burstsize')
            args.append(str(packets_per_burst))

        args.append(str(port_id))
        args.append(str(target_host))

        self._remote_run_script(source_network, args)

    def start_traffic_generator(self, source_network, port_id):
        """Start generating traffic."""

        args = ['start', str(port_id)]
        self._remote_run_script(source_network, args)

    def stop_traffic_generator(self, source_network, port_id):
        """Stop generating traffic."""

        args = ['stop', str(port_id)]
        self._remote_run_script(source_network, args)

    def clear_traffic_generator(self, source_network, port_id):
        """Clear the network generator's configuration."""

        args = ['delete', str(port_id)]
        self._remote_run_script(source_network, args)
