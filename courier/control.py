# courier.control -- python module for handling Courier message control files
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

import ipaddress
import time
import urllib.parse


def try_decode(value):
    """Return a string decoded from value, or description of malformed UTF-8"""
    try:
        return value.strip().decode('utf-8')
    except UnicodeDecodeError:
        return '(malformed utf8):%s' % urllib.parse.quote_plus(
            value.strip(), safe='@'
        )


def get_lines(control_paths, key, max_lines=0):
    """Return a list of values in the control_paths matching key.

    "key" should be a one character string.  See the "Control Records"
    section of Courier's Mail Queue documentation for a list of valid
    control record keys.

    If the "max_lines" argument is given, it must be a number greater
    than zero.  No more values than indicated by this argument will
    be returned.

    """
    key = key.encode('ascii')
    lines = []
    for control_path in control_paths:
        with open(control_path, 'rb') as control_file:
            for control_line in control_file:
                if control_line[:1] == key:
                    lines.append(try_decode(control_line[1:]))
                    if max_lines and len(lines) == max_lines:
                        break
    return lines


def get_senders_mta(control_paths):
    """Return the "Received-From-MTA" record.

    Courier's documentation indicates that this specifies what goes
    into this header for DSNs generated due to this message.

    """
    sender_lines = get_lines(control_paths, 'f', 1)
    if sender_lines:
        return sender_lines[0]
    return None


def get_senders_ip(control_paths):
    """Return an IP address if one is found in the "Received-From-MTA" record."""
    sender = get_lines(control_paths, 'O')
    for line in sender:
        if line.startswith('TCPREMOTEIP='):
            sender_ip = ipaddress.ip_address(line[12:])
            if isinstance(sender_ip, ipaddress.IPv6Address) and sender_ip.ipv4_mapped:
                return str(sender_ip.ipv4_mapped)
            return str(sender_ip)
    return None


def get_sender(control_paths):
    """Return the envelope sender."""
    sender_lines = get_lines(control_paths, 's', 1)
    if sender_lines:
        return sender_lines[0]
    return None


def get_recipients(control_paths):
    """Return a list of message recipients.

    This list contains addresses in canonical format, after Courier's
    address rewriting and alias expansion.

    """
    return [x[0] for x in get_recipients_data(control_paths)]


def get_recipients_data(control_paths):
    """Return a list of lists with details about message recipients.

    Each list in the list returned will have the following elements:
    0: The rewritten address
    1: The "original message recipient", as defined by RFC1891
    2: Zero or more characters indicating DSN behavior.

    """
    recipients_data = []
    for control_path in control_paths:
        rcpts = _get_recipients_from_file(control_path)
        for rcpt in rcpts:
            if rcpt[1] is False:
                recipients_data.append(rcpt[2])
    return recipients_data


def _get_recipients_from_file(control_path):
    """Return a list of lists with details about message recipients.

    Each list in the list returned will have the following elements:
    0: The sequence number of this recipient
    1: Delivery status as either True (delivered) or False (not delivered)
    2: A list containing the following elements, describing this recipient:
        0: The rewritten address
        1: The "original message recipient", as defined by RFC1891
        2: Zero or more characters indicating DSN behavior.

    """
    recipients = []
    rbuf = ['', '', '']  # This list will contain the recipient data.
    with open(control_path, 'rb') as control_file:
        for control_line in control_file:
            control_key = control_line[:1]
            control_val = control_line[1:]
            if control_key == b'r':
                rbuf[0] = try_decode(control_val)
            if control_key == b'R':
                rbuf[1] = try_decode(control_val)
            if control_key == b'N':
                rbuf[2] = try_decode(control_val)
                # This completes a new record, add it to the recipient data list.
                if rbuf and rbuf[0]:
                    rcpt = [len(recipients), False, rbuf]
                    recipients.append(rcpt)
                rbuf = ['', '', '']
            if control_key in (b'S', b'F'):
                # Control file records either a successful or failed
                # delivery.  Either way, mark this recipient completed.
                rnum = control_line.split(b' ', 1)[0]
                rnum = int(rnum[1:])
                recipients[rnum][1] = True
    return recipients


