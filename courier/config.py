# courier.config -- python module for Courier configuration access
# Copyright (C) 2003-2008  Gordon Messmer <gordon@dragonsdawn.net>
#
# This file is part of pythonfilter.
#
# pythonfilter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pythonfilter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pythonfilter.  If not, see <http://www.gnu.org/licenses/>.

import dbm
import configparser
import ipaddress
import os
import socket
import subprocess
import sys

try:
    import DNS
except ImportError:
    DNS = None


prefix = '/usr/lib/courier'
exec_prefix = '/usr/lib/courier'
bindir = '/usr/lib/courier/bin'
sbindir = '/usr/lib/courier/sbin'
libexecdir = '/usr/lib/courier/libexec'
sysconfdir = '/etc/courier'
datadir = '/usr/lib/courier/share'
localstatedir = '/var/spool/courier'
mailuser = 'daemon'
mailgroup = 'daemon'
mailuid = '2'
mailgid = '2'
version = 'unknown'


def _setup():
    # Get the path layout for Courier.
    try:
        ch = subprocess.Popen('courier-config', stdout=subprocess.PIPE)
    except OSError:
        pass
    else:
        for ch_out_line in ch.stdout:
            ch_out_line = ch_out_line.decode()
            try:
                (setting, value) = ch_out_line.split('=', 1)
                value = value.strip()
            except ValueError:
                continue
            if setting in ('prefix', 'exec_prefix', 'bindir', 'sbindir',
                           'libexecdir', 'sysconfdir', 'datadir', 'localstatedir',
                           'mailuser', 'mailgroup', 'mailuid', 'mailgid'):
                globals()[setting] = value
        # Catch the exit of courier-config
        try:
            ch.wait()
        except OSError:
            pass
    # Get the version of Courier currently running.
    try:
        ch = subprocess.Popen(['%s/courier' % sbindir, '--version'],
                              stdout=subprocess.PIPE)
    except OSError:
        pass
    else:
        ch_out_line = ch.stdout.readline().decode()
        vers_output = ch_out_line.split(' ')
        if vers_output[0] == 'Courier':
            globals()['version'] = vers_output[1]
        # Catch the exit of courier --version
        try:
            ch.wait()
        except OSError:
            pass
    # Initialize the DNS module
    if DNS:
        DNS.DiscoverNameServers()


def _open_dbm(path):
    # If the DBM doesn't exist, os.stat will raise an exception, and the
    # logging code will be bypassed.
    os.stat(path)
    try:
        config_dbm = dbm.open(path, 'r')
    except ImportError:
        sys.stderr.write('Couldn\'t load python support for reading %s\n' % path)
        raise
    except dbm.error:
        try:
            import bsddb3
            config_dbm = bsddb3.hashopen(path, 'r')
        except:
            sys.stderr.write('Error reading %s\n' % path)
            raise
    return config_dbm


def is_min_version(min_version):
    """Check for minimum version of Courier.

    Return True if the version of courier currently installed is newer
    than or the same as the version given as an argument.

    """
    if version == 'unknown':
        return False
    curv = version.split('.')
    minv = min_version.split('.')
    return curv >= minv


def read1line(config_path):
    try:
        cfile = open(sysconfdir + '/' + config_path, 'r')
    except IOError:
        return None
    return cfile.readline().strip()


def me(_cached=[None]):
    """Return Courier's "me" value.

    Call this function with no arguments.

    """
    # check the cache to see if "me" has been looked up already
    # next look at the "me" config file
    # otherwise use the value of gethostname()
    if _cached[0]:
        return _cached[0]
    val = read1line('me')
    if val:
        _cached[0] = val
        return val
    val = socket.gethostname()
    _cached[0] = val
    return val


def esmtphelo(connection=None):
    """Returns a fully qualified domain name.

    The value will be computed as documented by Courier's man page. The
    optional "connection" argument should be a socket object which is
    connected to an SMTP server.

    """
    val = read1line('esmtphelo')
    if not val:
        val = me()
    if val == '*':
        if connection is None or DNS is None:
            val = me()
        else:
            val = DNS.revlookup(connection.getsockname()[0])
    return val


def defaultdomain(_cached=[None]):
    """Return Courier's "defaultdomain" value.

    Call this function with no arguments.

    """
    # check the cache to see if "defaultdomain" has been looked up already
    # next look at the "defaultdomain" config file
    # otherwise use the value of me()
    if _cached[0]:
        return _cached[0]
    val = read1line('defaultdomain')
    if val:
        _cached[0] = val
        return val
    return me()


def dsnfrom(_cached=[None]):
    """Return Courier's "dsnfrom" value.

    Call this function with no arguments.

    """
    if _cached[0]:
        return _cached[0]
    val = read1line('dsnfrom')
    if val:
        _cached[0] = val
        return val
    return '"Courier mail server at %s" <@>' % me()


def locallowercase():
    """Return True if the locallowercase file exists, and False otherwise."""
    if os.access('%s/locallowercase' % sysconfdir, os.F_OK):
        return 1
    return 0


def is_local(domain):
    """Return True if domain is "local", and False otherwise.

    See the courier(8) man page for more information on local domains.

    """
    try:
        locals_ = open('%s/locals' % sysconfdir)
    except IOError:
        if domain == me():
            return 1
        return 0
    for line in locals_.readlines():
        if line[0] in '#\n':
            continue
        line = line.strip()
        if line[0] == '!' and line[1:] == domain:
            return 0
        if line[0] == '.' and domain.endswith(line):
            return 1
        if line == domain:
            return 1
    return 0


