def save(db, user, preferences):
    user.preferences = preferences.model_dump()
    db.commit()
    return user.preferences
