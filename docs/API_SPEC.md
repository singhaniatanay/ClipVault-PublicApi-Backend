## ClipVault Public API — Specification (v0.1.0)

This document mirrors the OpenAPI at `docs/openapi.json` (OpenAPI 3.1). Use `/openapi.json` or `/docs` from a running server for the authoritative machine- and human-readable specs.

- Base URL: deployment-specific; paths below are absolute (e.g., `/clips/`).
- Security scheme: HTTP Bearer (`Authorization: Bearer <jwt>`), alias `HTTPBearer` in the OpenAPI securitySchemes.

### Authentication

#### POST /auth/token
- Summary: Exchange OAuth code for JWT token
- Auth: Not required
- Request body (application/json): `TokenExchangeRequest`
  - `provider` (string, required)
  - `code` (string, required)
  - `code_verifier` (string|null)
  - `redirect_uri` (string|null)
- Responses:
  - 200: `TokenResponse`
  - 400: AuthError (Bad request)
  - 401: AuthError (Invalid authorization code)
  - 422: HTTPValidationError

#### GET /auth/me
- Summary: Get current user profile
- Security: HTTPBearer
- Responses:
  - 200: `UserProfile`
  - 401: AuthError (Authentication required)
  - 403: AuthError (Access forbidden)
  - 404: AuthError (User not found)

#### GET /auth/verify
- Summary: Verify JWT token validity
- Security: HTTPBearer
- Response 200: object (free-form JSON per OpenAPI)

### Clips

#### POST /clips/
- Summary: Save a new clip (link)
- Description: Idempotent save of a link and publish a clip.created event if new.
- Security: HTTPBearer
- Request body: `ClipCreateRequest`
- Responses:
  - 201: `ClipCreateResponse`
  - 400: Malformed or unsupported URL
  - 401: Authentication required
  - 409: `ClipDuplicateResponse`
  - 422: HTTPValidationError

#### GET /clips/{clip_id}
- Summary: Get a clip by ID (with tags and saved_at)
- Security: HTTPBearer
- Path parameters:
  - `clip_id` (string, required)
- Responses:
  - 200: `ClipDetailResponse`
  - 400: Invalid clip ID format
  - 401: Authentication required
  - 404: Clip not found or not accessible
  - 422: HTTPValidationError

### Search

#### GET /search/
- Summary: Search clips by keyword and tags
- Security: HTTPBearer
- Query parameters:
  - `query` (string|null)
  - `tags` (string|null) — comma-separated
  - `page` (integer, minimum 1, default 1)
  - `limit` (integer, 1–100, default 40)
- Responses:
  - 200: `SearchResponse`
  - 400: Invalid search parameters
  - 401: Authentication required
  - 422: Validation error

### Collections

#### POST /collections/
- Summary: Create Collection Endpoint
- Description: Create a new collection.
- Security: HTTPBearer
- Request body: `CollectionCreateRequest`
- Responses:
  - 201: `CollectionResponse`
  - 422: HTTPValidationError

#### GET /collections/
- Summary: List Collections
- Description: Get all collections owned by the authenticated user.
- Security: HTTPBearer
- Query parameters:
  - `page` (integer, minimum 1, default 1)
  - `limit` (integer, 1–100, default 20)
  - `include_clips_count` (boolean, default false)
- Responses:
  - 200: `CollectionListResponse`
  - 422: HTTPValidationError

#### GET /collections/{coll_id}
- Summary: Get Collection
- Description: Get a specific collection by ID.
- Security: HTTPBearer
- Path parameters: `coll_id` (string)
- Query parameters:
  - `include_clips` (boolean, default false)
  - `page` (integer, minimum 1, default 1)
  - `limit` (integer, 1–100, default 20)
- Responses:
  - 200: `CollectionDetailResponse`
  - 422: HTTPValidationError

#### PATCH /collections/{coll_id}
- Summary: Update Collection Endpoint
- Description: Update a collection.
- Security: HTTPBearer
- Path parameters: `coll_id` (string)
- Request body: `CollectionUpdateRequest`
- Responses:
  - 200: `CollectionResponse`
  - 422: HTTPValidationError

