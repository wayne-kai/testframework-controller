"""Utility functions shared by Cisco-related modules."""

import pexpect
import logging
import re


def parse_backspace(string):
    """
    Parse backspace characters (0x08) in a string.

    Returns the parsed string.
    """

    parsed_str = ""

    for ch in string:
        if ch == '\x08':
            parsed_str = parsed_str[:-1]
        else:
            parsed_str = parsed_str + ch

    return parsed_str


def parse_special_character(strings):
    """Add a backslash to any regex special character."""

    special_char = "\^$.|?*+()"
    parsed_strings = ""

    for ch in strings:
        if ch in special_char:
            parsed_strings = parsed_strings + '\\' + ch
        else:
            parsed_strings = parsed_strings + ch

    return parsed_strings


def ping_wait(IP, timeout):

    ping_process = pexpect.spawn("ping -i 5 " + IP)
    ping_process.expect("bytes from", timeout)
    ping_process.close()


def spawn_and_print(cmd_to_spawn, cmd_args=[], maxread=4000, timeout=None):

    logging.debug(
            'Spawning command: {:s} Args: {:s}'.format(
                cmd_to_spawn,
                cmd_args))

    full_cmd_line = "{:s}{:s}".format(cmd_to_spawn, ' '.join([''] + cmd_args))
    logging.info(full_cmd_line + "\r\n")

    return pexpect.spawn(
            command=cmd_to_spawn,
            args=cmd_args,
            maxread=maxread,
            timeout=timeout)


def expect_and_print(pexpect_process, expect_string, timeout=None):
    """Function that prints out the expected output too. Default to 120s."""

    logging.debug('expect_string: {:s}'.format(expect_string))
    pexpect_process.expect(expect_string, timeout)

    output = pexpect_process.before + str(pexpect_process.after)
    logging.debug("Output:\n{:s}".format(output))
    logging.info(parse_backspace(output))


def expect_eof(pexpect_process, timeout=None):
    """Function that waits for an EOF from the given process."""
    pexpect_process.expect(pexpect.EOF, timeout)
    logging.debug("EOF received")


def output_should_contain(output, should_contain):
    if should_contain in output:
        return True
    else:
        return False


def output_should_begin_with(output, should_begin):
    regex = "^[\s]*" + should_begin + "[\s\S]*"
    if re.match(regex, output):
        return True
    else:
        return False


def output_should_end_with(output, should_end):
    regex = "[\s\S]*" + should_end + "[\s\S]*$"
    if re.match(regex, output):
        return True
    else:
        return False


def output_should_match_regex(output, regex):
    if re.match(regex, output):
        return True
    else:
        return False


def output_should_be_empty(output):
    if len(output) == 0:
        return True
    else:
        return False


def output_should_not_be_empty(output):
    if len(output) != 0:
        return True
    else:
        return False
