""" Test the networking package.
"""
# pylint: disable=import-error

# Standard library imports


# External module imports
import pytest
import requests

# Local imports
from notion2html.networking import get_network_data, Error404NotFound
import notion2html.networking


__author__ = "Ramsey Tantawi"
__email__ = "ramsey@tantawi.com"
__status__ = "Production"


def test_get_network_data_success(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})
    mock_response = mocker.Mock()
    mock_response.json.return_value = {'data': 'some data'}
    mock_response.ok = True
    mock_response.status_code = 200
    mocker.patch('notion2html.networking._execute_request', return_value=mock_response)
    mocker.patch('notion2html.networking._handle_response', return_value=({'data': 'some data'}, False))

    # Execute
    result = get_network_data('https://example.com', 'get')

    # Assert
    assert result == {'data': 'some data'}


def test_get_network_data_404_not_found(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})
    mock_response = mocker.Mock()
    mock_response.json.return_value = {'code': 'object_not_found', 'message': 'Not found'}
    mock_response.ok = False
    mock_response.status_code = 404
    mocker.patch('notion2html.networking._execute_request', return_value=mock_response)

    # Expectations and Execute
    with pytest.raises(Error404NotFound):
        get_network_data('https://example.com', 'get')


def test_get_network_data_no_retries_left(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})
    mocker.patch('notion2html.networking._execute_request', side_effect=requests.exceptions.Timeout('Timeout'))

    # Expectations and Execute
    with pytest.raises(RuntimeError, match="No more retries left!"):
        get_network_data('https://example.com', 'get')


def test_get_network_data_file_download(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={})
    mock_response = mocker.Mock()
    mock_response.ok = True
    mocker.patch('notion2html.networking._execute_request', return_value=mock_response)

    # Execute
    result = get_network_data('https://example.com/file', 'get', file_download=True)

    # Assert
    assert result == mock_response  # For file downloads, the function should return the raw response


def test_get_network_data_invalid_method(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})

    # Expectations and Execute
    with pytest.raises(ValueError, match="Invalid method!"):
        get_network_data('https://example.com', 'invalid_method')


def test_get_network_data_missing_notion_token(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', side_effect=RuntimeError("Notion access token not provided."))

    # Expectations and Execute
    with pytest.raises(RuntimeError, match="Notion access token not provided."):
        get_network_data('https://example.com', 'get')


def test_get_network_data_rate_limit(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})
    mock_response = mocker.Mock()
    mock_response.status_code = 429
    mock_response.headers = {'Retry-After': '2'}
    mocker.patch('notion2html.networking._execute_request', return_value=mock_response)
    mocker.patch('notion2html.networking._handle_response', return_value=(None, True))  # Indicate that a retry is needed

    # Expectations and Execute
    with pytest.raises(RuntimeError, match="No more retries left!"):
        get_network_data('https://example.com', 'get')


def test_get_network_data_invalid_json(mocker):
    # Mocks
    mocker.patch('notion2html.networking._get_headers', return_value={'Authorization': 'Bearer TOKEN'})
    mock_response = mocker.Mock()
    mock_response.json.side_effect = Exception("Invalid JSON")
    mock_response.ok = True
    mocker.patch('notion2html.networking._execute_request', return_value=mock_response)
    mocker.patch('notion2html.networking._handle_response', return_value=(None, True))  # Indicate that a retry is needed

    # Expectations and Execute
    with pytest.raises(RuntimeError, match="No more retries left!"):
        get_network_data('https://example.com', 'get')
