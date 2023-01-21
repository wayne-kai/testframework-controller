import re
import logging
import MySQLdb
import time
from contextlib import closing
from dateutil.parser import parse
from Common import spawn_and_print


# Fields to extract from the 'accounting' table
ACCOUNTING_FIELDS = (
        'id', 'nas', 'uid', 'terminal', 'client_ip', 'type', 'service',
        'priv_lvl', 'cmd', 'elapsed_time')

# Fields to extract from the 'access' table
ACCESS_FIELDS = (
        'id', 'nas', 'terminal', 'uid', 'client_ip', 'service', 'status')

# Fields to extract from the 'Syslog.systemevents' table
SYSTEMEVENTS_FIELDS = (
        'id', 'receivedat', 'devicereportedtime', 'fromhost', 'message',
        'syslogtag')

# Fields to extract from the 'net_snmp.notifications' table
# net_snmp.varbinds.trap_id, date_time, host, auth,
# net_snmp.notifications.type AS 'snmp_type', version, request_id,
# snmpTrapOID, transport, security_model, oid,
# net_snmp.varbinds.type AS 'oid_type',
# CAST(value AS CHAR(1000) CHARACTER SET utf8) AS 'string_value'
SNMPNOTIFICATION_FIELDS = (
        'net_snmp.varbinds.trap_id', 'date_time', 'auth', 'snmptrapoid',
        'transport', 'security_model', 'oid',
        'net_snmp.varbinds.type AS \'oid_type\'',
        'CAST(value AS CHAR(1000) CHARACTER SET utf8) AS \'string_value\'')


class CiscoShowHistoryLog:

    def __init__(self, line):

        # Use Regex to search for the date and time
        mTime = re.search("(\d{2}:\d{2}:\d{2})", line)
        mDate = re.search("((Mon|Tue|Wed|Thu|Fri|Sat|Sun)?( )?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{2}( )?(\d{4})?)", line)

        # Parse the datetime of the log entry
        if mDate and mTime:
            self.logDateTime = parse(mDate.group(0).strip() + " " + mTime.group(0).strip(),
                                     dayfirst=True)
        elif mDate:
            self.logDateTime = parse(mDate.group(0).strip(), dayfirst=True)
        elif mTime:
            self.logDateTime = parse(mTime.group(0).strip())
        else:
            self.logDateTime = None

        self.line = line


