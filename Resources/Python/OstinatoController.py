#! /usr/bin/env python

import logging
import struct
import socket
import subprocess
import argparse
import time
import sys

# import ostinato modules
from ostinato.core import DroneProxy, ost_pb
from ostinato.protocols.ip4_pb2 import ip4
from ostinato.protocols.payload_pb2 import Payload, payload
from ostinato.protocols.mac_pb2 import mac


class OstinatoControllerError(Exception):
    pass


def ip_link_get_mac(device):
    """
    Returns the MAC address of a network device.

    Uses the Linux ip program.
    """

    args = ['ip', 'link', 'show', device]
    output = subprocess.check_output(args)
    logging.info('Output of "%s":\n%s', ' '.join(args), output)
    if not output:
        raise OstinatoControllerError("No device {:s}".format(device))

    output_split = output.split()
    mac = output_split[output_split.index('link/ether') + 1]

    return mac


def ip_nexthop_get_mac(addr, tries=10):
    """
    Obtain the MAC address of the nexthop node for the route to the given
    address.

    Uses the Linux ip program.
    """

    # To ensure that the ARP cache is up to date, continously ping the next
    # hop address until the ARP entry is refreshed and its NUD is "REACHABLE"
    tries_left = tries
    args = ['ip', 'neighbor', 'show', addr, 'nud', 'reachable']
    ping_args = ['ping', '-q', '-c', '1', addr]
    output = subprocess.check_output(args)

    while (tries_left > 0) and (not output):
        logging.info("Pinging {:s}".format(addr))
        try:
            ping_output = subprocess.check_output(ping_args)
            logging.debug('Output of "%s":\n%s', ' '.join(ping_args), ping_output)
        except subprocess.CalledProcessError as e:
            logging.warning(e)
            logging.warning('Output of "%s":\n%s', ' '.join(ping_args), e.output)

        tries_left -= 1
        time.sleep(1)
        output = subprocess.check_output(args)
        logging.debug('Output of "%s":\n%s', ' '.join(args), output)

    logging.info('Output of "%s":\n%s', ' '.join(args), output)

    if not output:
        raise OstinatoControllerError(
                "No neighbour with address {:s}".format(addr))

    output_split = output.split()
    nexthop_mac = output_split[output_split.index('lladdr') + 1]

    return nexthop_mac


def resolve_src_dst(addr):
    """
    Returns the source device MAC and destination MAC address for a route to
    the given address.

    Uses the Linux ip program.
    """
    args = ['ip', 'route', 'get', addr]
    output = subprocess.check_output(['ip', 'route', 'get', addr])
    logging.info('Output of "%s":\n%s', ' '.join(args), output)
    if not output:
        raise OstinatoControllerError("No route found to {:s}".format(addr))

    output_split = output.split()

    src_ip = output_split[output_split.index('src') + 1]
    dev = output_split[output_split.index('dev') + 1]
    src_mac = ip_link_get_mac(dev)

    if 'via' in output_split:
        # Nexthop is an intermediate node
        nexthop_ip = output_split[output_split.index('via') + 1]
    else:
        # Destination is the nexthop
        nexthop_ip = addr

    dst_mac = ip_nexthop_get_mac(nexthop_ip)

    return (src_ip, src_mac, dst_mac)


def ip_to_int(addr):
    """Convert an IP address string to its integer representation."""
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def mac_to_int(mac):
    """Convert a MAC address string to its integer representation."""
    return int(''.join(mac.split(':')), 16)


DEFAULT_BURST_SIZE = 64


