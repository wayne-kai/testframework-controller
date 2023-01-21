import logging
import subprocess
import re

class RSALib(object):

    def __init__(self):

        self.programName = "openssl"
        self.argsForExtractModulus = ["rsa","-pubin","-modulus","-noout","-in"]

    def get_modulus_from_keyfile(self, keyfile):

        modulusStr = ""

        #   Create a new list for constructing the command to run by subprocess
        #   Program name is always the first to be added
        cmdToRun = []
        cmdToRun.append(self.programName)

        #   Adds each arg into the command to run
        for arg in self.argsForExtractModulus:
            cmdToRun.append(arg)

        #   Add the input file as the last
        logging.info("Extracting modulus from public key file, {}".format(keyfile))
        cmdToRun.append(keyfile)

        #   Run command via subprocess
        for item in cmdToRun:
            logging.debug("{}".format(item))
        logging.debug("Running command, [{}]".format(" ".join(cmdToRun)))
        p = subprocess.Popen(cmdToRun, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE)

        #   Command should not require any input
        out, err = p.communicate()
        logging.debug("Output: [{}]".format(out))
        logging.debug("Error: [{}]".format(err))

        #   Extract the modulus from the output of the command
        compiledPattern = re.compile("[\s\S]*Modulus=(.*)[\s\S]*")
        m = compiledPattern.match(out)
        if m is not None:
            
            #   Extract the modulus from the result
            modulusStr = m.group(1)
            logging.info("Modulus: [{}]".format(modulusStr))

        return modulusStr

    def construct_match_pattern(self, modulusStr, noOfBytesInARow=16, separator=":"):

        #   Check if the string has no. of characters
        #   which is multiple of 2 (2 characters = 1 byte representation)
        if len(modulusStr) % 2 != 0:
            raise ValueError("Modulus String does not represent an array of bytes.")

        #   Constructing the string pattern to be matched
        #   a specific display requirement

        logging.info("Modulus: [{}]".format(modulusStr))
        logging.debug("No. of characters in Modulus: [{}]".format(len(modulusStr)))        

        logging.debug("No. of bytes in a row: [{}]".format(noOfBytesInARow))
        logging.debug("Separator character: [{}]".format(separator))
        
        #   To match everything before the string pattern
        outputModulusStr = "[\s\S]*"

        #   Iterate through all the characters
        for index in range(0, len(modulusStr) - 1, 2):

            #   Append the first character of the byte representation
            outputModulusStr += modulusStr[index]

            #   Append the second character of the byte representation
            outputModulusStr += modulusStr[index + 1]

            #   Append the separator when it is not yet the end
            if (index + 2) < len(modulusStr):
                outputModulusStr += separator

            #   Append the regex representation
            #   for any special characters + tab, space, carriage return and new line
            if (index + 2) % (noOfBytesInARow * 2) == 0:
                outputModulusStr += "[ \\t\\r\\n\S]*"

        logging.info("Match pattern: [{}]".format(outputModulusStr))

        return outputModulusStr