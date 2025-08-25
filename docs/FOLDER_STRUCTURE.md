# AI Agent Project Structure

This document describes the reorganized folder structure of the AI Agent project.

## Folder Structure

```
ai-agent/
├── backend/                    # Backend classes and core logic
│   ├── intelligent_chat/       # Intelligent chat UI components
│   ├── __init__.py
│   ├── context_retrieval_engine.py
│   ├── conversation_history_store.py
│   ├── customer_db_tool.py
│   ├── database.py
│   ├── db_utils.py
│   ├── enhanced_customer_db_tool.py
│   ├── enhanced_rag_orchestrator.py
│   ├── gdpr_compliance.py
│   ├── memory_config.py
│   ├── memory_error_handler.py
│   ├── memory_layer_manager.py
│   ├── memory_migration.py
│   ├── memory_models.py
│   ├── memory_schema_update.py
│   ├── models.py
│   ├── privacy_utils.py
│   ├── security_integration.py
│   ├── security_manager.py
│   ├── security_migration.py
│   ├── support_knowledge_db_tool.py
│   ├── tick_api.py
│   ├── ticking_service.py
│   ├── ticking_system.py
│   ├── tool_usage_analytics.py
│   └── tools.py
├── tests/                      # All test files
│   ├── __init__.py
│   ├── simple_test.py
│   ├── test_*.py               # All test files
│   └── ...
├── examples/                   # Demo and example files
│   ├── __init__.py
│   ├── conversation_history_integration_example.py
│   ├── demo_enhanced_rag_integration.py
│   ├── demo_multi_tool.py
│   ├── example_memory_usage.py
│   ├── memory_config_usage_example.py
│   ├── memory_error_handler_integration_example.py
│   ├── performance_optimization_demo.py
│   ├── response_improvement_demo.py
│   ├── security_example.py
│   ├── tick_demo.py
│   ├── tool_analytics_integration_example.py
│   └── use_rag_system.py
├── scripts/                    # Utility and setup scripts
│   ├── __init__.py
│   ├── add_missing_intents.py
│   ├── create_customer_knowledge_base.py
│   ├── database_init.py
│   ├── fix_user_sessions_schema.py
│   ├── init_database.py
│   ├── init_ticking_system.py
│   ├── inspect_customer_support_knowledge_base.py
│   ├── migrate_data.py
│   ├── migrate_postgres_schema.py
│   ├── run_memory_migration.py
│   ├── run_migration.py
│   ├── setup_database.py
│   ├── update_support_knowledge.py
│   └── verify_memory_schema.py
├── docs/                       # Documentation files
│   ├── COMPREHENSIVE_TESTING_COMPLETE.md
│   ├── CONTEXT_RETRIEVER_IMPLEMENTATION.md
│   ├── CONTEXT_WINDOW_MANAGEMENT_IMPLEMENTATION.md
│   ├── CONVERSATION_HISTORY_STORE_GUIDE.md
│   ├── DATABASE_SETUP_GUIDE.md
│   ├── FOLDER_STRUCTURE.md
│   ├── INTEGRATION_TESTS_SUMMARY.md
│   ├── INTELLIGENT_CHAT_API_DOCUMENTATION.md
│   ├── INTELLIGENT_CHAT_README.md
│   ├── MEMORY_CONFIG_GUIDE.md
│   ├── MEMORY_ERROR_HANDLING_GUIDE.md
│   ├── MULTI_TOOL_SYSTEM_GUIDE.md
│   ├── PERFORMANCE_OPTIMIZATION_SUMMARY.md
│   ├── RESPONSE_IMPROVEMENT_SUMMARY.md
│   ├── SECURITY_PRIVACY_GUIDE.md
│   ├── USER_EXPERIENCE_TESTS_SUMMARY.md
│   └── VISUAL_FEEDBACK_SYSTEM.md
├── frontend/                   # Frontend files (HTML, CSS, JS)
├── config/                     # Configuration files
├── data/                       # Data files
├── data_lake/                  # Data lake files
├── README.md                   # Main project README
├── main.py                     # Main application entry point
└── ...                         # Other project files
```

## Import Changes

All import statements have been updated to use the new structure:

### In main.py:
- `from tools import ...` → `from backend.tools import ...`
- `from models import ...` → `from backend.models import ...`
- `from database import ...` → `from backend.database import ...`
- etc.

### Within backend modules:
- `from models import ...` → `from .models import ...`
- `from database import ...` → `from .database import ...`
- `from tools import ...` → `from .tools import ...`
- etc.

### Within intelligent_chat modules:
- `from intelligent_chat.models import ...` → `from .models import ...`
- Backend references use `from ..database import ...`

## Benefits of This Structure

1. **Clear Separation**: Backend logic is separated from tests, examples, and scripts
2. **Better Organization**: Related files are grouped together
3. **Easier Navigation**: Developers can quickly find what they need
4. **Maintainability**: Cleaner structure makes the codebase easier to maintain
5. **Scalability**: Structure supports future growth and additional modules

## Running Tests

Tests can now be run from the project root:
```bash
python -m pytest tests/
```

## Running Examples

Examples can be run from the project root:
```bash
python -m examples.demo_multi_tool
```

## Running Scripts

Scripts can be run from the project root:
```bash
python -m scripts.setup_database
```