class OstinatoController(object):
    """Controller for an Ostinato Drone."""

    ROBOT_LIBRARY_VERSION = "1.0.0"

    def __init__(self, drone_host_name="127.0.0.1"):
        self.drone_host_name = drone_host_name

    def set_drone_host_name(self, host_name):
        self.drone_host_name = host_name

    def _connect_to_drone(self):
        """Connect to drone. Returns a DroneProxy instance."""
        drone = DroneProxy(self.drone_host_name)

        # connect to drone
        logging.info(
                'Connecting to drone(%s:%d)'
                % (drone.hostName(), drone.portNumber()))
        drone.connect()
        return drone

    def configure_streams(
            self,
            tx_port_number,
            dst_ip,
            src_mac=None,
            src_ip=None,
            dst_mac=None,
            packets_per_burst=DEFAULT_BURST_SIZE):
        """
        Configure a transmit stream in the Ostinato drone.

        tx_port_number: transmit port number
        src_mac: source MAC address; pass None to resolve automatically
        src_ip: source IP address
        dst_mac: destination MAC address; pass None to resolve automatically
        dst_ip: destination IP address
        packets_per_burst: no. of packets to transmit per transmit burst
        """

        input_src_ip = src_ip
        input_dst_ip = dst_ip
        input_src_mac = src_mac
        input_dst_mac = dst_mac

        if input_src_ip is None or input_src_mac is None or input_dst_mac is None:
            resolv_src_ip, resolv_src_mac, resolv_dst_mac = resolve_src_dst(dst_ip)

            if input_src_ip is None:
                input_src_ip = resolv_src_ip

            if input_src_mac is None:
                input_src_mac = resolv_src_mac

            if input_dst_mac is None:
                input_dst_mac = resolv_dst_mac

        src_mac_int = mac_to_int(input_src_mac)
        dst_mac_int = mac_to_int(input_dst_mac)

        src_ip_int = ip_to_int(input_src_ip)
        dst_ip_int = ip_to_int(input_dst_ip)

        logging.info("Configuring streams")

        logging.info("Src MAC: %s (%x)", input_src_mac, src_mac_int)
        logging.info("Src IP: %s (%x)", input_src_ip, src_ip_int)

        logging.info("Dst MAC: %s (%x)", input_dst_mac, dst_mac_int)
        logging.info("Dst IP: %s (%x)", input_dst_ip, dst_ip_int)

        logging.info("Number of packets per burst: %d", int(packets_per_burst))

        drone = self._connect_to_drone()
        try:
            self._configure_streams(
                    drone,
                    int(tx_port_number),
                    src_mac_int,
                    src_ip_int,
                    dst_mac_int,
                    dst_ip_int,
                    int(packets_per_burst))
        finally:
            drone.disconnect()

    def _tx_port(self, tx_port_number):
        """Setup a TX port list."""
        tx_port = ost_pb.PortIdList()
        tx_port.port_id.add().id = int(tx_port_number)

        return tx_port

    def _stream_id(self, tx_port_number):
        stream_id = ost_pb.StreamIdList()
        stream_id.port_id.id = int(tx_port_number)
        stream_id.stream_id.add().id = 1
        stream_id.stream_id.add().id = 2

        return stream_id

    def _configure_streams(
            self,
            drone,
            tx_port_number,
            src_mac,
            src_ip,
            dst_mac,
            dst_ip,
            packets_per_burst):
        """
        Configure a transmit stream in the Ostinato drone.

        tx_port_number: transmit port number in integer
        src_mac: source MAC address in integer
        src_ip: source IP address in integer
        dst_mac: destination MAC address in integer
        dst_ip: destination IP address in integer
        packets_per_burst: no. of packets to transmit per transmit burst
        """

        # setup tx port list
        logging.debug("Add port {:d} to transmit port".format(tx_port_number))

        # ------------#
        # add streams #
        # ------------#
        drone.addStream(self._stream_id(tx_port_number))

        # ------------------#
        # configure streams #
        # ------------------#
        stream_cfg = ost_pb.StreamConfigList()
        stream_cfg.port_id.id = tx_port_number

        # stream 1 tcp
        logging.info("Configuring TCP stream")
        s = stream_cfg.stream.add()
        s.stream_id.id = 1
        s.core.name = 'tcp'
        s.core.is_enabled = True
        s.control.unit = ost_pb.StreamControl.e_su_bursts
        s.control.packets_per_burst = packets_per_burst

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kMacFieldNumber
        p.Extensions[mac].dst_mac = dst_mac
        p.Extensions[mac].src_mac = src_mac

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kEth2FieldNumber

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kIp4FieldNumber
        p.Extensions[ip4].src_ip = src_ip
        p.Extensions[ip4].dst_ip = dst_ip

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kTcpFieldNumber

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kPayloadFieldNumber

        # stream 2 udp
        logging.info("Configuring UDP stream")
        s = stream_cfg.stream.add()
        s.stream_id.id = 2
        s.core.name = 'udp'
        s.core.is_enabled = True
        s.core.ordinal = 0x1
        s.control.unit = ost_pb.StreamControl.e_su_bursts
        s.control.packets_per_burst = packets_per_burst
        s.control.next = ost_pb.StreamControl.e_nw_goto_id

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kMacFieldNumber
        p.Extensions[mac].dst_mac = dst_mac
        p.Extensions[mac].src_mac = src_mac

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kEth2FieldNumber

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kIp4FieldNumber
        p.Extensions[ip4].src_ip = src_ip
        p.Extensions[ip4].dst_ip = dst_ip

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kUdpFieldNumber

        p = s.protocol.add()
        p.protocol_id.id = ost_pb.Protocol.kPayloadFieldNumber
        p.Extensions[payload].pattern_mode = Payload.e_dp_random

        drone.modifyStream(stream_cfg)

    def delete_streams(self, tx_port_number):
        """Delete transmit streams."""

        tx_port = self._tx_port(tx_port_number)
        stream_id = self._stream_id(tx_port_number)
        drone = self._connect_to_drone()

        try:
            logging.info("Stop transmitting")
            drone.stopTransmit(tx_port)
            logging.info("Deleting tx_streams")
            drone.deleteStream(stream_id)
        finally:
            drone.disconnect()

    def clear_tx_rx_stats(self, tx_port_number):
        """Clear TX/RX stats."""
        tx_port = self._tx_port(tx_port_number)

        logging.info('clearing tx stats')
        drone = self._connect_to_drone()
        try:
            drone.clearStats(tx_port)
        finally:
            drone.disconnect()

    def start_transmit(self, tx_port_number):
        """Start transmitting."""
        tx_port = self._tx_port(tx_port_number)

        drone = self._connect_to_drone()
        logging.info('starting transmit')
        try:
            drone.startTransmit(tx_port)
        finally:
            drone.disconnect()

    def get_tx_port_stats(self, tx_port_number):
        """Obtain the transmitting port stats."""
        tx_port = self._tx_port(tx_port_number)
        tx_stats = None

        drone = self._connect_to_drone()
        try:
            tx_stats = drone.getStats(tx_port)
        finally:
            drone.disconnect()

        return tx_stats

    def is_transmit_on(self):
        """Returns True if drone is transmitting."""

        is_transmit_on = False

        tx_stats = self.get_tx_port_stats()

        try:
            is_transmit_on = tx_stats.port_stats[0].state.is_transmit_on
        except IndexError:
            raise OstinatoControllerError("No TX port has been configured")

        return is_transmit_on

    def stop_transmit(self, tx_port_number):
        """Stop transmit and capture."""
        tx_port = self._tx_port(tx_port_number)
        logging.info("Stopping transmit")
        drone = self._connect_to_drone()

        try:
            drone.stopTransmit(tx_port)
        finally:
            drone.disconnect()


