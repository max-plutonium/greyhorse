import os

import pytest


@pytest.fixture
def local_root_password():
    return os.getenv('LOCAL_ROOT_PASSWORD')


@pytest.fixture
def ssh_host():
    return os.getenv('SSH_HOST')


@pytest.fixture
def ssh_username():
    return os.getenv('SSH_USERNAME')


@pytest.fixture
def ssh_root_password():
    return os.getenv('SSH_ROOT_PASSWORD')
