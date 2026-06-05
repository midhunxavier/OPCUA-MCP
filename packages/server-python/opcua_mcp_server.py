from mcp.server.fastmcp import FastMCP, Context
from opcua import Client
from contextlib import asynccontextmanager
from typing import AsyncIterator
import asyncio
import os
import sys
from typing import List, Dict, Any
from datetime import datetime
from opcua import ua
from opcua.ua import NodeClass

server_url = os.getenv("OPCUA_SERVER_URL", "opc.tcp://localhost:4840")

import json
from pathlib import Path


def _load_contract() -> dict:
    """Load the shared tool contract (single source of truth).

    The canonical file is ``/contract/tools.json`` at the repo root, read directly
    when running from the source tree (dev / editable installs / tests). When the
    package is installed as a wheel the contract is bundled next to this module
    (see the ``force-include`` in pyproject.toml), so the installed copy is found
    there instead. Without the bundled copy a pip/uvx install would raise
    FileNotFoundError on import, since parents[2] is not the repo root.
    """
    here = Path(__file__).resolve()
    candidates = (
        here.parent / "opcua_mcp_server_contract.json",  # bundled in the wheel
        here.parents[2] / "contract" / "tools.json",     # repo-root source layout
    )
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError(
        "Shared tool contract not found; looked in "
        + ", ".join(str(p) for p in candidates)
    )


# Shared tool contract so tool descriptions and capability node IDs stay in sync
# with the Node server.
_CONTRACT = _load_contract()
_DESC = {t["name"]: t["description"] for t in _CONTRACT["tools"]}
_HISTORY_NODE_ID = _CONTRACT["capabilities"]["history"]["nodeId"]

# Manage the lifecycle of the OPC UA client connection
@asynccontextmanager
async def opcua_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Handle OPC UA client connection lifecycle."""
    client = Client(server_url)  
    try:
        # Connect to OPC UA server synchronously, wrapped in a thread for async compatibility
        await asyncio.to_thread(client.connect)
        # Log to stderr: stdout is reserved for the MCP stdio JSON-RPC transport.
        print("Connected to OPC UA server", file=sys.stderr)
        yield {"opcua_client": client}
    finally:
        # Disconnect from OPC UA server on shutdown
        await asyncio.to_thread(client.disconnect)
        print("Disconnected from OPC UA server", file=sys.stderr)

# Create an MCP server instance
mcp = FastMCP("OPCUA-Control", lifespan=opcua_lifespan)

# Tool: Read the value of an OPC UA node
@mcp.tool(description=_DESC["read_opcua_node"])
def read_opcua_node(node_id: str, ctx: Context) -> str:
    """
    Read the value of a specific OPC UA node.
    
    Parameters:
        node_id (str): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'.
                       Example: 'ns=2;i=2'.
    
    Returns:
        str: The value of the node as a string, prefixed with the node ID.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    node = client.get_node(node_id)
    value = node.get_value()  # Synchronous call to get node value
    return f"Node {node_id} value: {value}"

def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an optional ISO-8601 string into a datetime.

    MCP delivers these as strings, so they are converted here before being handed
    to the opcua client. Mirrors the npx server's ``toDate`` error wording so both
    servers reject malformed input identically.
    """
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError(
            f'Invalid date/time: "{value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z'
        )


# Tool: Read historical values of an OPC UA node.
# Registered only when the server supports historical data access (see below),
# mirroring the npx server's capability gating.
def read_history_opcua_node(node_id: str,
                            ctx: Context,
                            start_time: str | None = None,
                            end_time: str | None = None,
                            num_values: int = 0) -> list[dict]:
    """
    Read the historical values of a specific OPC UA node.

    Parameters:
        node_id (str): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'.
                       Example: 'ns=2;i=2'.
        start_time (str): Start time (ISO 8601).
                          Example: '2026-04-22T18:50:00Z'
        end_time (str): End time (ISO 8601).
                        Example: '2026-04-22T18:51:00Z'
        num_values (int): Number of values to read (default: unlimited)

    Returns:
        list[dict]: An array of values `{ "value": <value>, "timestamp": <timestamp>, "status": "Good" }`
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    node = client.get_node(node_id)
    values = node.read_raw_history(
        starttime=_parse_iso_datetime(start_time),
        endtime=_parse_iso_datetime(end_time),
        numvalues=num_values,
    )
    return [
        {
            "value": str(v.Value.Value),
            "timestamp": str(v.SourceTimestamp),
            "status": str(v.StatusCode.name)
        }
        for v in values
    ]


def _server_supports_history(url: str) -> bool:
    """Probe the server's AccessHistoryDataCapability (ns=0;i=11193).

    Used to expose `read_history_opcua_node` only when the server actually
    supports historical reads, matching the npx server's behaviour.
    """
    try:
        probe = Client(url)
        probe.connect()
        try:
            return bool(probe.get_node(_HISTORY_NODE_ID).get_value())
        finally:
            probe.disconnect()
    except Exception:
        return False


