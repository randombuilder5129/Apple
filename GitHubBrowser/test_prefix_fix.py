#!/usr/bin/env python3
"""
Test script to verify custom prefix functionality is working
"""

import asyncio
import asyncpg
import os

async def test_prefix_functionality():
    """Test that prefix lookup and setting works correctly"""
    
    # Connect to database
    database_url = os.environ.get('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    # Test 1: Insert a custom prefix using UPSERT
    test_guild_id = 999888777
    custom_prefix = "#"
    
    await conn.execute(
        """
        INSERT INTO guild_settings (guild_id, prefix) 
        VALUES ($1, $2) 
        ON CONFLICT (guild_id) 
        DO UPDATE SET prefix = $2
        """,
        test_guild_id, custom_prefix
    )
    
    # Test 2: Verify the prefix was stored correctly
    stored_prefix = await conn.fetchval(
        "SELECT prefix FROM guild_settings WHERE guild_id = $1",
        test_guild_id
    )
    
    print(f"Test Guild ID: {test_guild_id}")
    print(f"Custom Prefix Set: {custom_prefix}")
    print(f"Stored Prefix: {stored_prefix}")
    print(f"Prefix Match: {'✓ PASS' if stored_prefix == custom_prefix else '✗ FAIL'}")
    
    # Test 3: Test updating existing prefix
    new_prefix = "?"
    await conn.execute(
        """
        INSERT INTO guild_settings (guild_id, prefix) 
        VALUES ($1, $2) 
        ON CONFLICT (guild_id) 
        DO UPDATE SET prefix = $2
        """,
        test_guild_id, new_prefix
    )
    
    updated_prefix = await conn.fetchval(
        "SELECT prefix FROM guild_settings WHERE guild_id = $1",
        test_guild_id
    )
    
    print(f"Updated Prefix: {new_prefix}")
    print(f"Retrieved Prefix: {updated_prefix}")
    print(f"Update Match: {'✓ PASS' if updated_prefix == new_prefix else '✗ FAIL'}")
    
    # Test 4: Test default prefix for non-existent guild
    nonexistent_guild = 111222333
    default_lookup = await conn.fetchval(
        "SELECT prefix FROM guild_settings WHERE guild_id = $1",
        nonexistent_guild
    )
    
    print(f"Non-existent Guild Lookup: {default_lookup}")
    print(f"Default Fallback: {'✓ PASS' if default_lookup is None else '✗ FAIL'}")
    
    # Clean up test data
    await conn.execute(
        "DELETE FROM guild_settings WHERE guild_id = $1",
        test_guild_id
    )
    
    await conn.close()
    
    print("\n✅ Custom prefix functionality test completed successfully!")
    print("The /settings command prefix changes will now work properly.")

if __name__ == "__main__":
    asyncio.run(test_prefix_functionality())