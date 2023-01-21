import ftplib
import os
import logging


class FtpLib(object):
    """A library to support common FTP functions."""

    def __init__(self):
        self.ftp = ftplib.FTP()

    def ftp_connect(self, host, port=21, timeout=30):
        """Open FTP connection."""

        timeout = int(timeout)
        port = int(port)

        # Create new instance as a closed FTP instance can't be reused
        self.ftp.close()
        self.ftp = ftplib.FTP()

        logging.info("Connecting to FTP host {:s}".format(host))
        logging.info("Timeout: {:d}".format(timeout))
        logging.info("Port: {:d}".format(port))

        outputMsg = self.ftp.connect(host, port, timeout)

        logging.info(outputMsg)

    def ftp_login(self, user='anonymous', password='anonymous@'):
        """Login to the FTP server."""

        output_msg = self.ftp.login(user=user, passwd=password)
        logging.info(output_msg)

    def ftp_close(self):
        """Closes FTP connection."""
        self.ftp.close()

    def cwd(self, pathname):
        """Set the current directory on the FTP server."""

        logging.debug("Change to directory {:s}".format(pathname))
        output_msg = self.ftp.cwd(pathname)
        logging.info(output_msg)

    def dir(self):
        """
        Produce a directory listing as returned by the LIST command.

        Return a list of string.
        """

        logging.debug("Listing directory")
        dir_list = []
        self.ftp.dir(dir_list.append)

        return dir_list

    def nlst(self, pathname=None):
        """Return a list of file names as returned by the NLST command."""

        nlst_list = []

        if pathname:
            nlst_list = self.ftp.nlst(pathname)
        else:
            nlst_list = self.ftp.nlst()

        return nlst_list

    def delete(self, filename):
        """Delete a file at the current directory."""

        output_msg = self.ftp.delete(filename)
        logging.info(output_msg)
        return output_msg

    def mdelete(self, *args):
        """Delete multiple remote files."""

        for arg in args:
            remote_file = str(arg)
            file_list = self.ftp.nlst(remote_file)
            for filename in file_list:
                logging.info("Deleting {:s}".format(filename))
                self.delete(filename)

    def ftp_binary_get(self, filename, output_dir='.'):
        """Retrieve a binary file."""

        command = "RETR {:s}".format(filename)
        logging.debug("FTP command: {:s}".format(command))

        output_filename = os.path.join(output_dir, filename)
        logging.debug("Output filename: '{:s}'".format(output_filename))

        with open(output_filename, 'wb') as fout:
            self.ftp.retrbinary(command, fout.write)

