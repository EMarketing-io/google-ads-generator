# generate_password_hash.py

import bcrypt
from dotenv import set_key, load_dotenv
import os

ENV_PATH = ".env"


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode()


def main():
    username = input("Enter a username: ").strip()
    password = input("Enter a password: ").strip()

    if not username or not password:
        print("❌ Username and password cannot be empty.")
        return

    hashed = hash_password(password)

    # Store as USERNAME_HASHED = ...
    key = f"{username.upper()}_HASHED"
    set_key(ENV_PATH, key, hashed)

    print(f"✅ Hashed password saved in .env as {key}")


if __name__ == "__main__":
    load_dotenv()
    main()
