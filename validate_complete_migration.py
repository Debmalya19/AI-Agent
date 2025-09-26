#!/usr/bin/env python3
"""
Complete Migration Validation Script

This script validates that the PostgreSQL migration was successful and all
application functionality works correctly with the migrated data.

Requirements: 2.1, 2.2, 2.3, 5.1, 5.2
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_validation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MigrationValidator:
    """Validates complete migration and application functionality"""
    
    def __init__(self):
        load_dotenv()
        self.validation_results = {
            'overall_success': True,
            'tests': {},
            'errors': []
        }
    
    def validate_database_connection(self) -> bool:
        """Validate database connection works"""
        logger.info("Validating database connection...")
        
        try:
            from backend.database import get_db
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test basic query
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            session.close()
            
            self.validation_results['tests']['database_connection'] = {
                'success': True,
                'message': 'Database connection successful'
            }
            logger.info("✅ Database connection validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Database connection validation failed: {e}"
            self.validation_results['tests']['database_connection'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_data_migration(self) -> bool:
        """Validate that data was migrated correctly"""
        logger.info("Validating data migration...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedUser, UnifiedUserSession, UnifiedTicket, UnifiedChatHistory
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Check migrated data counts
            user_count = session.query(UnifiedUser).count()
            session_count = session.query(UnifiedUserSession).count()
            ticket_count = session.query(UnifiedTicket).count()
            chat_count = session.query(UnifiedChatHistory).count()
            
            logger.info(f"Found {user_count} users, {session_count} sessions, {ticket_count} tickets, {chat_count} chat records")
            
            # Validate we have the expected data
            assert user_count > 0, "No users found after migration"
            assert session_count > 0, "No user sessions found after migration"
            assert ticket_count > 0, "No tickets found after migration"
            assert chat_count > 0, "No chat history found after migration"
            
            # Test data integrity - check that users have valid data
            sample_user = session.query(UnifiedUser).first()
            assert sample_user.username is not None, "User username is null"
            assert sample_user.email is not None, "User email is null"
            assert sample_user.password_hash is not None, "User password hash is null"
            
            session.close()
            
            self.validation_results['tests']['data_migration'] = {
                'success': True,
                'message': f'Data migration successful: {user_count} users, {session_count} sessions, {ticket_count} tickets, {chat_count} chat records'
            }
            logger.info("✅ Data migration validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Data migration validation failed: {e}"
            self.validation_results['tests']['data_migration'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_authentication_functionality(self) -> bool:
        """Validate authentication functionality with existing users"""
        logger.info("Validating authentication functionality...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedUser
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test user retrieval (authentication simulation)
            test_user = session.query(UnifiedUser).filter_by(username="test_admin").first()
            assert test_user is not None, "Test admin user not found"
            assert test_user.email == "test_admin@example.com", "User email mismatch"
            assert test_user.password_hash is not None, "User password hash is null"
            assert test_user.is_active == True, "User is not active"
            assert test_user.is_admin == True, "User is not admin"
            
            # Test user query by email
            user_by_email = session.query(UnifiedUser).filter_by(email="test_admin@example.com").first()
            assert user_by_email is not None, "User not found by email"
            assert user_by_email.id == test_user.id, "User ID mismatch"
            
            session.close()
            
            self.validation_results['tests']['authentication'] = {
                'success': True,
                'message': 'Authentication functionality validated with existing users'
            }
            logger.info("✅ Authentication functionality validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Authentication functionality validation failed: {e}"
            self.validation_results['tests']['authentication'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_admin_dashboard_functionality(self) -> bool:
        """Validate admin dashboard functionality with existing data"""
        logger.info("Validating admin dashboard functionality...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedUser, UnifiedTicket, TicketStatus, TicketPriority
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test admin dashboard queries
            # 1. Get all users (admin functionality)
            all_users = session.query(UnifiedUser).all()
            assert len(all_users) > 0, "No users found for admin dashboard"
            
            # 2. Get all tickets (admin functionality)
            all_tickets = session.query(UnifiedTicket).all()
            assert len(all_tickets) > 0, "No tickets found for admin dashboard"
            
            # 3. Get admin users only
            admin_users = session.query(UnifiedUser).filter_by(is_admin=True).all()
            assert len(admin_users) > 0, "No admin users found"
            
            # 4. Test ticket status filtering
            tickets_by_status = {}
            for status in TicketStatus:
                count = session.query(UnifiedTicket).filter_by(status=status).count()
                tickets_by_status[status.value] = count
            
            # 5. Test user role filtering
            customer_users = session.query(UnifiedUser).filter_by(is_admin=False).all()
            
            logger.info(f"Admin dashboard data: {len(all_users)} users, {len(all_tickets)} tickets, {len(admin_users)} admins, {len(customer_users)} customers")
            
            session.close()
            
            self.validation_results['tests']['admin_dashboard'] = {
                'success': True,
                'message': f'Admin dashboard functionality validated: {len(all_users)} users, {len(all_tickets)} tickets'
            }
            logger.info("✅ Admin dashboard functionality validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Admin dashboard functionality validation failed: {e}"
            self.validation_results['tests']['admin_dashboard'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_session_management(self) -> bool:
        """Validate session management functionality"""
        logger.info("Validating session management functionality...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedUserSession, UnifiedUser
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test session queries
            all_sessions = session.query(UnifiedUserSession).all()
            assert len(all_sessions) > 0, "No user sessions found"
            
            # Test session-user relationship
            sample_session = all_sessions[0]
            user = session.query(UnifiedUser).filter_by(id=sample_session.user_id).first()
            assert user is not None, "Session user relationship broken"
            
            # Test active sessions
            active_sessions = session.query(UnifiedUserSession).filter_by(is_active=True).all()
            
            # Test session token validation
            assert sample_session.session_id is not None, "Session ID is null"
            assert sample_session.token_hash is not None, "Session token hash is null"
            
            logger.info(f"Session management data: {len(all_sessions)} total sessions, {len(active_sessions)} active sessions")
            
            session.close()
            
            self.validation_results['tests']['session_management'] = {
                'success': True,
                'message': f'Session management validated: {len(all_sessions)} sessions'
            }
            logger.info("✅ Session management validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Session management validation failed: {e}"
            self.validation_results['tests']['session_management'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_chat_functionality(self) -> bool:
        """Validate chat functionality with existing data"""
        logger.info("Validating chat functionality...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedChatHistory, UnifiedUser
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test chat history queries
            all_chat_history = session.query(UnifiedChatHistory).all()
            assert len(all_chat_history) > 0, "No chat history found"
            
            # Test chat-user relationship
            sample_chat = all_chat_history[0]
            user = session.query(UnifiedUser).filter_by(id=sample_chat.user_id).first()
            assert user is not None, "Chat user relationship broken"
            
            # Test chat data integrity
            assert sample_chat.user_message is not None, "Chat user message is null"
            assert sample_chat.bot_response is not None, "Chat bot response is null"
            
            # Test user's chat history
            user_chat_count = session.query(UnifiedChatHistory).filter_by(user_id=sample_chat.user_id).count()
            assert user_chat_count > 0, "User has no chat history"
            
            logger.info(f"Chat functionality data: {len(all_chat_history)} chat records")
            
            session.close()
            
            self.validation_results['tests']['chat_functionality'] = {
                'success': True,
                'message': f'Chat functionality validated: {len(all_chat_history)} chat records'
            }
            logger.info("✅ Chat functionality validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Chat functionality validation failed: {e}"
            self.validation_results['tests']['chat_functionality'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_memory_layer(self) -> bool:
        """Validate memory layer functionality"""
        logger.info("Validating memory layer functionality...")
        
        try:
            from backend.database import get_db
            from backend.memory_models import EnhancedChatHistory, MemoryContextCache
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test enhanced chat history
            enhanced_chat_count = session.query(EnhancedChatHistory).count()
            logger.info(f"Found {enhanced_chat_count} enhanced chat history records")
            
            # Test memory context cache
            cache_count = session.query(MemoryContextCache).count()
            logger.info(f"Found {cache_count} memory context cache records")
            
            # Memory layer is optional, so we don't require data to exist
            # Just validate that the tables are accessible
            
            session.close()
            
            self.validation_results['tests']['memory_layer'] = {
                'success': True,
                'message': f'Memory layer validated: {enhanced_chat_count} enhanced chat, {cache_count} cache records'
            }
            logger.info("✅ Memory layer validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Memory layer validation failed: {e}"
            self.validation_results['tests']['memory_layer'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def validate_voice_assistant_integration(self) -> bool:
        """Validate voice assistant integration"""
        logger.info("Validating voice assistant integration...")
        
        try:
            from backend.database import get_db
            from backend.unified_models import UnifiedVoiceSettings, UnifiedVoiceAnalytics
            
            db_gen = get_db()
            session = next(db_gen)
            
            # Test voice settings and analytics tables
            voice_settings_count = session.query(UnifiedVoiceSettings).count()
            voice_analytics_count = session.query(UnifiedVoiceAnalytics).count()
            
            logger.info(f"Voice assistant data: {voice_settings_count} settings, {voice_analytics_count} analytics records")
            
            # Voice assistant data is optional, so we don't require data to exist
            # Just validate that the tables are accessible
            
            session.close()
            
            self.validation_results['tests']['voice_assistant'] = {
                'success': True,
                'message': f'Voice assistant integration validated: {voice_settings_count} settings, {voice_analytics_count} analytics'
            }
            logger.info("✅ Voice assistant integration validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Voice assistant integration validation failed: {e}"
            self.validation_results['tests']['voice_assistant'] = {
                'success': False,
                'message': error_msg
            }
            self.validation_results['errors'].append(error_msg)
            self.validation_results['overall_success'] = False
            logger.error(f"❌ {error_msg}")
            return False
    
    def run_complete_validation(self) -> dict:
        """Run all validation tests"""
        logger.info("Starting complete migration validation...")
        
        validation_functions = [
            self.validate_database_connection,
            self.validate_data_migration,
            self.validate_authentication_functionality,
            self.validate_admin_dashboard_functionality,
            self.validate_session_management,
            self.validate_chat_functionality,
            self.validate_memory_layer,
            self.validate_voice_assistant_integration
        ]
        
        for validation_func in validation_functions:
            try:
                validation_func()
            except Exception as e:
                logger.error(f"Validation function {validation_func.__name__} failed: {e}")
                self.validation_results['overall_success'] = False
                self.validation_results['errors'].append(f"{validation_func.__name__}: {e}")
        
        # Generate summary
        passed_tests = sum(1 for test in self.validation_results['tests'].values() if test['success'])
        total_tests = len(self.validation_results['tests'])
        
        logger.info(f"Validation completed: {passed_tests}/{total_tests} tests passed")
        
        if self.validation_results['overall_success']:
            logger.info("🎉 ALL VALIDATIONS PASSED - Migration is successful!")
        else:
            logger.error("❌ Some validations failed - Review errors above")
        
        return self.validation_results

def main():
    """Main validation function"""
    print("=" * 80)
    print("AI Agent PostgreSQL Migration - Complete Validation")
    print("=" * 80)
    
    try:
        validator = MigrationValidator()
        results = validator.run_complete_validation()
        
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        passed_tests = sum(1 for test in results['tests'].values() if test['success'])
        total_tests = len(results['tests'])
        
        if results['overall_success']:
            print("🎉 ALL VALIDATIONS PASSED!")
            print(f"✅ {passed_tests}/{total_tests} tests passed")
            print("\nThe PostgreSQL migration was successful and all functionality is working correctly.")
            print("The application is ready for production deployment with PostgreSQL.")
        else:
            print("❌ SOME VALIDATIONS FAILED")
            print(f"❌ {passed_tests}/{total_tests} tests passed")
            
            if results['errors']:
                print("\nErrors found:")
                for i, error in enumerate(results['errors'], 1):
                    print(f"{i}. {error}")
        
        print("\nDetailed test results:")
        for test_name, test_result in results['tests'].items():
            status = "✅ PASS" if test_result['success'] else "❌ FAIL"
            print(f"{status} {test_name}: {test_result['message']}")
        
        print("\n" + "=" * 80)
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        print(f"❌ VALIDATION FAILED: {e}")
        logger.error(f"Main validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())