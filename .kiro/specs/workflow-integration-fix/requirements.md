# Workflow Integration Fix Requirements

## Introduction

This document outlines the requirements to fix critical workflow inconsistencies identified across the multi-agent BI system components (backend, frontend, agents, tidb-mcp-server). These inconsistencies are causing broken integration points and preventing the system from working properly as described in the architecture documentation.

## Requirements

### Requirement 1: API Endpoint Alignment

**User Story:** As a system integrator, I want consistent API endpoint naming across frontend and backend, so that HTTP requests reach the correct handlers.

#### Acceptance Criteria

1. WHEN frontend makes requests to `/api/query` THEN backend SHALL provide a matching endpoint handler
2. WHEN backend implements endpoints THEN they SHALL match the exact paths used by frontend API calls
3. WHEN endpoint paths are changed THEN both frontend and backend SHALL be updated simultaneously
4. WHEN endpoints are documented THEN they SHALL reflect the actual implemented routes
5. WHEN testing integration THEN all frontend API calls SHALL successfully reach their backend handlers

### Requirement 2: Request/Response Format Standardization

**User Story:** As a developer, I want standardized data structures across all components, so that data flows correctly through the multi-agent workflow.

#### Acceptance Criteria

1. WHEN frontend sends QueryRequest THEN all components SHALL understand the same request format
2. WHEN backend returns QueryResponse THEN it SHALL match the interface expected by frontend
3. WHEN agents return data THEN their response formats SHALL align with backend expectations
4. WHEN data is transformed THEN the field names and types SHALL remain consistent across agents
5. WHEN errors occur THEN error response formats SHALL be standardized across all components

### Requirement 3: Agent Integration Workflow Repair

**User Story:** As a backend orchestrator, I want proper agent sequence orchestration, so that queries are processed through the correct workflow.

#### Acceptance Criteria

1. WHEN processing queries THEN backend SHALL call NLP Agent → Data Agent → Viz Agent in correct sequence
2. WHEN calling NLP Agent THEN backend SHALL use the `/process` endpoint that agent provides
3. WHEN calling Data Agent THEN backend SHALL use the correct endpoint that data agent implements
4. WHEN calling Viz Agent THEN backend SHALL use the `/visualize` endpoint with proper request format
5. WHEN agent calls fail THEN backend SHALL implement proper error handling and fallback mechanisms

### Requirement 4: Data Agent Implementation Unification

**User Story:** As a data agent maintainer, I want a single, clear implementation pattern, so that integration is predictable and maintainable.

#### Acceptance Criteria

1. WHEN choosing between HTTP and MCP implementations THEN data agent SHALL use one consistent approach
2. WHEN implementing endpoints THEN data agent SHALL provide the exact endpoints that backend expects
3. WHEN importing dependencies THEN data agent SHALL only import from its own modules, not from other agents
4. WHEN processing queries THEN data agent SHALL use either HTTP or MCP protocol consistently throughout
5. WHEN configuring data agent THEN environment variables SHALL clearly control which implementation is active

### Requirement 5: Visualization Agent API Compatibility

**User Story:** As a visualization agent, I want to receive data in the correct format, so that I can generate visualizations without data transformation errors.

#### Acceptance Criteria

1. WHEN backend calls visualization agent THEN it SHALL use the `/visualize` endpoint that agent provides
2. WHEN sending data to viz agent THEN backend SHALL format data according to VisualizationRequest interface
3. WHEN viz agent processes requests THEN it SHALL return data in the format expected by backend
4. WHEN chart generation fails THEN viz agent SHALL provide detailed error information for debugging
5. WHEN multiple chart types are needed THEN viz agent SHALL support all chart types used by frontend

### Requirement 6: Schema Management Endpoint Implementation

**User Story:** As a data agent, I want access to schema management endpoints, so that I can discover and use database schema information dynamically.

#### Acceptance Criteria

