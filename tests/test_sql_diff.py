import subprocess
import os

def diff_generation():
    old_file = os.path.abspath('tests/old.sql')
    new_file = os.path.abspath('tests/new.sql')
    script_path = os.path.abspath('sql_diff.py')

    process = subprocess.run(
        ['python', script_path, '-p', old_file, '-n', new_file],
        capture_output=True,
        text=True
    )

    assert process.returncode == 1
    
    stdout = process.stdout.strip()
    
    # TODO: This test is brittle and depends on the exact output of the script.
    # The column rename heuristic is not perfect and should be improved.
    assert "CREATE INDEX users_email_idx ON public.users USING btree (email);" in stdout
    assert "ALTER TABLE public.users RENAME COLUMN name TO username;" in stdout
    assert "ALTER TABLE public.users ALTER COLUMN email SET NOT NULL;" in stdout
    assert "ALTER TABLE public.users RENAME COLUMN created_at TO last_login;" in stdout
    assert "ALTER TABLE public.users ALTER COLUMN last_login DROP DEFAULT;" in stdout

def constraint_diff_generation():
    old_file = os.path.abspath('tests/old_constraints.sql')
    new_file = os.path.abspath('tests/new_constraints.sql')
    script_path = os.path.abspath('sql_diff.py')

    process = subprocess.run(
        ['python', script_path, '-p', old_file, '-n', new_file],
        capture_output=True,
        text=True
    )

    assert process.returncode == 1
    
    stdout = process.stdout.strip()
    
    assert "ALTER TABLE public.posts DROP CONSTRAINT IF EXISTS posts_user_id_fkey;" in stdout
    assert "ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_name_unique;" in stdout
    assert "ALTER TABLE ONLY public.users ADD CONSTRAINT users_email_unique UNIQUE (email);" in stdout
    assert "ALTER TABLE public.users ADD COLUMN email CHARACTER varying(255);" in stdout
    assert "ALTER TABLE public.posts ADD COLUMN created_at timestamp WITHOUT TIME ZONE DEFAULT now();" in stdout

if __name__ == "__main__":
    diff_generation()
    constraint_diff_generation()
    print("All tests passed.")