# Conditionally register the history tool based on server capability.
if _server_supports_history(server_url):
    read_history_opcua_node = mcp.tool(description=_DESC["read_history_opcua_node"])(read_history_opcua_node)


# Tool: Write a value to an OPC UA node
@mcp.tool(description=_DESC["write_opcua_node"])
def write_opcua_node(node_id: str, value: str, ctx: Context) -> str:
    """
    Write a value to a specific OPC UA node.
    
    Parameters:
        node_id (str): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'.
                       Example: 'ns=2;i=3'.
        value (str): The value to write to the node. Will be converted based on node type.
    
    Returns:
        str: A message indicating success or failure of the write operation.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    node = client.get_node(node_id)
    try:
        # Convert value based on the node's current type.
        # Note: check bool before (int, float) because bool is a subclass of int.
        current_value = node.get_value()
        if isinstance(current_value, bool):
            node.set_value(str(value).lower() in ['true', '1', 'yes', 'on'])
        elif isinstance(current_value, (int, float)):
            node.set_value(float(value))
        else:
            node.set_value(value)
        return f"Successfully wrote {value} to node {node_id}"
    except Exception as e:
        return f"Error writing to node {node_id}: {str(e)}"

# Tool: Browse the children of a specific OPC UA node
@mcp.tool(description=_DESC["browse_opcua_node_children"])
def browse_opcua_node_children(node_id: str, ctx: Context) -> str:
    """
    Browse the children of a specific OPC UA node.

    Parameters:
        node_id (str): The OPC UA node ID to browse (e.g., 'ns=0;i=85' for Objects folder).

    Returns:
        str: A string representation of a list of child nodes, including their NodeId and BrowseName.
             Returns an error message on failure.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    try:
        node = client.get_node(node_id)
        children = node.get_children()
        
        children_info = []
        for child in children:
            try:
                browse_name = child.get_browse_name()
                children_info.append({
                    "node_id": child.nodeid.to_string(),
                    "browse_name": f"{browse_name.NamespaceIndex}:{browse_name.Name}"
                })
            except Exception as e:
                 children_info.append({
                     "node_id": child.nodeid.to_string(),
                     "browse_name": f"Error getting name: {e}"
                 })

        # import json
        # return json.dumps(children_info, indent=2) 
        return f"Children of {node_id}: {children_info!r}" 
        
    except Exception as e:
        return f"Error Browse children of node {node_id}: {str(e)}"

# Tool: Call an OPC UA method
@mcp.tool(description=_DESC["call_opcua_method"])
def call_opcua_method(object_node_id: str, method_node_id: str, ctx: Context, arguments: List[Any] = None) -> str:
    """
    Call a method on a specific OPC UA object node.

    Parameters:
        object_node_id (str): The OPC UA node ID of the object that contains the method.
                             Example: 'ns=2;i=1' for the Methods folder.
        method_node_id (str): The OPC UA node ID of the method to call.
                             Example: 'ns=2;i=2' for StartProduction method.
        ctx (Context): The context for the request.
        arguments (List[Any], optional): List of arguments to pass to the method.
                                       Arguments will be converted to appropriate OPC UA variants.

    Returns:
        str: The result of the method call or an error message if the call fails.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    try:
        # Get the object and method nodes
        object_node = client.get_node(object_node_id)
        method_node = client.get_node(method_node_id)

        # Prepare arguments
        method_args = []
        if arguments:
            for arg in arguments:
                # Convert arguments to appropriate types
                if isinstance(arg, str):
                    # Try to convert string to appropriate type
                    try:
                        # Try float first
                        method_args.append(float(arg))
                    except ValueError:
                        try:
                            # Try int
                            method_args.append(int(arg))
                        except ValueError:
                            # Keep as string
                            method_args.append(arg)
                else:
                    method_args.append(arg)
        
        # Call the method on the object node. python-opcua exposes call_method on Node
        # (not Client), and a string methodid is treated as a child browse-name, so pass
        # the resolved method Node to call it by node id.
        result = object_node.call_method(method_node, *method_args)

        return f"Method call successful. Object: {object_node_id}, Method: {method_node_id}, Result: {result}"
        
    except Exception as e:
        return f"Error calling method {method_node_id} on object {object_node_id}: {str(e)}"

# Tool: Read multiple OPC UA nodes
@mcp.tool(description=_DESC["read_multiple_opcua_nodes"])
def read_multiple_opcua_nodes(node_ids: List[str], ctx: Context) -> str:
    """
    Read the values of multiple OPC UA nodes in a single request.

    Parameters:
        node_ids (List[str]): A list of OPC UA node IDs to read (e.g., ['ns=2;i=2', 'ns=2;i=3']).

    Returns:
        str: A string representation of a dictionary mapping node IDs to their values, or an error message.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    try:
        results = {}
        for node_id in node_ids:
            try:
                node = client.get_node(node_id)
                value = node.get_value()
                results[node_id] = value
            except Exception as e:
                results[node_id] = f"Error: {str(e)}"
        
        return f"Multiple node read results: {results!r}"
        
    except Exception as e:
        return f"Error reading multiple nodes: {str(e)}"

