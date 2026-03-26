import pytest
from unittest.mock import MagicMock, patch
from db.repository.users import UsersRepository



def test_connect_db() -> None:

    with UsersRepository() as repo:
        print(repo.get_all())
        
test_connect_db()