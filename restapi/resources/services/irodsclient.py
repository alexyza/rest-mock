# -*- coding: utf-8 -*-

"""

### iRODS abstraction for FS virtualization with resources ###

My irods client class wrapper.

Since python3 is not ready for irods official client,
we based this wrapper on plumbum package handling shell commands.

"""

import os
import inspect
import re
from collections import OrderedDict
from ..basher import BashCommands
from confs.config import IRODS_ENV

# from ..templating import Templa
# from . import string_generator, appconfig

from restapi import get_logger
logger = get_logger(__name__)

IRODS_USER_ALIAS = 'clientUserName'
CERTIFICATES_DIR = '/opt/certificates'


# ######################################
#
# # Basic iRODS client commands
#
# ######################################

class ICommands(BashCommands):
    """irods icommands in a class"""

    _init_data = {}
    _current_environment = None
    _base_dir = ''

    first_resource = 'demoResc'
    second_resource = 'replicaResc'

    def __init__(self, user=None, irodsenv=IRODS_ENV):

        # Recover plumbum shell enviroment
        super(ICommands, self).__init__()

        # How to add a new user
        # $ iadmin mkuser guest rodsuser

        # In case i am the admin
        if user is None:
            # Use the physical file for the irods environment
            self.irodsenv = irodsenv
            self.become_admin()
            # Verify if connected
# // TO FIX: change it to ilsresc
            self.list()
        # A much common use case: a request from another user
        else:
            self.change_user(user)

    #######################
    # ABOUT CONFIGURATION
    def become_admin(self):
        """
        Try to check if you're on Docker and have variables set
        to become iRODS administrator.

        It can also be used without docker by setting the same
        environment variables.

        Possible schemes: 'credentials', 'GSI', 'PAM'
        """
        authscheme = os.environ.get('IRODS_AUTHSCHEME', None)
        if authscheme is None:
            authscheme = 'credentials'

        user = os.environ.get('IRODS_USER', None)
        if user is None:
            raise BaseException(
                "Cannot become admin without env var 'IRODS_USER' set!")

        if authscheme == 'credentials' or authscheme == 'PAM':

# // TO FIX: use the method prepare_irods_environment...

            self._init_data = OrderedDict({
                "irods_host": os.environ['ICAT_1_ENV_IRODS_HOST'],
                "irods_port":
                    int(os.environ['ICAT_1_PORT'].split(':')[::-1][0]),
                "irods_user_name": user,
                "irods_zone_name": os.environ['IRODS_ZONE'],
                # "irods_password": os.environ['ICAT_1_ENV_IRODS_PASS']
            })

            # Set external auth scheme if requested
            if authscheme is not None:
                self._init_data["irods_authentication_scheme"] = authscheme

            with open(self.irodsenv, 'w') as fw:
                import json
                json.dump(self._init_data, fw)

            self.set_password()
            logger.info("Saved irods admin credentials")
            logger.debug("iRODS admin environment found\n%s" % self._init_data)

        elif authscheme == 'GSI':
            self.prepare_irods_environment(user, authscheme)

    def set_password(self, tmpfile='/tmp/temppw'):
        """
        Interact with iinit to set the password.
        This is the case i am not using certificates.
        """

        passw = os.environ.get('ICAT_1_ENV_IRODS_PASS', None)
        if passw is None:
            raise BaseException(
                "Missing password: Use env var 'ICAT_1_ENV_IRODS_PASS'")

        from plumbum.cmd import iinit
        with open(tmpfile, 'w') as fw:
            fw.write(passw)
        com = iinit < tmpfile
        com()
        os.remove(tmpfile)
        logger.debug("Pushed credentials")

    def get_user_home(self, user):
        return os.path.join(
            '/' + self._init_data['irods_zone_name'],
            'home',
            user)

    def prepare_irods_environment(self, user, schema='GSI'):
        """
        Prepare the OS variables environment
        which allows to become another user using the GSI protocol.

        It requires that user to be recognized inside the iRODS server,
        e.g. the certificate is available on the server side.
        """

        irods_env = os.environ.copy()

        zone = os.environ.get('IRODS_ZONE', None)
        if zone is None:
            raise BaseException(
                "Missing zone: Use env var 'IRODS_ZONE'")
        home = os.environ.get('IRODS_CUSTOM_HOME', '/home')

        irods_env['IRODS_USER_NAME'] = user
        irods_env['IRODS_HOME'] = '/' + zone + home + '/' + user
        irods_env['IRODS_AUTHENTICATION_SCHEME'] = schema
        irods_env['IRODS_HOST'] = os.environ['ICAT_1_ENV_IRODS_HOST']
        irods_env['IRODS_PORT'] = \
            int(os.environ['ICAT_1_PORT'].split(':')[::-1][0])
        irods_env['IRODS_ZONE'] = zone

        if schema == 'GSI':
            # ## X509 certificates variables
            # CA Authority
            irods_env['X509_CERT_DIR'] = CERTIFICATES_DIR + '/caauth'
            # ## USER PEMs: Private (key) and Public (Cert)
            irods_env['X509_USER_CERT'] = \
                CERTIFICATES_DIR + '/' + user + '/usercert.pem'
            irods_env['X509_USER_KEY'] = \
                CERTIFICATES_DIR + '/' + user + '/userkey.pem'

            # PROXY ?

        # # DEBUG
        # for key, item in irods_env.items():
        #     if 'irods' == key[0:5].lower() or 'x509_' == key[0:5].lower():
        #         print("ITEM", key, item)

        if schema == 'PAM':
            # irodsSSLCACertificateFile PATH/TO/chain.pem
            # irodsSSLVerifyServer      cert
            logger.critical("PAM not IMPLEMENTED yet")
            return False

        self._current_environment = irods_env
        return irods_env

    def change_user(self, user=None):
        """ Impersonification of another user because you're an admin """

