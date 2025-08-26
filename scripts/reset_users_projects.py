import sys
import psycopg2

try:
    from backend.services.config import Settings
except Exception:
    Settings = None


def get_conn():
    if Settings is not None:
        s = Settings()
        return psycopg2.connect(
            host=s.postgres_host,
            port=s.postgres_port,
            dbname=s.postgres_database,
            user=s.postgres_user,
            password=s.postgres_password,
        )
    # Fallback to defaults
    return psycopg2.connect(host="localhost", port=5432, dbname="odras", user="postgres", password="password")


def main():
    confirm = os.environ.get("CONFIRM_RESET")
    if confirm != "yes":
        print("Refusing to run without CONFIRM_RESET=yes")
        return 2

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Remove memberships first to avoid foreign key constraints
            cur.execute("TRUNCATE TABLE public.project_members CASCADE;")
            # Requirements and jobs depend on projects
            cur.execute("TRUNCATE TABLE public.requirements CASCADE;")
            cur.execute("TRUNCATE TABLE public.extraction_jobs CASCADE;")
            # Projects
            cur.execute("TRUNCATE TABLE public.projects CASCADE;")
            # Users
            cur.execute("TRUNCATE TABLE public.users CASCADE;")
            # Ontologies registry
            cur.execute("TRUNCATE TABLE public.ontologies_registry;")
            conn.commit()
            print("Truncated users, projects, memberships, jobs, requirements, ontologies registry")

            # Seed two users
            cur.execute(
                "INSERT INTO public.users (username, display_name, is_admin) VALUES (%s, %s, %s) ON CONFLICT (username) DO UPDATE SET display_name=EXCLUDED.display_name, is_admin=EXCLUDED.is_admin",
                ("admin", "Administrator", True),
            )
            cur.execute(
                "INSERT INTO public.users (username, display_name, is_admin) VALUES (%s, %s, %s) ON CONFLICT (username) DO UPDATE SET display_name=EXCLUDED.display_name, is_admin=EXCLUDED.is_admin",
                ("jdehart", "J DeHart", False),
            )
            conn.commit()
            print("Seeded users: admin, jdehart")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    sys.exit(main())


