#!/usr/bin/python3
# pythonfilter -- A python framework for Courier global filters
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

import dbm
import os
import tempfile
import shutil
import unittest
import courier.config


def makedbm(name, replace_commas=0, tmpdir="."):
    with dbm.open(f'{tmpdir}/configfiles/{name}.dat', 'c') as newdbm:
        file = open(f'{tmpdir}/configfiles/{name}')
        line = file.readline()
        while line:
            parts = line.split(':', 1)
            if len(parts) == 1:
                key = parts[0].strip()
                value = '1'
            else:
                key, value = [x.strip() for x in parts]
            if replace_commas:
                value = value.replace(',', '\n') + '\n'
            newdbm[key] = value
            line = file.readline()


class TestCourierConfig(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        shutil.copytree(f"{os.path.dirname(__file__)}/configfiles", f"{self.tmpdir}/configfiles")
        courier.config.sysconfdir = f'{self.tmpdir}/configfiles'
        makedbm('aliases', 1, tmpdir=self.tmpdir)
        makedbm('hosteddomains', tmpdir=self.tmpdir)
        makedbm('smtpaccess', tmpdir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def testMe(self):
        self.assertEqual(courier.config.me(),
                         'ascension.private.dragonsdawn.net')

    def testDefaultDomain(self):
        self.assertEqual(courier.config.defaultdomain(),
                         'dragonsdawn.net')

    def testDsnFrom(self):
        self.assertEqual(courier.config.dsnfrom(),
                         '"Courier mail server at ascension.private.dragonsdawn.net" <@>')

    def testLocalLowerCase(self):
        self.assertEqual(courier.config.locallowercase(),
                         True)

    def testIsLocal(self):
        # Deprecated function test
        self.assertEqual(courier.config.isLocal('ascension.private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.isLocal('private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.isLocal('herald.private.dragonsdawn.net'),
                         False)

        # New function test
        self.assertEqual(courier.config.is_local('ascension.private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.is_local('private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.is_local('herald.private.dragonsdawn.net'),
                         False)

    def testIsHosteddomain(self):
        # Deprecated function test
        self.assertEqual(courier.config.isHosteddomain('virtual.private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.isHosteddomain('ascension.private.dragonsdawn.net'),
                         False)

        # New function test
        self.assertEqual(courier.config.is_hosteddomain('virtual.private.dragonsdawn.net'),
                         True)
        self.assertEqual(courier.config.is_hosteddomain('ascension.private.dragonsdawn.net'),
                         False)

    def testAliases(self):
        # Deprecated function test
        self.assertEqual(courier.config.getAlias('alias1'),
                         ['gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.getAlias('alias1@ascension.private.dragonsdawn.net'),
                         ['gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.getAlias('alias2'),
                         ['root@ascension.private.dragonsdawn.net',
                          'gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.getAlias('alias3@virtual.private.dragonsdawn.net'),
                         ['root@ascension.private.dragonsdawn.net'])

        # New function test
        self.assertEqual(courier.config.get_alias('alias1'),
                         ['gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.get_alias('alias1@ascension.private.dragonsdawn.net'),
                         ['gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.get_alias('alias2'),
                         ['root@ascension.private.dragonsdawn.net',
                          'gordon@ascension.private.dragonsdawn.net'])
        self.assertEqual(courier.config.get_alias('alias3@virtual.private.dragonsdawn.net'),
                         ['root@ascension.private.dragonsdawn.net'])

    def testSmtpaccess(self):
        self.assertEqual(courier.config.smtpaccess('127.0.0.1'),
                         'allow,RELAYCLIENT')
        self.assertEqual(courier.config.smtpaccess('192.168.1.1'),
                         'allow,BLOCK')
        self.assertEqual(courier.config.smtpaccess('192.168.2.1'),
                         'allow,BLOCK=shoo')
        self.assertEqual(courier.config.smtpaccess('192.168.3.1'),
                         None)

    def testGetSmtpaccessVal(self):
        # Deprecated function test
        self.assertEqual(courier.config.getSmtpaccessVal('RELAYCLIENT', '127.0.0.1'),
                         '')
        self.assertEqual(courier.config.getSmtpaccessVal('BLOCK', '127.0.0.1'),
                         None)
        self.assertEqual(courier.config.getSmtpaccessVal('RELAYCLIENT', '192.168.3.1'),
                         None)
        self.assertEqual(courier.config.getSmtpaccessVal('BLOCK', '192.168.2.1'),
                         'shoo')

        # New function test
        self.assertEqual(courier.config.get_smtpaccess_val('RELAYCLIENT', '127.0.0.1'),
                         '')
        self.assertEqual(courier.config.get_smtpaccess_val('BLOCK', '127.0.0.1'),
                         None)
        self.assertEqual(courier.config.get_smtpaccess_val('RELAYCLIENT', '192.168.3.1'),
                         None)
        self.assertEqual(courier.config.get_smtpaccess_val('BLOCK', '192.168.2.1'),
                         'shoo')

    def testIsRelayed(self):
        # Deprecated function test
        self.assertEqual(courier.config.isRelayed('127.0.0.1'),
                         True)
        self.assertEqual(courier.config.isRelayed('192.168.1.1'),
                         False)
        self.assertEqual(courier.config.isRelayed('192.168.3.1'),
                         False)

        # New function test
        self.assertEqual(courier.config.is_relayed('127.0.0.1'),
                         True)
        self.assertEqual(courier.config.is_relayed('192.168.1.1'),
                         False)
        self.assertEqual(courier.config.is_relayed('192.168.3.1'),
                         False)

    def testIsWhiteblocked(self):
        # Deprecated function test
        self.assertEqual(courier.config.isWhiteblocked('127.0.0.1'),
                         False)
        self.assertEqual(courier.config.isWhiteblocked('192.168.1.1'),
                         True)
        self.assertEqual(courier.config.isWhiteblocked('192.168.3.1'),
                         False)

        # New function test
        self.assertEqual(courier.config.is_whiteblocked('127.0.0.1'),
                         False)
        self.assertEqual(courier.config.is_whiteblocked('192.168.1.1'),
                         True)
        self.assertEqual(courier.config.is_whiteblocked('192.168.3.1'),
                         False)

    def testGetBlockVal(self):
        # Deprecated function test
        self.assertEqual(courier.config.getBlockVal('127.0.0.1'),
                         None)
        self.assertEqual(courier.config.getBlockVal('192.168.1.1'),
                         '')
        self.assertEqual(courier.config.getBlockVal('192.168.2.1'),
                         'shoo')
        self.assertEqual(courier.config.getBlockVal('192.168.3.1'),
                         None)

        # New function test
        self.assertEqual(courier.config.get_block_val('127.0.0.1'),
                         None)
        self.assertEqual(courier.config.get_block_val('192.168.1.1'),
                         '')
        self.assertEqual(courier.config.get_block_val('192.168.2.1'),
                         'shoo')
        self.assertEqual(courier.config.get_block_val('192.168.3.1'),
                         None)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCourierConfig)
    unittest.TextTestRunner(verbosity=2).run(suite)