# Where to change with:
# https://github.com/EUDAT-B2STAGE/http-api/issues/1#issuecomment-196729596
        self._current_environment = None

        if user is None:
            # Do not change user, go with the main admin
            user = self._init_data['irods_user_name']
        else:
            #########
            # # OLD: impersonification because i am an admin
            # Use an environment variable to reach the goal
            # os.environ[IRODS_USER_ALIAS] = user

            #########
            # # NEW: use the certificate
            self.prepare_irods_environment(user)

        logger.info("Switched to user '%s'" % user)

        # If i want to check
        # return self.list(self.get_user_home(user))
        return True

    ###################
    # Basic command with the GSI plugin
    def basic_icom(self, com, args=[]):
        """
        Use the current environment variables to be another irods user
        """
        return self.execute_command(
            com,
            parameters=args,
            env=self._current_environment)

    ###################
    # ICOMs !!!
    def get_base_dir(self):
        com = "ipwd"
        return self.basic_icom(com).strip()

    def list(self, path=None, detailed=False):
        """ List the files inside an iRODS path/collection """

        # Prepare the command
        com = "ils"
        if path is None:
            path = self.get_base_dir()
        args = [path]
        if detailed:
            args.append("-l")
        # Do it
        stdout = self.basic_icom(com, args)
        # Parse output
        lines = stdout.splitlines()
        replicas = []
        for line in lines:
            replicas.append(re.split("\s+", line.strip()))
        return replicas

    def save(self, path, destination=None):
        com = 'iput'
        args = [path]
        if destination is not None:
            args.append(destination)
        # Execute
        return self.basic_icom(com, args)

################################################
################################################

###### WE NEED TO CHECK ALL THIS ICOMMANDS BELOW

################################################
################################################

    def get_resource_from_dataobject(self, ifile):
        """ The attribute of resource from a data object """
        details = self.list(ifile, True)
        resources = []
        for element in details:
            # 2nd position is the resource in irods ils -l
            resources.append(element[2])
        return resources

    def create_empty(self, path, directory=False, ignore_existing=False):
        args = [path]
        if directory:
            com = "imkdir"
            if ignore_existing:
                args.append("-p")
        else:
            # // TODO:
            # super call of create_tempy with file (touch)
            # icp / iput of that file
            # super call of remove for the original temporary file
            logger.debug("NOT IMPLEMENTED for a file '%s'" %
                         inspect.currentframe().f_code.co_name)
            return

        # Debug
        self.execute_command(com, args)
        logger.debug("Created %s" % path)
        # com = ""
        # self.execute_command(com, [path])

    def current_location(self, ifile):
        """
        irods://130.186.13.14:1247/cinecaDMPZone/home/pdonorio/replica/test2
        """
        protocol = 'irods://'
        URL = protocol + \
            self._init_data['irodsHost'] + ':' + \
            self._init_data['irodsPort'] + \
            os.path.join(self._base_dir, ifile)
        return URL

    def remove(self, path, recursive=False, force=False):
        com = 'irm'
        args = []
        if force:
            args.append('-f')
        if recursive:
            args.append('-r')
        args.append(path)
        # Execute
        self.execute_command(com, args)
        # Debug
        logger.debug("Removed irods object: %s" % path)

    def check(self, path, retcodes=(0, 4)):
        """
        Retcodes for this particular case, skip also error 4, no file found
        """
        (status, stdin, stdout) = self.list(path, False, retcodes)
        logger.debug("Check %s with %s " % (path, status))
        return status == 0

    def search(self, path, like=True):
        com = "ilocate"
        if like:
            path += '%'
        logger.debug("iRODS search for %s" % path)
        # Execute
        try:
            out = self.execute_command(com, path)
        except Exception:
            logger.debug("No data found.")
            exit(1)
        if out:
            return out.strip().split('\n')
        return out

    def replica(self, dataobj, replicas_num=1, resOri=None, resDest=None):
        """ Replica
        Replicate a file in iRODS to another storage resource.
        Note that replication is always within a zone.
        """

        com = "irepl"
        if resOri is None:
            resOri = self.first_resource
        if resDest is None:
            resDest = self.second_resource

        args = [dataobj]
        args.append("-P")  # debug copy
        args.append("-n")
        args.append(replicas_num)
        # Ori
        args.append("-S")
        args.append(resOri)
        # Dest
        args.append("-R")
        args.append(resDest)

        return self.execute_command(com, args)

    def replica_list(self, dataobj):
        return self.get_resource_from_dataobject(dataobj)


