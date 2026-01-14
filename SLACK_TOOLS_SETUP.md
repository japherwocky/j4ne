# Slack Bot Tools - Setup Guide

This guide explains the new Slack bot tools and how to configure them.

## 🔧 Environment Variables Setup

### Web Search (Serper API)

The Slack bot uses **Serper** for web search capabilities:

```bash
# Add to your .env file:
SERPER_API_KEY=your_serper_api_key_here
```

**Getting Started with Serper:**

1. **Sign Up**: Visit https://serper.dev/
2. **Choose Plan**: 
   - Free: 2,500 searches/month (great for testing)
   - Pro: $50/month for 100,000 searches (production)
3. **Get API Key**: Copy your API key from dashboard
4. **Configure**: Add to your environment variables

**Why Serper?**
- ✅ Real Google search results
- ✅ Simple REST API (no Google Cloud setup)
- ✅ Fast and reliable
- ✅ Clean JSON responses perfect for Slack
- ✅ Built-in rate limiting

### GitHub API (Optional)

Enhance GitHub tool functionality with higher rate limits:

```bash
# Add to your .env file (optional but recommended):
GITHUB_TOKEN=ghp_your_github_token_here
```

**Setting up GitHub Token:**

1. **Visit**: https://github.com/settings/tokens
2. **Generate Token**: Click "Generate new token (classic)"
3. **Configure**:
   - Note: "j4ne-slack-bot"
   - Expiration: No expiration (or 90 days)
   - Scopes: `public_repo` (for public repository access)
4. **Copy Token**: Securely store and add to environment

**Benefits:**
- ✅ 60 → 5,000 requests/hour
- ✅ More reliable API access
- ✅ Private repo access (if needed later)

## 🛠️ Available Slack Tools

### Web Search
```bash
# Users can ask:
@j4ne search for "python web frameworks"
@j4ne what's the latest news about AI?
@j4ne find tutorials on machine learning
```

### GitHub Explorer
```bash
# Users can ask:
@j4ne explore the microsoft/vscode repository
@j4ne search for python repositories with machine learning
@j4ne get the README from torvalds/linux
```

## 🔒 Security Features

- **No Filesystem Access**: Slack never touches your local files
- **Public APIs Only**: Only accesses public web and GitHub data
- **Rate Limited**: Built-in protection against abuse
- **Context-Aware**: Different tool sets for CLI vs Slack

## 🚀 Production Deployment

For production use:

1. **Set up .env file** with your API keys
2. **Use HTTP mode** for Slack (more reliable than Socket Mode)
3. **Consider reverse proxy** (nginx) for HTTPS endpoints
4. **Monitor usage**: Check API dashboard for rate limits

## 📊 Example Usage

Once configured, users can interact naturally:

```
User: @j4ne search for "best python frameworks 2024"
Bot: 🔍 I found these results about Python frameworks...
     1. Django - The web framework for perfectionists...
     2. FastAPI - Modern, fast web framework...
     3. Flask - A lightweight WSGI web application framework...

User: @j4ne explore the django/django repository
Bot: 🐙 Here's what I found in the django/django repository:
     ⭐ Stars: 78,234 | 🍴 Forks: 31,845 | 📝 Language: Python
     📂 Key files: setup.py, README.md, django/__init__.py...
     📋 Description: The Web framework for perfectionists with deadlines...
```

## 🆘 Troubleshooting

**Web search not working?**
- Check SERPER_API_KEY is set correctly
- Verify Serper account has available searches
- Check API key permissions

**GitHub search limited?**
- Add GITHUB_TOKEN for higher rate limits
- Verify token has `public_repo` scope
- Check token expiration

**Tools not appearing in Slack?**
- Restart bot after updating .env file
- Check bot has the right permissions in Slack
- Verify context="slack" in DirectClient initialization