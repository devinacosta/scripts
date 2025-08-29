#!/bin/bash

# Test runner script for escmd
# Provides convenient commands for running different types of tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment should be used
if [[ -n "$VIRTUAL_ENV" ]]; then
    print_status "Using virtual environment: $VIRTUAL_ENV"
else
    print_warning "No virtual environment detected. Consider using a virtual environment."
fi

# Install test dependencies if needed
install_deps() {
    print_status "Installing test dependencies..."
    pip install -r requirements-test.txt
    print_success "Test dependencies installed"
}

# Run all tests
run_all() {
    print_status "Running all tests..."
    pytest
    print_success "All tests completed"
}

# Run only unit tests
run_unit() {
    print_status "Running unit tests..."
    pytest tests/unit/ -v
    print_success "Unit tests completed"
}

# Run only integration tests
run_integration() {
    print_status "Running integration tests..."
    pytest tests/integration/ -v
    print_success "Integration tests completed"
}

# Run tests with coverage
run_coverage() {
    print_status "Running tests with coverage report..."
    pytest --cov=. --cov-report=term-missing --cov-report=html
    print_success "Coverage report generated in htmlcov/"
}

# Run specific test file
run_specific() {
    if [[ -z "$1" ]]; then
        print_error "Please specify a test file or pattern"
        exit 1
    fi
    print_status "Running specific test: $1"
    pytest "$1" -v
    print_success "Specific test completed"
}

# Clean test artifacts
clean() {
    print_status "Cleaning test artifacts..."
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    print_success "Test artifacts cleaned"
}

# Show help
show_help() {
    echo "Test runner for escmd"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install      Install test dependencies"
    echo "  all          Run all tests (default)"
    echo "  unit         Run only unit tests"
    echo "  integration  Run only integration tests"
    echo "  coverage     Run tests with coverage report"
    echo "  specific     Run specific test file (requires argument)"
    echo "  clean        Clean test artifacts"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 unit                              # Run unit tests only"
    echo "  $0 specific tests/unit/test_health_handler.py  # Run specific test"
    echo "  $0 coverage                          # Run with coverage"
}

# Main script logic
case "${1:-all}" in
    "install")
        install_deps
        ;;
    "all")
        run_all
        ;;
    "unit")
        run_unit
        ;;
    "integration")
        run_integration
        ;;
    "coverage")
        run_coverage
        ;;
    "specific")
        run_specific "$2"
        ;;
    "clean")
        clean
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