#### DELETE /collections/{coll_id}
- Summary: Delete Collection Endpoint
- Description: Delete a collection.
- Security: HTTPBearer
- Path parameters: `coll_id` (string)
- Responses:
  - 204: No content
  - 422: HTTPValidationError

#### POST /collections/{coll_id}/clips
- Summary: Add Clip To Collection Endpoint
- Description: Add a clip to a collection.
- Security: HTTPBearer
- Path parameters: `coll_id` (string)
- Request body: `CollectionClipRequest`
- Responses:
  - 204: No content
  - 422: HTTPValidationError

#### DELETE /collections/{coll_id}/clips/{clip_id}
- Summary: Remove Clip From Collection Endpoint
- Description: Remove a clip from a collection.
- Security: HTTPBearer
- Path parameters: `coll_id` (string), `clip_id` (string)
- Responses:
  - 204: No content
  - 422: HTTPValidationError

### Digest

Note: Some internal dependencies appear as parameters in the OpenAPI (e.g., a `db` query parameter). Clients typically do not need to provide these; they are implementation details surfaced by automatic schema generation.

#### GET /digest/preferences
- Summary: Get user's digest preferences
- Description: Retrieve the authenticated user's digest preferences from their profile
- Security: HTTPBearer
- Query parameters (per OpenAPI):
  - `db` (required) — framework artifact
- Responses:
  - 200: `DigestPreferences`
  - 401: Authentication required
  - 404: User profile not found
  - 422: HTTPValidationError

#### PUT /digest/preferences
- Summary: Update user's digest preferences
- Security: HTTPBearer
- Query parameters (per OpenAPI):
  - `db` (required) — framework artifact
- Request body: `DigestPreferences`
- Responses:
  - 200: `DigestPreferences`
  - 401: Authentication required
  - 422: Validation error
  - 500: Internal server error

#### GET /digest/preview
- Summary: Generate digest preview
- Description: Generate an HTML preview of the user's digest with their latest clips
- Security: HTTPBearer
- Query parameters (per OpenAPI):
  - `db` (required) — framework artifact
- Request body (per OpenAPI): `DigestPreviewRequest`
- Responses:
  - 200: `DigestPreviewResponse`
  - 401: Authentication required
  - 422: Validation error
  - 500: Internal server error

#### POST /digest/subscribe
- Summary: Enable digest subscription
- Security: HTTPBearer
- Query parameters (per OpenAPI):
  - `db` (required) — framework artifact
- Request body: `DigestSubscribeRequest`
- Responses:
  - 200: `DigestSubscribeResponse`
  - 401: Authentication required
  - 500: Internal server error
  - 422: HTTPValidationError

#### DELETE /digest/subscribe
- Summary: Disable digest subscription
- Security: HTTPBearer
- Query parameters (per OpenAPI):
  - `db` (required) — framework artifact
- Responses:
  - 200: `DigestSubscribeResponse`
  - 401: Authentication required
  - 500: Internal server error
  - 422: HTTPValidationError

### Health

#### GET /ping
- Summary: Health Check
- Description: Health check endpoint for Cloud Run.
- Response 200: `HealthResponse`

#### GET /health
- Summary: Detailed Health Check
- Description: Detailed health check including database and Pub/Sub status.
- Response 200: object

### Schemas (from components)

- AuthError, HealthResponse, HTTPValidationError, ValidationError
- TokenExchangeRequest, TokenResponse, UserProfile
- ClipCreateRequest, ClipCreateResponse, ClipDuplicateResponse, ClipModel, ClipDetailResponse, TagModel
- CollectionCreateRequest, CollectionUpdateRequest, CollectionResponse, CollectionListResponse, CollectionDetailResponse, CollectionClipRequest, CollectionClipInfo
- SearchClip, PaginationInfo, SearchResponse
- DigestPreferences, DigestPreviewRequest, DigestPreviewResponse, DigestSubscribeRequest, DigestSubscribeResponse




