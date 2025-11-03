#!/usr/bin/env python3
"""
Add test comments with likes to demonstrate sorting functionality.
This script adds dummy comments to blog/smars-q.html with varying like counts.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select
from app.models import Comment, User, CommentLike

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

DATABASE_URL = os.getenv('DATABASE_URL')

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# URL for the test page
TEST_URL = "blog/smars-q.html"

# Test comments with different characteristics
TEST_COMMENTS = [
    {
        "content": "This is a very popular comment that should appear first when sorted by popularity!",
        "likes": 15,
        "days_ago": 5
    },
    {
        "content": "This is the most recent comment - should appear first in recent view!",
        "likes": 2,
        "days_ago": 0
    },
    {
        "content": "This is a moderately popular comment from a few days ago.",
        "likes": 8,
        "days_ago": 3
    },
    {
        "content": "Old comment with few likes - should appear last in both views.",
        "likes": 1,
        "days_ago": 10
    },
    {
        "content": "Another recent comment to test sorting by date.",
        "likes": 3,
        "days_ago": 1
    },
    {
        "content": "Mid-popularity comment to fill out the list.",
        "likes": 5,
        "days_ago": 7
    },
]


def add_test_data():
    """Add test comments with varying like counts"""

    with Session(engine) as session:
        # Get multiple users to distribute likes
        users = session.exec(select(User)).all()

        if not users:
            print("Error: No users found in database. Please create a user first.")
            return

        if len(users) < 2:
            print("Warning: Only one user found. Likes will be limited.")

        primary_user = users[0]
        print(f"Adding test comments as user: {primary_user.username} (ID: {primary_user.id})")
        print(f"Found {len(users)} users total for distributing likes")
        print(f"URL: {TEST_URL}")
        print("-" * 60)

        # Add each test comment
        for i, test_data in enumerate(TEST_COMMENTS, 1):
            # Create the comment
            created_at = datetime.now() - timedelta(days=test_data["days_ago"])

            comment = Comment(
                url=TEST_URL,
                user_id=primary_user.id,
                content=test_data["content"],
                like_count=test_data["likes"],
                created_at=created_at
            )
            session.add(comment)
            session.flush()  # Get the comment ID

            print(f"\n{i}. Added comment (ID: {comment.id}):")
            print(f"   Content: {test_data['content'][:50]}...")
            print(f"   Created: {test_data['days_ago']} days ago")
            print(f"   Will have {test_data['likes']} likes")

            # Add likes for this comment, cycling through available users
            likes_to_add = min(test_data["likes"], len(users))
            for j in range(likes_to_add):
                like = CommentLike(
                    comment_id=comment.id,
                    user_id=users[j % len(users)].id,  # Cycle through users
                    created_at=created_at + timedelta(minutes=j)
                )
                session.add(like)

            if test_data["likes"] > len(users):
                print(f"   Note: Could only add {likes_to_add} likes (limited by {len(users)} users)")

        session.commit()
        print("\n" + "=" * 60)
        print("✅ Test data added successfully!")
        print("=" * 60)
        print("\nExpected sorting results:")
        print("\n📅 RECENT view (sorted by created_at DESC):")
        sorted_by_recent = sorted(enumerate(TEST_COMMENTS, 1),
                                  key=lambda x: x[1]["days_ago"])
        for i, (idx, comment) in enumerate(sorted_by_recent, 1):
            print(f"  {i}. Comment {idx}: {comment['days_ago']} days ago ({comment['likes']} likes)")

        print("\n🔥 POPULAR view (sorted by like_count DESC):")
        sorted_by_popular = sorted(enumerate(TEST_COMMENTS, 1),
                                   key=lambda x: x[1]["likes"], reverse=True)
        for i, (idx, comment) in enumerate(sorted_by_popular, 1):
            print(f"  {i}. Comment {idx}: {comment['likes']} likes ({comment['days_ago']} days ago)")


if __name__ == "__main__":
    print("=" * 60)
    print("Adding Test Comments for Sort Testing")
    print("=" * 60)
    add_test_data()
