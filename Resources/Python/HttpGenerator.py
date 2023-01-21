#!/usr/bin/env python

import time
import sys
import argparse
import logging
import urllib2
import multiprocessing
import collections


HTTPResult = collections.namedtuple("HTTPResult",
                                    ("url", "header", "code", "error"))


def _http_request_worker(url, timeout):
    """Worker function that generates HTTP GET requests."""

    try:
        f = urllib2.urlopen(url=url, timeout=timeout)

        result = HTTPResult(url=f.geturl(),
                            header=f.info(),
                            code=f.getcode(),
                            error='')

        f.close()

    except urllib2.URLError as e:
        result = HTTPResult(url=url, header='', code=0, error=str(e))

    return result


class HttpGenerator(object):
    """Generate HTTP requests."""

    ROBOT_LIBRARY_VERSION = "1.0.0"

    def generate_http_get_traffic(self, target_host, connections, http_timeout=3):
        """Generate HTTP traffic to a host."""

        host = str(target_host)
        num_connections = int(connections)
        timeout = int(http_timeout)

        logging.debug("Host = {:s}".format(host))
        logging.debug("Connections = {:d}".format(num_connections))
        logging.debug("HTTP timeout = {:d}".format(timeout))

        logging.info("Generating {:d} HTTP GET requests to {:s}"
                     "".format(num_connections, host))

        start_time = time.time()

        pool = multiprocessing.Pool()
        responses = {}
        for request_id in range(1, num_connections+1):
            responses[request_id] = pool.apply_async(func=_http_request_worker,
                                                     args=(host, timeout))

        pool.close()
        pool.join()

        stop_time = time.time()
        status_ok_count = 0

        for request_id in sorted(responses):

            result = responses[request_id].get()
            logging.debug("HTTP Request ID: {:d}\nurl: {:s}\ncode: {:d}\n"
                          "error: {:s}\nheader:\n{:s}"
                          "".format(request_id,
                                    result.url,
                                    result.code,
                                    result.error,
                                    result.header))

            if result.code == 200:
                status_ok_count += 1
            else:
                logging.error("HTTP Request ID: {:d}\ncode: {:d}\nerror: {:s}"
                              "".format(request_id, result.code, result.error))

        elapsed = stop_time - start_time

        logging.info("{:d} HTTP GET requests in {:f} seconds"
                     "".format(num_connections, elapsed))

        if status_ok_count == num_connections:
            logging.info("{:d} successful GET requests made"
                         "".format(status_ok_count))
        else:
            raise IOError("{:d} HTTP requests failed"
                          "".format(num_connections - status_ok_count))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Generate HTTP requests")
    parser.add_argument("host", help="Host")
    parser.add_argument("--connections",
                        help="Number of connections",
                        type=int,
                        default=1)
    parser.add_argument("--timeout",
                        help="Timeout in seconds",
                        type=int,
                        default=3)
    parser.add_argument("--debug",
                        help="Enable debug output",
                        action="store_true")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    result = 0
    hg = HttpGenerator()

    try:
        hg.generate_http_get_traffic(args.host, args.connections, args.timeout)

    except IOError as e:
        print(e)
        logging.error(e)
        result = 1

    except Exception as e:
        print(e)
        logging.exception(e)
        result = 1

    sys.exit(result)
