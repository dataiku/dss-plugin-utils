import logging

import pytest

from dkulib.dku_config.custom_check import CustomCheckError
from dkulib.dku_config.dss_parameter import DSSParameter, DSSParameterError

LOGGER = logging.getLogger(__name__)


class TestDSSParameter:
    def test_nominal_case(self):
        dss_parameter = DSSParameter(
            name='test',
            value=3,
            checks=[{
                "type": "inf",
                "op": 4
            }],
            required=True
        )
        assert dss_parameter.value == 3
        assert dss_parameter.name == 'test'
        assert len(dss_parameter.checks) == 1

    def test_error(self):
        with pytest.raises(CustomCheckError):
            _ = DSSParameter(
                name='test',
                value=3,
                checks=[{
                    "type": "unknown_type",
                    "op": 4
                }],
                required=True
            )

    def test_success(self, caplog):
        caplog.set_level(logging.DEBUG)
        _ = DSSParameter(
            name='test',
            value=3,
            checks=[{
                "type": "inf",
                "op": 4
            }],
            required=True
        )
        assert 'All checks passed successfully' in caplog.text

    def test_failure(self, caplog):
        caplog.set_level(logging.INFO)
        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test',
                value=3,
                checks=[{
                    "type": "inf",
                    "op": 2
                }]
            )
        assert 'Validation error with parameter' in str(err.value)

    def test_double_failure(self, caplog):
        caplog.set_level(logging.INFO)
        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test',
                value=3,
                checks=[{
                    "type": "inf",
                    "op": 2
                }],
                required=True
            )
        error_message = str(err.value)
        assert 'Validation error with parameter' in error_message
        assert 'required' not in error_message
        assert 'less' in error_message

    def test_default(self, caplog):
        dss_parameter_1 = DSSParameter(
            name='test_1',
            value=None,
            default=4
        )
        assert dss_parameter_1.value == 4

        dss_parameter_2 = DSSParameter(
            name='test_2',
            value=3,
            default=4
        )
        assert dss_parameter_2.value == 3

        dss_parameter_3 = DSSParameter(
            name='test_2',
            value=None,
            default=4,
            required=True
        )
        assert dss_parameter_3.value == 4

    def test_cast(self, caplog):
        dss_parameter_1 = DSSParameter(
            name='test_1',
            value='4',
            cast_to=int
        )
        assert dss_parameter_1.value == 4

        dss_parameter_2 = DSSParameter(
            name='test_2',
            value=4,
            cast_to=int
        )
        assert dss_parameter_2.value == 4

        caplog.set_level(logging.INFO)
        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test_3',
                value='foo',
                cast_to=int
            )
        error_message = str(err.value)
        assert 'error with parameter' in error_message
        assert '<class \'int\'>' in error_message
        assert '<class \'str\'>' in error_message

        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test_4',
                value=[1, 2, 3],
                cast_to=float
            )
        error_message = str(err.value)
        assert '<class \'list\'>' in error_message
        assert '<class \'float\'>' in error_message

        dss_parameter_5 = DSSParameter(
            name='test_5',
            value=None,
            cast_to=int,
            default=5
        )
        assert dss_parameter_5.value == 5

        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test_6',
                value=None,
                cast_to=str,
                required=True
            )
        error_message = str(err.value)
        assert 'required' in error_message

        dss_parameter_7 = DSSParameter(
            name='test_5',
            value=None,
            cast_to=int,
        )
        assert dss_parameter_7.value == None

    def test_label(self, caplog):
        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test_1',
                value=7,
                label='Display Name',
                checks=[{
                    "type": "is_type",
                    "op": str
                }]
            )
        error_message = str(err.value)
        assert 'Display Name' in error_message

        with pytest.raises(DSSParameterError) as err:
            _ = DSSParameter(
                name='test_1',
                value=7,
                checks=[{
                    "type": "is_type",
                    "op": str
                }]
            )
        error_message = str(err.value)
        assert 'test_1' in error_message
