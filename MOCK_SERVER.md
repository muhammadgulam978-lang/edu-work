EduPilot Mobile Mock Server

This document explains how to run a local mock server for the EduPilot Student Mobile API and how to import the Postman collection.

Files included:
- postman_collection.json  — Postman collection for core mobile flows
- postman_environment.json — Postman environment (baseUrl defaults to http://localhost:4010)
- openapi.yaml            — OpenAPI spec (detailed)
- MOCK_DATA.json          — Example JSON payloads for common endpoints

Option A — Run a local mock server with Prism (recommended)
1. Install Node.js (if not installed). Then install Prism:
   npm install -g @stoplight/prism-cli

2. Run Prism mock server using the OpenAPI spec:
   prism mock openapi.yaml -p 4010

   - The mock server will listen on http://localhost:4010
   - Prism will return example responses where available. If endpoints have no examples, Prism synthesizes responses from the schema.

3. Test with curl or Postman using the Postman collection. Example:
   curl -X POST "http://localhost:4010/auth/login/" -H "Content-Type: application/json" -d '{"username":"student1@example.com","password":"pass123"}'

Option B — Use Postman mock server
1. Open Postman, import `openapi.yaml` or `postman_collection.json` (File → Import).
2. Create a mock server in Postman from the collection: Collections → ... → Mock Collection.
3. Use the mock server URL as the baseUrl in `postman_environment.json`.

Notes & tips
- The Postman collection uses {{baseUrl}} as the root. Import the provided environment or set baseUrl manually to http://localhost:4010.
- For realistic responses, you can copy example objects from MOCK_DATA.json into Postman example responses or extend openapi.yaml with examples.
- WebSocket endpoints (`/ws/communication/`, `/ws/vouchers/`) cannot be served by Prism. Use Postman or a small Node/Express mock WS server if you need WS testing. The mock server will let mobile teams exercise REST workflows without a live backend.

Deliverables for mobile devs
- postman_collection.json (import into Postman)
- postman_environment.json (set baseUrl and token)
- openapi.yaml (detailed spec)
- MOCK_DATA.json (example responses)

If you want, I can also:
- Generate a Postman mock server from the OpenAPI and provide the mock server URL (requires a Postman account).
- Create a tiny Node Express + WS mock server that also serves WebSocket events for vouchers/communication.
- Add examples into openapi.yaml to make Prism return richer example responses.

What would you like next?
- "Create Postman mock server (requires Postman account)"
- "Create Node Express + WS mock server repository files"
- "Add examples to openapi.yaml for Prism to use"
- "Nothing — I'm done"
