import time
import logging
import os

class CiscoOutput:

    def __init__(self, output_file_path, output_file_suffix):

        #curr_date_time = time.strftime('%Y%m%d:%H:%M:%S')
        #logging.debug('curr_date_time: {:s}'.format(curr_date_time))

        # Create output file directory if does not exists
        #out_dir = os.path.dirname(output_file_path)

        #if not os.path.exists(out_dir):
            #logging.info("Creating directory {:s}".format(out_dir))
            #os.makedirs(out_dir)

        output_filename = output_file_path + curr_date_time + "_" + output_file_suffix
        #logging.info("Output file: {:s}".format(output_filename))

        #self.output_file = open(output_filename, 'a+')
  
    def write(self, string):
        print(string)
        #self.output_file.write(string)