def get_control_data(control_paths):
    """Return a dictionary containing all of the data that was given to submit.

    The dictionary will have the following elements:
    's': The envelope sender
    'f': The "Received-From-MTA" record
    'e': The envid of this message, as specified in RFC1891, or None
    'M': The "message id" of this message
    'i': The name used to authenticate the sender, or None
    't': Either 'F' or 'H', specifying FULL or HDRS in the RET parameter
         that was given in the MAIL FROM command, as specified in RFC1891,
         or None
    'E': Expiration time of this message, in seconds as returned by the
         time() system call
    'p': Expiration time of this message, for the fax module
    'W': Time at which sender will be warned if the message is still
         undeliverable
    'w': True if a warning has already been sent, False otherwise
    '8': True if the message contains 8-bit data, False otherwise
    'm': True if the message contains 8-bit headers, False otherwise
    'V': True if the envelope sender address should be VERPed, False
         otherwise
    'v': vhost argument given to submit, or the domain of the auth user,
         or None
    'X': The reason for canceling the message if it has been cancelled,
         or None
    'U': The security level requested for the message
    'u': The "message source" given on submit's command line
    'T': True if backscatter should be suppressed, False otherwise
    'r': The list of recipients, as returned by get_recipients_data

    See courier/libs/comctlfile.h in the Courier source code, and the
    submit(8) man page for more information.

    """
    data = {'s': '',
            'f': '',
            'e': None,
            'M': None,
            'i': None,
            't': None,
            'E': None,
            'p': None,
            'W': None,
            'w': False,
            '8': False,
            'm': False,
            'V': False,
            'v': None,
            'X': None,
            'U': '',
            'u': None,
            'T': False,
            'r': []}
    with open(control_paths[0], 'rb') as control_file:
        for control_line in control_file:
            control_key = control_line[:1]
            control_val = control_line[1:]
            if control_key in b'sfeMitEpWvXUu':
                data[control_key.decode('ascii')] = try_decode(control_val)
            if control_key in b'w8mVT':
                data[control_key.decode('ascii')] = True
    data['r'] = get_recipients_data(control_paths)
    return data


def add_recipient(control_paths, recipient):
    """Add a recipient to a control_paths set.

    The recipient argument must contain a canonical address.  Local
    aliases are not allowed.

    """
    recipient_data = [recipient, '', '']
    add_recipient_data(control_paths, recipient_data)


def add_recipient_data(control_paths, recipient_data):
    """Add a recipient to a control_paths set.

    The recipient_data argument must contain the same information that
    is normally returned by the get_recipients_data function for each
    recipient.  Recipients should be added one at a time.

    """
    # FIXME:  How strict is courier about its upper limit of
    # recipients per control file?  It's easiest to append the
    # recipient to the last control file, but it would be more
    # robust to check the number of recipients in it first and
    # create a new file if necessary.
    if len(recipient_data) != 3:
        raise ValueError('recipient_data must be a list of 3 values.')
    control_path = control_paths[-1]
    with open(control_path, 'a') as control_file:
        control_file.write('r%s\n' % recipient_data[0])
        control_file.write('R%s\n' % recipient_data[1])
        control_file.write('N%s\n' % recipient_data[2])


def _mark_complete(control_path, recipient_index):
    """Mark a single recipient's delivery as completed."""
    with open(control_path, 'a') as control_file:
        control_file.seek(0, 2)  # Seek to the end of the file
        control_file.write('I%d R 250 Ok - Removed by courier.control.py\n' %
                           recipient_index)
        control_file.write('S%d %d\n' % (recipient_index, int(time.time())))


def del_recipient(control_paths, recipient):
    """Remove a recipient from the list.

    The recipient arg is a canonical address found in one of the
    control files in control_paths.

    The first recipient in the control_paths that exactly matches
    the address given will be removed by way of marking that delivery
    complete, successfully.

    You should log all such removals so that messages are never
    silently lost.

    """
    for control_path in control_paths:
        rcpts = _get_recipients_from_file(control_path)
        for rcpt in rcpts:
            if (rcpt[1] is False  # Delivery is not complete for this recipient
                    and rcpt[2][0] == recipient):
                _mark_complete(control_path, rcpt[0])
                return


def del_recipient_data(control_paths, recipient_data):
    """Remove a recipient from the list.

    The recipient_data arg is a list similar to the data returned by
    get_recipients_data found in one of the control files in
    control_paths.

    The first recipient in the control_paths that exactly matches
    the data given will be removed by way of marking that delivery
    complete, successfully.

    You should log all such removals so that messages are never
    silently lost.

    """
    if len(recipient_data) != 3:
        raise ValueError('recipient_data must be a list of 3 values.')
    for cf in control_paths:
        rcpts = _get_recipients_from_file(cf)
        for x in rcpts:
            if (x[1] is False  # Delivery is not complete for this recipient
                    and x[2] == recipient_data):
                _mark_complete(cf, x[0])
                return


def get_auth_user(control_paths, body_file=None):
    """Return the username used during SMTP AUTH, if available.

    The return value with be a string containing the username used
    for authentication during submission of the message, or None,
    if authentication was not used.

    The body_file argument is not needed.  It is accepted for
    compatibility with older releases of pythonfilter.

    """
    auth_lines = get_lines(control_paths, 'i', 1)
    if auth_lines:
        return auth_lines[0]
    return None


# Deprecated names preserved for compatibility with older releases
getLines = get_lines
getSendersMta = get_senders_mta
getSendersIP = get_senders_ip
getSender = get_sender
getRecipients = get_recipients
getRecipientsData = get_recipients_data
getControlData = get_control_data
addRecipient = add_recipient
addRecipientData = add_recipient_data
delRecipient = del_recipient
delRecipientData = del_recipient_data
getAuthUser = get_auth_user
