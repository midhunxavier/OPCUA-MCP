#!/usr/bin/env python3
"""
Example OPC UA client for the Industrial Control System server.
This demonstrates how to connect to and interact with the server.
"""

import time
import logging
from datetime import datetime, timedelta
from opcua import Client, ua


def main():
    """Main client function demonstrating server interaction."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Server endpoint
    endpoint = "opc.tcp://localhost:4840/freeopcua/server/"
    
    # Create client instance
    client = Client(endpoint)
    
    try:
        # Connect to server
        print(f"Connecting to {endpoint}...")
        client.connect()
        print("Connected successfully!")
        
        # Get the root node of our industrial system
        root = client.get_objects_node()
        industrial_system = root.get_child(["2:IndustrialControlSystem"])
        
        print("\n" + "="*50)
        print("INDUSTRIAL CONTROL SYSTEM DEMO")
        print("="*50)
        
        # === READING SENSOR VALUES ===
        print("\n📊 Current Sensor Readings:")
        sensors = industrial_system.get_child(["2:Sensors"])
        
        # Read all sensor values
        sensor_names = ["Temperature", "Pressure", "FlowRate", "TankLevel", 
                       "Vibration", "PhLevel", "Humidity", "MotorSpeed"]
        
        for sensor_name in sensor_names:
            try:
                sensor_node = sensors.get_child([f"2:{sensor_name}"])
                value = sensor_node.get_value()
                print(f"  {sensor_name}: {value:.2f}")

                endtime = datetime.utcnow()
                starttime = endtime - timedelta(hours=1)
                history_data = sensor_node.read_raw_history(starttime, endtime, 5)
                for history_data_value in history_data:
                        print(f"  {sensor_name}: {history_data_value.Value.Value:.2f} @ {history_data_value.SourceTimestamp}")
            except Exception as e:
                print(f"  ⚠️ Error reading {sensor_name}: {e}")
        
        # === CONTROLLING ACTUATORS ===
        print("\n⚙️ Controlling Actuators:")
        actuators = industrial_system.get_child(["2:Actuators"])
        
        # Turn on pump
        pump_node = actuators.get_child(["2:PumpEnabled"])
        print("  Turning on pump...")
        pump_node.set_value(True)
        pump_status = pump_node.get_value()
        print(f"  Pump status: {'ON' if pump_status else 'OFF'}")
        
        # Set valve position to 75%
        valve_node = actuators.get_child(["2:ValvePosition"])
        print("  Setting valve position to 75%...")
        valve_node.set_value(75.0)
        valve_pos = valve_node.get_value()
        print(f"  Valve position: {valve_pos}%")
        
        # Set heater power to 30%
        heater_node = actuators.get_child(["2:HeaterPower"])
        print("  Setting heater power to 30%...")
        heater_node.set_value(30.0)
        heater_power = heater_node.get_value()
        print(f"  Heater power: {heater_power}%")
        
        # === CHECKING SYSTEM STATUS ===
        print("\n📈 System Status:")
        system_status = industrial_system.get_child(["2:SystemStatus"])
        
        mode_node = system_status.get_child(["2:SystemMode"])
        mode = mode_node.get_value()
        print(f"  System Mode: {mode}")
        
        prod_rate_node = system_status.get_child(["2:ProductionRate"])
        prod_rate = prod_rate_node.get_value()
        print(f"  Production Rate: {prod_rate} units/hour")
        
        # === CALLING METHODS ===
        print("\n🎯 Using Command Variables (Alternative to Methods):")
        system_status = industrial_system.get_child(["2:SystemStatus"])
        
        # Start production using command variable
        print("  Starting production at 25 units/hour...")
        try:
            start_cmd_node = system_status.get_child(["2:StartProductionCommand"])
            start_cmd_node.set_value(25.0)
            print(f"  Start production command sent: 25.0")
        except Exception as e:
            print(f"  ⚠️ Error sending start production command: {e}")
        
        # Wait a moment for changes to take effect
        time.sleep(3)
        
        # Check updated system status
        print("\n📈 Updated System Status After Starting Production:")
        mode = mode_node.get_value()
        prod_rate = prod_rate_node.get_value()
        print(f"  System Mode: {mode}")
        print(f"  Production Rate: {prod_rate} units/hour")
        
        # Read some sensors again to see changes
        print("\n📊 Updated Sensor Readings:")
        for sensor_name in ["Temperature", "Pressure", "FlowRate"]:
            try:
                sensor_node = sensors.get_child([f"2:{sensor_name}"])
                value = sensor_node.get_value()
                print(f"  {sensor_name}: {value:.2f}")
            except Exception as e:
                print(f"  ⚠️ Error reading {sensor_name}: {e}")
        
        # Check pump status
        pump_node = actuators.get_child(["2:PumpEnabled"])
        pump_status = pump_node.get_value()
        print(f"  Pump Status: {'ON' if pump_status else 'OFF'}")
        
        # Wait and then stop production
        print("\n⏸️ Stopping production using command variable...")
        time.sleep(2)
        try:
            stop_cmd_node = system_status.get_child(["2:StopProductionCommand"])
            stop_cmd_node.set_value(True)
            print(f"  Stop production command sent")
        except Exception as e:
            print(f"  ⚠️ Error sending stop production command: {e}")
        
        # Final status check
        time.sleep(2)
        mode = mode_node.get_value()
        prod_rate = prod_rate_node.get_value()
        pump_status = pump_node.get_value()
        print(f"\n📈 Final System Status:")
        print(f"  System Mode: {mode}")
        print(f"  Production Rate: {prod_rate} units/hour")
        print(f"  Pump Status: {'ON' if pump_status else 'OFF'}")
        
        # Demonstrate emergency stop
        print("\n🚨 Testing Emergency Stop:")
        try:
            emergency_cmd_node = system_status.get_child(["2:EmergencyStopCommand"])
            emergency_cmd_node.set_value(True)
            print("  Emergency stop command sent")
            
            time.sleep(2)
            estop_node = system_status.get_child(["2:EmergencyStop"])
            estop_status = estop_node.get_value()
            mode = mode_node.get_value()
            print(f"  Emergency Stop Status: {estop_status}")
            print(f"  System Mode: {mode}")
            
        except Exception as e:
            print(f"  ⚠️ Error testing emergency stop: {e}")
        
        # Reset system
        print("\n🔄 Resetting System:")
        try:
            reset_cmd_node = system_status.get_child(["2:ResetSystemCommand"])
            reset_cmd_node.set_value(True)
            print("  Reset system command sent")
            
            time.sleep(2)
            estop_status = estop_node.get_value()
            mode = mode_node.get_value()
            print(f"  Emergency Stop Status: {estop_status}")
            print(f"  System Mode: {mode}")
            
        except Exception as e:
            print(f"  ⚠️ Error resetting system: {e}")
        
        print("\n✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logging.exception("Client error:")
        
    finally:
        # Always disconnect
        try:
            client.disconnect()
            print("🔌 Disconnected from server")
        except:
            pass


if __name__ == "__main__":
    print("OPC UA Industrial Control System - Client Demo")
    print("=" * 50)
    print("Make sure the server is running before starting this client!")
    print("Start the server with: python main.py")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Client stopped by user")
    except Exception as e:
        print(f"❌ Failed to run client: {e}") 