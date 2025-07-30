import bcrypt
from dotenv import set_key, load_dotenv
import os

# Define the path to the .env file
ENV_PATH = ".env"


# Generate a hashed password
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode()


# Ensure the .env file exists
def main():
    username = input("Enter a username: ").strip()
    password = input("Enter a password: ").strip()

    # Validate inputs
    if not username or not password:
        print("❌ Username and password cannot be empty.")
        return

    # Hash the password
    hashed = hash_password(password)
    key = f"{username.upper()}_HASHED"
    set_key(ENV_PATH, key, hashed)

    print(f"✅ Hashed password saved in .env as {key}")


if __name__ == "__main__":
    load_dotenv()
    main()