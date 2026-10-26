"""Console reporting is separate from frozen scientific execution and raw data."""
import json
from unittest.mock import patch

import numpy as np

from malecns_backend.live import balance_contribution_console as cli


def report(accepted=True):
    return dict(run_status='COMPLETE', evaluation=dict(accepted=accepted,
        unity_replay_eligible=accepted, status='INTEGRITY_ACCEPTED' if accepted else 'INCONCLUSIVE_INTEGRITY',
        checks=dict(complete=np.bool_(accepted)), arms=dict(NC=dict(count=np.int64(20001))),
        behavior=dict(primary_label='MIXED_OR_UNRESOLVED', posture=dict(NP=dict(samples=np.int64(20001))),
                      interpretation_limits=['ONE_SEED_ASSISTED'], independent_balance_proven=False,
                      factorial_root_vector=[[np.float64(0.)]*3]*20001)))


def test_numpy_results_serialize_without_dumping_full_traces():
    result = cli.summary(report())
    encoded = json.dumps(result, allow_nan=False)
    assert json.loads(encoded)['accepted'] is True
    assert 'factorial_root_vector' not in encoded and 'ONE_SEED_ASSISTED' in encoded
    assert len(encoded) < 2000


def test_saved_evaluation_console_uses_core_and_returns_integrity_exit_status(tmp_path, capsys):
    saved = report()
    cli.experiment.base.save(tmp_path/'report.json', saved)
    with patch.object(cli.experiment, 'evaluate', return_value=saved['evaluation']) as evaluate:
        assert cli.main(['--evaluate',str(tmp_path)]) == 0
    assert evaluate.call_count == 1
    assert json.loads(capsys.readouterr().out)['unity_replay_eligible'] is True


def test_inconclusive_result_is_not_promoted_by_console(tmp_path, capsys):
    saved = report(False)
    cli.experiment.base.save(tmp_path/'report.json', saved)
    with patch.object(cli.experiment, 'evaluate', return_value=saved['evaluation']):
        assert cli.main(['--evaluate',str(tmp_path)]) == 1
    assert not json.loads(capsys.readouterr().out)['accepted']
