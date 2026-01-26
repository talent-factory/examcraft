#!/bin/bash
# ExamCraft Deployment Test Script
# Tests 2-tier deployment: Core (OpenSource) and Full (Premium + Enterprise)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TIMEOUT=120  # 2 minutes timeout for container startup
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_INTERVAL=5

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up containers..."
    docker compose --env-file .env -f docker-compose.yml down -v 2>/dev/null || true
    docker compose --env-file .env -f docker-compose.full.yml down -v 2>/dev/null || true
}

# Health check function
check_service_health() {
    local service_name=$1
    local port=$2
    local endpoint=${3:-"/health"}

    log_info "Checking health of $service_name on port $port..."

    for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
        if curl -f -s "http://localhost:$port$endpoint" > /dev/null 2>&1; then
            log_success "$service_name is healthy!"
            return 0
        fi
        log_warning "Attempt $i/$HEALTH_CHECK_RETRIES: $service_name not ready yet..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "$service_name failed health check!"
    return 1
}

# Test Core Deployment (OpenSource)
test_core_deployment() {
    log_info "========================================="
    log_info "TEST 1: Core Deployment (OpenSource)"
    log_info "========================================="

    cleanup

    log_info "Starting Core services..."
    docker compose --env-file .env -f docker-compose.yml up -d

    log_info "Waiting for services to start..."
    sleep 10

    # Check PostgreSQL
    log_info "Checking PostgreSQL..."
    docker compose --env-file .env -f docker-compose.yml exec -T postgres pg_isready -U examcraft || {
        log_error "PostgreSQL is not ready!"
        return 1
    }
    log_success "PostgreSQL is ready!"

    # Check Redis
    log_info "Checking Redis..."
    docker compose --env-file .env -f docker-compose.yml exec -T redis redis-cli ping | grep -q PONG || {
        log_error "Redis is not responding!"
        return 1
    }
    log_success "Redis is ready!"

    # Check Backend
    check_service_health "Backend" 8000 "/api/health" || return 1

    # Check Frontend
    check_service_health "Frontend" 3000 "/" || return 1

    log_success "✅ Core Deployment: PASS"

    cleanup
    return 0
}

# Test Full Deployment (Premium + Enterprise)
test_full_deployment() {
    log_info "=============================================="
    log_info "TEST 2: Full Deployment (Premium + Enterprise)"
    log_info "=============================================="

    cleanup

    # Check if submodules are available
    if [ ! -d "packages/premium" ] || [ -z "$(ls -A packages/premium 2>/dev/null)" ]; then
        log_warning "Premium submodule not initialized. Initializing..."
        git submodule update --init --recursive packages/premium || {
            log_error "Failed to initialize Premium submodule!"
            return 1
        }
    fi

    if [ ! -d "packages/enterprise" ] || [ -z "$(ls -A packages/enterprise 2>/dev/null)" ]; then
        log_warning "Enterprise submodule not initialized. Initializing..."
        git submodule update --init --recursive packages/enterprise || {
            log_error "Failed to initialize Enterprise submodule!"
            return 1
        }
    fi

    log_info "Starting Full services (Core + Premium + Enterprise)..."
    docker compose --env-file .env -f docker-compose.full.yml up -d

    log_info "Waiting for services to start..."
    sleep 20

    # Check PostgreSQL
    log_info "Checking PostgreSQL..."
    docker compose --env-file .env -f docker-compose.full.yml exec -T postgres pg_isready -U examcraft || {
        log_error "PostgreSQL is not ready!"
        return 1
    }
    log_success "PostgreSQL is ready!"

    # Check Redis
    log_info "Checking Redis..."
    docker compose --env-file .env -f docker-compose.full.yml exec -T redis redis-cli ping | grep -q PONG || {
        log_error "Redis is not responding!"
        return 1
    }
    log_success "Redis is ready!"

    # Check Qdrant (Premium feature)
    log_info "Checking Qdrant..."
    check_service_health "Qdrant" 6333 "/" || return 1

    # Check Backend with Premium/Enterprise features
    check_service_health "Backend (Full)" 8000 "/api/health" || return 1

    # Check Frontend
    check_service_health "Frontend" 3000 "/" || return 1

    log_success "✅ Full Deployment: PASS"

    cleanup
    return 0
}

# Main execution
main() {
    log_info "ExamCraft Deployment Test Suite"
    log_info "================================"
    log_info "2-Tier Architecture: Core (OpenSource) + Full (Premium + Enterprise)"
    echo ""

    # Trap cleanup on exit
    trap cleanup EXIT

    # Run tests
    FAILED_TESTS=0

    if test_core_deployment; then
        echo ""
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "Core deployment test failed!"
    fi

    if test_full_deployment; then
        echo ""
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "Full deployment test failed!"
    fi

    # Final report
    echo ""
    log_info "========================================="
    log_info "DEPLOYMENT TEST SUMMARY"
    log_info "========================================="

    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "All deployment tests passed! ✅"
        exit 0
    else
        log_error "$FAILED_TESTS test(s) failed! ❌"
        exit 1
    fi
}

# Run main function
main "$@"
