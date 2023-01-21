import logging
import re


class CiscoCmdDescriptor(object):

    def __init__(self, cmd):
        self.cmd = cmd
        self.contain = list()
        self.notcontain = list()
        self.begin = list()
        self.end = list()
        self.regex = list()
        self.empty = None
        self.logger = logging.getLogger(__name__)

    def should_contain(self, contain):
        self.contain.append(contain)

    def should_not_contain(self, notcontain):
        self.notcontain.append(notcontain)

    def should_begin_with(self, begin):
        self.begin.append(begin)

    def should_end_with(self, end):
        self.end.append(end)

    def should_matched_regex(self, regex):
        self.regex.append(regex)

    def should_be_empty(self):
        self.empty = True

    def should_not_be_empty(self):
        self.empty = False

    def add_criteria(self,
                     should_contain=None,
                     should_not_contain=None,
                     should_begin_with=None,
                     should_end_with=None,
                     should_match_regex=None,
                     should_be_empty=None):

        if should_contain:
            self.logger.debug("Add to contain [{}]".format(should_contain))
            self.contain.append(should_contain)

        if should_not_contain:
            self.logger.debug("Add to not contain [{}]".format(should_not_contain))
            self.notcontain.append(should_not_contain)

        if should_begin_with:
            self.begin.append(should_begin_with)

        if should_end_with:
            self.end.append(should_end_with)

        if should_match_regex:
            self.regex.append(should_match_regex)

        if should_be_empty is not None:
            self.empty = should_be_empty

    def parse_cmd_output(self, output):

        errmsg = ""

        # Check if output is empty
        if output.strip():
            # Not empty
            if self.empty is True:
                # Should be empty
                errmsg += "\t-> Output is not empty [{}]\n".format(output)

            if self.contain:
                for string in self.contain:
                    if string not in output:
                        errmsg += "\t-> Output does not contain[{}]\n".format(string)

            if self.notcontain:
                for string in self.notcontain:
                    if string in output:
                        errmsg += "\t-> Output contains[{}]\n".format(string)

            if self.begin:
                for start in self.begin:
                    regex = "^[\s]*" + start + "[\s\S]*"

                    if re.match(regex, output) is None:
                        errmsg += "\t-> Output does not begin with [{}]\n".format(start)

            if self.end:
                for last in self.end:
                    regex = "[\s\S]*" + last + "[\s\S]*$"

                    if re.match(regex, output) is None:
                        errmsg += "\t-> Output does not end with [{}]\n".format(last)

            if self.regex:
                for rgx in self.regex:
                    self.logger.debug("rgx[{}]\noutput[{}]\n".format(rgx,
                                                                     output))
                    output_hex = ":".join("{:02x}".format(ord(c)) for c in output)
                    self.logger.debug("output_hex[{}]\n".format(output_hex))
                    if re.match(rgx, output) is None:
                        errmsg += "\t-> Output does not match regex [{}]\n".format(rgx)

        else:
            # Empty!
            if self.empty is False:
                # Should not be empty
                errmsg += "\t-> Output is empty\n"

            if self.contain:
                for should in self.contain:
                    errmsg += "\t-> Output should contain[{}]\n".format(should)
            if self.begin:
                for should in self.begin:
                    errmsg += "\t-> Output should begin with[{}]\n".format(should)
            if self.end:
                for should in self.end:
                    errmsg += "\t-> Output should end with[{}]\n".format(should)
            if self.regex:
                for should in self.regex:
                    errmsg += "\t-> Output should match regex[{}]\n".format(should)

        return errmsg
