import logging
import atexit
import time
import re
from httplib import BadStatusLine
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect

"""
Service Instance wrapper class written to address httplib2 issue
Httplib2 issue #250. Server side close the connection
causing an exception BadStatusLine "".
Workaround is to reconnect.
EsxiServiceInstanceHelper will automatically handles
ServiceInstance object's BadStatusLine exception by reconnecting
and attempt to run the callee again
"""
class EsxiServiceInstanceHelper:

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.pwd = password
        
        self.si = None

    def _connect(self):
        logging.debug(
                "Connecting to ESXI at [{:s}] with username [{:s}]"
                "".format(self.host, self.user))
        self.si = SmartConnect(host=self.host, user=self.user, pwd=self.pwd)
        # safe guard: disconnect on exit
        atexit.register(Disconnect, self.si)

    def _disconnect(self):
        if self.si:
            logging.debug("Disconnecting from ESXI")
            Disconnect(self.si)
            self.si = None

    def __getattr__(self, attr):
        if self.si is None:
            self._connect()
  
        try: 
            original_attr = self.si.__getattribute__(attr)
        except BadStatusLine:
            self._connect()
            original_attr = self.si.__getattribute__(attr)
        
        if callable(original_attr):
            def handles_disconnect_wrapper(*args, **kwargs):
                try:
                    return original_attr(*args, **kwargs)
                except BadStatusLine:
                    self = args[0]
                    self._connect()
                    return original_attr(*args, **kwargs)
            return handles_disconnect_wrapper
        else:
            return original_attr

