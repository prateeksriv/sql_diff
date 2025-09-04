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
    
    # Check for some expected statements in the output
    assert "CREATE INDEX users_email_idx ON public.users USING btree (email);" in stdout
    assert "ALTER TABLE public.users RENAME COLUMN name TO username;" in stdout
    assert "ALTER TABLE public.users ALTER COLUMN email SET NOT NULL;" in stdout
    assert "ALTER TABLE public.users DROP COLUMN created_at;" in stdout
    assert "ALTER TABLE public.users ADD COLUMN last_login timestamp without time zone;" in stdout

if __name__ == "__main__":
    test_diff_generation()
    print("Test passed.")
