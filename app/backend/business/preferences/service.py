def save(db, user, preferences):
    if (preferences.quiet_start is None) != (preferences.quiet_end is None):
        from fastapi import HTTPException
        raise HTTPException(422, 'Configura ambas horas del horario silencioso o ninguna.')
    user.preferences = preferences.model_dump()
    db.commit()
    return user.preferences
