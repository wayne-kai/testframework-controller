from VMController import VMController
from EsxiController import EsxiController
import logging
import time
import posixpath
import os


class RemoteHttpGeneratorError(Exception):
    """Exceptions thrown by the remote HTTP traffic generator."""
    pass


class RemoteHttpGenerator(object):
    """Remote HTTP traffic generator."""

    ROBOT_LIBRARY_VERSION = "1.1.0"
    HTTP_GENERATOR_FILENAME = "HttpGenerator.py"

    def __init__(self):
        self.esxi_host = ''
        self.esxi_user = ''
        self.esxi_password = ''
        self.vm_host = ''
        self.vm_user = ''
        self.vm_password = ''
        self.http_generator_path = self.HTTP_GENERATOR_FILENAME
        self.output_log_path = '/tmp/http-generator-output.log'
        self.error_log_path = '/tmp/http-generator-error.log'

    def initialise_remote_http_generator(self,
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
        self.http_generator_path = posixpath.join('/home',
                                                  vm_user,
                                                  self.HTTP_GENERATOR_FILENAME)

    def _upload_http_generator(self, vmc, network):
        """Upload the script to the VM inside a test network."""

        # Get path of the HttpGenerator.py file
        local_script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                         self.HTTP_GENERATOR_FILENAME)

        if not os.path.exists(local_script_path):
            raise IOError(local_script_path + " does not exist")

        logging.debug("Uploading %s to the VM", local_script_path)
        vmc.vm_upload_file(local_script_path, self.http_generator_path)
        logging.info("Successfully uploaded %s to the VM", local_script_path)

    def remote_generate_http_traffic(self,
                                     target_host,
                                     source_network,
                                     connections=32,
                                     http_timeout=3):

        """Generate HTTP traffic to a host via a VM."""

        vm_name = self.vm_host.format(source_network)
        arguments = 'python {:s} --connections {:d} --timeout {:d} {:s} 1> {:s} 2> {:s}'.format(
                self.http_generator_path,
                int(connections),
                int(http_timeout),
                str(target_host),
                self.output_log_path,
                self.error_log_path)

        si = EsxiController()

        si.esxi_initialise(host=self.esxi_host,
                           user=self.esxi_user,
                           password=self.esxi_password)

        try:
            logging.info('Connecting to VM "{:s}"'.format(vm_name))
            vm = si.get_vm_from_name(vm_name)

            vmc = VMController()
            vmc.vmc_initialise(si=si.get_service_instance(),
                               vm=vm,
                               user=self.vm_user,
                               pwd=self.vm_password,
                               interactive=False)

            self._upload_http_generator(vmc, source_network)

            logging.info('Executing "{:s} {:s}" on guest'.format(
                    '/bin/env', arguments))
            pid = vmc.vm_run_program('/bin/env', arguments)

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
                    raise RemoteHttpGeneratorError(
                            "Error executing {:s} on guest\n"
                            "Processes:\n{:s}"
                            "".format(self.http_generator_path,
                                      process_info_list))

                logging.debug("Exit code of process {:d}: {}"
                              "".format(process_info.pid,
                                        process_info.exitCode))
                exit_code = process_info_list[0].exitCode

            stdout_log = vmc.vm_read_file(self.output_log_path)
            stderr_log = vmc.vm_read_file(self.error_log_path)

            logging.info("{:s} executed on guest\n"
                         "Exit code: {}\n"
                         "stdout:\n{:s}\n"
                         "stderr:\n{:s}".format(self.http_generator_path,
                                                exit_code,
                                                stdout_log,
                                                stderr_log))

            if exit_code != 0:
                raise RemoteHttpGeneratorError(
                        "Error executing {:s} on guest\n"
                        "Exit code: {}\n"
                        "Output:\n{:s}\n"
                        "Error:\n{:s}".format(
                            self.http_generator_path,
                            exit_code,
                            stdout_log,
                            stderr_log))
        finally:
            si.esxi_disconnect()
