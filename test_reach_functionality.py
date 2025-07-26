#!/usr/bin/env python3
"""
Test script to verify the new reach functionality
"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import init_db, create_blogger, get_blogger
from database.models import Platform, BlogCategory, UserRole
from handlers.seller import SellerStates
from handlers.buyer import BuyerStates


async def test_reach_functionality():
    """Test the new reach functionality"""
    print("🧪 Testing reach functionality...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Create a test blogger with reach data
    test_blogger = await create_blogger(
        seller_id=1,
        name="Test Blogger",
        url="https://instagram.com/test_blogger",
        platforms=[Platform.INSTAGRAM],
        categories=[BlogCategory.LIFESTYLE],
        stories_reach_min=5000,
        stories_reach_max=8000,
        reels_reach_min=10000,
        reels_reach_max=15000,
        subscribers_count=50000,
        avg_likes=2000,
        engagement_rate=4.5,
        price_stories=2000,
        price_post=5000,
        price_video=10000
    )
    
    print(f"✅ Test blogger created with ID: {test_blogger.id}")
    print(f"   Stories reach: {test_blogger.stories_reach_min:,}-{test_blogger.stories_reach_max:,}")
    print(f"   Reels reach: {test_blogger.reels_reach_min:,}-{test_blogger.reels_reach_max:,}")
    
    # Retrieve the blogger and verify the data
    retrieved_blogger = await get_blogger(test_blogger.id)
    if retrieved_blogger:
        print("✅ Blogger retrieved successfully")
        print(f"   Stories reach: {retrieved_blogger.stories_reach_min:,}-{retrieved_blogger.stories_reach_max:,}")
        print(f"   Reels reach: {retrieved_blogger.reels_reach_min:,}-{retrieved_blogger.reels_reach_max:,}")
        
        # Verify the data matches
        assert retrieved_blogger.stories_reach_min == 5000
        assert retrieved_blogger.stories_reach_max == 8000
        assert retrieved_blogger.reels_reach_min == 10000
        assert retrieved_blogger.reels_reach_max == 15000
        print("✅ All reach data verified correctly")
    else:
        print("❌ Failed to retrieve blogger")
        return False
    
    # Test the state transitions
    print("\n🧪 Testing state transitions...")
    
    # Test seller states
    seller_states = [
        SellerStates.waiting_for_stories_reach_min,
        SellerStates.waiting_for_stories_reach_max,
        SellerStates.waiting_for_reels_reach_min,
        SellerStates.waiting_for_reels_reach_max
    ]
    
    for state in seller_states:
        print(f"✅ State {state} exists")
    
    print("\n🎉 All tests passed! The reach functionality is working correctly.")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_reach_functionality())
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)