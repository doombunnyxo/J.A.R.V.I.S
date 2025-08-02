import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration management with environment validation"""
    
    # Discord Configuration
    DISCORD_TOKEN: str
    AUTHORIZED_USER_ID: int
    
    # API Keys
    GROQ_API_KEY: Optional[str]
    OPENAI_API_KEY: Optional[str]
    PERPLEXITY_API_KEY: Optional[str]
    GOOGLE_API_KEY: Optional[str]
    GOOGLE_SEARCH_ENGINE_ID: Optional[str]
    
    # File Paths
    SETTINGS_FILE: str = 'data/user_settings.json'
    PERMANENT_CONTEXT_FILE: str = 'data/permanent_context.json'
    UNFILTERED_PERMANENT_CONTEXT_FILE: str = 'data/unfiltered_permanent_context.json'
    HISTORY_FILE: str = 'data/conversation_history.json'
    
    # AI Configuration  
    AI_MODEL: str = "llama3-8b-8192"  # Groq model for main processing
    AI_MAX_TOKENS: int = 1000
    AI_TEMPERATURE: float = 0.7
    
    # Rate Limiting
    AI_RATE_LIMIT_REQUESTS: int = 10  # requests per minute per user
    AI_RATE_LIMIT_WINDOW: int = 60    # seconds
    
    # Channel Context
    CHANNEL_CONTEXT_LIMIT: int = 50
    CHANNEL_CONTEXT_DISPLAY: int = 35
    
    def __init__(self):
        self._validate_and_load()
    
    def _validate_and_load(self):
        """Validate and load configuration from environment"""
        errors = []
        
        # Required configuration
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        if not self.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is required")
        
        authorized_id = os.getenv('AUTHORIZED_USER_ID')
        if not authorized_id:
            errors.append("AUTHORIZED_USER_ID is required")
        else:
            try:
                self.AUTHORIZED_USER_ID = int(authorized_id)
            except ValueError:
                errors.append("AUTHORIZED_USER_ID must be a valid integer")
        
        # Optional configuration
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        self.GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        # Override defaults with environment variables if provided
        if os.getenv('AI_MODEL'):
            self.AI_MODEL = os.getenv('AI_MODEL')
        
        if os.getenv('AI_MAX_TOKENS'):
            try:
                self.AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS'))
            except ValueError:
                errors.append("AI_MAX_TOKENS must be a valid integer")
        
        if os.getenv('AI_TEMPERATURE'):
            try:
                self.AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE'))
                if not 0.0 <= self.AI_TEMPERATURE <= 2.0:
                    errors.append("AI_TEMPERATURE must be between 0.0 and 2.0")
            except ValueError:
                errors.append("AI_TEMPERATURE must be a valid float")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    def has_groq_api(self) -> bool:
        """Check if Groq API is configured"""
        return bool(self.GROQ_API_KEY)
    
    def has_openai_api(self) -> bool:
        """Check if OpenAI API is configured"""
        return bool(self.OPENAI_API_KEY)
    
    def has_perplexity_api(self) -> bool:
        """Check if Perplexity API is configured"""
        return bool(self.PERPLEXITY_API_KEY)
    
    def has_google_search(self) -> bool:
        """Check if Google Search is configured"""
        return bool(self.GOOGLE_API_KEY and self.GOOGLE_SEARCH_ENGINE_ID)
    
    def get_file_paths(self) -> dict:
        """Get all data file paths"""
        return {
            'history': self.HISTORY_FILE,
            'settings': self.SETTINGS_FILE,
            'permanent_context': self.PERMANENT_CONTEXT_FILE,
            'unfiltered_permanent_context': self.UNFILTERED_PERMANENT_CONTEXT_FILE
        }

# Global configuration instance
_config_instance = None

def get_config() -> Config:
    """Get or create the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def init_config() -> Config:
    """Initialize configuration with error handling"""
    global _config_instance
    try:
        _config_instance = Config()
        return _config_instance
    except Exception as e:
        print(f"[ERROR] Configuration Error: {e}")
        raise

# Create config instance on import, but handle errors gracefully
try:
    config = Config()
    print("[OK] Configuration loaded successfully")
except Exception as e:
    print(f"[WARNING] Configuration error: {e}")
    print("Some features may not work without proper configuration")
    # Create a minimal config object that won't crash on access
    config = None