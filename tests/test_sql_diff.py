import subprocess
import os

def test_diff_generation():
    old_file = os.path.abspath('tests/old.sql')
    new_file = os.path.abspath('tests/new.sql')
    script_path = os.path.abspath('sql_diff.py')

    process = subprocess.run(
        ['python', script_path, '-f', old_file, new_file],
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

if __name__ == "__main__":
    test_diff_generation()
    print("Test passed.")
