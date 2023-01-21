import logging
import requests
import time
from pyVmomi import vim


#  VMController require vmtools to be running in order to perform many of its
#  functions
#  VMtools will automatically be installed if it is not already installed
#  However, Vmtools will only be running when the vm os is running.
#  To do so make sure that the VM is already log in.
#  To ensure that VMController work correctly, set the VMs such that they will
#  login automatically
class VMController:

    def __init__(self):
        self.si = None
        self.vm = None
        self.user = None
        self.pwd = None
        self.default_interactive_mode = None

    def vmc_initialise(self, si, vm, user, pwd, interactive=False):
        self.si = si
        self.vm = vm
        self.user = user
        self.pwd = pwd
        self.default_interactive_mode = interactive

    def set_default_interactive(self, interactive):
        self.default_interactive_mode = interactive

    def _get_auth(self, interactive=None):
        inact_mode = None
        if interactive:
            inact_mode = interactive
        else:
            inact_mode = self.default_interactive_mode

        return vim.vm.guest.NamePasswordAuthentication(
                                        username=self.user,
                                        password=self.pwd,
                                        interactiveSession=inact_mode)

    def _check_vmtools(self):
        """Check status of VMTools and install if required."""

        # Wait for VM to be in ready state before checking for vmtools
        # (VMtools could be loaded after os is ready)
        self._wait_for_guest_operations()

        logging.debug(
                "VMTools Checking status: [{:s}]"
                "".format(self.vm.guest.toolsStatus))

        if self.vm.guest.toolsStatus != "toolsOk":
            logging.info("VMTools Installing")
            self._install_vmtools()

    def _wait_for_guest_operations(self, timeout=600):
        """Wait for guest operations to be in ready state."""

        if self.vm.guest.guestState == "notRunning":
            raise ValueError("VM not in running state")

        for i in range(timeout):
            if self.vm.guest.guestOperationsReady:
                logging.debug("Guest Operations Ready")
                return
            else:
                time.sleep(1)

        raise ValueError(
            "_wait_for_guest_operations timeout: {:d}. VM Guest[{:s}]".format(
                            timeout,
                            self.vm.guest)
                         )

    def _wait_for_interactive_guest_operations(self, timeout=600):

        for i in range(timeout):
            if self.vm.guest.interactiveGuestOperationsReady:
                logging.debug("Interactive Guest Operations Ready")
                return
            else:
                time.sleep(1)

        raise ValueError(
            "_wait_for_interactive_guest_operations timeout: {:d}. VM Guest[{:s}]".format(
                            timeout,
                            self.vm.guest)
                         )

    def _wait_for_vmtools(self, timeout=600):
        """Wait for VMTools to be ready."""
        for i in range(timeout):
            if self.vm.guest.toolsStatus == "toolsOk":
                logging.debug("VMTools Ready")
                return
            else:
                time.sleep(1)

        raise ValueError(
            "wait_for_vm_tools timeout: {:d}. VM Guest[{:s}]".format(
                            timeout,
                            self.vm.guest)
                         )

    def install_vmtools(self):
        """Check if vm tools are available if not install them."""

        self._wait_for_guest_operations()

        if self.vm.runtime.toolsInstallerMounted is True:
            logging.debug("VMTools already Mounted. Unmounting...")
            self.vm.UnmountToolsInstaller()
            self._wait_for_guest_operations()

        self.vm.MountToolsInstaller()
        self._wait_for_vmtools()
        logging.debug("VMTools Installed")
        self._wait_for_guest_operations()

        if self.vm.runtime.toolsInstallerMounted is True:
            logging.debug("Install complete. Unmounting VMTools CD")
            self.vm.UnmountToolsInstaller()
            self._wait_for_guest_operations()

    def vm_wait_for_process(self,
                            process_name,
                            interactive=None,
                            nocase=False,
                            wait_interval=10,
                            wait_count=30):
        """Wait for process to spawn in VM"""

        if interactive:
            self._wait_for_interactive_guest_operations()

        found_process = None
        for i in range(wait_count):
            found_process = self.vm_find_process_name(
                    process_name, nocase=nocase)
            if found_process:
                return found_process
            else:
                time.sleep(wait_interval)

        raise ValueError(
                "vm_wait_for_process timeout: i[{:d}]c[{:d}]"
                "".format(wait_interval, wait_count))

    def vm_wait_for_process_complete(self, pid, timeout):
        exit_code = None
        timer_count = 0
        while exit_code is None:
            time.sleep(1)
            logging.debug("Timer: {}".format(timeout))
            if timer_count > timeout:
                raise ValueError(
                    "vm_wait_for_process_complete "
                    "timeout [{}]".format(timeout))
            else:
                timer_count += 1
            
            # Obtain ProcessInfo of a single process with the PID
            process_info_list = self.vm_get_processinfo_list(pids=[pid])
            logging.debug(
                    "Processes with PID {:d}\n{:s}".format(
                    pid, process_info_list))

            if len(process_info_list) != 1:
                raise ValueError(
                    "vm_wait_for_process_complete "
                    "{} process found with pid [{}]"
                    .format(len(process_info_list), pid))

            exit_code = process_info_list[0].exitCode

        return exit_code

    def vm_find_process_name(self,
                             process_name,
                             interactive=None,
                             filter_pids=None,
                             nocase=False):
        """Find a process in VM by name."""
        self._check_vmtools()

        if interactive:
            self._wait_for_interactive_guest_operations()

        pm = self.si.content.guestOperationsManager.processManager
        processes = pm.ListProcessesInGuest(
                vm=self.vm,
                auth=self._get_auth(interactive),
                pids=filter_pids)

        for process in processes:
            if nocase:
                if process.name.lower() == process_name.lower():
                    return process
            else:
                if process.name == process_name:
                    return process

        return None

    def vm_get_processinfo_list(self, interactive=None, pids=None):
        """
        Obtain list of processes in VM.

        pids: If set, only return information about specified processes.
        """
        self._check_vmtools()

        if interactive:
            self._wait_for_interactive_guest_operations()

        pm = self.si.content.guestOperationsManager.processManager
        return pm.ListProcessesInGuest(
                vm=self.vm,
                auth=self._get_auth(interactive),
                pids=pids)

    def vm_get_process_list(self, interactive=None):
        """Obtain a string listing the processes in VM."""
        processes = self.vm_get_processinfo_list(interactive=interactive)

        processes_str = ""
        for process in processes:
            processes_str += "{:s}".format(process)

        logging.debug("Process List[{:s}]".format(processes_str))
        return processes_str

    def vm_download_file(self, src_vm_path, dst_local_path, interactive=None):
        """Download a file from VM."""
        self._check_vmtools()

        if interactive:
            self._wait_for_interactive_guest_operations()

        fm = self.si.content.guestOperationsManager.fileManager
        # Initiate File transfer
        ft_info = fm.InitiateFileTransferFromGuest(
                self.vm, self._get_auth(interactive), src_vm_path)

        resp = requests.get(ft_info.url, verify=False)
        if resp.status_code == 200:
            content = resp.text
            with open(dst_local_path, 'wb') as local_file:
                local_file.write(content)
            logging.info("Download successful")
        else:
            raise ValueError("Error download file: resp[{:s}]".format(resp))

    def vm_read_file(self, src_vm_path, interactive=None):
        """Read a file from VM."""
        self._check_vmtools()

        if interactive:
            self._wait_for_interactive_guest_operations()

        fm = self.si.content.guestOperationsManager.fileManager
        # Initiate File transfer
        ft_info = fm.InitiateFileTransferFromGuest(
                self.vm, self._get_auth(interactive), src_vm_path)

        resp = requests.get(ft_info.url, verify=False)
        if resp.status_code == 200:
            logging.debug("File Content[{}]".format(resp.text))
            return resp.text
        else:
            raise ValueError("Error reading file: resp[{:s}]".format(resp))

    def vm_upload_file(self,
                       local_path,
                       vm_path,
                       interactive=None,
                       overwrite=True):
        """Upload a file to VM."""
        self._check_vmtools()

        if interactive:
            self._wait_for_interactive_guest_operations()

        # Read file content
        file_content = ""
        with open(local_path, 'rb') as local_file:
            file_content = local_file.read()

        if len(file_content) <= 0:
            raise ValueError(
                    "Local Path [{:s}] content length less than or "
                    "equal 0".format(local_path))

        # Create File Attribute
        file_attribute = vim.vm.guest.FileManager.FileAttributes()

        fm = self.si.content.guestOperationsManager.fileManager

        # Initiate File transfer
        logging.debug(
                "Auth[{:s}], VM_Path[{:s}], File_Attribute[{:s}], len[{:d}], "
                "overwrite[{}]"
                "".format(
                    self._get_auth(interactive),
                    vm_path,
                    file_attribute,
                    len(file_content),
                    overwrite))
        url = fm.InitiateFileTransferToGuest(
                self.vm,
                self._get_auth(interactive),
                vm_path,
                file_attribute,
                len(file_content),
                overwrite)

        resp = requests.put(url, data=file_content, verify=False)

        if resp.status_code == 200:
            logging.info("Upload successful")
        else:
            raise ValueError("Error uploading file: resp[{:s}]".format(resp))

    def vm_run_program(self,
                       program_path,
                       program_arguments,
                       interactive=None,
                       working_dir=None):
        """Run a program in VM."""

        logging.debug(
                "path[{:s}], args[{:s}], working_dir[{:s}]"
                "".format(program_path, program_arguments, working_dir))

        # Check if vm tools are available if not install them
        self._check_vmtools()

        pm = self.si.content.guestOperationsManager.processManager
        program_spec = vim.vm.guest.ProcessManager.ProgramSpec(
                programPath=program_path,
                arguments=program_arguments,
                workingDirectory=working_dir)

        # Check if vm tools are available if not install them
        self._check_vmtools()
        # Wait for guest operations to be ready before running the program
        self._wait_for_guest_operations()
        logging.debug("[{:s}]".format(program_spec))

        if interactive:
            self._wait_for_interactive_guest_operations()

        # Run the program in vm
        process_id = pm.StartProgramInGuest(self.vm,
                                            self._get_auth(interactive),
                                            program_spec)

        return process_id
