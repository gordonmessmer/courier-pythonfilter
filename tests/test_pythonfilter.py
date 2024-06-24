#!/usr/bin/python3
# pythonfilter -- A python framework for Courier global filters
# Copyright (C) 2003-2018  Gordon Messmer <gordon@dragonsdawn.net>
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

import os
import select
import socket
import sys
import unittest

project_root = os.path.dirname(os.path.dirname(__file__))

# Add the cwd to PATH so that a modified courier-config is used
# by the courier.config module.
os.environ['PATH'] = '%s/tests:%s' % (project_root, os.environ['PATH'])
# Add the local library path to PYTHONPATH so that the child
# process (pythonfilter) loads modules from this dir rather than
# the system library path.
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] = '%s:%s/filters:%s' % (
        project_root, project_root, os.environ['PYTHONPATH'])
else:
    os.environ['PYTHONPATH'] = '%s:%s/filters' % (
        project_root, project_root)


class TestPythonfilter(unittest.TestCase):
    def setUp(self):
        # create socket directory
        sockdir = f'{project_root}/tests/spool/courier/allfilters'
        os.makedirs(sockdir, exist_ok=True)
        # File descriptor 3 is reserved while creating pipes.
        fd3 = open('/dev/null')
        # pythonfilter will close one end of this pipe to signal that it
        # is listening and ready to process messages.
        ready_fd = os.pipe()
        # This process will close one end of this pipe to signal that
        # pythonfilter should shut down.
        self.term_fd = os.pipe()
        fd3.close()

        child_pid = os.fork()
        if child_pid == 0:
            # The child process will dup its own end of each pipe to the
            # fd where it will be expected by pythonfilter and then close
            # the original reference.
            os.dup2(self.term_fd[0], 0)
            os.dup2(ready_fd[1], 3)
            os.close(self.term_fd[0])
            os.close(ready_fd[1])
            # Close the parent's end of the pipe.
            os.close(self.term_fd[1])
            os.close(ready_fd[0])
            os.execlp('python3', 'python3', f'{project_root}/pythonfilter')
        else:
            # The test process will close the child's end of each pipe and
            # wait for pythonfilter to close its end of the "ready" pipe.
            os.close(self.term_fd[0])
            os.close(ready_fd[1])
            ready_files = select.select([ready_fd[0]], [], [])
            if ready_fd[0] not in ready_files[0]:
                print('Error: notification file not closed')
                sys.exit(0)

    def tearDown(self):
        # Tell pythonfilter to shut down.
        os.close(self.term_fd[1])

    def testFilter(self):
        socket_path = '%s/tests/spool/courier/allfilters/pythonfilter' % project_root
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.sendall(('%s/tests/queuefiles/data-test1\n' % project_root).encode())
        sock.sendall(('%s/tests/queuefiles/control-duplicate\n' % project_root).encode())
        sock.sendall(('\n').encode())

        status = sock.recv(1024).decode()
        # print('Status: %s' % status)

        self.assertEqual(status, '200 Ok')
