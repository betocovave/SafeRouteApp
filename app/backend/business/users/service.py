def profile(user):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role, 'preferences': user.preferences, 'created_at': user.created_at}
