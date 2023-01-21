from EsxiController import EsxiController
from VMController import VMController
          
if __name__ == "__main__":

    #base_vm_name = "Ubuntu 14.04 - 64 bit - base"
    #base_snapshot_name = "Tool"
    #new_vm_name = "Ubuntu 14.04 - 64 bit - linked - Test Script"
    #find_process_name = "kworker/0:3"
    #start_program = "/usr/bin/firefox"
    #start_program_args = "&"
    #working_dir = None
    #vm_login_user = "user"
    #vm_login_pwd = "password"
    #ethernet_name = "eth0"
    #upload_src = "/home/Test-Framework/Resources/Python/FtpLib.py"
    #upload_dst = "/home/user/test/test.py"
    #download_src = "/home/user/test/test.py"
    #download_dst = "/home/Test-Framework/Resources/Python/testdl.py"

    
    #base_vm_name = "CentOS 7 Server - 64-bit - base"
    #base_snapshot_name = "Baseline"
    #new_vm_name = "CentOS 7 Server - 64-bit - linked - Test Script"

    
    base_vm_name = "Win 7 - 64 bit - base"
    base_snapshot_name = "Updated"
    new_vm_name = "Win 7 - 64 bit - linked - Test Script"
    find_process_name = "iexplore.exe"
    start_program = "c:\\Program Files (x86)\\Internet Explorer\\iexplore.exe"
    start_program_args = "10.13.13.1\\pages\\default.php"
    working_dir = "c:\\Users\\test"
    vm_login_user = "test"
    vm_login_pwd = "password"
    ethernet_name = "Local Area Connection"
    upload_src = "/home/Test-Framework/Resources/Python/FtpLib.py"
    upload_dst = "c:\\Users\\test\\test.txt"
    download_src = upload_dst
    download_dst = "/home/Test-Framework/Resources/Python/testdl2.py"
    new_snapshot_name = "snapshot_test"

    
    # Initialise and connect to ESXI
    esxi = EsxiController()
    esxi.esxi_initialise("vcenter.phantom.net", "tfuser", "password123.")

    # Clone VM
    #task = esxi.linked_clone(base_vm_name, base_snapshot_name, new_vm_name)
    task = esxi.linked_clone("Brocade Virtual Traffic Manager Appliance", "Setup", "Testnet Brocade - VTM Appliance")
    #esxi.wait_for_task(task)

    # Get Old IP
    #old_ip = esxi.vm_get_ip()
    #print "VM [{:s}] old_ip[{:s}]".format(new_vm_name, old_ip)

    # Power off the VM before configuring virtual NIC (Not necessary but for more predictable behavior)
    #tasks = esxi.power_off_vms(new_vm_name)
    #esxi.wait_for_tasks(tasks)

    # Set virtual NIC Card
    #task = esxi.set_virtual_nic(new_vm_name, "Network adapter 1", "Jumphost Net")
    #esxi.wait_for_task(task)
   
    # Create VMController for the new vm
    #vmc = VMController()
    #vmc.vmc_initialise(esxi.get_service_instance(), esxi.get_vm_from_name(new_vm_name), vm_login_user, vm_login_pwd)
    #pid = vmc.run_program(start_program, start_program_args, working_dir)

    # Power on the VM
    #tasks = esxi.power_on_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    #new_ip = esxi.vm_wait_for_ip("MK Test Win7 64bit Client", "139\\.139\\.[0-9]{1,3}\\.[0-9]{1,3}")
    #print "new_ip[{:s}]".format(new_ip)
    #new_ip = esxi.vm_wait_for_new_ip(new_vm_name, old_ip)
    #print "VM [{:s}] new_ip[{:s}]".format(new_vm_name, new_ip)

    #pid = vmc.run_program(start_program, start_program_args, working_dir)
    #if pid >= 0:
        #print "Created: {:d}".format(pid)
    #else:
        #print "Process {:s} not created".format(find_process_name)
    #process = vmc.find_process_name(find_process_name, [pid], nocase=True)
    #if process:
        #print "Found Process [{:s}]".format(process)
    #else:
        #print "Process {:s} not found".format(find_process_name)

    #vmc.upload_file(upload_src, upload_dst)
    #vmc.download_file(download_src, download_dst)

    # Take Snapshot
    #task = esxi.take_snapshot(new_vm_name, new_snapshot_name)
    #esxi.wait_for_tasks([task])
    
    #pid = esxi.vm_run_program(new_vm_name, vm_login_user, vm_login_pwd, start_program, start_program_args, working_dir)


    #pid = esxi.vm_set_ip(new_vm_name, vm_login_user, vm_login_pwd, ethernet_name, "15.15.15.15", "255.255.255.0", "15.15.15.254")
    #if pid >= 0:
        #print "Created: {:d}".format(pid)
    #else:
        #print "Process {:s} not created".format(find_process_name)

    #process = esxi.vm_find_process(new_vm_name, vm_login_user, vm_login_pwd, find_process_name, [pid], nocase=True)
    #if process:
        #print "Found Process [{:s}]".format(process)
    #else:
        #print "Process {:s} not found".format(find_process_name)

    #esxi.vm_upload_file(new_vm_name, vm_login_user, vm_login_pwd, upload_src, upload_dst)

    #esxi.vm_download_file(new_vm_name, vm_login_user, vm_login_pwd, download_src, download_dst)

    #pid = vmc.run_program(start_program, start_program_args, working_dir)
    #if pid >= 0:
        #print "Created: {:d}".format(pid)
    #else:
        #print "Process {:s} not created".format(find_process_name)
    #process = vmc.find_process_name(find_process_name, [pid], nocase=True)
    #if process:
        #print "Found Process [{:s}]".format(process)
    #else:
        #print "Process {:s} not found".format(find_process_name)
    #vmc.upload_file(upload_src, upload_dst)
    #vmc.download_file(download_src, download_dst)

    #task = esxi.set_virtual_nic(new_vm_name, "Network adapter 1", "Testnet 3845")
    #esxi.wait_for_tasks([task])

    #old_ip = esxi.vm_wait_for_new_ip(new_vm_name)
    #print "VM [{:s}] ip[{:s}]".format(new_vm_name, old_ip)

    #task = esxi.set_virtual_nic(new_vm_name, "Network adapter 1", "Jumphost Net")
    #esxi.wait_for_tasks([task])

    # Reset the VM for it to load a new dhcp ip
    #tasks = esxi.reset_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    #task = esxi.set_vm_ip(new_vm_name, "15.15.15.15", "255.255.0.0", "15.15.255.254")
    #esxi.wait_for_tasks([task])
    
    # Reset the VM
    #tasks = esxi.reset_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    #ip = esxi.vm_wait_for_new_ip(new_vm_name, old_ip)
    #print "VM [{:s}] ip[{:s}]".format(new_vm_name, ip)

    # Suspend the VM
    #tasks = esxi.suspend_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    # Power on the VM
    #tasks = esxi.power_on_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    # Revert VM
    #task = esxi.revert_vm(new_vm_name, new_snapshot_name)
    #esxi.wait_for_tasks([task])

    # Delete Snapshot
    #task = esxi.delete_snapshot(new_vm_name, new_snapshot_name)
    #esxi.wait_for_tasks([task])

    # Delete VM
    #tasks = esxi.delete_vms([new_vm_name])
    #esxi.wait_for_tasks(tasks)

    # Close connection to ESXI
    esxi.esxi_disconnect()