def is_hosteddomain(domain):
    """Return True if domain is a hosted domain, and False otherwise.

    See the courier(8) man page for more information on hosted domains.

    """
    try:
        hosteddomains = _open_dbm('%s/hosteddomains.dat' % sysconfdir)
    except:
        return 0
    if domain in hosteddomains:
        return 1
    parts = domain.split('.')
    for x in range(1, len(parts)):
        domain_sub = '.' + '.'.join(parts[x:])
        if domain_sub in hosteddomains:
            return 1
    return 0


def get_alias(address):
    """Return a list of addresses to which the address argument will expand.

    If no alias matches the address argument, None will be returned.

    """
    if '@' in address:
        at_index = address.index('@')
        domain = address[at_index + 1:]
        if is_local(domain):
            address = '%s@%s' % (address[:at_index], me())
    else:
        address = '%s@%s' % (address, me())
    try:
        aliases = _open_dbm('%s/aliases.dat' % sysconfdir)
    except:
        return None
    if address in aliases:
        return aliases[address].decode().strip().split('\n')
    return None


def smtpaccess(ip):
    """ Return the courier smtpaccess value associated with the IP address."""
    # First break the IP address into parts, either IPv4 or IPv6
    if '.' in ip:
        ipsep = '.'
    elif ':' in ip:
        ipsep = ':'
        ip = ipaddress.ip_address(ip).exploded
    else:
        sys.stderr.write('Couldn\'t break %s into parts\n' % ip)
        return None
    # Next, open the smtpaccess database for ip lookups
    try:
        smtpdb = _open_dbm(sysconfdir + '/smtpaccess.dat')
    except:
        return None
    # Search for a match, most specific to least, and return the
    # first match.
    while ip:
        if ipsep == '.' and ip in smtpdb:
            return smtpdb[ip].decode()
        elif ipsep == ':' and (':' + ip) in smtpdb:
            return smtpdb[':' + ip].decode()
        # if the ip doesn't match yet, strip off another part
        try:
            ri = ip.rindex(ipsep)
            ip = ip[:ri]
        except ValueError:
            # separator wasn't found, we don't need to search any more
            return None


def get_smtpaccess_val(key, ip):
    """Return a string from the smtpaccess database.

    The value returned will be None if the IP is not found in the
    database, or if the database value doesn\'t contain the key
    argument.

    The value returned will be '' if the IP is found, and database
    value contains the key, but the key's value is empty.

    Otherwise, the value returned will be a string.

    """
    dbval = smtpaccess(ip)
    if dbval is None:
        return None
    keyeqlen = len(key) + 1
    keyeq = key + '='
    dbvals = dbval.split(',')
    for val in dbvals:
        if val == key:
            # This item in the db matches the key, but has no
            # associated value.
            return ''
        if val.startswith(keyeq):
            val = val[keyeqlen:]
            return val


def is_relayed(ip):
    """Return a true or false value indicating the RELAYCLIENT setting in
    the access db.
    """
    if get_smtpaccess_val('RELAYCLIENT', ip) is None:
        return 0
    return 1


def is_whiteblocked(ip):
    """Return a true or false value indicating the BLOCK setting in the
    access db.

    If the client ip is specifically whitelisted from blocks in the
    smtpaccess database, the return value will be true.  If the ip is
    not listed, or the value in the database is not '', the return
    value will be false.

    """
    if get_smtpaccess_val('BLOCK', ip) == '':
        return 1
    return 0


def get_block_val(ip):
    """Return the value of the BLOCK setting in the access db.

    The value will either be None, '', or another string which will be
    sent back to a client to indicate that mail will not be accepted
    from them.  The values None and '' indicate that the client is not
    blocked.  The value '' indicates that the client is specifically
    whitelisted from blocks.

    """
    return get_smtpaccess_val('BLOCK', ip)


_standard_config_paths = ['/etc/pythonfilter-modules.conf',
                          '/usr/local/etc/pythonfilter-modules.conf']


def get_module_config(module_name):
    """Return a dictionary of config values.

    The function will attempt to parse "pythonfilter-modules.conf" in
    "/etc" and "/usr/local/etc", and load the values from the
    section matching the module_name argument.  If the configuration
    files aren't found, or a name was requested that is not found in
    the config file, an empty dictionary will be returned.

    The values read from the configuration file will be passed to
    eval(), so they must be valid python expressions.  They will be
    returned to the caller in their evaluated form.

    """
    config = {}
    cp = configparser.RawConfigParser()
    cp.optionxform = str
    try:
        cp.read(_standard_config_paths)
        ci = cp.items(module_name)
    except configparser.NoSectionError:
        ci = {}
    except Exception as e:
        sys.stderr.write('error parsing config module: %s, exception: %s\n' % (module_name, str(e)))
        ci = {}
    for i in ci:
        # eval the value of this item in a new environment to
        # avoid unpredictable side effects to this modules
        # namespace
        value = eval(i[1], {})
        config[i[0]] = value
    return config


def apply_module_config(module_name, module_namespace):
    """Modify module_namespace with values from configuration file.

    This function will load configuration files using the
    get_module_config function, and will then add or replace any names
    in module_namespace with the values from the configuration files.

    """
    config = get_module_config(module_name)
    for i in config:
        module_namespace[i] = config[i]


# Call _setup to correct the module path values
_setup()

# Deprecated names preserved for compatibility with older releases
isMinVersion = is_min_version
getBlockVal = get_block_val
isLocal = is_local
isHosteddomain = is_hosteddomain
getAlias = get_alias
getSmtpaccessVal = get_smtpaccess_val
isRelayed = is_relayed
isWhiteblocked = is_whiteblocked
getModuleConfig = get_module_config
applyModuleConfig = apply_module_config
