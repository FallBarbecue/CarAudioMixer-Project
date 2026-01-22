from app import app, db, User, Project

with app.app_context():
    print("\n--- USER LIST ---")
    users = User.query.all()
    if not users:
        print("No registered users found.")
    for u in users:
        print(f"ID: {u.id} | Username: {u.username} | Password(Hash): {u.password[:20]}...")

    print("\n--- Project List ---")
    projects = Project.query.all()
    if not projects:
        print("No registered projects found.")
    for p in projects:
        print(f"Project: {p.project_name} | Name: {p.project_name} | Status: {p.status}")

    print("\n---------------------\n")