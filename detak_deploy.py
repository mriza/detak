import os
import subprocess
from shutil import copyfile, copy
from pymongo import MongoClient

def main():
    print("=== Detak Agent Deployment Script ===")

    # Step 1: Check for .env template in the same directory
    env_template_path = "./.env"
    if not os.path.exists(env_template_path):
        print("Error: .env template not found in the current directory.")
        return

    # Step 2: Ask for UUID
    uuid = input("\nEnter the UUID for this agent: ").strip()

    # Step 3: Ask for object name
    object_name = input("\nEnter the object name for this agent: ").strip()

    # Step 4: Create /opt/detak/detak_agent directory
    print("\nSetting up /opt/detak/detak_agent directory...")
    detak_dir = "/opt/detak/detak_agent"
    os.makedirs(detak_dir, exist_ok=True)

    # Copy .env file
    env_path = os.path.join(detak_dir, ".env")
    copyfile(env_template_path, env_path)

    # Customize .env with new UUID
    with open(env_path, "r") as env_file:
        env_lines = env_file.readlines()
    with open(env_path, "w") as env_file:
        for line in env_lines:
            if line.startswith("STATIC_UUID="):
                env_file.write(f"STATIC_UUID={uuid}\n")  # Replace UUID
            else:
                env_file.write(line)
    print(f".env file customized and saved to {env_path}")

    # Step 5: Clone the repository and copy detak_agent.py
    print("\nCloning the repository...")
    repo_url = "https://github.com/mriza/detak"
    repo_dir = "/tmp/detak_repo"
    subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
    print("Repository cloned successfully.")

    # Copy detak_agent.py from the cloned repository
    detak_agent_path = os.path.join(detak_dir, "detak_agent.py")
    repo_agent_path = os.path.join(repo_dir, "detak_agent.py")
    copy(repo_agent_path, detak_agent_path)
    print(f"detak_agent.py copied to {detak_agent_path}")

    # Step 6: Save object name to database
    print("\nSaving object name to database...")
    mongo_uri = next((line.split("=")[1].strip() for line in env_lines if line.startswith("MONGODB_URI=")), None)
    mongo_db = next((line.split("=")[1].strip() for line in env_lines if line.startswith("MONGODB_DB=")), None)
    objects_collection = next((line.split("=")[1].strip() for line in env_lines if line.startswith("MONGODB_OBJECTS_COLLECTION=")), None)

    try:
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db[objects_collection]
        collection.update_one({"uuid": uuid}, {"$set": {"object_name": object_name}}, upsert=True)
        print(f"Object name '{object_name}' saved to database with UUID '{uuid}'.")
    except Exception as e:
        print(f"Error saving object name to database: {e}")
        return

    # Step 7: Create a systemd service for detak_agent.py
    print("\nCreating systemd service for detak_agent.py...")
    service_content = f"""
[Unit]
Description=Detak Agent Service
After=network.target

[Service]
User=detak
WorkingDirectory={detak_dir}
ExecStart=/usr/bin/python3 {detak_agent_path}
Restart=always

[Install]
WantedBy=multi-user.target
"""
    service_path = "/etc/systemd/system/detak_agent.service"
    if not os.path.exists(service_path):
        with open(service_path, "w") as service_file:
            service_file.write(service_content)
        print(f"Systemd service file created at {service_path}")
    else:
        print("Systemd service already exists. Skipping creation.")

    # Reload systemd and enable the service
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "detak_agent.service"], check=True)
    subprocess.run(["sudo", "systemctl", "start", "detak_agent.service"], check=True)
    print("Detak Agent service started and enabled.")

    # Clean up the cloned repository
    subprocess.run(["rm", "-rf", repo_dir], check=True)
    print("Temporary repository files cleaned up.")

    print("\n=== Deployment Complete ===")

if __name__ == "__main__":
    main()