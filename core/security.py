from db.repository.security import SecurityRepository


def is_valid_security_key(key: str) -> bool:
    with SecurityRepository() as repo:
        return repo.get() == key
    

def is_valid_jwt(key: str) -> bool:
    pass