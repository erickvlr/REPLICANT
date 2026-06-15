from config.settings import settings

LEVEL_NONE = 0
LEVEL_READER = 1
LEVEL_EDITOR = 2
LEVEL_OWNER = 3

def is_owner(user_id: int) -> bool:
    return user_id in settings.owner_ids

def owner_level(user_id: int) -> int:
    return LEVEL_OWNER if is_owner(user_id) else LEVEL_NONE