# Tool: Write multiple OPC UA nodes
@mcp.tool(description=_DESC["write_multiple_opcua_nodes"])
def write_multiple_opcua_nodes(nodes_to_write: List[Dict[str, Any]], ctx: Context) -> str:
    """
    Write values to multiple OPC UA nodes in a single request.

    Parameters:
        nodes_to_write (List[Dict[str, Any]]): A list of dictionaries, where each dictionary 
                                               contains 'node_id' (str) and 'value' (Any).
                                               The value will be wrapped in an OPC UA Variant.
                                               Example: [{'node_id': 'ns=2;i=2', 'value': 10.5}, 
                                                         {'node_id': 'ns=2;i=3', 'value': 'active'}]

    Returns:
        str: A message indicating the success or failure of the write operation. 
             Returns status codes for each write attempt.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    try:
        results = []
        for item in nodes_to_write:
            node_id = item['node_id']
            value = item['value']
            
            try:
                node = client.get_node(node_id)
                
                # Convert value based on the node's current type.
                # Note: check bool before (int, float) because bool is a subclass of int.
                current_value = node.get_value()
                if isinstance(current_value, bool):
                    converted_value = str(value).lower() in ['true', '1', 'yes', 'on']
                elif isinstance(current_value, (int, float)):
                    converted_value = float(value)
                else:
                    converted_value = str(value)
                
                node.set_value(converted_value)
                results.append({"node_id": node_id, "status": "Success"})
                
            except Exception as e:
                results.append({"node_id": node_id, "status": f"Error: {str(e)}"})
        
        return f"Write operation results: {results!r}"
        
    except Exception as e:
        return f"Error writing multiple nodes: {str(e)}"

# Tool: Get all variables information
@mcp.tool(description=_DESC["get_all_variables"])
def get_all_variables(ctx: Context) -> str:
    """
    Get all available variables from the OPC UA server, excluding those under the built-in 'Server' object.
    
    Returns:
        str: A string representation of all variables with their name, nodeid, object_id, value, 
             data_type, and description.
    """
    client = ctx.request_context.lifespan_context["opcua_client"]
    variables_info = []
    
    try:
        objects_node = client.get_objects_node()

        def search_variables(node):
            try:
                children = node.get_children()
            except Exception:
                return

            for child in children:
                try:
                    node_class = child.get_node_class()
                except Exception:
                    continue

                # Skip the entire "Server" subtree
                try:
                    child_browse_name = child.get_browse_name().Name
                    if child_browse_name == "Server":
                        continue
                except Exception:
                    continue

                if node_class == NodeClass.Variable:
                    browse_name = child_browse_name
                    node_id = child.nodeid.to_string()
                    
                    try:
                        parent_node = child.get_parent()
                        object_id = parent_node.nodeid.to_string() if parent_node else "N/A"
                    except Exception:
                        object_id = "N/A"

                    try:
                        value = child.get_value()
                    except Exception:
                        value = None

                    try:
                        data_type = child.get_data_type().to_string()
                    except Exception:
                        data_type = ""

                    try:
                        desc = child.get_description().Text
                    except Exception:
                        desc = ""
                    
                    variables_info.append({
                        "name": browse_name,
                        "nodeid": node_id,
                        "object_id": object_id,
                        "value": value,
                        "data_type": data_type,
                        "description": desc
                    })
                elif node_class == NodeClass.Object:
                    # Recursively search children of this object,
                    # unless it is the "Server" object
                    search_variables(child)

        search_variables(objects_node)
        
        if variables_info:
            result = f"Found {len(variables_info)} variables:\n"
            for var in variables_info:
                result += f"\n- Name: {var['name']}\n"
                result += f"  NodeID: {var['nodeid']}\n"
                result += f"  Object ID: {var['object_id']}\n"
                result += f"  Value: {var['value']}\n"
                result += f"  Data Type: {var['data_type']}\n"
                result += f"  Description: {var['description']}\n"
            return result
        else:
            return "No variables found in the OPC UA server."
            
    except Exception as e:
        return f"Error while finding variables: {str(e)}"

# Run the server
def main() -> None:
    """Entry point for the `opcua-mcp-server` console script."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()