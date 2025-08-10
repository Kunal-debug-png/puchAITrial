"""
intent parser for mcp code generator

analyzes user prompts to extract requirements for mcp generation.
"""

from typing import Dict, List


class IntentParser:
    """parses user prompts to understand mcp requirements."""
    
    def __init__(self):
        """init intent parser with keyword mappings."""
        self.api_keywords = {
            "weather": ["openweathermap", "weatherapi"],
            "flight": ["skyscanner", "amadeus", "expedia"],
            "hotel": ["booking", "expedia", "hotels"],
            "email": ["sendgrid", "mailgun", "gmail"],
            "sms": ["twilio", "messagebird"],
            "payment": ["stripe", "paypal", "square"],
            "social": ["twitter", "facebook", "instagram", "linkedin"],
            "ai": ["openai", "anthropic", "gemini"],
            "image": ["unsplash", "dall-e", "midjourney", "stability"],
            "news": ["newsapi", "reddit"],
            "crypto": ["coinbase", "binance", "coingecko"],
            "stock": ["alpha-vantage", "yahoo-finance", "polygon"],
            "database": ["postgresql", "mongodb", "sqlite"],
            "file": ["aws-s3", "cloudinary"],
            "calendar": ["google-calendar", "outlook"],
            "maps": ["google-maps", "mapbox"],
            "translate": ["google-translate", "deepl"],
            "qr": ["qrcode"],
            "url": ["bitly", "tinyurl"],
            "pdf": ["pypdf", "reportlab"],
            "excel": ["openpyxl", "pandas"],
            "webhook": ["webhooks"],
            "slack": ["slack-sdk"],
            "discord": ["discord"],
            "github": ["github", "git"],
            "monitoring": ["uptime", "ping"],
            "scraping": ["beautifulsoup", "scrapy"],
        }
        
        self.complexity_indicators = {
            "simple": ["simple", "basic", "easy", "quick", "generate", "create"],
            "intermediate": ["search", "compare", "track", "monitor", "alert", "notify", "manage"],
            "advanced": ["analyze", "predict", "automate", "integrate", "dashboard", "pipeline", "workflow"]
        }
        
        self.functionality_patterns = {
            "tracker": ["track", "monitor", "watch", "follow"],
            "generator": ["generate", "create", "make", "build"],
            "searcher": ["search", "find", "lookup", "query"],
            "notifier": ["alert", "notify", "send", "email", "sms"],
            "analyzer": ["analyze", "report", "summarize", "process"],
            "converter": ["convert", "transform", "export", "import"],
            "manager": ["manage", "organize", "store", "save"],
            "automation": ["automate", "schedule", "trigger", "workflow"]
        }
    
    async def parse_intent(self, prompt: str, include_database: bool = False) -> Dict:
        """parse user prompt to extract mcp requirements."""
        prompt_lower = prompt.lower()
        
        intent = {
            "main_functionality": self._extract_main_functionality(prompt),
            "apis": self._detect_apis(prompt_lower),
            "complexity": self._determine_complexity(prompt_lower),
            "functionality_type": self._detect_functionality_type(prompt_lower),
            "requires_database": include_database or self._needs_database(prompt_lower),
            "requires_user_data": self._needs_user_data(prompt_lower),
            "requires_scheduling": self._needs_scheduling(prompt_lower),
            "requires_authentication": self._needs_auth(prompt_lower),
            "data_operations": self._detect_data_operations(prompt_lower),
            "environment_vars": self._extract_env_vars(prompt_lower),
            "python_packages": self._suggest_packages(prompt_lower),
            "deployment_notes": self._generate_deployment_notes(prompt_lower)
        }
        
        return intent
    
    def _extract_main_functionality(self, prompt: str) -> str:
        """extract main functionality description."""
        # clean up the prompt for the main functionality
        cleaned = prompt.strip()
        if cleaned.endswith('.'):
            cleaned = cleaned[:-1]
        
        # capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned
    
    def _detect_apis(self, prompt: str) -> List[str]:
        """detect which apis might be needed based on keywords."""
        detected_apis = []
        
        for category, apis in self.api_keywords.items():
            if any(keyword in prompt for keyword in [category] + [category + "s"]):
                detected_apis.extend(apis[:1])  # Add primary API for category
        
        # remove duplicates while preserving order
        return list(dict.fromkeys(detected_apis))
    
    def _determine_complexity(self, prompt: str) -> str:
        """determine complexity level of the requested mcp."""
        complexity_scores = {"simple": 0, "intermediate": 0, "advanced": 0}
        
        for level, keywords in self.complexity_indicators.items():
            for keyword in keywords:
                if keyword in prompt:
                    complexity_scores[level] += 1
        
        # default to intermediate if no clear indicators
        if all(score == 0 for score in complexity_scores.values()):
            return "intermediate"
        
        return max(complexity_scores, key=complexity_scores.get)
    
    def _detect_functionality_type(self, prompt: str) -> str:
        """detect the primary type of functionality."""
        for func_type, keywords in self.functionality_patterns.items():
            if any(keyword in prompt for keyword in keywords):
                return func_type
        
        return "general"
    
    def _needs_database(self, prompt: str) -> bool:
        """check if the mcp needs database functionality."""
        db_keywords = [
            "store", "save", "database", "persist", "history", "log", 
            "record", "track", "remember", "cache", "data", "manage",
            "task", "user", "profile", "list", "collection"
        ]
        return any(keyword in prompt for keyword in db_keywords)
    
    def _needs_scheduling(self, prompt: str) -> bool:
        """check if the mcp needs scheduling/cron functionality."""
        schedule_keywords = [
            "schedule", "daily", "weekly", "monthly", "periodic", "regular",
            "cron", "timer", "interval", "recurring", "automatic"
        ]
        return any(keyword in prompt for keyword in schedule_keywords)
    
    def _needs_auth(self, prompt: str) -> bool:
        """check if the mcp needs authentication."""
        auth_keywords = [
            "login", "auth", "user", "account", "secure", "private",
            "token", "key", "password", "credential"
        ]
        return any(keyword in prompt for keyword in auth_keywords)
    
    def _needs_user_data(self, prompt: str) -> bool:
        """check if the mcp needs user-specific data management."""
        user_data_keywords = [
            "task", "todo", "note", "reminder", "personal", "my", "user",
            "manage", "track", "list", "collection", "profile", "setting",
            "preference", "history", "favorite", "bookmark", "subscription"
        ]
        return any(keyword in prompt for keyword in user_data_keywords)
    
    def _detect_data_operations(self, prompt: str) -> List[str]:
        """detect what kind of data operations are needed."""
        operations = []
        
        operation_keywords = {
            "read": ["get", "fetch", "read", "retrieve", "load"],
            "write": ["save", "store", "write", "create", "add"],
            "update": ["update", "modify", "change", "edit"],
            "delete": ["delete", "remove", "clear", "clean"],
            "search": ["search", "find", "query", "filter"],
            "export": ["export", "download", "backup", "extract"],
            "import": ["import", "upload", "load", "migrate"]
        }
        
        for operation, keywords in operation_keywords.items():
            if any(keyword in prompt for keyword in keywords):
                operations.append(operation)
        
        return operations if operations else ["read", "write"]
    
    def _extract_env_vars(self, prompt: str) -> List[str]:
        """extract likely environment variables needed."""
        env_vars = ["AUTH_TOKEN", "MY_NUMBER"]  # always needed for puch ai
        
        # api-specific environment variables
        api_env_map = {
            "openweathermap": ["OPENWEATHER_API_KEY"],
            "weatherapi": ["WEATHER_API_KEY"],
            "skyscanner": ["SKYSCANNER_API_KEY"],
            "amadeus": ["AMADEUS_API_KEY", "AMADEUS_API_SECRET"],
            "sendgrid": ["SENDGRID_API_KEY"],
            "mailgun": ["MAILGUN_API_KEY", "MAILGUN_DOMAIN"],
            "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
            "stripe": ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"],
            "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "slack": ["SLACK_BOT_TOKEN"],
            "discord": ["DISCORD_BOT_TOKEN"],
            "github": ["GITHUB_TOKEN"],
        }
        
        for api in self._detect_apis(prompt):
            if api in api_env_map:
                env_vars.extend(api_env_map[api])
        
        if self._needs_database(prompt):
            env_vars.extend(["DATABASE_URL"])
        
        return list(dict.fromkeys(env_vars))  # remove duplicates
    
    def _suggest_packages(self, prompt: str) -> List[str]:
        """suggest additional python packages based on functionality."""
        packages = ["fastmcp", "python-dotenv", "httpx", "pydantic"]
        
        # api-specific packages
        if any(api in prompt for api in ["weather", "openweather"]):
            packages.append("pyowm")
        
        if any(word in prompt for word in ["email", "mail"]):
            packages.extend(["sendgrid", "emails"])
        
        if any(word in prompt for word in ["sms", "text"]):
            packages.append("twilio")
        
        if any(word in prompt for word in ["pdf", "document"]):
            packages.extend(["pypdf2", "reportlab"])
        
        if any(word in prompt for word in ["excel", "spreadsheet"]):
            packages.extend(["openpyxl", "pandas"])
        
        if any(word in prompt for word in ["image", "photo"]):
            packages.extend(["pillow", "requests"])
        
        if any(word in prompt for word in ["qr", "barcode"]):
            packages.append("qrcode[pil]")
        
        if self._needs_database(prompt):
            packages.extend(["sqlalchemy", "psycopg2-binary"])
        
        if self._needs_scheduling(prompt):
            packages.append("schedule")
        
        return list(dict.fromkeys(packages))  # remove duplicates
    
    def _generate_deployment_notes(self, prompt: str) -> str:
        """generate deployment-specific notes."""
        notes = []
        
        if any(api in self._detect_apis(prompt) for api in ["openai", "anthropic"]):
            notes.append("Requires AI API credits and proper rate limiting")
        
        if self._needs_database(prompt):
            notes.append("Requires database setup (PostgreSQL recommended)")
        
        if any(word in prompt for word in ["email", "sms", "notification"]):
            notes.append("Requires third-party service configuration for notifications")
        
        if self._needs_scheduling(prompt):
            notes.append("Consider using background job processing for scheduled tasks")
        
        return "; ".join(notes) if notes else "Standard deployment with environment variables"
