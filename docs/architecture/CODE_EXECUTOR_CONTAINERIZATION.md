# Code Executor Containerization - Future Consideration

## Overview

The current `SandboxedCodeExecutor` implementation executes Python code in-process within the main ODRAS application. For enhanced security and isolation, we should consider moving code execution to a dedicated Docker container.

## Current Implementation

- **Location**: `backend/services/code_executor.py`
- **Execution Model**: In-process execution with restricted namespace
- **Isolation**: Python namespace restrictions and import hooks
- **Security**: AST-based validation, restricted imports, timeout enforcement

## Proposed Architecture

### Dedicated Code Executor Container

- **Separate Docker Service**: New `code-executor` service in `docker-compose.yml`
- **API Endpoint**: HTTP/gRPC API for code execution requests
- **Isolation**: Complete process isolation from main application
- **Resource Limits**: Docker-level CPU, memory, and timeout limits
- **Security**: Container-level security policies

### Benefits

1. **Enhanced Security**
   - Complete process isolation
   - No shared memory or file system access
   - Container-level resource limits
   - Easier to implement stricter security policies

2. **Scalability**
   - Can scale code executor independently
   - Multiple executor instances for parallel execution
   - Better resource management

3. **Fault Isolation**
   - Code execution failures don't affect main application
   - Easier to restart/recover executor service
   - Better monitoring and logging separation

4. **Compliance**
   - Easier to audit and certify security
   - Clear separation of concerns
   - Better for enterprise deployments

### Implementation Considerations

1. **API Design**
   - REST API or gRPC for code execution requests
   - Request/response format compatible with `CodeExecutorInterface`
   - Authentication/authorization between services

2. **Container Configuration**
   - Minimal Python runtime (Alpine-based)
   - Only required libraries installed
   - Network isolation (no external network access by default)
   - Read-only file system where possible

3. **Resource Management**
   - Docker CPU limits
   - Docker memory limits
   - Timeout enforcement at container level
   - Process monitoring and cleanup

4. **Integration**
   - Update `CodeExecutorInterface` to support remote execution
   - Create `RemoteCodeExecutor` implementation
   - Maintain backward compatibility with in-process executor
   - Configuration option to choose executor type

5. **Monitoring**
   - Separate logging for executor service
   - Metrics for execution time, success rate, resource usage
   - Health checks and status endpoints

### Migration Path

1. **Phase 1**: Design API and container architecture
2. **Phase 2**: Implement executor container service
3. **Phase 3**: Create `RemoteCodeExecutor` implementation
4. **Phase 4**: Add configuration option to switch between executors
5. **Phase 5**: Test and validate security improvements
6. **Phase 6**: Deploy and monitor in production

### Related Components

- `backend/services/code_executor.py` - Current implementation
- `backend/services/code_executor_interface.py` - Interface definition
- `docker-compose.yml` - Container orchestration
- `backend/services/config.py` - Configuration management

### Security Considerations

- Container should have minimal privileges
- No access to host file system
- Network isolation (only communicate with main app)
- Resource limits enforced at container level
- Regular security updates for container image
- Audit logging for all code executions

### Performance Considerations

- Network latency for remote execution
- Serialization overhead for code/context
- Container startup time (consider keeping warm)
- Resource overhead of separate container

## Status

**Status**: Future Consideration  
**Priority**: Medium  
**Created**: 2025-01-XX  
**Related Issues**: None

## Notes

- Current in-process executor is sufficient for MVP
- Containerization becomes more important as:
  - Security requirements increase
  - Code execution volume grows
  - Multi-tenant deployments are needed
  - Compliance requirements become stricter
