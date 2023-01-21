import re
import logging
import os
from FtpController import FtpController

def get_router_running_image(cisco_conn):

    cisco_conn.sendline_and_expect_hostname(
            "show version | i System image file is")

    image_path = re.search(
            "System image file is \"(.+?)\"", cisco_conn.before()).group(1)
    return image_path


def get_image_md5(cisco_conn, image_name):

    cisco_conn.sendline_and_expect_hostname("verify /md5 " + image_name)

    md5 = re.search("verify \/md5 \([\S]*\) = (.+?)[\s]*$", cisco_conn.before()).group(1)
    return md5


def process_copy_verify_firmware(cisco_conn,
                                 filesystem,
                                 ftp_source_path,
                                 local_dst_path,
                                 router_name,
                                 timeout):
    
    logging.debug("In process_copy_verify_file")
    
    # Prepare for copy file, for filesystem C
    #  copying to a dst tmp file is required to check its MD5
    copy_src = ftp_source_path
    copy_dst = local_dst_path
    
    if filesystem == "C":
        # Create tmp file name
        dst_root_path, dst_ext_path = os.path.splitext(local_dst_path)
        copy_dst = dst_root_path + "-tmp" + dst_ext_path

    cisco_conn.sendline("copy " + copy_src + " " + copy_dst)

    expectstr = "(Erasing the flash|Erase flash: before copying\? \[confirm\]|Do you want to over write\? \[confirm\]|Address or name of |Destination filename|Invalid input detected|" + router_name + ")"
    cisco_conn.expectline(
            expectstr,
            timeout)

    while router_name not in cisco_conn.after():
        logging.debug("Waiting for router name to appear")

        if "Invalid input detected" in cisco_conn.after():
            raise ValueError("Invalid Input detected!\n")
        elif "Address or name of " in cisco_conn.after():
            logging.debug("\"Address of name of\" detected")
            cisco_conn.sendline()
        elif "Destination filename" in cisco_conn.after():
            logging.debug("\"Destination filename\" detected")
            cisco_conn.sendline()
        elif "Do you want to over write" in cisco_conn.after():
            logging.debug("\"Do you want to over write\" detected")
            cisco_conn.sendline()
        elif "Erase flash: before copying?" in cisco_conn.after():
            logging.debug("\"Do you want to erase flash: before copying?\" detected")
            cisco_conn.sendline("N")
        elif "Erasing the flash filesystem will remove all files! Continue?" in cisco_conn.after():
            logging.debug("\"Erasing the flash filesystem will remove all files! Continue?\" detected")
            cisco_conn.sendline()
        else:
            break

        logging.debug(".after() = [{}]".format(cisco_conn.after()))
        cisco_conn.expectline(
                expectstr,
                timeout)

    # Check if file transfer has corruption
    if filesystem == "B":
        # When copying the file, Class B filesystem will do a checksum check
        if " OK " not in cisco_conn.before():
            raise ValueError("process_copy_verify_file checksum ok not found [{}]!\n".format(cisco_conn.after()))
    elif filesystem == "C":

        logging.debug('Get image md5 from router...')
        check_md5 = get_image_md5(cisco_conn, copy_dst)
        
        logging.debug('Get image md5 from ftp...')
        ftp_ctrl = FtpController()
        ftp_md5 = ftp_ctrl.get_ftp_md5(copy_src)

        logging.debug('Check MD5 of {:s}: {:s}'.format(copy_dst, check_md5))
        if check_md5.lower() != ftp_md5.lower():
            raise ValueError("process_copy_verify_file firmware_md5[{}] != ftp_md5[{}]!\n".format(check_md5.lower(), ftp_md5.lower()))
        else:
            # Rename the firmware
            cisco_conn.sendline("rename {} {}".format(copy_dst, local_dst_path))
            cisco_conn.expectline("(Destination filename|" + cisco_conn.hostname + ")")
            if "Destination filename" in cisco_conn.after():
                cisco_conn.sendline()
                cisco_conn.expectline(cisco_conn.hostname)
    else:
        raise ValueError("Unknown Filesystem Type [{}]!\n".format(filesystem))

def process_delete_file(cisco_conn, class_type, image_path):

    # Delete the original image
    logging.debug('File Class is '+ class_type)
    logging.debug('Deleting ' + image_path)
    cisco_conn.sendline("delete /force " + image_path)
    cisco_conn.expectline(cisco_conn.hostname+"#")

    if class_type == "B":
        logging.debug('Squeezing flash:')
        cisco_conn.sendline("squeeze flash")
        cisco_conn.expectline("Squeeze operation may take a while. Continue\? \[confirm\]")
        cisco_conn.sendline()
        cisco_conn.expectline(cisco_conn.hostname+"#")