# ######################################
#
# # iRODS and METADATA
#
# ######################################

# class IMetaCommands(ICommands):
#     """irods icommands in a class"""
#     ###################
#     # METADATA for irods

#     def meta_command(self, path, action='list', attributes=[], values=[]):
#         com = "imeta"
#         args = []

#         # Base commands for imeta:
#         # ls, set, rm
#         # - see https://docs.irods.org/master/icommands/metadata/#imeta
#         if action == "list":
#             args.append("ls")
#         elif action == "write":
#             args.append("set")
#         elif action != "":
#             raise KeyError("Unknown action for metadata: " + action)
#         # imeta set -d FILEPATH a b
#         # imeta ls -d FILEPATH
#         # imeta ls -d FILEPATH a

#         # File to list metadata?
#         args.append("-d") # if working with data object metadata
#         args.append(path)

#         if len(attributes) > 0:
#             if len(values) == 0 or len(attributes) == len(values):
#                 for key in range(0,len(attributes)):
#                     args.append(attributes[key])
#                     try:
#                         args.append(values[key])
#                     except:
#                         pass
#             else:
#                 logger.debug("No valid attributes specified for action %s" % action)
#                 logger.debug("Attrib %s Val %s" % (attributes, values) )

#         # Execute
#         return self.execute_command(com, args)

#     def meta_list(self, path, attributes=[]):
#         """ Listing all irods metadata """
#         out = self.meta_command(path, 'list', attributes)

#         # Parse out
#         metas = {}
#         pattern = re.compile("attribute:\s+(.+)")
#         keys = pattern.findall(out)
#         pattern = re.compile("value:\s+(.+)")
#         values = pattern.findall(out)
#         for j in range(0, len(keys)):
#             metas[keys[j]] = values[j]

#         # m1 = re.search(r"attribute:\s+(.+)", out)
#         # m2 = re.search(r"value:\s+(.+)", out)
#         # if m1 and m2:
#         #     metas[m1.group(1)] = m2.group(1)

#         return metas

#     def meta_sys_list(self, path):
#         """ Listing file system metadata """
#         com = "isysmeta"
#         args = ['ls']
#         args.append(path)
#         out = self.execute_command(com, args)
#         metas = {}
#         if out:
#             pattern = re.compile("([a-z_]+):\s+([^\n]+)")
#             metas = pattern.findall(out)
#         return metas

#     def meta_write(self, path, attributes, values):
#         return self.meta_command(path, 'write', attributes, values)


# ######################################
#
# # Execute iRules
#
# ######################################

# class IRuled(IMetaCommands):

#     ###################
#     # IRULES and templates
#     def irule_execution(self, rule=None, rule_file=None):
#         com='irule'
#         args=[]
#         if rule is not None:
#             args.append(rule)
#             logger.info("Executing irule %s" % rule)
#         elif rule_file is not None:
#             args.append('-F')
#             args.append(rule_file)
#             logger.debug("Irule execution from file %s" % rule_file)

#         # Execute
#         return self.execute_command(com, args)

#     def irule_from_file(self, rule_file):
#         return self.irule_execution(None, rule_file)

# ######################################
#
# # EUDAT project irods configuration
#
# ######################################

# class EudatICommands(IRuled):
#     """ See project documentation
#     http://eudat.eu/User%20Documentation%20-%20iRODS%20Deployment.html
#     """

#     latest_pid = None

#     def search(self, path, like=True):
#         """ Remove eudat possible metadata from this method """
#         ifiles = super(EudatICommands, self).search(path, like)
#         for ifile in ifiles:
#             if '.metadata/' in ifile:
#                 logger.debug("Skipping metadata file %s" % ifile)
#                 ifiles.remove(ifile)
#         return ifiles

#     def execute_rule_from_template(self, rule, context={}):
#         """
#         Using my template class for executing an irods rule
#         from a rendered file with variables in context
#         """
#         jin = Templa(rule)
#         # Use jinja2 templating
#         irule_file = jin.template2file(context)
#         # Call irule from template rendered
#         out = self.irule_from_file(irule_file)
#         # Remove file
#         os.remove(irule_file)
#         # Send response back
#         return out

