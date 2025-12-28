import asyncio
import httpx
from pathlib import Path

async def create_ethereal_account():
    print("Attempting to create Ethereal account...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.nodemailer.com/user", json={"requestor": "contri-test", "version": "nodemailerta/1.0.0"})
            
            if response.status_code == 200:
                account = response.json()
                print("=" * 50)
                print("ETHEREAL EMAIL ACCOUNT GENERATED")
                print("=" * 50)
                print(f"User: {account['user']}")
                print(f"Password: {account['pass']}")
                
                # Prepare content to specific vars
                env_content = f"\n# Ethereal Email Settings\nSMTP_HOST={account['smtp']['host']}\nSMTP_PORT={account['smtp']['port']}\nSMTP_USER={account['user']}\nSMTP_PASSWORD={account['pass']}\nEMAILS_FROM_EMAIL=service@contri.com\nEMAILS_FROM_NAME=Contri\n"
                
                # Update .env file
                env_path = Path(".env")
                if env_path.exists():
                    print("Updating .env file...")
                    with open(env_path, "a") as f:
                        f.write(env_content)
                else:
                    print("Creating .env file...")
                    with open(env_path, "w") as f:
                        f.write(env_content)
                
                print("Successfully updated .env file with new credentials.")
                print("PLEASE RESTART YOUR CELERY WORKER TO APPLY CHANGES.")
                print("=" * 50)
            else:
                print(f"Failed to create account: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(create_ethereal_account())
