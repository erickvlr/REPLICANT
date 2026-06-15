from config.permissions import is_owner

def require_owner(interaction) -> bool:
    return is_owner(interaction.user.id)
