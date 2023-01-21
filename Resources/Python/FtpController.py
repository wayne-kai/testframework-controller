import ftplib
import logging
import hashlib
import urlparse
import os


class FtpController(object):

    def _create_ftp_connection(self, site, user, password):
        """Returns an instance of FTP."""

        logging.debug(
                "Logging into FTP server at {:s} using \"{:s}\" and "
                "\"{:s}\"".format(site, user, password))

        ftp = ftplib.FTP(site)
        ftp.login(user, password)

        return ftp

    def get_ftp_md5(self, ftp_url):
        """Return the MD5 checksum of a file at the FTP URL."""

        parser = urlparse.urlsplit(ftp_url)
        return self._get_ftp_md5(
                parser.hostname,
                parser.path,
                parser.username,
                parser.password)

    def _get_ftp_md5(self, site, remote_path, user=None, password=None):

        ftp = self._create_ftp_connection(site, user, password)

        logging.debug("Hashing firmware...")
        m = hashlib.md5()

        logging.debug("Retrieve firmware...")
        ftp.retrbinary("RETR {:s}".format(remote_path), m.update)

        logging.debug("Close FTP connection...")
        ftp.quit()

        logging.debug("Returning digest...")

        return m.hexdigest()

    def list_ftp_files(self, ftp_url):
        """Return a list of files at the FTP URL."""

        parser = urlparse.urlsplit(ftp_url)
        return self._list_ftp_files(
                parser.hostname,
                parser.path,
                parser.username,
                parser.password)

    def _list_ftp_files(self, site, remote_path, user=None, password=None):

        ftp = self._create_ftp_connection(site, user, password)

        logging.debug("Retrieve file listing...")
        file_list = ftp.nlst(remote_path)

        ftp.quit()

        return file_list

    def get_ftp_file(self, ftp_url, output_dir):
        """
        Get a file at the FTP URL.

        Returns the path of the downloaded file.
        """

        parser = urlparse.urlsplit(ftp_url)
        return self._get_ftp_file(
                parser.hostname,
                parser.path,
                output_dir,
                parser.username,
                parser.password)

    def _get_ftp_file(
            self,
            site,
            remote_path,
            output_dir,
            user=None,
            password=None):

        ftp = self._create_ftp_connection(site, user, password)

        output_filename = os.path.join(
                output_dir,
                os.path.basename(remote_path))

        logging.debug("Output filename: '{:s}'".format(output_filename))

        command = "RETR {:s}".format(remote_path)

        with open(output_filename, 'wb') as fout:
            ftp.retrbinary(command, fout.write)

        ftp.quit()

        return output_filename

    def get_ftp_files_with_wildcard(self, ftp_url, output_dir):
        """
        Get multiple files at the FTP URL. Supports wildcard.

        Returns a list of the downloaded files.
        """

        parser = urlparse.urlsplit(ftp_url)
        return self._get_ftp_files_with_wildcard(
                    parser.hostname,
                    parser.path,
                    output_dir,
                    parser.username,
                    parser.password)

    def _get_ftp_files_with_wildcard(
            self,
            site,
            remote_path,
            output_dir,
            user=None,
            password=None):

        dl_file_list = []
        ftp = self._create_ftp_connection(site, user, password)

        logging.debug("Retrieve file listing for {:s}".format(remote_path))
        file_list = ftp.nlst(remote_path)
        logging.debug("File listing: {:s}".format(file_list))

        for filename in file_list:
            logging.debug("Downloading {:s}".format(filename))
            output_filename = os.path.join(
                    output_dir,
                    os.path.basename(filename))
            command = "RETR {:s}".format(filename)
            with open(output_filename, 'wb') as fout:
                ftp.retrbinary(command, fout.write)

            dl_file_list.append(output_filename)

        ftp.quit()

        return dl_file_list

    def send_ftp_file(self, local_path, ftp_url):
        """
        Send a file to the FTP URL.

        Returns the path of the uploaded file
        """
        parser = urlparse.urlsplit(ftp_url)
        return self._send_ftp_file(
                parser.hostname,
                local_path,
                parser.path,
                parser.username,
                parser.password)


    def _send_ftp_file(
            self,
            site,
            local_filename,
            remote_path,
            user=None,
            password=None):

        ftp = self._create_ftp_connection(site, user, password)

        if os.path.isabs(local_filename):
            src_filepath = local_filename
        else:
            src_filepath = os.path.join(os.path.dirname(__file__), local_filename)

        logging.debug("Uploading '{:s}' to '{:s}'".format(src_filepath, remote_path))

        command = "STOR {:s}".format(remote_path)

        with open(src_filepath, 'rb') as fout:
            ftp.storbinary(command, fout)

        ftp.quit()

        return remote_path

    def delete_ftp_files(self, ftp_url):
        """Delete files at the FTP URL.

        The function uses the FTP command NLST to find the files to delete.
        Wildcards are supported.

        Returns a list of file that have been deleted.
        """

        parser = urlparse.urlsplit(ftp_url)
        return self._delete_ftp_files(
                parser.hostname,
                parser.path,
                parser.username,
                parser.password)

    def _delete_ftp_files(self, site, remote_path, user=None, password=None):

        ftp = self._create_ftp_connection(site, user, password)

        logging.debug("Retrieve file listing for {:s}...".format(remote_path))
        file_list = ftp.nlst(remote_path)

        for filename in file_list:
            logging.debug("Deleting {:s}".format(filename))
            ftp.delete(filename)

        ftp.quit()

        return file_list
