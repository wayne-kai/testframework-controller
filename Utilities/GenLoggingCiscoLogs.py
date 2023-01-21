import sys
import threading
import argparse
import pexpect
import time

def login(args):

    if args.ssh:
        child = pexpect.spawn("ssh " + args.user + "@" + args.ip_address)
        child.expect("Password: ", timeout=60)
        child.sendline(args.passwd)

    if args.telnet:
        child = pexpect.spawn("telnet " + args.ip_address)
        child.expect("Username: ", timeout=60)
        child.sendline(args.user)
        child.expect("Password: ", timeout=60)
        child.sendline(args.passwd)

    index = child.expect([">", "#"], timeout=60)
    if index == 0:
        child.sendline("enable")
        child.expect("Password: ")
        child.sendline(args.enable)
        child.expect("#", timeout=60)

    return child

def main():

    #   Required variables
    parser = argparse.ArgumentParser(description="Generate logging logs for Cisco Router")
    parser.add_argument("-i", "--ip_address", help="Specify the IP Address to connect")
    parser.add_argument("-u", "--user", help="Specify the user id to be used for authentication")
    parser.add_argument("-p", "--passwd", help="Specify the password to be used for authentication")
    parser.add_argument("-e", "--enable", help="Specify the enable password to be used for privilege escalation")
    parser.add_argument("--ssh", help="Use SSH connection", action="store_true")
    parser.add_argument("--telnet", help="Use Telnet connection", action="store_true")
    parser.add_argument("-n", "--repeat", help="Specify the no. of logs to generate")
    args = parser.parse_args()
    
    if (args.ip_address is None 
            or args.user is None or args.passwd is None 
            or args.enable is None 
            or args.repeat is None):
        parser.print_help()
        sys.exit(1)
    else:

        #   Check that both of the connection protocol are not selected at the same time
        if (args.ssh == True and args.telnet == True):
            print("[-] Error: Both protocols are selected")
            sys.exit(1)
        
        else:            
            
            for i in range(0, int(args.repeat)):
                child = login(args)
                child.sendline("conf t")
                child.expect("\(config\)#")
                child.sendline("line vty 0 4")
                child.expect("\(config-line\)#")
                child.sendline("exit")
                child.expect("\(config\)#")
                child.sendline("exit")
                child.expect("#")
                child.sendline("exit")

            print("Finished")

if __name__ == "__main__":
    main()