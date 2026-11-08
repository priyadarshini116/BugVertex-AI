def get_user_name(user):
    if not user or not user.get("name"):
        return ""
    return user["name"].strip()
