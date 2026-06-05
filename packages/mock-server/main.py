import asyncio
from opcua_local_server import main as run_opcua_server


def main():
    """Main entry point for the OPC UA Industrial Control System."""
    print("Starting OPC UA Industrial Control System Server...")
    try:
        run_opcua_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"Error starting server: {e}")


if __name__ == "__main__":
    main()