def cmd_configure(oc, args):
    oc.configure_streams(
            tx_port_number=args.portid,
            src_mac=args.srcmac,
            src_ip=args.srcip,
            dst_mac=args.dstmac,
            dst_ip=args.dstip,
            packets_per_burst=args.burstsize)

    print("Configured streams on drone {:s} port {:d}".format(
        oc.drone_host_name, args.portid))


def cmd_start(oc, args):
    oc.start_transmit(tx_port_number=args.portid)
    print("Started transmitting on drone {:s} port {:d}".format(
        oc.drone_host_name, args.portid))


def cmd_stop(oc, args):
    oc.stop_transmit(tx_port_number=args.portid)
    print("Stopped transmitting on drone {:s} port {:d}".format(
        oc.drone_host_name, args.portid))


def cmd_del(oc, args):
    oc.delete_streams(tx_port_number=args.portid)
    print("Deleted streams on drone {:s} port {:d}".format(
        oc.drone_host_name, args.portid))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Ostinato controller")
    parser.add_argument('--drone', help="IP address of drone. Default to 127.0.0.1")
    parser.add_argument('--debug', help="Enable debug printouts", action="store_true")

    subparsers = parser.add_subparsers(title="subcommands")

    # create the parser for "configure" command
    parser_config = subparsers.add_parser(
            'configure', help="Configure streams in Ostinato drone")
    parser_config.add_argument('portid', type=int)
    parser_config.add_argument('--srcmac', help="Override source MAC address")
    parser_config.add_argument('--srcip', help="Override source IP address")
    parser_config.add_argument(
            '--dstmac', help="Override destination MAC address")
    parser_config.add_argument('dstip', help="Destination IP address")
    parser_config.add_argument(
            '--burstsize', type=int, default=DEFAULT_BURST_SIZE,
            help="Size of each burst in number of packets")
    parser_config.set_defaults(func=cmd_configure)

    # create the parser for "start" command
    parser_start = subparsers.add_parser("start", help="Start transmitting")
    parser_start.add_argument('portid', type=int)
    parser_start.set_defaults(func=cmd_start)

    # create the parser for "stop" command
    parser_stop = subparsers.add_parser("stop", help="Stop transmitting")
    parser_stop.add_argument('portid', type=int)
    parser_stop.set_defaults(func=cmd_stop)

    # create the parser
    parser_delete = subparsers.add_parser(
            "delete", help="Delete streams in Ostinato drone")
    parser_delete.add_argument('portid', type=int)
    parser_delete.set_defaults(func=cmd_del)

    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("Arguments: {:s}".format(args))

    oc = OstinatoController()
    if args.drone:
        oc.set_drone_host_name(args.drone)

    try:
        args.func(oc, args)
    except Exception as e:
        print("Error: {:s}".format(e))
        logging.exception(e)
        sys.exit(1)