class EsxiController:
    """ESXI Controller."""

    def __init__(self):

        self.host = None
        self.user = None
        self.pwd = None

        self.si = None

    def esxi_exception_handler_wrapper(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                self = args[0]
                self.esxi_disconnect()
                raise
        return wrapper

    def esxi_initialise(self, host, user, password):
        """Initialise and connect to ESXI."""
        self.host = host
        self.user = user
        self.pwd = password

        self.esxi_connect()
        # safe guard: disconnect on exit
        atexit.register(self.esxi_disconnect)  

    @esxi_exception_handler_wrapper
    def esxi_connect(self):
        self.si = EsxiServiceInstanceHelper(self.host, self.user, self.pwd)

    def esxi_disconnect(self):
        """Command to disconnect"""
        if self.si:
            Disconnect(self.si)
            self.si = None

    def get_service_instance(self):
        """Return the service instance for vmcontroller to access vms."""
        if self.si is None:
            self.esxi_connect()
        return self.si

    def _get_obj(self, vim_types):
        content = self.si.content
        obj_view = content.viewManager.CreateContainerView(
                content.rootFolder, vim_types, True)
        obj_list = obj_view.view
        obj_view.Destroy()
        return obj_list

    def _get_obj_filter_by_name(self, vim_types, filter_name):
        obj_list = self._get_obj(vim_types)

        found_obj = None
        for obj in obj_list:
            if obj.name == filter_name:
                found_obj = obj
                break

        return found_obj

    def _get_host_list(self):
        return self._get_obj([vim.HostSystem])

    def _get_vm_list(self):
        return self._get_obj([vim.VirtualMachine])

    def _get_dvportgroup_by_name(self, network_name):
        """
        Get the distributed virtual port group by name.

        dvportgroup is using the network name as its name.
        dvportgroup will also have a network obj but a network that does not
        belong to a dvportgroup will not have a dvportgroup obj.
        """
        return self._get_obj_filter_by_name(
                [vim.dvs.DistributedVirtualPortgroup], network_name)

    def _get_resourcepool_by_name(self, rsrcpool_name):
        return self._get_obj_filter_by_name([vim.ResourcePool], rsrcpool_name)

    def _get_network_by_name(self, network_name):
        return self._get_obj_filter_by_name([vim.Network], network_name)

    def _get_datacenter(self, datacenter_name=None):
        """Assumes and returns the first datacenter obj found."""
        if datacenter_name:
            return self._get_obj_filter_by_name(
                    [vim.Datacenter], datacenter_name)
        else:
            datacenter_list = self._get_obj([vim.Datacenter])
            return datacenter_list[0]

    def _get_datacenter_folder(self, datacenter_name=None):
        dc = self._get_datacenter(datacenter_name)
        if dc is None:
            raise ValueError(
                    "Datacenter {:s} not found!".format(datacenter_name))

        return dc.vmFolder

    @esxi_exception_handler_wrapper
    def get_vm_from_name(self, vm_name):
        for vm in self._get_vm_list():
            if vm.name == vm_name:
                return vm
        return None

    def _get_device_from_vm_nic(self, vm, nic_name):
        """"
        Get the Device obj of the VM obj through its virtual adapter name.
        """
        found_device = None
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                logging.debug("Found device [{:s}]".format(device))
                if device.deviceInfo.label.lower() == nic_name.lower():
                    found_device = device
                    break
        return found_device

    def _search_snapshot_tree(self, tree, snapshot_name):
        """
        Search for the snapshot obj using the snapshot name by iterating
        through the snapshot tree.
        """
        for snapshot_info in tree:
            if snapshot_info.name == snapshot_name:
                return snapshot_info.snapshot

            child_snapshot_tree = snapshot_info.childSnapshotList
            if child_snapshot_tree:
                found_snapshot = self._search_snapshot_tree(
                        child_snapshot_tree, snapshot_name)
                if found_snapshot:
                    return found_snapshot

        return None

    def _get_snapshot_obj_from_vm(self, vm, snapshot_name):
        """
        Get the snapshot obj from the vm obj by searching using the snapshot
        name.
        """
        snapshot_tree = vm.snapshot.rootSnapshotList
        return self._search_snapshot_tree(snapshot_tree, snapshot_name)

    def _get_snapshot_obj(self, vm_name, snapshot_name):
        """
        Get the snapshot obj by searching for the vm and then its snapshot by
        name.
        """
        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM [{:s}] not found!".format(vm_name))

        return self._get_snapshot_obj_from_vm(vm, snapshot_name)

    def _create_linked_clone_spec(self,
                                  snapshot,
                                  datastore,
                                  resource_pool,
                                  power_on=True,
                                  template=False):
        """Create the default linked clone specification for cloning."""
        reloc_spec = vim.vm.RelocateSpec()
        reloc_spec.diskMoveType = 'createNewChildDiskBacking'
        reloc_spec.datastore = datastore
        reloc_spec.pool = resource_pool

        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = reloc_spec
        clone_spec.powerOn = power_on
        clone_spec.template = template
        clone_spec.snapshot = snapshot

        return clone_spec

    @esxi_exception_handler_wrapper
    def wait_for_task(self, task):
        self.wait_for_tasks([task])

    @esxi_exception_handler_wrapper
    def wait_for_tasks(self, tasks):
        """
        Given the service instance si and tasks, it returns after all the
        tasks are complete.
        """
        property_collector = self.si.content.propertyCollector
        task_list = [str(task) for task in tasks]
        # Create filter
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                     for task in tasks]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(
                type=vim.Task, pathSet=[], all=True)
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = None, None
            # Loop looking for updates till the state moves to a completed
            # state.
            while len(task_list):
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()

    @esxi_exception_handler_wrapper
    def take_snapshot(self, vm_name, new_snapshot_name, memory_snapshot=False):
        logging.debug(
                "In take_snapshot, vm_name[{:s}], new_snapshot_name[{:s}], "
                "memory_snapshot[{}]"
                "".format(vm_name, new_snapshot_name, memory_snapshot))

        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM [{:s}] not found!".format(vm_name))
        logging.info(
                "Taking snapshot [{:s}] for [{:s}]".format(new_snapshot_name,
                                                           vm_name))

        task = vm.CreateSnapshot_Task(name=new_snapshot_name,
                                      memory=memory_snapshot,
                                      quiesce=True)
        return task

    @esxi_exception_handler_wrapper
    def delete_snapshot(self, vm_name, snapshot_name):
        logging.debug(
                "In delete_snapshot, vm_name[{:s}], snapshot_name[{:s}]"
                "".format(vm_name, snapshot_name))

        snapshot_obj = self._get_snapshot_obj(vm_name, snapshot_name)
        if snapshot_obj is None:
            raise ValueError(
                    "Snapshot [{:s}] not found!".format(snapshot_name))
        logging.info(
                "Deleting snapshot [{:s}] for [{:s}]".format(
                    snapshot_name, vm_name))
        task = snapshot_obj.RemoveSnapshot_Task(False)
        return task

    @esxi_exception_handler_wrapper
    def revert_vm(self, vm_name, snapshot_name):
        logging.debug(
                "In revert_vm, vm_name[{:s}], snapshot_name[{:s}]"
                "".format(vm_name, snapshot_name))

        snapshot_obj = self._get_snapshot_obj(vm_name, snapshot_name)
        if snapshot_obj is None:
            raise ValueError(
                    "Snapshot [{:s}] not found!".format(snapshot_name))

        logging.info("Reverting snapshot [{:s}]".format(snapshot_name))
        task = snapshot_obj.RevertToSnapshot_Task()
        return task

    @esxi_exception_handler_wrapper
    def linked_clone(self,
                     vm_name,
                     snapshot_name,
                     new_vm_name,
                     dst_rsrcpool_name=None,
                     datacenter_name=None):

        logging.debug(
                "In linked_clone, vm_name[{:s}], snapshot_name[{:s}], "
                "new_vm_name[{:s}]"
                "".format(vm_name, snapshot_name, new_vm_name))

        vm = self.get_vm_from_name(vm_name)
        if vm:
            logging.debug("VM [{:s}] found!".format(vm_name))
            snapshot = self._get_snapshot_obj_from_vm(vm, snapshot_name)
            if snapshot:
                logging.debug("Snapshot [{:s}] found!".format(snapshot_name))

                dst_rsrcpool = None
                if dst_rsrcpool_name:
                    dst_rsrcpool = self._get_resourcepool_by_name(dst_rsrcpool_name)
                else:
                    dst_rsrcpool = vm.resourcePool
                    
                # Get the DC folder directory
                dc_folder = self._get_datacenter_folder(datacenter_name)
                # Create the clone specifications. Using the same datastore
                # and resourcePool as parent VM
                clone_spec = self._create_linked_clone_spec(
                        snapshot, vm.datastore[0], dst_rsrcpool)
                # Clone VM
                task = vm.CloneVM_Task(dc_folder, new_vm_name, clone_spec)
            else:
                raise ValueError(
                        "Snapshot [{:s}] not found!".format(snapshot_name))
        else:
            raise ValueError("VM [{:s}] not found!".format(vm_name))

        return task

    @esxi_exception_handler_wrapper
    def make_vm_name_list(self, vm_names):
        """"Make sure that the vm_names return as a list"""
        vm_name_list = ""
        if isinstance(vm_names, list):
            vm_name_list = vm_names
        elif isinstance(vm_names, unicode):
            vm_name_list = [vm_names]
        else:
            raise ValueError(
                    "Type[{}] should be of type 'list' or 'unicode'"
                    "".format(type(vm_names)))

        return vm_name_list

    @esxi_exception_handler_wrapper
    def delete_vms(self, vm_names):
        logging.debug("In delete_vms, vm_names[{:s}]".format(vm_names))
        tasks = list()

        vm_name_list = self.make_vm_name_list(vm_names)

        for vm_name in vm_name_list:
            vm = self.get_vm_from_name(vm_name)
            if vm:
                logging.debug("Deleting VM [{:s}]".format(vm_name))
                tasks.append(vm.Destroy_Task())
            else:
                raise ValueError("VM [{:s}] not found!".format(vm_name))

        return tasks

    @esxi_exception_handler_wrapper
    def power_off_vms(self, vm_names):
        logging.debug("In power_off_vms, vm_names[{:s}]".format(vm_names))
        tasks = list()

        vm_name_list = self.make_vm_name_list(vm_names)

        for vm_name in vm_name_list:
            vm = self.get_vm_from_name(vm_name)
            if vm:
                logging.debug("Powering Off [{:s}]".format(vm_name))
                tasks.append(vm.PowerOffVM_Task())
            else:
                raise ValueError("VM [{:s}] not found!".format(vm_name))

        return tasks

    @esxi_exception_handler_wrapper
    def power_on_vms(self, vm_names):

        logging.debug("In power_on_vms, vm_names[{:s}]".format(vm_names))
        tasks = list()

        vm_name_list = self.make_vm_name_list(vm_names)

        for vm_name in vm_name_list:
            vm = self.get_vm_from_name(vm_name)
            if vm:
                logging.debug("Powering On [{:s}]".format(vm_name))
                tasks.append(vm.PowerOnVM_Task())
            else:
                raise ValueError("VM [{:s}] not found!".format(vm_name))

        return tasks

    @esxi_exception_handler_wrapper
    def reset_vms(self, vm_names):
        #  Can't reset suspended VMs. Call power_off first
        #  Can't reset powered Off Vms. Call power_on

        logging.debug("In reset_vms, vm_names[{:s}]".format(vm_names))
        tasks = list()

        vm_name_list = self.make_vm_name_list(vm_names)

        for vm_name in vm_name_list:
            vm = self.get_vm_from_name(vm_name)
            if vm:
                logging.debug("Resetting [{:s}]".format(vm_name))
                tasks.append(vm.ResetVM_Task())
            else:
                raise ValueError("VM [{:s}] not found!".format(vm_name))

        return tasks

    @esxi_exception_handler_wrapper
    def suspend_vms(self, vm_names):

        logging.debug("In suspend_vms, vm_names[{:s}]".format(vm_names))
        tasks = list()

        vm_name_list = self.make_vm_name_list(vm_names)

        for vm_name in vm_name_list:
            vm = self.get_vm_from_name(vm_name)
            if vm:
                logging.debug("Suspending [{:s}]".format(vm_name))
                tasks.append(vm.SuspendVM_Task())
            else:
                raise ValueError("VM [{:s}] not found!".format(vm_name))

        return tasks

    def _get_vm_summary_ip(self, vm):
        vm_guest = vm.summary.guest
        if vm_guest:
            return vm_guest.ipAddress
        else:
            return None

    def _get_vm_nics_ip(self, vm):
        ips = list()
        if vm.guest:
            nic_infos = vm.guest.net
            for nic_info in nic_infos:
                if nic_info.ipAddress:
                    for ip in nic_info.ipAddress:
                        ips.append(ip)
        return ips

    def _get_vm_ips(self, vm):
        ips = self._get_vm_nics_ip(vm)
        logging.debug("Nic ips: {:s}\n".format(ips))
        summary_ip = self._get_vm_summary_ip(vm)
        logging.debug("summary_ip: {:s}\n".format(summary_ip))
        ips.append(summary_ip)
        logging.debug("all ip: {:s}\n".format(ips))
        return ips

    def _match_ip_regex(self, ips, ip_regex):
        for ip in ips:
            if ip:
                found = re.match(ip_regex, ip)
                if found:
                    return ip

        return None

    @esxi_exception_handler_wrapper
    def vm_wait_for_ip(self, vm_name, new_ip_regex=None, timeout=300):
        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM: [{:s}] not found".format(vm_name))

        for i in range(timeout):
            ips = self._get_vm_ips(vm)
            if new_ip_regex:
                first_match_ip = self._match_ip_regex(ips, new_ip_regex)
                if first_match_ip:
                    return first_match_ip
            else:
                return ips[0]

            time.sleep(1)

        raise ValueError("vm_wait_for_ip timeout: {:d}".format(timeout))

    @esxi_exception_handler_wrapper
    def vm_get_ip(self, vm_name):
        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM: [{:s}] not found".format(vm_name))

        summary = vm.summary
        if summary.guest:
            return summary.guest.ipAddress

        return None

    @esxi_exception_handler_wrapper
    def vm_set_virtual_nic(self,
                           vm_name,
                           nic_name,
                           network_name,
                           connected=True,
                           connect_at_power_on=True,
                           allow_guest_control=True):
        """Set virtual NIC in VM."""
        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM: [{:s}] not found".format(vm_name))

        logging.debug(
                "setting virtual nic [{:s}] to [{:s}]".format(nic_name,
                                                              network_name))

        # Get the virtual nic card from name
        device = self._get_device_from_vm_nic(vm, nic_name)
        logging.debug("Found device [{:s}]".format(device))
        if device is None:
            raise ValueError("Device not found: [{:s}]".format(nic_name))

        # Create nic specification for editing
        nicspec = vim.vm.device.VirtualDeviceSpec()
        nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nicspec.device = device

        # Code for adding the device backing info to nic specification:
        # Try to get the network distribued virtual portgroup
        dv_portgroup = self._get_dvportgroup_by_name(network_name)
        # If device selected is a distributed switch
        if dv_portgroup:
            port_connection = vim.dvs.PortConnection()
            port_connection.portgroupKey = dv_portgroup.key
            port_connection.switchUuid = dv_portgroup.config.distributedVirtualSwitch.uuid

            nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            nicspec.device.backing.port = port_connection
        # If device is not a distributed switch
        else:
            # Get the network from name
            network = self._get_network_by_name(network_name)
            logging.debug("Found network: [{:s}]".format(network))

            if network:
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicspec.device.backing.network = network
                nicspec.device.backing.deviceName = network_name
            else:
                raise ValueError(
                        "Network not found: [{:s}]".format(network_name))

        # Add connect info to nic specification
        nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nicspec.device.connectable.connected = connected
        nicspec.device.connectable.startConnected = connect_at_power_on
        nicspec.device.connectable.allowGuestControl = allow_guest_control

        logging.debug("nicspec[{:s}]".format(nicspec))
        config_spec = vim.vm.ConfigSpec(deviceChange=[nicspec])
        task = vm.ReconfigVM_Task(config_spec)
        return task

    @esxi_exception_handler_wrapper
    def not_working_set_vm_ip(self, vm_name, ip_address, subnet_mask, gateway):
        # Online suggest this method but can't get it to work yet
        vm = self.get_vm_from_name(vm_name)
        if vm is None:
            raise ValueError("VM: [{:s}] not found".format(vm_name))

        # Create customization spec
        custom_spec = vim.vm.customization.Specification()

        # Create Adapter mapping
        adapter_map = vim.vm.customization.AdapterMapping()
        adapter_map.adapter = vim.vm.customization.IPSettings()
        adapter_map.adapter.ip = vim.vm.customization.FixedIp()
        adapter_map.adapter.ip.ipAddress = ip_address
        adapter_map.adapter.subnetMask = subnet_mask
        adapter_map.adapter.gateway = gateway
        custom_spec.nicSettingMap = [adapter_map]

        # Create vm identity
        vm_host_name = vim.vm.customization.FixedName(name="testing")
        ident = vim.vm.customization.LinuxPrep(domain=" ",
                                               hostName=vm_host_name)
        custom_spec.identity = ident

        # Create global ip settings
        globalip = vim.vm.customization.GlobalIPSettings()
        custom_spec.globalIPSettings = globalip

        return vm.CustomizeVM_Task(spec=custom_spec)