1. WHEN data agent needs schema information THEN backend SHALL provide `/api/schema/discovery` endpoint
2. WHEN requesting schema mappings THEN backend SHALL provide `/api/schema/mappings` endpoint
3. WHEN querying relationships THEN backend SHALL provide `/api/schema/relationships` endpoint
4. WHEN schema endpoints are called THEN they SHALL return data in the format expected by agents
5. WHEN schema information is cached THEN endpoints SHALL provide cache invalidation capabilities

### Requirement 7: TiDB MCP Server Integration Standardization

**User Story:** As an agent developer, I want consistent MCP server integration patterns, so that all agents can reliably communicate with the database layer.

#### Acceptance Criteria

1. WHEN connecting to TiDB MCP Server THEN all agents SHALL use the same connection URL and protocol
2. WHEN making MCP requests THEN agents SHALL use the standardized MCP client interface
3. WHEN TiDB MCP Server provides APIs THEN they SHALL be available at the documented ports and paths
4. WHEN schema discovery is needed THEN agents SHALL use the MCP server's schema discovery tools
5. WHEN database context is required THEN agents SHALL receive proper database selection information

### Requirement 8: Communication Protocol Unification

**User Story:** As a system architect, I want consistent communication protocols, so that services can reliably interact with each other.

#### Acceptance Criteria

1. WHEN agents communicate THEN they SHALL use either WebSocket OR HTTP consistently, not mixed
2. WHEN backend calls agents THEN it SHALL use the same protocol that agents are configured to receive
3. WHEN WebSocket connections are used THEN proper connection management SHALL be implemented
4. WHEN HTTP connections are used THEN proper connection pooling SHALL be implemented
5. WHEN protocol configuration is needed THEN environment variables SHALL control protocol selection

### Requirement 9: Database Context and Selection Workflow

**User Story:** As a user, I want proper database selection and initialization, so that queries are executed against the correct database context.

#### Acceptance Criteria

1. WHEN frontend shows database selector THEN backend SHALL handle database selection requests
2. WHEN database is selected THEN schema discovery workflow SHALL be triggered automatically
3. WHEN schema is discovered THEN agents SHALL be initialized with the correct database context
4. WHEN queries are processed THEN they SHALL execute against the selected database
5. WHEN database context is lost THEN system SHALL provide clear error messages and recovery options

### Requirement 10: Error Handling and Recovery Standardization

**User Story:** As a user, I want consistent error handling, so that I receive helpful feedback when workflow issues occur.

#### Acceptance Criteria

1. WHEN API endpoints don't match THEN system SHALL provide clear "endpoint not found" errors
2. WHEN data formats don't match THEN system SHALL provide detailed format validation errors
3. WHEN agents are unreachable THEN system SHALL provide helpful connectivity error messages
4. WHEN database context is missing THEN system SHALL guide users through database selection
5. WHEN workflow steps fail THEN system SHALL provide recovery suggestions and alternative actions

### Requirement 11: Configuration and Environment Management

**User Story:** As a DevOps engineer, I want centralized configuration management, so that integration settings are consistent across all services.

#### Acceptance Criteria

1. WHEN configuring endpoints THEN environment variables SHALL define all service URLs and ports
2. WHEN setting protocols THEN configuration SHALL clearly specify HTTP vs WebSocket for each service
3. WHEN defining MCP connections THEN configuration SHALL specify MCP server URLs and authentication
4. WHEN managing database contexts THEN configuration SHALL specify default databases and schemas
5. WHEN troubleshooting THEN configuration SHALL provide clear logging of all integration attempts

### Requirement 12: Integration Testing and Validation

**User Story:** As a quality assurance engineer, I want comprehensive integration tests, so that workflow inconsistencies are caught before deployment.

#### Acceptance Criteria

1. WHEN running integration tests THEN tests SHALL verify all API endpoint connections work
2. WHEN testing data flow THEN tests SHALL verify data formats are consistent across components
3. WHEN testing agent communication THEN tests SHALL verify proper orchestration sequence
4. WHEN testing error scenarios THEN tests SHALL verify proper error handling and recovery
5. WHEN testing full workflow THEN tests SHALL verify end-to-end query processing works correctly
