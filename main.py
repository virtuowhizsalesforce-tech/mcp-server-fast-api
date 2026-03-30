import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from salesforce import create_lead, assign_permission_set, create_permission_set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Salesforce MCP Server", version="1.0.0")


@app.get("/")
def home():
    """Health check endpoint"""
    return {"message": "MCP Server Running ✅", "status": "healthy"}


@app.post("/mcp")
async def mcp_handler(request: Request):
    """MCP protocol handler - supports initialize, tools/list, tools/call"""
    try:
        # Log incoming request
        body = await request.json()
        logger.info(f"Incoming MCP request: {body}")

        req_type = body.get("type")
        req_id = body.get("id")

        # Validate required fields
        if not req_type:
            logger.error("Missing 'type' field in request")
            return JSONResponse(
                status_code=400,
                content={
                    "type": "error",
                    "error": {
                        "message": "Missing required field: 'type'"
                    }
                }
            )

        if req_id is None:
            logger.error("Missing 'id' field in request")
            return JSONResponse(
                status_code=400,
                content={
                    "type": "error",
                    "error": {
                        "message": "Missing required field: 'id'"
                    }
                }
            )

        # Handle MCP protocol messages
        if req_type == "initialize":
            logger.info("Processing initialize request")
            return JSONResponse(
                content={
                    "id": req_id,
                    "type": "result",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "salesforce-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }
            )

        elif req_type == "tools/list":
            logger.info("Processing tools/list request")
            return JSONResponse(
                content={
                    "id": req_id,
                    "type": "result",
                    "result": {
                        "tools": [
                            {
                                "name": "createLead",
                                "description": "Create a new Salesforce Lead with basic information",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "first_name": {
                                            "type": "string",
                                            "description": "First name of the lead"
                                        },
                                        "last_name": {
                                            "type": "string",
                                            "description": "Last name of the lead"
                                        },
                                        "email": {
                                            "type": "string",
                                            "description": "Email address of the lead"
                                        },
                                        "company": {
                                            "type": "string",
                                            "description": "Company name of the lead"
                                        }
                                    },
                                    "required": ["first_name", "last_name", "email", "company"]
                                }
                            },
                            {
                                "name": "assignPermissionSet",
                                "description": "Assign a permission set to a Salesforce user",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {
                                            "type": "string",
                                            "description": "Username of the Salesforce user"
                                        },
                                        "permission_set_name": {
                                            "type": "string",
                                            "description": "Name of the permission set to assign"
                                        }
                                    },
                                    "required": ["username", "permission_set_name"]
                                }
                            },
                            {
                                "name": "createPermissionSet",
                                "description": "Create a new Salesforce Permission Set using Metadata API",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "ps_name": {
                                            "type": "string",
                                            "description": "API name of the permission set"
                                        },
                                        "ps_label": {
                                            "type": "string",
                                            "description": "Label/display name of the permission set"
                                        }
                                    },
                                    "required": ["ps_name", "ps_label"]
                                }
                            }
                        ]
                    }
                }
            )

        elif req_type == "tools/call":
            tool_name = body.get("name")
            args = body.get("arguments", {})

            logger.info(f"Processing tools/call request for tool: {tool_name} with args: {args}")

            if not tool_name:
                return JSONResponse(
                    content={
                        "id": req_id,
                        "type": "error",
                        "error": {
                            "message": "Missing required field: 'name' for tools/call"
                        }
                    }
                )

            try:
                if tool_name == "createLead":
                    result = create_lead(**args)
                elif tool_name == "assignPermissionSet":
                    result = assign_permission_set(**args)
                elif tool_name == "createPermissionSet":
                    result = create_permission_set(**args)
                else:
                    result = f"❌ Unknown tool: {tool_name}"

                logger.info(f"Tool {tool_name} executed successfully")
                return JSONResponse(
                    content={
                        "id": req_id,
                        "type": "result",
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result
                                }
                            ]
                        }
                    }
                )

            except Exception as tool_error:
                logger.error(f"Error executing tool {tool_name}: {str(tool_error)}")
                return JSONResponse(
                    content={
                        "id": req_id,
                        "type": "error",
                        "error": {
                            "message": f"Tool execution failed: {str(tool_error)}"
                        }
                    }
                )

        else:
            logger.warning(f"Invalid MCP request type: {req_type}")
            return JSONResponse(
                content={
                    "id": req_id,
                    "type": "error",
                    "error": {
                        "message": f"Invalid MCP request type: {req_type}"
                    }
                }
            )

    except Exception as e:
        logger.error(f"Unexpected error in MCP handler: {str(e)}")
        # For unexpected errors, we might not have req_id, so return generic error
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "error": {
                    "message": f"Internal server error: {str(e)}"
                }
            }
        )