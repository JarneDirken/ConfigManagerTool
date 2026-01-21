import os
import shutil
import re
import json

SERVERS_FILE = "servers.json"
ENV_RULES_FILE = "environment.json"


def load_json(file_path):
    """Load a JSON file with error handling."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Required file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_latest_version_path(server_path):
    """Find the most recently created version folder in a server path."""
    subdirs = [
        os.path.join(server_path, d)
        for d in os.listdir(server_path)
        if os.path.isdir(os.path.join(server_path, d))
    ]
    if not subdirs:
        raise FileNotFoundError(f"No subdirectories found in {server_path}")

    latest_dir = max(subdirs, key=os.path.getctime)
    return latest_dir


def version_exists(server_path, version):
    """Check if the target version already exists."""
    return os.path.exists(os.path.join(server_path, version))


def copy_version_folder(source_path, new_version):
    """Duplicate the latest version folder."""
    parent = os.path.dirname(source_path)
    new_path = os.path.join(parent, new_version)
    shutil.copytree(source_path, new_path)
    print(f"Copied version {os.path.basename(source_path)} → {new_version}")
    return new_path


def modify_ports_and_paths(file_path, env_rules):
    """Modify paths, environment markers, and port numbers inside an INI-like file."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Replace environment-specific strings
        for old, new in env_rules["replace"].items():
            line = line.replace(old, new)

        # Adjust ports in the 4000–6000 range
        ports = re.findall(r"(\d{4,5})", line)
        for port in ports:
            port_int = int(port)
            if 4000 <= port_int <= 6000:
                new_port = port_int + env_rules["port_offset"]
                line = line.replace(port, str(new_port))

        new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def update_environment_files(version_path, env_rules):
    """Walk through version folder and apply modifications to all .ini files."""
    for root, _, files in os.walk(version_path):
        for file in files:
            if file.lower().endswith(".ini"):
                modify_ports_and_paths(os.path.join(root, file), env_rules)


def process_server(server, new_version, env_rules):
    """Process a single server path."""
    print(f"\nProcessing {server['name']}...")
    server_path = server["path"]
    if not os.path.exists(server_path):
        print(f"Path not found: {server_path}")
        return

    if version_exists(server_path, new_version):
        print(f"Version {new_version} already exists in {server_path}. Skipping.")
        return

    latest_path = get_latest_version_path(server_path)
    new_version_path = copy_version_folder(latest_path, new_version)
    update_environment_files(new_version_path, env_rules)

    print(f"Server {server['name']} updated successfully to version {new_version}")


def main():
    print("=== IpMatix Configuration Automation Tool ===\n")
    new_version = input("Enter new version name (e.g. 3.8.0): ").strip()
    environment = input("Enter environment (A or B): ").strip().upper()

    servers = load_json(SERVERS_FILE)
    env_rules_data = load_json(ENV_RULES_FILE)

    if environment not in env_rules_data:
        print("Invalid environment. Must be 'A' or 'B'.")
        return

    env_rules = env_rules_data[environment]
    print(f"\nFound {len(servers['servers'])} servers in configuration.\n")

    for srv in servers["servers"]:
        process_server(srv, new_version, env_rules)

    print("\nAll servers processed successfully.")


if __name__ == "__main__":
    main()
