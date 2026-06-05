# Security Policy

## Connection security (important)

Both server implementations currently connect to OPC UA endpoints using:

- `SecurityPolicy.None`
- `MessageSecurityMode.None`

This means traffic is **unencrypted and unauthenticated**. It is suitable for
local development and evaluation against mock/test servers, **not** for
production or anything exposed to an untrusted network.

For production deployments you should add:

- Certificate-based authentication
- Encrypted communication (a non-`None` security policy/mode)
- User authentication
- Input validation on node IDs and written values

Treat the MCP servers as having the same privileges as the OPC UA account they
connect with: anyone able to talk to the MCP server can read and write any node
that account can.

## Supported versions

This project is pre-1.0. Security fixes land on `main` and the latest published
npm release of `opcua-mcp-server`.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/midhunxavier/OPCUA-MCP/security/advisories/new),
or email the maintainer at midhunxavier@outlook.com.

Please include:

- A description of the issue and its impact
- Steps to reproduce (or a proof of concept)
- Affected version(s)/commit

We aim to acknowledge reports within a few days and will coordinate a fix and
disclosure timeline with you.
