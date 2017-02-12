# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mock import call
import os
import uuid
import json
import mock
import tempfile
import requests
import argparse
import logging

from tests import base
from st2client import config_parser
from st2client import shell
from st2client.models.core import add_auth_token_to_kwargs_from_env
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.utils.httpclient import add_auth_token_to_headers, add_json_content_type_to_headers


LOG = logging.getLogger(__name__)

RULE = {
    'id': uuid.uuid4().hex,
    'description': 'i am THE rule.',
    'name': 'drule',
    'pack': 'cli',
}


class TestWhoami(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestWhoami, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_whoami(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test 'st2 whoami' functionality
        """

        # Mock config
        config_file = config_parser.ST2_CONFIG_PATH
        self.shell._get_config_file_path = mock.MagicMock(return_value="/tmp/st2config")
        mock_cli.return_value._get_config_file_path.return_value = config_file

        self.shell.run(['whoami'])

        mock_cfg.return_value.__getitem__.assert_called_with('credentials')
        mock_cfg.return_value.__getitem__('credentials').__getitem__.assert_called_with('username')

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_whoami_not_logged_in(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test 'st2 whoami' functionality with a missing username
        """

        # Mock config
        config_file = config_parser.ST2_CONFIG_PATH
        self.shell._get_config_file_path = mock.MagicMock(return_value="/tmp/st2config")
        mock_cli.return_value._get_config_file_path.return_value = config_file

        # Trigger keyerror exception when trying to access username.
        # We have to do it this way because ConfigParser acts like a
        # dict but also has methods like read()
        attrs = {'__getitem__.side_effect': KeyError}
        mock_cfg.return_value.__getitem__.return_value.configure_mock(**attrs)

        # assert that the config field lookup caused the CLI to return an error code
        # we are also using "--debug" flag to ensure the exception is re-raised once caught
        self.assertEqual(
            self.shell.run(['--debug', 'whoami']),
            1
        )

        # Some additional asserts to ensure things are being called correctly
        mock_cfg.return_value.__getitem__.assert_called_with('credentials')
        mock_cfg.return_value.__getitem__.return_value.__getitem__.assert_called_with('username')

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_whoami_missing_credentials_section(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test 'st2 whoami' functionality with a missing credentials section
        """

        # mocked config that is empty (no credentials section at all)
        mock_cfg.return_value.read.return_value = {}

        # Mock config
        config_file = config_parser.ST2_CONFIG_PATH
        self.shell._get_config_file_path = mock.MagicMock(return_value="/tmp/st2config")
        mock_cli.return_value._get_config_file_path.return_value = config_file

        # Trigger keyerror exception when trying to access username.
        # We have to do it this way because ConfigParser acts like a
        # dict but also has methods like read()
        attrs = {'__getitem__.side_effect': KeyError}
        mock_cfg.return_value.configure_mock(**attrs)

        # assert that the config field lookup caused the CLI to return an error code
        # we are also using "--debug" flag to ensure the exception is re-raised once caught
        self.assertEqual(
            self.shell.run(['--debug', 'whoami']),
            1
        )

        # An additional assert to ensure things are being called correctly
        mock_cfg.return_value.__getitem__.assert_called_with('credentials')


class TestLogin(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestLogin, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_login_password_and_config(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test the 'st2 login' functionality by providing a password, and specifying a configuration file
        """

        args = ['--config', '/tmp/st2config', 'login', 'st2admin', '--password', 'Password1!']
        expected_username = 'st2admin'

        mock_gp.getpass.return_value = "Password1!"

        # Mock config
        config_file = args[args.index('--config') + 1]
        self.shell._get_config_file_path = mock.MagicMock(return_value="/tmp/st2config")
        mock_cli.return_value._get_config_file_path.return_value = config_file

        self.shell.run(args)

        # Ensure getpass was only used if "--password" option was omitted
        mock_gp.getpass.assert_not_called()

        # Ensure token was generated
        mock_cli.return_value._cache_auth_token.assert_called_once()

        # Build list of expected calls for mock_cfg
        config_calls = [call('username', expected_username)]

        # Ensure that the password field was removed from the config
        mock_cfg.return_value.__getitem__.return_value.pop.assert_called_once_with('password', None)

        # Run common assertions for testing login functionality
        self._login_common_assertions(mock_gp, mock_cli, mock_open, mock_cfg,
                                      config_calls, config_file)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_login_no_password(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test the 'st2 login' functionality without the "--password" arg
        """

        args = ['login', 'st2admin']
        expected_username = 'st2admin'

        mock_gp.getpass.return_value = "Password1!"

        config_file = config_parser.ST2_CONFIG_PATH
        mock_cli.return_value._get_config_file_path.return_value = config_file

        self.shell.run(args)

        # Ensure getpass was only used if "--password" option was omitted
        mock_gp.getpass.assert_called_once()

        # Ensure token was generated
        mock_cli.return_value._cache_auth_token.assert_called_once()

        config_calls = [call('username', expected_username)]

        # Ensure that the password field was removed from the config
        mock_cfg.return_value.__getitem__.return_value.pop.assert_called_once_with('password', None)

        # Run common assertions for testing login functionality
        self._login_common_assertions(mock_gp, mock_cli, mock_open, mock_cfg,
                                      config_calls, config_file)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_login_password_with_write(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test the 'st2 login' functionality by providing a password, and writing it to config file
        """

        args = ['login', 'st2admin', '--password', 'Password1!', '-w']
        expected_username = 'st2admin'

        mock_gp.getpass.return_value = "Password1!"

        config_file = config_parser.ST2_CONFIG_PATH
        mock_cli.return_value._get_config_file_path.return_value = config_file

        self.shell.run(args)

        # Ensure getpass was only used if "--password" option was omitted
        mock_gp.getpass.assert_not_called()

        # Ensure token was generated
        mock_cli.return_value._cache_auth_token.assert_called_once()

        # Build list of expected calls for mock_cfg
        config_calls = [call('username', expected_username), call('password', 'Password1!')]

        # Run common assertions for testing login functionality
        self._login_common_assertions(mock_gp, mock_cli, mock_open, mock_cfg,
                                      config_calls, config_file)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch("st2client.commands.auth.ConfigParser")
    @mock.patch("st2client.commands.auth.open")
    @mock.patch("st2client.commands.auth.BaseCLIApp")
    @mock.patch("st2client.commands.auth.getpass")
    def test_login_no_password_with_write_and_config(self, mock_gp, mock_cli, mock_open, mock_cfg):
        """Test the 'st2 login' functionality by providing config file and writing password to it
        """

        args = ['--config', '/tmp/st2config', 'login', 'st2admin', '-w']
        expected_username = 'st2admin'

        mock_gp.getpass.return_value = "Password1!"

        # Mock config
        config_file = args[args.index('--config') + 1]
        self.shell._get_config_file_path = mock.MagicMock(return_value="/tmp/st2config")
        mock_cli.return_value._get_config_file_path.return_value = config_file

        self.shell.run(args)

        mock_gp.getpass.assert_called_once()

        # Ensure token was generated
        mock_cli.return_value._cache_auth_token.assert_called_once()

        # Build list of expected calls for mock_cfg
        config_calls = [call('username', expected_username), call('password', 'Password1!')]

        # Run common assertions for testing login functionality
        self._login_common_assertions(mock_gp, mock_cli, mock_open, mock_cfg,
                                      config_calls, config_file)

    def _login_common_assertions(self, mock_gp, mock_cli, mock_open, mock_cfg,
                                 config_calls, config_file):
        # Ensure file was written to with a context manager
        mock_open.return_value.__enter__.assert_called_once()
        mock_open.return_value.__exit__.assert_called_once()

        # Make sure 'credentials' key in config was initialized properly
        mock_cfg.return_value.__setitem__.assert_has_calls(
            [call('credentials', {})], any_order=True
        )

        # Ensure configuration was performed properly
        mock_open.assert_called_once_with(config_file, 'w')
        mock_cfg.return_value.read.assert_called_once_with(config_file)
        mock_cfg.return_value.add_section.assert_called_once_with('credentials')
        mock_cfg.return_value.__getitem__.return_value.__setitem__.assert_has_calls(
            config_calls,
            any_order=True
        )


class TestAuthToken(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestAuthToken, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    def setUp(self):
        super(TestAuthToken, self).setUp()

        # Setup environment.
        os.environ['ST2_BASE_URL'] = 'http://127.0.0.1'

    def tearDown(self):
        super(TestAuthToken, self).tearDown()

        # Clean up environment.
        if 'ST2_AUTH_TOKEN' in os.environ:
            del os.environ['ST2_AUTH_TOKEN']
        if 'ST2_API_KEY' in os.environ:
            del os.environ['ST2_API_KEY']
        if 'ST2_BASE_URL' in os.environ:
            del os.environ['ST2_BASE_URL']

    @add_auth_token_to_kwargs_from_cli
    @add_auth_token_to_kwargs_from_env
    def _mock_run(self, args, **kwargs):
        return kwargs

    def test_decorate_auth_token_by_cli(self):
        token = uuid.uuid4().hex
        args = self.parser.parse_args(args=['-t', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})
        args = self.parser.parse_args(args=['--token', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_api_key_by_cli(self):
        token = uuid.uuid4().hex
        args = self.parser.parse_args(args=['--api-key', token])
        self.assertDictEqual(self._mock_run(args), {'api_key': token})

    def test_decorate_auth_token_by_env(self):
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_api_key_by_env(self):
        token = uuid.uuid4().hex
        os.environ['ST2_API_KEY'] = token
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {'api_key': token})

    def test_decorate_without_auth_token(self):
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {})

    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def _mock_http(self, url, **kwargs):
        return kwargs

    def test_decorate_auth_token_to_http_headers(self):
        token = uuid.uuid4().hex
        kwargs = self._mock_http('/', token=token)
        expected = {'content-type': 'application/json', 'X-Auth-Token': token}
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    def test_decorate_api_key_to_http_headers(self):
        token = uuid.uuid4().hex
        kwargs = self._mock_http('/', api_key=token)
        expected = {'content-type': 'application/json', 'St2-Api-Key': token}
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    def test_decorate_without_auth_token_to_http_headers(self):
        kwargs = self._mock_http('/', auth=('stanley', 'stanley'))
        expected = {'content-type': 'application/json'}
        self.assertIn('auth', kwargs)
        self.assertEqual(kwargs['auth'], ('stanley', 'stanley'))
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_resource_list(self):
        url = 'http://127.0.0.1:9101/v1/rules/?limit=50'

        # Test without token.
        self.shell.run(['rule', 'list'])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from  cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'list', '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'list'])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_get(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])
        url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref

        # Test without token.
        self.shell.run(['rule', 'get', rule_ref])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'get', rule_ref, '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'get', rule_ref])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_post(self):
        url = 'http://127.0.0.1:9101/v1/rules'
        data = {'name': RULE['name'], 'description': RULE['description']}

        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'create', path])
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)

            # Test with token from cli.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'create', path, '-t', token])
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)

            # Test with token from env.
            token = uuid.uuid4().hex
            os.environ['ST2_AUTH_TOKEN'] = token
            self.shell.run(['rule', 'create', path])
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_put(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])

        get_url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref
        put_url = 'http://127.0.0.1:9101/v1/rules/%s' % RULE['id']
        data = {'name': RULE['name'], 'description': RULE['description'], 'pack': RULE['pack']}

        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'update', rule_ref, path])
            kwargs = {}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)

            # Test with token from cli.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'update', rule_ref, path, '-t', token])
            kwargs = {'headers': {'X-Auth-Token': token}}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)

            # Test with token from env.
            token = uuid.uuid4().hex
            os.environ['ST2_AUTH_TOKEN'] = token
            self.shell.run(['rule', 'update', rule_ref, path])
            kwargs = {'headers': {'X-Auth-Token': token}}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    @mock.patch.object(
        requests, 'delete',
        mock.MagicMock(return_value=base.FakeResponse('', 204, 'OK')))
    def test_decorate_resource_delete(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])
        get_url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref
        del_url = 'http://127.0.0.1:9101/v1/rules/%s' % RULE['id']

        # Test without token.
        self.shell.run(['rule', 'delete', rule_ref])
        kwargs = {}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

        # Test with token from cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'delete', rule_ref, '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'delete', rule_ref])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)
