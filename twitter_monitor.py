import tweepy
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import Config

class TwitterMonitor:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Twitter API client
        self._init_twitter_client()
    
    def _init_twitter_client(self):
        """Initialize the Twitter API client with authentication"""
        try:
            auth = tweepy.OAuth1UserHandler(
                self.config.TWITTER_API_KEY,
                self.config.TWITTER_API_SECRET,
                self.config.TWITTER_ACCESS_TOKEN,
                self.config.TWITTER_ACCESS_TOKEN_SECRET
            )
            self.client = tweepy.API(auth, wait_on_rate_limit=True)
            self.v2_client = tweepy.Client(
                bearer_token=self.config.TWITTER_BEARER_TOKEN,
                consumer_key=self.config.TWITTER_API_KEY,
                consumer_secret=self.config.TWITTER_API_SECRET,
                access_token=self.config.TWITTER_ACCESS_TOKEN,
                access_token_secret=self.config.TWITTER_ACCESS_TOKEN_SECRET,
                wait_on_rate_limit=True
            )
            self.logger.info("Twitter API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Twitter client: {e}")
            raise
    
    def get_user_id(self, handle: str) -> Optional[str]:
        """Get the user ID for a Twitter handle"""
        try:
            user = self.v2_client.get_user(username=handle)
            if user.data:
                return user.data.id
            return None
        except Exception as e:
            self.logger.error(f"Error getting user ID for {handle}: {e}")
            return None
    
    def check_mentions(self, handle: str, last_checked: Optional[datetime]) -> List[Dict[str, Any]]:
        """
        Check for new mentions of a handle since the last check
        Returns a list of mention data
        """
        user_id = self.get_user_id(handle)
        if not user_id:
            self.logger.error(f"Could not find user ID for handle: {handle}")
            return []
        
        mentions = []
        try:
            # If no last checked time, check the last 24 hours
            if not last_checked:
                last_checked = datetime.utcnow() - timedelta(days=1)
            
            # Search for tweets mentioning the handle
            query = f"@{handle}"
            tweets = tweepy.Paginator(
                self.v2_client.search_recent_tweets,
                query=query,
                start_time=last_checked,
                tweet_fields=["created_at", "author_id", "public_metrics", "context_annotations"],
                user_fields=["username"],
                expansions=["author_id"],
                max_results=100
            ).flatten(limit=100)
            
            for tweet in tweets:
                # Skip tweets from the official handle
                if tweet.author_id == self.get_user_id(self.config.OFFICIAL_HANDLE):
                    continue
                
                # Get author username
                author = None
                if hasattr(tweet, 'includes') and 'users' in tweet.includes:
                    for user in tweet.includes['users']:
                        if user.id == tweet.author_id:
                            author = user.username
                            break
                
                if not author:
                    author = f"user_{tweet.author_id}"
                
                mention_data = {
                    'tweet_id': tweet.id,
                    'handle': handle,
                    'author': author,
                    'text': tweet.text,
                    'timestamp': tweet.created_at.isoformat(),
                    'url': f"https://twitter.com/{author}/status/{tweet.id}"
                }
                mentions.append(mention_data)
            
            self.logger.info(f"Found {len(mentions)} new mentions for {handle}")
            return mentions
        
        except Exception as e:
            self.logger.error(f"Error checking mentions for {handle}: {e}")
            return []
    
    def monitor_handles(self, storage, handles: List[str]):
        """Monitor all specified handles for new mentions"""
        for handle in handles:
            try:
                last_checked = storage.get_last_checked(handle)
                mentions = self.check_mentions(handle, last_checked)
                
                if mentions:
                    for mention in mentions:
                        storage.add_mention(mention)
                    
                    # Update last checked time to the most recent mention
                    most_recent = max(mentions, key=lambda m: m['timestamp'])
                    storage.update_last_checked(handle, datetime.fromisoformat(most_recent['timestamp']))
                else:
                    # If no new mentions, update to current time
                    storage.update_last_checked(handle, datetime.utcnow())
            
            except Exception as e:
                self.logger.error(f"Error monitoring handle {handle}: {e}")
                continue