class CiscoLogging:

    def __init__(self, tacacs_IP, syslog_IP, snmp_IP):

        self.tacacs_IP = tacacs_IP
        self.syslog_IP = syslog_IP
        self.snmp_IP = snmp_IP

        self.show_history_all_last = None
        self.show_history_all = None
        self.buffered = None
        self.archive = None
        self.tacacs_access = None
        self.tacacs_accounting = None
        self.syslog = None
        self.snmp = None
        self.shHistLogList = None

        self.tacacs_db_user = "tacacs"
        self.tacacs_db_pass = "tac_plus"
        self.tacacs_db_name = "tacacs"
        self.tacacs_access_table = "tacacs.access"
        self.tacacs_accounting_table = "tacacs.accounting"

        self.syslog_snmp_db_user = "testfw"
        self.syslog_snmp_db_pass = "password"
        self.syslog_db_name = "Syslog"
        self.syslog_table = "Syslog.SystemEvents"
        self.snmp_db_name = "net_snmp"
        self.snmp_table = "net_snmp.notifications RIGHT JOIN net_snmp.varbinds ON net_snmp.varbinds.trap_id = net_snmp.notifications.trap_id"

        self.access_id = 0
        self.accounting_id = 0
        self.syslog_id = 0
        self.snmp_id = 0

    def clear_local_logs(self, cisco_conn, log_check_list):
        """Clear Syslog log buffer and archive log."""

        # Clear Syslog Log buffer
        if "show log" in log_check_list:
            cisco_conn.sendline("clear log")
            cisco_conn.expectline("Clear logging buffer \[confirm\]")
            cisco_conn.sendline_and_expect_hostname()

        # Clear Archive Log
        if "show archive log config all" in log_check_list:
            cisco_conn.sendline_and_expect_hostname("configure terminal")
            cisco_conn.sendline_and_expect_hostname("archive")
            cisco_conn.sendline_and_expect_hostname("log config")
            cisco_conn.sendline_and_expect_hostname("no logging enable")
            cisco_conn.sendline_and_expect_hostname("logging enable")
            cisco_conn.sendline_and_expect_hostname("end")

    def logging_start(self, cisco_conn, log_check_list):

        self.clear_local_logs(cisco_conn, log_check_list)

        if "show history all" in log_check_list:
            self.show_history_all_last = self.get_show_history_all_last(cisco_conn)

        logging.debug("### SNMP Flush out before starting log (experimental)  ###")
        logging.debug("Waiting for SNMP to flush itself...")
        time.sleep(120)
        logging.debug("Waiting for SNMP to flush itself... DONE")

        if "tacacs access" in log_check_list:
            self.access_id = self.get_database_table_last_id(self.tacacs_IP,
                                                            self.tacacs_db_user,
                                                            self.tacacs_db_pass,
                                                            self.tacacs_db_name,
                                                            self.tacacs_access_table) + 1

        if "tacacs accounting" in log_check_list:
            self.accounting_id = self.get_database_table_last_id(self.tacacs_IP,
                                                                self.tacacs_db_user,
                                                                self.tacacs_db_pass,
                                                                self.tacacs_db_name,
                                                                self.tacacs_accounting_table) + 1

        if "syslog" in log_check_list:
            self.syslog_id = self.get_database_table_last_id(self.syslog_IP,
                                                            self.syslog_snmp_db_user,
                                                            self.syslog_snmp_db_pass,
                                                            self.syslog_db_name,
                                                            self.syslog_table) + 1

        if "snmp" in log_check_list:
            self.snmp_id = self.get_database_table_last_id(self.snmp_IP,
                                                        self.syslog_snmp_db_user,
                                                        self.syslog_snmp_db_pass,
                                                        self.snmp_db_name,
                                                        self.snmp_table,
                                                        id_name="net_snmp.varbinds.trap_id") + 1

        logging.debug("last id in snmp:{}".format(self.snmp_id))

    def logging_retrieve(self, cisco_conn, log_check_list,test_user):
        self.logging_read(cisco_conn, log_check_list, test_user)
        self.logging_write_all()

    def logging_read(self, cisco_conn, log_check_list, test_user):
        '''Read the logs since running "logging_start()".'''

        # Retrieving the tacacs access records
        if "tacacs access" in log_check_list:
            self.tacacs_access = self.get_tacacs_access_logs(cisco_conn.IP,
                                                            test_user)

        # Retrieving the tacacs accounting records
        if "tacacs accounting" in log_check_list:
            self.tacacs_accounting = self.get_tacacs_accounting_logs(cisco_conn.IP,
                                                                    test_user)

        # Retrieving the syslog_snmp records
        if "syslog" in log_check_list:
            self.syslog = self.get_syslogs(cisco_conn.IP)

        # Retrieving the syslog_snmp records
        if "snmp" in log_check_list:
            self.snmp = self.get_snmp_logs(cisco_conn.IP)

        # !Note! Remote servers logs should run before local logs

        # Retrieving the 'show history all' records
        if ("show history all" in log_check_list) or self.show_history_all_last:
            self.show_history_all = self.get_show_history_all_new(
                    cisco_conn, self.show_history_all_last)

        # Retrieving the 'show logging' 'Log Buffer' records
        if "show log" in log_check_list:
            self.buffered = self.get_show_logging_logs(cisco_conn)

        # Retrieving the 'show archive log config all' records
        if "show archive log config all" in log_check_list:
            self.archive = self.get_archive_logs(cisco_conn)

    def get_buffered_log(self):
        return self.buffered

    def _convert_tuple_to_string(self, db_tuples):
        str_out = ""

        for innerlist in db_tuples:
            inner_out = ""

            for item in innerlist:

                if inner_out == "":
                    inner_out = str(item)
                else:
                    inner_out = inner_out + "\t" + str(item)

            if str_out == "":
                str_out = inner_out
            else:
                str_out = str_out + "\n" + inner_out

        return str_out

    def get_tacacs_access_log(self):
        return self._convert_tuple_to_string(self.tacacs_access)

    def get_tacacs_accounting_log(self):
        return self._convert_tuple_to_string(self.tacacs_accounting)

    def get_syslog_log(self):
        return self._convert_tuple_to_string(self.syslog)

    def get_snmp_log(self):
        return self._convert_tuple_to_string(self.snmp)

    def get_history_all_log(self):
        return " ".join(self.show_history_all)

    def get_archive_log(self):
        return self.archive

    def logging_write_all(self):
        self.logging_write(self.tacacs_access, "Tacacs Access Logs")
        self.logging_write(self.tacacs_accounting, "Tacacs Accounting Logs")
        self.logging_write(self.syslog, "Remote Syslog")
        self.logging_write(self.snmp, "SNMP Logs")

    def logging_write(self, logs, log_name):
        logging.info(
                "\n**************\n{}:\n**************\n".format(log_name))

        if len(logs) == 0:
            logging.info("No records found.\n")
        else:
            logging.info(self._convert_tuple_to_string(logs))

    def get_tacacs_access_logs(self, router_ip, user):

        conn = MySQLdb.connect(host=self.tacacs_IP,
                               user=self.tacacs_db_user,
                               passwd=self.tacacs_db_pass,
                               db=self.tacacs_db_name,
                               port=3306)

        with closing(conn) as db:
            with closing(db.cursor()) as cur:
                return self.query_table(cur,
                                        ACCESS_FIELDS,
                                        self.tacacs_access_table,
                                        self.access_id, "id",
                                        router_ip, "nas",
                                        user, "uid")

    def get_tacacs_accounting_logs(self, router_ip, user):

        conn = MySQLdb.connect(host=self.tacacs_IP,
                               user=self.tacacs_db_user,
                               passwd=self.tacacs_db_pass,
                               db=self.tacacs_db_name,
                               port=3306)

        with closing(conn) as db:
            with closing(db.cursor()) as cur:
                return self.query_table(cur,
                                        ACCOUNTING_FIELDS,
                                        self.tacacs_accounting_table,
                                        self.accounting_id, "id",
                                        router_ip, "nas",
                                        user, "uid")

    def get_syslogs(self, router_ip):

        conn = MySQLdb.connect(host=self.syslog_IP,
                               user=self.syslog_snmp_db_user,
                               passwd=self.syslog_snmp_db_pass,
                               db=self.syslog_db_name,
                               port=3306)

        with closing(conn) as db:
            with closing(db.cursor()) as cur:
                return self.query_table(cur,
                                        SYSTEMEVENTS_FIELDS,
                                        self.syslog_table,
                                        self.syslog_id, "id",
                                        router_ip, "FromHost")

    def get_snmp_logs(self, router_ip):

        conn = MySQLdb.connect(host=self.snmp_IP,
                               user=self.syslog_snmp_db_user,
                               passwd=self.syslog_snmp_db_pass,
                               db=self.snmp_db_name,
                               port=3306)

        with closing(conn) as db:
            with closing(db.cursor()) as cur:
                return self.query_table(cur,
                                        SNMPNOTIFICATION_FIELDS,
                                        self.snmp_table,
                                        self.snmp_id,
                                        "net_snmp.varbinds.trap_id",
                                        router_ip, "transport")

    def query_table(self,
                    cur,
                    fields,
                    table,
                    id_start,
                    id_field_name,
                    router_ip=None,
                    router_ip_field_name=None,
                    user=None,
                    user_field_name=None):
        """ Return rows from a table with the given fields."""

        query = """SELECT {0} FROM {1}""".format(','.join(fields), table)
        parameters = list()
        where_clauses = list()

        if id_start:
            where_clauses.append(id_field_name + " >= %s")
            parameters.append(id_start)
            logging.debug("id_start = {}".format(id_start))

        if user:
            where_clauses.append(user_field_name + " = %s")
            parameters.append(user)
            logging.debug("user = {}".format(user))

        if router_ip:
            if router_ip_field_name == "transport":
                router_ip = "UDP: [%s]%%" % router_ip
                where_clauses.append(router_ip_field_name + " LIKE %s")
            else:
                where_clauses.append(router_ip_field_name + " = %s")
            parameters.append(router_ip)
            logging.debug("router_ip = {}".format(router_ip))

        if where_clauses:
            query = query + " WHERE " + " AND ".join(where_clauses)

        logging.debug("SQL Query exec: {}".format(query))
        cur.execute(query, parameters)
        return cur.fetchall()

    def get_database_table_last_id(self,
                                   db_ip,
                                   db_user,
                                   db_pass,
                                   db_name,
                                   table,
                                   port=3306,
                                   id_name="ID"):

        query = "SELECT " + id_name + " FROM " + table + " ORDER BY " + id_name + " DESC" + " LIMIT 1"

        conn = MySQLdb.connect(host=db_ip,
                               user=db_user,
                               passwd=db_pass,
                               db=db_name,
                               port=port)

        with closing(conn) as db:
            with closing(db.cursor()) as cur:
                cur.execute(query)
                row = cur.fetchone()
                return int(row[0])

    def get_syslog_snmp_logs(self, router_IP):

        syslog_snmp_process = spawn_and_print(
                "python",
                [
                    "syslog_snmp_logs_db.py", self.syslog_IP,
                    "--filter-nas", router_IP,
                    "--filter-id", str(self.syslog_snmp_id),
                ],
                maxread=10000)
        syslog_snmp = syslog_snmp_process.read()
        syslog_snmp_process.close()
        return syslog_snmp

    def get_show_history_all(self, cisco_conn):

        bDoNotSort = False

        #   Execute "show history all" command
        cisco_conn.sendline_and_expect_hostname("show history all")

        #   Log the size of the show history all buffer
        logging.debug("Show History All buffer size: {}".format(len(cisco_conn.before())))

        #   Split by lines
        lines = cisco_conn.before().splitlines()

        showHistLogList = []
        bWriteDateTimeBackwards = False

        for line in (lines):

            # Should match either "CMD:" or "001293:" to be unique
            found = re.search("^((\*(.+?):)|[\d]+:|CMD:)(.+?)$", line)
            if found:

                # Convert line into a show hist entry object
                showHistLog = CiscoShowHistoryLog(line)

                # Handle the case when entry does not have a date time in
                # string
                if showHistLog.logDateTime is None:

                    logging.debug("Current entry({}) has no date time".format(line))
                    logging.debug("List has {} entry(s)".format(len(showHistLogList)))

                    if len(showHistLogList) > 0 and bWriteDateTimeBackwards == False:
                        showHistLog.logDateTime = showHistLogList[-1].logDateTime
                        bWriteDateTimeBackwards = False

                    #   Default assignment to indicate that there is a need to
                    #   transverse backwards in the entry
                    bWriteDateTimeBackwards = True

                else:

                    #   Indicates that there are entries without datetime
                    #   behind
                    #   Note: This is to cover the first few entries without
                    #   date time
                    if bWriteDateTimeBackwards == True:

                        logging.debug("Backporting datetime")

                        #   Transversing backwards to ensure that all entries
                        #   are with datetime
                        for logEntry in reversed(showHistLogList):

                            if logEntry.logDateTime is None:
                                logEntry.logDateTime = showHistLog.logDateTime
                            else:
                                break

                        bWriteDateTimeBackwards = False

                        logging.debug("Backporting datetime ... DONE")

                # Add the current entry to list
                showHistLogList.append(showHistLog)

        #   This is to handle the case where there is entries without datetime at the end
        #   of the "show history all" list
        if bWriteDateTimeBackwards == True:

            logging.debug("Found entry(s) witout datetime at the end")

            #   Search for an entry before the first entry without datetime
            for logEntry in reversed(showHistLogList):

                if logEntry.logDateTime is not None:
                    logDateTimeToBP = logEntry.logDateTime
                    break

            #   To guard against case where there is completely no entry with datetime
            #   NOTE: Unlikely case but this is just failsafe
            if logDateTimeToBP is None:
                
                #   No point in sorting since there are no entry with datetime
                bDoNotSort = True

            else:

                logging.debug("Backporting date time")

                #   Transversing backwards to ensure that all entries are with datetime
                for logEntry in reversed(showHistLogList):

                    if logEntry.logDateTime is None:
                        logEntry.logDateTime = showHistLog.logDateTime
                    else:
                        break                            

            bWriteDateTimeBackwards = False

        if bDoNotSort == False:
            
            # Sort the list in order of early to latest
            showHistLogList.sort(key=lambda CiscoShowHistoryLog: CiscoShowHistoryLog.logDateTime)

        # Store list to class member
        self.shHistLogList = showHistLogList

        return showHistLogList

    def get_show_history_all_last(self, cisco_conn):
        """
        Get logs that start from the last unique line of show history all.
        """

        showHistLogList = self.get_show_history_all(cisco_conn)

        if showHistLogList.count > 0:
            return showHistLogList[-1]
        else:
            return None

    def get_show_history_all_new(self, cisco_conn, last_list):
        """Get logs that start from "being" line of show history all."""

        logging.debug('last_list: {:s}'.format(last_list.line))

        showHistLogList = self.get_show_history_all(cisco_conn)

        new_logs = []

        logging.debug("prev_last: {}".format(last_list.line))
        for entry in showHistLogList:
            logging.debug("current entry: {}".format(entry.line))
            if entry.logDateTime > last_list.logDateTime:
                logging.debug("New log found!!")
                new_logs.append(entry.line)

        logging.debug('new_logs: {:s}'.format(new_logs))

        return new_logs

    def get_archive_logs(self, cisco_conn):
        cisco_conn.sendline_and_expect_hostname("show archive log config all")

        return cisco_conn.before().split("Logged command", 1)[1]

    def get_show_logging_logs(self, cisco_conn):
        cisco_conn.sendline_and_expect_hostname("show logging")

        return re.search("Log Buffer \([\d]* bytes\):([\s\S]*)$",
                         cisco_conn.before()).group(1)
