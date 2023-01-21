import unittest
import socket
import subprocess
from OstinatoController import (ip_to_int, mac_to_int, resolve_src_dst)

class TestIpToInt(unittest.TestCase):

    def test_ip_to_int(self):
        self.assertEqual(ip_to_int("10.11.12.254"), 0x0a0b0cfe)
        self.assertEqual(ip_to_int("0.0.0.0"), 0)

    def test_invalid_ip_address(self):
        with self.assertRaises(socket.error):
            ip_to_int("10.11.12.270")


class TestMacToInt(unittest.TestCase):

    def test_mac_to_int(self):
        self.assertEqual(mac_to_int("00:23:5e:d0:46:49"), 0x00235ed04649)

    def test_mac_to_int_no_colon(self):
        self.assertEqual(mac_to_int("00235ed04649"), 0x00235ed04649)


class TestResolvSrcDst(unittest.TestCase):

    def test_invalid_address(self):
        with self.assertRaises(subprocess.CalledProcessError):
            resolve_src_dst("10.1.1.270")
