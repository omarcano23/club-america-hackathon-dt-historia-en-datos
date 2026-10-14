import pandas as pd
import pytest

from club_america_isac.validation import require_columns


def test_require_columns_passes_when_present():
    frame = pd.DataFrame({"match_id": [1], "team": ["Club América"]})
    require_columns(frame, ["match_id", "team"])


def test_require_columns_reports_missing():
    frame = pd.DataFrame({"match_id": [1]})
    with pytest.raises(ValueError, match="team"):
        require_columns(frame, ["match_id", "team"])
