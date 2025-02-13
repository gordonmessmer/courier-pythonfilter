#!/usr/bin/python
# whitelist_dnswl -- Courier filter which exempts DNS whitelisted IPs from filtering
# Copyright (C) 2007-2008  Gordon Messmer <gordon@dragonsdawn.net>
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

import sys
import socket
import ipaddress
import courier.control
import courier.config


dnswl_zone = ['list.dnswl.org']


def init_filter():
    courier.config.apply_module_config('whitelist_dnswl.py', globals())
    # Record in the system log that this filter was initialized.
    sys.stderr.write('Initialized the "whitelist_dnswl" python filter\n')


def do_filter(body_path, control_paths):
    """Return a 200 code if the message came from an IP in a DNS whitelist.

    After returning a 200 code, the pythonfilter process will
    discontinue further filter processing.

    """

    try:
        senders_ip = courier.control.get_senders_ip(control_paths)
    except:
        return '451 Internal failure locating control files'

    try:
        sender = ipaddress.ip_address(senders_ip)
    except ValueError:
        sys.stderr.write(f'whitelist_dnswl: unparsable senders_ip: {senders_ip}\n')
        return ''

    # sender is either IPV4Address or IPV6Address object, 
    reverse = sender.reverse_pointer.replace('.in-addr.arpa', '').replace('.ip6.arpa', '')

    for zone in dnswl_zone:
        lookup = '%s.%s' % (reverse, zone)
        try:
            lookup_result = socket.gethostbyname(lookup)
        except:
            lookup_result = None
        if lookup_result:
            # For now, any result is good enough.
            return '200 Ok'

    # Return no decision if reaching this
    return ''


if __name__ == '__main__':
    # For debugging, you can create a file that contains one line,
    # formatted as Courier's Received-From-MTA record:
    # faddresstype; address
    # Run this script with the name of that file as an argument,
    # and it'll print either "200 Ok" to indicate that the address
    # is whitelisted, or nothing to indicate that the remaining
    # filters would be run.
    if not sys.argv[1:]:
        print('Use:  whitelist_dnswl.py <control file>')
        sys.exit(1)
    init_filter()
    print(do_filter('', sys.argv[1:]))
