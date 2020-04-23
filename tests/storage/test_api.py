# test_api.py
import requests
import schemathesis
import pytest

from ert_shared.storage.http_server import FlaskWrapper

from tests.storage import populated_db


@pytest.fixture()
def test_schema(populated_db):
    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    flWrapper = FlaskWrapper(rdb_url=populated_db, blob_url=populated_db)
    # Establish an application context before running the tests.
    ctx = flWrapper.app.app_context()
    ctx.push()
    yield schemathesis.from_wsgi("/schema.json", flWrapper.app) 
    ctx.pop()

schema = schemathesis.from_pytest_fixture("test_schema")

@schema.parametrize()
def test_no_server_errors(case):
    # `requests` will make an appropriate call under the hood
    response = case.call_wsgi()  # use `call_wsgi` if you used `schemathesis.from_wsgi`
    # You could use built-in checks
    case.validate_response(response)