#     def parse_rest_json(self, json_string=None, json_file=None):
#         """ Parsing REST API output in JSON format """
#         import json
#         json_data = ""

#         if json_string is not None:
#             json_data = json.loads(json_string)
#         elif json_file is not None:
#             with open(json_file) as f:
#                 json_data = json.load(f)

#         metas = {}
#         for meta in json_data:
#             key = meta['type']
#             value = meta['parsed_data']
#             metas[key] = value

#         return metas

#     # PID
#     def register_pid(self, dataobj):
#         """ Eudat rule for irods to register a PID to a Handle """

#         # Path fix
#         dataobj = os.path.join(self._base_dir, dataobj)

#         if appconfig.mocking():

#             #pid = "842/a72976e0-5177-11e5-b479-fa163e62896a"
#             # 8 - 4 - 4 - 4 - 12
#             base = "842"
#             code = string_generator(8)
#             code += "-" + str(random.randint(1000,9999))
#             code += "-" + string_generator(4) + "-" + string_generator(4)
#             code += "-" + string_generator(12)
#             pid = base + "/" + code

#         else:
#             context = {
#                 'irods_file': dataobj.center(len(dataobj)+2, '"')
#             }
#             pid = self.execute_rule_from_template('getpid', context)

#         return pid

#     def meta_list(self, path, attributes=[]):
#         """
#         Little trick to save PID from metadata listing:
#         override the original method
#         """
#         metas = super(EudatICommands, self).meta_list(path, attributes)
#         if 'PID' in metas:
#             self.latest_pid = metas['PID']
#         else:
#             self.latest_pid = None
#         return metas

#     # PID
#     def check_pid(self, dataobj):
#         """ Should get this value from irods metadata """

#         # Solved with a trick
#         pid = self.latest_pid
#         # Otherwise
#         #self.meta_list(dataobj, ['PID'])
#         # Might also use an irods rule to seek
#         #self.irule_from_file(irule_file)

#         return pid

#     def pid_metadata(self, pid):
#         """ Metadata derived only inside an Eudat enviroment """

#         # Binary included inside the neoicommands docker image
#         com = 'epicc'
#         credentials = './conf/credentials.json'
#         args = ['os', credentials, 'read', pid]

#         json_data = ""
#         select = {
#             'location':'URL',
#             'checksum': 'CHECKSUM',
#             'parent_pid':'EUDAT/PPID',
#         }
#         metas = {}

#         if appconfig.mocking():
# # // TO FIX:
#             empty = ""
# # Generate random
# # e.g. irods://130.186.13.14:1247/cinecaDMPZone/home/pdonorio/replica/test2
# # e.g. sha2:dCdRWFfS2TGm/4BfKQPu1WdQSdBwxRoxCRMX3zan3SM=
# # e.g. 842/52ae4c2c-4feb-11e5-afd1-fa163e62896a
#             pid_metas = {
#                 'URL': empty,
#                 'CHECKSUM': empty,
#                 'EUDAT/PPID': empty,
#             }
# # // TO REMOVE:
#             # Fake, always the same
#             metas = self.parse_rest_json(None, './tests/epic.pid.out')

#         else:
#             logger.debug("Epic client for %s " % args)
#             json_data = self.execute_command(com, args).strip()
#             if json_data.strip() == 'None':
#                 return {}

#             # Get all epic metas
#             metas = self.parse_rest_json(json_data)

#         ## Meaningfull data
#         pid_metas = {}
#         for name, selection in select.items():
#             value = None
#             if selection in metas:
#                 value = metas[selection]
#             pid_metas[name] = value

#         return pid_metas

#     def eudat_replica(self, dataobj_ori, dataobj_dest=None, pid_register=True):
#         """ Replication as Eudat B2safe """

#         if dataobj_dest is None:
#             dataobj_dest = dataobj_ori + ".replica"
#         dataobj_ori = os.path.join(self._base_dir, dataobj_ori)
#         dataobj_dest = os.path.join(self._base_dir, dataobj_dest)

#         context = {
#             'dataobj_source': dataobj_ori.center(len(dataobj_ori)+2, '"'),
#             'dataobj_dest': dataobj_dest.center(len(dataobj_dest)+2, '"'),
#             'pid_register': \
#                 str(pid_register).lower().center(len(str(pid_register))+2, '"'),
#         }

#         return self.execute_rule_from_template('replica', context)

#     def eudat_find_ppid(self, dataobj):
#         logger.debug("***REPLICA EUDAT LIST NOT IMPLEMENTED YET ***")
#         exit()


#######################################
# Creating the iRODS main instance
test_irods = ICommands()
# Note: this will be changed in the near future
# We should create the instance before every request
# (see Flask before_request decorator)
