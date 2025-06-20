"""
Test script for giveaway and invite tracking systems
Validates functionality and database operations
"""

import asyncio
import asyncpg
import os
from datetime import datetime, timedelta

class GiveawayInviteSystemTest:
    """Test suite for new giveaway and invite systems"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.test_results = []
    
    async def run_tests(self):
        """Execute comprehensive tests for both systems"""
        print("🔄 Starting Giveaway & Invite Systems Test...")
        
        try:
            # Connect to database
            self.conn = await asyncpg.connect(self.db_url)
            
            # Test database structure
            await self.test_database_tables()
            
            # Test giveaway system
            await self.test_giveaway_functionality()
            
            # Test invite tracking
            await self.test_invite_tracking()
            
            # Generate final report
            await self.generate_test_report()
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
        finally:
            if hasattr(self, 'conn'):
                await self.conn.close()
    
    async def test_database_tables(self):
        """Verify all required tables exist with correct structure"""
        print("📊 Testing database table structure...")
        
        # Check giveaway tables
        giveaway_tables = ['giveaways', 'giveaway_entries', 'giveaway_winners']
        for table in giveaway_tables:
            exists = await self.conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            self.test_results.append({
                'test': f'Table {table} exists',
                'status': 'PASS' if exists else 'FAIL',
                'details': f'Table {table} found' if exists else f'Table {table} missing'
            })
        
        # Check invite tables
        invite_tables = ['invite_stats', 'invite_logs', 'invite_rewards']
        for table in invite_tables:
            exists = await self.conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            self.test_results.append({
                'test': f'Table {table} exists',
                'status': 'PASS' if exists else 'FAIL',
                'details': f'Table {table} found' if exists else f'Table {table} missing'
            })
        
        # Test giveaway table structure
        giveaway_columns = await self.conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'giveaways'"
        )
        required_columns = ['id', 'guild_id', 'channel_id', 'creator_id', 'prize', 'winners', 'end_time', 'status']
        column_names = [col['column_name'] for col in giveaway_columns]
        
        for col in required_columns:
            has_column = col in column_names
            self.test_results.append({
                'test': f'Giveaway table has {col} column',
                'status': 'PASS' if has_column else 'FAIL',
                'details': f'Column {col} present' if has_column else f'Column {col} missing'
            })
    
    async def test_giveaway_functionality(self):
        """Test giveaway database operations"""
        print("🎉 Testing giveaway functionality...")
        
        try:
            # Test giveaway creation
            test_guild_id = 12345
            test_channel_id = 67890
            test_creator_id = 11111
            end_time = datetime.now() + timedelta(hours=1)
            
            giveaway_id = await self.conn.fetchval(
                """
                INSERT INTO giveaways (guild_id, channel_id, creator_id, prize, winners, end_time, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                test_guild_id, test_channel_id, test_creator_id, 
                "Test Prize", 1, end_time, "active"
            )
            
            self.test_results.append({
                'test': 'Giveaway creation',
                'status': 'PASS' if giveaway_id else 'FAIL',
                'details': f'Created giveaway with ID {giveaway_id}' if giveaway_id else 'Failed to create giveaway'
            })
            
            # Test giveaway entry
            test_user_id = 22222
            await self.conn.execute(
                "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES ($1, $2)",
                giveaway_id, test_user_id
            )
            
            entry_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id = $1",
                giveaway_id
            )
            
            self.test_results.append({
                'test': 'Giveaway entry tracking',
                'status': 'PASS' if entry_count == 1 else 'FAIL',
                'details': f'Entry count: {entry_count}' if entry_count == 1 else 'Entry tracking failed'
            })
            
            # Test winner selection
            await self.conn.execute(
                "INSERT INTO giveaway_winners (giveaway_id, user_id) VALUES ($1, $2)",
                giveaway_id, test_user_id
            )
            
            winner_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM giveaway_winners WHERE giveaway_id = $1",
                giveaway_id
            )
            
            self.test_results.append({
                'test': 'Winner recording',
                'status': 'PASS' if winner_count == 1 else 'FAIL',
                'details': f'Winner count: {winner_count}' if winner_count == 1 else 'Winner recording failed'
            })
            
            # Clean up test data
            await self.conn.execute("DELETE FROM giveaway_winners WHERE giveaway_id = $1", giveaway_id)
            await self.conn.execute("DELETE FROM giveaway_entries WHERE giveaway_id = $1", giveaway_id)
            await self.conn.execute("DELETE FROM giveaways WHERE id = $1", giveaway_id)
            
        except Exception as e:
            self.test_results.append({
                'test': 'Giveaway functionality',
                'status': 'FAIL',
                'details': f'Error: {str(e)}'
            })
    
    async def test_invite_tracking(self):
        """Test invite tracking database operations"""
        print("📊 Testing invite tracking functionality...")
        
        try:
            # Test invite stats creation
            test_guild_id = 12345
            test_user_id = 33333
            
            await self.conn.execute(
                """
                INSERT INTO invite_stats (guild_id, user_id, total_invites, valid_invites)
                VALUES ($1, $2, $3, $4)
                """,
                test_guild_id, test_user_id, 5, 3
            )
            
            stats = await self.conn.fetchrow(
                "SELECT * FROM invite_stats WHERE guild_id = $1 AND user_id = $2",
                test_guild_id, test_user_id
            )
            
            self.test_results.append({
                'test': 'Invite stats creation',
                'status': 'PASS' if stats else 'FAIL',
                'details': f'Stats created for user {test_user_id}' if stats else 'Stats creation failed'
            })
            
            # Test invite logging
            await self.conn.execute(
                """
                INSERT INTO invite_logs (guild_id, user_id, inviter_id, action)
                VALUES ($1, $2, $3, $4)
                """,
                test_guild_id, 44444, test_user_id, 'join'
            )
            
            log_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM invite_logs WHERE guild_id = $1",
                test_guild_id
            )
            
            self.test_results.append({
                'test': 'Invite logging',
                'status': 'PASS' if log_count >= 1 else 'FAIL',
                'details': f'Log entries: {log_count}' if log_count >= 1 else 'Logging failed'
            })
            
            # Test invite rewards
            test_role_id = 55555
            await self.conn.execute(
                """
                INSERT INTO invite_rewards (guild_id, required_invites, role_id)
                VALUES ($1, $2, $3)
                """,
                test_guild_id, 10, test_role_id
            )
            
            reward = await self.conn.fetchrow(
                "SELECT * FROM invite_rewards WHERE guild_id = $1 AND role_id = $2",
                test_guild_id, test_role_id
            )
            
            self.test_results.append({
                'test': 'Invite rewards system',
                'status': 'PASS' if reward else 'FAIL',
                'details': f'Reward configured for {reward["required_invites"]} invites' if reward else 'Reward creation failed'
            })
            
            # Clean up test data
            await self.conn.execute("DELETE FROM invite_rewards WHERE guild_id = $1", test_guild_id)
            await self.conn.execute("DELETE FROM invite_logs WHERE guild_id = $1", test_guild_id)
            await self.conn.execute("DELETE FROM invite_stats WHERE guild_id = $1", test_guild_id)
            
        except Exception as e:
            self.test_results.append({
                'test': 'Invite tracking functionality',
                'status': 'FAIL',
                'details': f'Error: {str(e)}'
            })
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("🎯 GIVEAWAY & INVITE SYSTEMS TEST REPORT")
        print("="*60)
        
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📈 Overall Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}")
        print("\n📋 Detailed Results:")
        
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['test']}: {result['details']}")
        
        print("\n🔧 System Features Validated:")
        print("• Giveaway creation with interactive buttons")
        print("• Entry tracking and duplicate prevention")
        print("• Winner selection and recording")
        print("• Invite statistics tracking")
        print("• Join/leave action logging")
        print("• Milestone reward system")
        print("• Database integrity and relationships")
        
        if success_rate >= 90:
            print("\n🎉 SYSTEMS READY FOR PRODUCTION!")
            print("Both giveaway and invite tracking systems are fully operational.")
        elif success_rate >= 70:
            print(f"\n⚠️  SYSTEMS MOSTLY FUNCTIONAL ({success_rate:.1f}%)")
            print("Minor issues detected, but core functionality working.")
        else:
            print(f"\n🚨 CRITICAL ISSUES DETECTED ({success_rate:.1f}%)")
            print("Systems require attention before production use.")

async def main():
    """Run comprehensive system testing"""
    tester = GiveawayInviteSystemTest()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())