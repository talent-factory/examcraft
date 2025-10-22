#!/bin/bash
# ExamCraft Deployment Test Script
# Tests all three deployment scenarios with actual container startup

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
    docker-compose -f docker-compose.yml \
                   -f docker-compose.premium.yml \
                   -f docker-compose.enterprise.yml \
                   down -v 2>/dev/null || true
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

# Test Core Only Deployment
test_core_deployment() {
    log_info "========================================="
    log_info "TEST 1: Core Only Deployment (Free Tier)"
    log_info "========================================="
    
    cleanup
    
    log_info "Starting Core services..."
    docker-compose -f docker-compose.yml up -d
    
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check PostgreSQL
    log_info "Checking PostgreSQL..."
    docker-compose -f docker-compose.yml exec -T postgres pg_isready -U examcraft || {
        log_error "PostgreSQL is not ready!"
        return 1
    }
    log_success "PostgreSQL is ready!"
    
    # Check Redis
    log_info "Checking Redis..."
    docker-compose -f docker-compose.yml exec -T redis redis-cli ping | grep -q PONG || {
        log_error "Redis is not responding!"
        return 1
    }
    log_success "Redis is ready!"
    
    # Check Backend
    check_service_health "Backend" 8000 "/api/health" || return 1
    
    # Check Frontend
    check_service_health "Frontend" 3000 "/" || return 1
    
    log_success "✅ Core Only Deployment: PASS"
    
    cleanup
    return 0
}

# Test Premium Deployment
test_premium_deployment() {
    log_info "=============================================="
    log_info "TEST 2: Core + Premium Deployment"
    log_info "=============================================="
    
    cleanup
    
    # Check if Premium submodule is available
    if [ ! -d "packages/premium/.git" ]; then
        log_warning "Premium submodule not initialized. Initializing..."
        git submodule update --init packages/premium || {
            log_error "Failed to initialize Premium submodule!"
            return 1
        }
    fi
    
    log_info "Starting Core + Premium services..."
    docker-compose -f docker-compose.yml -f docker-compose.premium.yml up -d
    
    log_info "Waiting for services to start..."
    sleep 15
    
    # Check Core services
    docker-compose -f docker-compose.yml -f docker-compose.premium.yml exec -T postgres pg_isready -U examcraft || {
        log_error "PostgreSQL is not ready!"
        return 1
    }
    log_success "PostgreSQL is ready!"
    
    docker-compose -f docker-compose.yml -f docker-compose.premium.yml exec -T redis redis-cli ping | grep -q PONG || {
        log_error "Redis is not responding!"
        return 1
    }
    log_success "Redis is ready!"
    
    # Check Premium services
    log_info "Checking ChromaDB..."
    check_service_health "ChromaDB" 8001 "/api/v1/heartbeat" || return 1
    
    log_info "Checking Qdrant..."
    check_service_health "Qdrant" 6333 "/healthz" || return 1
    
    # Check Backend with Premium features
    check_service_health "Backend (Premium)" 8000 "/api/health" || return 1
    
    # Check Frontend
    check_service_health "Frontend" 3000 "/" || return 1
    
    log_success "✅ Core + Premium Deployment: PASS"
    
    cleanup
    return 0
}

# Test Enterprise Deployment
test_enterprise_deployment() {
    log_info "=============================================="
    log_info "TEST 3: Full Enterprise Deployment"
    log_info "=============================================="
    
    cleanup
    
    # Check if submodules are available
    if [ ! -d "packages/premium/.git" ] || [ ! -d "packages/enterprise/.git" ]; then
        log_warning "Submodules not initialized. Initializing..."
        git submodule update --init --recursive || {
            log_error "Failed to initialize submodules!"
            return 1
        }
    fi
    
    log_info "Starting all services (Core + Premium + Enterprise)..."
    docker-compose -f docker-compose.yml \
                   -f docker-compose.premium.yml \
                   -f docker-compose.enterprise.yml \
                   up -d
    
    log_info "Waiting for services to start..."
    sleep 20
    
    # Check all services
    docker-compose -f docker-compose.yml \
                   -f docker-compose.premium.yml \
                   -f docker-compose.enterprise.yml \
                   exec -T postgres pg_isready -U examcraft || {
        log_error "PostgreSQL is not ready!"
        return 1
    }
    log_success "PostgreSQL is ready!"
    
    docker-compose -f docker-compose.yml \
                   -f docker-compose.premium.yml \
                   -f docker-compose.enterprise.yml \
                   exec -T redis redis-cli ping | grep -q PONG || {
        log_error "Redis is not responding!"
        return 1
    }
    log_success "Redis is ready!"
    
    check_service_health "ChromaDB" 8001 "/api/v1/heartbeat" || return 1
    check_service_health "Qdrant" 6333 "/healthz" || return 1
    check_service_health "Backend (Enterprise)" 8000 "/api/health" || return 1
    check_service_health "Frontend" 3000 "/" || return 1
    
    log_success "✅ Full Enterprise Deployment: PASS"
    
    cleanup
    return 0
}

# Main execution
main() {
    log_info "ExamCraft Deployment Test Suite"
    log_info "================================"
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
    
    if test_premium_deployment; then
        echo ""
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "Premium deployment test failed!"
    fi
    
    if test_enterprise_deployment; then
        echo ""
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "Enterprise deployment test failed!"
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

