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

from bson.errors import InvalidStringData
import eventlet
import mock
from oslo_config import cfg
import tempfile

import st2actions.worker as actions_worker
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import executions
from st2common.util import date as date_utils
from local_runner import LocalShellRunner


from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader
import st2tests.config as tests_config
tests_config.parse_args()

TEST_FIXTURES = {
    'runners': ['run-local.yaml'],
    'actions': ['local.yaml']
}

FIXTURES_PACK = 'generic'

NON_UTF8_RESULT = {'stderr': '', 'stdout': '\x82\n', 'succeeded': True, 'failed': False,

                   'return_code': 0}


class WorkerTestCase(DbTestCase):
    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(WorkerTestCase, cls).setUpClass()
        models = WorkerTestCase.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        WorkerTestCase.local_runnertype_db = models['runners']['run-local.yaml']
        WorkerTestCase.local_action_db = models['actions']['local.yaml']

    def _get_liveaction_model(self, action_db, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(name=action_db.name, pack=action_db.pack).ref
        parameters = params
        context = {'user': cfg.CONF.system_user.user}
        liveaction_db = LiveActionDB(status=status, start_timestamp=start_timestamp,
                                     action=action_ref, parameters=parameters,
                                     context=context)
        return liveaction_db

    @mock.patch.object(LocalShellRunner, 'run', mock.MagicMock(
        return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_UTF8_RESULT, None)))
    def test_non_utf8_action_result_string(self):
        action_worker = actions_worker.get_worker()
        params = {
            'cmd': "python -c 'print \"\\x82\"'"
        }
        liveaction_db = self._get_liveaction_model(WorkerTestCase.local_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        execution_db = executions.create_execution_object(liveaction_db)

        try:
            action_worker._run_action(liveaction_db)
        except InvalidStringData:
            liveaction_db = LiveAction.get_by_id(liveaction_db.id)
            self.assertEqual(liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED)
            self.assertTrue('error' in liveaction_db.result)
            self.assertTrue('traceback' in liveaction_db.result)
            execution_db = ActionExecution.get_by_id(execution_db.id)
            self.assertEqual(liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED)

    def test_worker_shutdown(self):
        action_worker = actions_worker.get_worker()

        # Create a temporary file that is deleted when the file is closed and then set up an
        # action to wait for this file to be deleted. This allows this test to run the action
        # over a separate thread, run the shutdown sequence on the main thread, and then let
        # the local runner to exit gracefully and allow _run_action to finish execution.
        with tempfile.NamedTemporaryFile() as fp:
            params = {'cmd': 'while [ -e \'%s\' ]; do sleep 0.1; done' % fp.name}
            liveaction_db = self._get_liveaction_model(WorkerTestCase.local_action_db, params)
            liveaction_db = LiveAction.add_or_update(liveaction_db)
            executions.create_execution_object(liveaction_db)
            runner_thread = eventlet.spawn(action_worker._run_action, liveaction_db)

            # Wait for the worker to add the liveaction to _running_liveactions.
            while len(action_worker._running_liveactions) <= 0:
                eventlet.sleep(0.1)

            self.assertEqual(len(action_worker._running_liveactions), 1)

            # Shutdown the worker to trigger the abandon process.
            action_worker.shutdown()
            liveaction_db = LiveAction.get_by_id(liveaction_db.id)

            # Verify that _running_liveactions is empty and the liveaction is abandoned.
            self.assertEqual(len(action_worker._running_liveactions), 0)
            self.assertEqual(liveaction_db.status, action_constants.LIVEACTION_STATUS_ABANDONED)

        # Wait for the local runner to complete. This will activate the finally block in
        # _run_action but will not result in KeyError because the discard method is used to
        # to remove the liveaction from _running_liveactions.
        runner_thread.wait()
