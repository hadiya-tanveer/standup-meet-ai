.PHONY: run clean

# Run the orchestrator script
run:
	python3 -m test.test_orchestrator

# Clean test/output and all __pycache__ folders
clean:
	@echo "Cleaning test/output and __pycache__ folders..."
	@rm -rf test/output/*
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Clean complete."
	@clear
