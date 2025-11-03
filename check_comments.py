#!/usr/bin/env python3
"""
Check comments in the database for debugging
"""
from sqlmodel import Session, select, create_engine
from app.models import Comment, User

# Database connection
DATABASE_URL = "postgresql://kevsrobots_user:ChangeMe123@192.168.2.1:5433/kevsrobots_cms"
engine = create_engine(DATABASE_URL)

def check_comments():
    with Session(engine) as session:
        # Get all comments for smars-q
        print("=" * 80)
        print("ALL COMMENTS FOR SMARS-Q URLs:")
        print("=" * 80)

        comments = session.exec(
            select(Comment)
            .where(Comment.url.like('%smars-q%'))
            .order_by(Comment.created_at)
        ).all()

        print(f"\nFound {len(comments)} total comments with 'smars-q' in URL\n")

        for c in comments:
            print(f"ID: {c.id}")
            print(f"  URL: '{c.url}'")
            print(f"  User ID: {c.user_id}")
            print(f"  Is Hidden: {c.is_hidden}")
            print(f"  Is Removed: {c.is_removed}")
            print(f"  Content: {c.content[:50]}...")
            print(f"  Created: {c.created_at}")
            print()

        # Now check specifically for 'projects/smars-q/'
        print("=" * 80)
        print("COMMENTS FOR EXACT URL 'projects/smars-q/':")
        print("=" * 80)

        exact_comments = session.exec(
            select(Comment)
            .where(Comment.url == 'projects/smars-q/')
            .order_by(Comment.created_at)
        ).all()

        print(f"\nFound {len(exact_comments)} comments for exact URL\n")

        for c in exact_comments:
            print(f"ID: {c.id}")
            print(f"  User ID: {c.user_id}")
            print(f"  Is Hidden: {c.is_hidden}")
            print(f"  Is Removed: {c.is_removed}")

            # Check if user exists
            user = session.get(User, c.user_id)
            if user:
                print(f"  User: {user.username} (exists)")
            else:
                print(f"  User: NOT FOUND (orphaned comment)")
            print()

        # Test the actual query used by the endpoint
        print("=" * 80)
        print("TESTING ACTUAL ENDPOINT QUERY:")
        print("=" * 80)

        url = 'projects/smars-q/'
        statement = (
            select(Comment, User)
            .where(Comment.url == url)
            .where(Comment.user_id == User.id)
            .where(Comment.is_hidden == False)
            .where(Comment.is_removed == False)
            .order_by(Comment.created_at.desc())
        )
        results = session.exec(statement).all()

        print(f"\nQuery returned {len(results)} results\n")

        for comment, user in results:
            print(f"ID: {comment.id}, User: {user.username}, Content: {comment.content[:50]}...")

if __name__ == "__main__":
    check_comments()
