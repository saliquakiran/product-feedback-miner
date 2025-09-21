"""
Ingestor Agent for Product Feedback Miner.

This agent collects raw feedback data from external sources (GitHub, Hacker News, Exa AI)
and stores it in the database for further processing.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.ingestor.sources.github import GitHubAPIClient, GitHubIssue
from agents.ingestor.sources.hackernews import HackerNewsAPIClient, HackerNewsPost
from agents.ingestor.sources.exa import ExaAPIClient, ExaSearchResult
from agents.ingestor.sources.twitter import TwitterAPIClient, TwitterPost
from agents.ingestor.sources.reddit import RedditAPIClient, RedditPost
from database.models import RawFeedback, SourceType
from config.settings import config

logger = logging.getLogger(__name__)

class IngestorAgent(BaseAgent):
    """
    Ingestor Agent for collecting raw feedback data.
    
    This agent fetches data from multiple sources:
    - GitHub issues and discussions
    - Hacker News posts and comments
    - Exa AI web search results
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__("ingestor", config_overrides)
        
        # Initialize API clients
        self.github_client = GitHubAPIClient()
        self.hn_client = HackerNewsAPIClient()
        self.exa_client = ExaAPIClient()
        self.twitter_client = TwitterAPIClient() if config.twitter else None
        self.reddit_client = RedditAPIClient() if config.reddit else None
        
        # Configuration
        self.repositories = self.config.get("repositories", [])
        self.hn_keywords = self.config.get("hn_keywords", [])
        self.exa_queries = self.config.get("exa_queries", [])
        self.twitter_queries = self.config.get("twitter_queries", [])
        self.reddit_subreddits = self.config.get("reddit_subreddits", [])
        self.product_name = self.config.get("product_name", "Product")
        self.days_back = self.config.get("days_back", 7)
        
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for the Ingestor Agent.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult: Processing results and statistics
        """
        start_time = datetime.utcnow()
        total_items = 0
        successful_items = 0
        failed_items = 0
        
        try:
            self.logger.info("Starting data ingestion from all sources")
            
            # Collect data from all sources
            all_feedback = []
            
            # 1. Collect from GitHub
            github_feedback = await self._collect_github_data()
            all_feedback.extend(github_feedback)
            self.logger.info(f"Collected {len(github_feedback)} items from GitHub")
            
            # 2. Collect from Hacker News
            hn_feedback = await self._collect_hackernews_data()
            all_feedback.extend(hn_feedback)
            self.logger.info(f"Collected {len(hn_feedback)} items from Hacker News")
            
            # 3. Collect from Exa AI
            exa_feedback = await self._collect_exa_data()
            all_feedback.extend(exa_feedback)
            self.logger.info(f"Collected {len(exa_feedback)} items from Exa AI")
            
            # 4. Collect from Twitter
            twitter_feedback = await self._collect_twitter_data()
            all_feedback.extend(twitter_feedback)
            self.logger.info(f"Collected {len(twitter_feedback)} items from Twitter")
            
            # 5. Collect from Reddit
            reddit_feedback = await self._collect_reddit_data()
            all_feedback.extend(reddit_feedback)
            self.logger.info(f"Collected {len(reddit_feedback)} items from Reddit")
            
            # 6. Store all feedback in database
            for feedback_data in all_feedback:
                try:
                    await self._store_raw_feedback(feedback_data)
                    successful_items += 1
                except Exception as e:
                    self.logger.error(f"Failed to store feedback: {e}")
                    failed_items += 1
                
                total_items += 1
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Ingestion completed: {successful_items}/{total_items} items stored successfully"
            )
            
            return AgentResult(
                success=True,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=execution_time,
                metadata={
                    "github_items": len(github_feedback),
                    "hn_items": len(hn_feedback),
                    "exa_items": len(exa_feedback),
                    "twitter_items": len(twitter_feedback),
                    "reddit_items": len(reddit_feedback),
                    "sources_processed": 5
                }
            )
            
        except Exception as e:
            self.logger.error(f"Ingestor Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    def get_input_dependencies(self) -> List[str]:
        """Get list of agent names that this agent depends on for input."""
        return []  # Ingestor has no dependencies - it's the first agent
    
    async def _collect_github_data(self) -> List[Dict[str, Any]]:
        """Collect data from GitHub repositories."""
        feedback_items = []
        
        try:
            # Test GitHub connection
            if not await self.github_client.test_connection():
                self.logger.warning("GitHub API connection failed, skipping GitHub data")
                return feedback_items
            
            # Calculate since date
            since_date = datetime.utcnow() - timedelta(days=self.days_back)
            
            # Process each repository
            for repo_config in self.repositories:
                owner = repo_config.get("owner")
                repo = repo_config.get("name")
                labels = repo_config.get("labels", [])
                
                if not owner or not repo:
                    self.logger.warning(f"Invalid repository config: {repo_config}")
                    continue
                
                try:
                    # Fetch issues
                    issues = await self.github_client.fetch_issues(
                        owner=owner,
                        repo=repo,
                        since=since_date,
                        state="all",
                        labels=labels
                    )
                    
                    # Convert to feedback format
                    for issue in issues:
                        feedback_items.append(self._convert_github_issue(issue))
                    
                    # Fetch discussions (if enabled)
                    if repo_config.get("include_discussions", False):
                        discussions = await self.github_client.fetch_discussions(
                            owner=owner,
                            repo=repo,
                            since=since_date
                        )
                        
                        for discussion in discussions:
                            feedback_items.append(self._convert_github_discussion(discussion))
                    
                except Exception as e:
                    self.logger.error(f"Error collecting GitHub data for {owner}/{repo}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error in GitHub data collection: {e}")
        
        return feedback_items
    
    async def _collect_hackernews_data(self) -> List[Dict[str, Any]]:
        """Collect data from Hacker News."""
        feedback_items = []
        
        try:
            # Test Hacker News connection
            if not await self.hn_client.test_connection():
                self.logger.warning("Hacker News API connection failed, skipping HN data")
                return feedback_items
            
            # Fetch top stories
            top_stories = await self.hn_client.fetch_top_stories(
                limit=self.config.get("hn_top_stories_limit", 50),
                min_score=self.config.get("hn_min_score", 10)
            )
            
            for story in top_stories:
                feedback_items.append(self._convert_hn_post(story))
            
            # Fetch stories by keywords
            if self.hn_keywords:
                keyword_stories = await self.hn_client.fetch_stories_by_keywords(
                    keywords=self.hn_keywords,
                    limit=self.config.get("hn_keyword_limit", 30),
                    min_score=self.config.get("hn_min_score", 5)
                )
                
                for story in keyword_stories:
                    feedback_items.append(self._convert_hn_post(story))
            
        except Exception as e:
            self.logger.error(f"Error in Hacker News data collection: {e}")
        
        return feedback_items
    
    async def _collect_exa_data(self) -> List[Dict[str, Any]]:
        """Collect data from Exa AI with timeout and error handling."""
        feedback_items = []
        
        try:
            # Add timeout to prevent getting stuck
            search_results = await asyncio.wait_for(
                self.exa_client.search_feedback_content(
                    product_name=self.product_name,
                    num_results=self.config.get("exa_results_limit", 20),  # Reduced limit
                    days_back=self.days_back
                ),
                timeout=45.0  # 45 second timeout
            )
            
            for result in search_results:
                try:
                    feedback_items.append(self._convert_exa_result(result))
                except Exception as e:
                    self.logger.warning(f"Failed to convert Exa result: {e}")
                    continue
            
            # Search for specific queries with timeout
            for query in self.exa_queries:
                try:
                    query_results = await asyncio.wait_for(
                        self.exa_client.search_content(
                            query=query,
                            num_results=self.config.get("exa_query_limit", 10),  # Reduced limit
                            start_published_date=datetime.utcnow() - timedelta(days=self.days_back)
                        ),
                        timeout=30.0  # 30 second timeout per query
                    )
                    
                    for result in query_results:
                        feedback_items.append(self._convert_exa_result(result))
                        
                except asyncio.TimeoutError:
                    self.logger.warning(f"Exa query '{query}' timed out, skipping")
                    continue
                except Exception as e:
                    self.logger.warning(f"Error searching Exa AI for query '{query}': {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error in Exa AI data collection: {e}")
        
        return feedback_items
    
    async def _collect_twitter_data(self) -> List[Dict[str, Any]]:
        """Collect data from Twitter."""
        feedback_items = []
        
        try:
            if not self.twitter_client:
                self.logger.info("Twitter client not configured, skipping Twitter data")
                return feedback_items
            
            # Test Twitter connection
            if not await self.twitter_client.test_connection():
                self.logger.warning("Twitter API connection failed, skipping Twitter data")
                return feedback_items
            
            # Search for product mentions
            search_results = await self.twitter_client.search_product_mentions(
                product_name=self.product_name,
                max_results=self.config.get("twitter_results_limit", 50),
                days_back=self.days_back
            )
            
            for result in search_results:
                feedback_items.append(self._convert_twitter_post(result))
            
        except Exception as e:
            self.logger.error(f"Error in Twitter data collection: {e}")
        
        return feedback_items
    
    async def _collect_reddit_data(self) -> List[Dict[str, Any]]:
        """Collect data from Reddit."""
        feedback_items = []
        
        try:
            if not self.reddit_client:
                self.logger.info("Reddit client not configured, skipping Reddit data")
                return feedback_items
            
            # Test Reddit connection
            if not await self.reddit_client.test_connection():
                self.logger.warning("Reddit API connection failed, skipping Reddit data")
                return feedback_items
            
            # Search for product feedback
            search_results = await self.reddit_client.search_product_feedback(
                product_name=self.product_name,
                subreddits=self.reddit_subreddits,
                limit=self.config.get("reddit_results_limit", 50),
                days_back=self.days_back
            )
            
            for result in search_results:
                feedback_items.append(self._convert_reddit_post(result))
            
        except Exception as e:
            self.logger.error(f"Error in Reddit data collection: {e}")
        
        return feedback_items
    
    def _convert_github_issue(self, issue: GitHubIssue) -> Dict[str, Any]:
        """Convert GitHub issue to feedback format."""
        return {
            "source_type": SourceType.GITHUB_ISSUE,
            "source_id": str(issue.id),
            "url": issue.url,
            "title": issue.title,
            "content": issue.body,
            "author": issue.author,
            "author_url": issue.author_url,
            "timestamp": issue.created_at,
            "raw_metadata": {
                "number": issue.number,
                "labels": issue.labels,
                "state": issue.state,
                "comments_count": issue.comments_count,
                "assignees": issue.assignees,
                "updated_at": issue.updated_at.isoformat(),
                **issue.raw_metadata
            }
        }
    
    def _convert_github_discussion(self, discussion: GitHubIssue) -> Dict[str, Any]:
        """Convert GitHub discussion to feedback format."""
        return {
            "source_type": SourceType.GITHUB_DISCUSSION,
            "source_id": str(discussion.id),
            "url": discussion.url,
            "title": discussion.title,
            "content": discussion.body,
            "author": discussion.author,
            "author_url": discussion.author_url,
            "timestamp": discussion.created_at,
            "raw_metadata": {
                "number": discussion.number,
                "labels": discussion.labels,
                "state": discussion.state,
                "comments_count": discussion.comments_count,
                "updated_at": discussion.updated_at.isoformat(),
                **discussion.raw_metadata
            }
        }
    
    def _convert_hn_post(self, post: HackerNewsPost) -> Dict[str, Any]:
        """Convert Hacker News post to feedback format."""
        return {
            "source_type": SourceType.HACKER_NEWS,
            "source_id": str(post.id),
            "url": post.url or f"https://news.ycombinator.com/item?id={post.id}",
            "title": post.title,
            "content": post.text,
            "author": post.author,
            "author_url": f"https://news.ycombinator.com/user?id={post.author}",
            "timestamp": post.time,
            "raw_metadata": {
                "score": post.score,
                "descendants": post.descendants,
                "type": post.type,
                **post.raw_metadata
            }
        }
    
    def _convert_exa_result(self, result: ExaSearchResult) -> Dict[str, Any]:
        """Convert Exa AI search result to feedback format."""
        return {
            "source_type": SourceType.EXA_BLOG,  # Default to blog, could be more specific
            "source_id": result.id,
            "url": result.url,
            "title": result.title,
            "content": result.content,
            "author": result.author,
            "author_url": "",  # Exa doesn't provide author URLs
            "timestamp": result.published_date,
            "raw_metadata": {
                "score": result.score,
                "domain": result.raw_metadata.get("domain", ""),
                "language": result.raw_metadata.get("language", ""),
                "type": result.raw_metadata.get("type", ""),
                **result.raw_metadata
            }
        }
    
    def _convert_twitter_post(self, post: TwitterPost) -> Dict[str, Any]:
        """Convert Twitter post to feedback format."""
        return {
            "source_type": SourceType.TWITTER_POST,
            "source_id": post.id,
            "url": post.url,
            "title": f"@{post.author_username}: {post.text[:100]}...",
            "content": post.text,
            "author": post.author,
            "author_url": post.author_url,
            "timestamp": post.created_at,
            "raw_metadata": {
                "retweet_count": post.retweet_count,
                "like_count": post.like_count,
                "reply_count": post.reply_count,
                "quote_count": post.quote_count,
                "is_retweet": post.is_retweet,
                "is_reply": post.is_reply,
                "hashtags": post.hashtags,
                "mentions": post.mentions,
                "author_verified": post.raw_metadata.get("author_verified", False),
                "author_followers": post.raw_metadata.get("author_followers", 0),
                **post.raw_metadata
            }
        }
    
    def _convert_reddit_post(self, post: RedditPost) -> Dict[str, Any]:
        """Convert Reddit post to feedback format."""
        return {
            "source_type": SourceType.REDDIT,
            "source_id": post.id,
            "url": post.url,
            "title": post.title,
            "content": post.content,
            "author": post.author,
            "author_url": post.author_url,
            "timestamp": post.created_at,
            "raw_metadata": {
                "subreddit": post.subreddit,
                "subreddit_url": post.subreddit_url,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "is_self": post.is_self,
                "link_url": post.link_url,
                "flair": post.flair,
                "awards": post.awards,
                **post.raw_metadata
            }
        }
    
    async def _store_raw_feedback(self, feedback_data: Dict[str, Any]) -> None:
        """Store raw feedback data in the database."""
        async with self.get_db_session() as session:
            # Check if feedback already exists
            existing = session.query(RawFeedback).filter(
                RawFeedback.source_type == feedback_data["source_type"],
                RawFeedback.source_id == feedback_data["source_id"]
            ).first()
            
            if existing:
                # Update existing record
                existing.title = feedback_data["title"]
                existing.content = feedback_data["content"]
                existing.raw_metadata = feedback_data["raw_metadata"]
                existing.updated_at = datetime.utcnow()
            else:
                # Create new record
                raw_feedback = RawFeedback(
                    source_type=feedback_data["source_type"],
                    source_id=feedback_data["source_id"],
                    url=feedback_data["url"],
                    title=feedback_data["title"],
                    content=feedback_data["content"],
                    author=feedback_data["author"],
                    author_url=feedback_data["author_url"],
                    timestamp=feedback_data["timestamp"],
                    raw_metadata=feedback_data["raw_metadata"]
                )
                session.add(raw_feedback)
            
            session.commit()
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """Test connections to all external APIs."""
        results = {}
        
        try:
            results["github"] = await self.github_client.test_connection()
        except Exception as e:
            self.logger.error(f"GitHub connection test failed: {e}")
            results["github"] = False
        
        try:
            results["hackernews"] = await self.hn_client.test_connection()
        except Exception as e:
            self.logger.error(f"Hacker News connection test failed: {e}")
            results["hackernews"] = False
        
        try:
            results["exa"] = await self.exa_client.test_connection()
        except Exception as e:
            self.logger.error(f"Exa AI connection test failed: {e}")
            results["exa"] = False
        
        try:
            if self.twitter_client:
                results["twitter"] = await self.twitter_client.test_connection()
            else:
                results["twitter"] = False
        except Exception as e:
            self.logger.error(f"Twitter connection test failed: {e}")
            results["twitter"] = False
        
        try:
            if self.reddit_client:
                results["reddit"] = await self.reddit_client.test_connection()
            else:
                results["reddit"] = False
        except Exception as e:
            self.logger.error(f"Reddit connection test failed: {e}")
            results["reddit"] = False
        
        return results
