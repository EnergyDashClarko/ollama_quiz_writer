import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional
import os
from pathlib import Path
from datetime import datetime

from .data_manager import DataManager
from .config_manager import ConfigManager
from .quiz_controller import QuizController

# Set up comprehensive logging
def setup_logging():
    """Set up comprehensive logging for debugging and monitoring."""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(logs_dir / "bot.log", encoding='utf-8'),  # File output
        ]
    )
    
    # Set up error-specific logging
    error_handler = logging.FileHandler(logs_dir / "errors.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s'
    ))
    
    # Add error handler to root logger
    logging.getLogger().addHandler(error_handler)
    
    # Set specific log levels for different components
    logging.getLogger('discord').setLevel(logging.WARNING)  # Reduce discord.py noise
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()

class QuizBot(commands.Bot):
    """Discord bot for conducting quizzes"""
    
    def __init__(self, config=None):
        # Set up intents - minimal intents for slash commands
        intents = discord.Intents.none()  # Start with no intents
        intents.guilds = True  # Required for slash commands
        # intents.message_content = True  # Enable this in Discord Developer Portal if needed
        
        # Use config for command prefix if available
        command_prefix = '!'
        if config and 'bot' in config:
            command_prefix = config['bot'].get('command_prefix', '!')
        
        super().__init__(
            command_prefix=command_prefix,  # Fallback prefix, mainly using slash commands
            intents=intents,
            help_command=None  # We'll implement our own help command
        )
        
        # Store configuration
        self.app_config = config or {}
        
        # Initialize core components
        self.data_manager: Optional[DataManager] = None
        self.config_manager: Optional[ConfigManager] = None
        self.quiz_controller: Optional[QuizController] = None
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            logger.info("Setting up bot components...")
            
            # Initialize managers
            self.data_manager = DataManager()
            self.config_manager = ConfigManager()
            
            # Apply configuration settings if available
            if self.app_config:
                await self.apply_configuration()
            
            self.quiz_controller = QuizController(self.data_manager, self.config_manager)
            
            # Load quiz data
            await self.load_quiz_data()
            
            # Register slash commands
            await self.setup_commands()
            
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise
    
    async def apply_configuration(self):
        """Apply settings from configuration file to managers."""
        try:
            quiz_config = self.app_config.get('quiz', {})
            
            # Set quiz directory
            quiz_directory = quiz_config.get('quiz_directory', './quizzes/')
            self.config_manager.set_quiz_directory(quiz_directory)
            
            # Set default question count
            default_question_count = quiz_config.get('default_question_count')
            if default_question_count is not None:
                self.config_manager.set_question_count(default_question_count)
            
            # Set default random order
            default_random_order = quiz_config.get('default_random_order', False)
            self.config_manager.set_random_order(default_random_order)
            
            # Set default timer duration
            default_timer_duration = quiz_config.get('default_timer_duration', 30)
            self.config_manager.set_timer_duration(default_timer_duration)
            
            logger.info("Configuration applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying configuration: {e}")
            # Don't raise - use defaults if config fails
    
    async def setup_commands(self):
        """Register all slash commands"""
        try:
            # Help command
            @self.tree.command(name="help", description="Display available commands and their descriptions")
            async def help_command(interaction: discord.Interaction):
                await self.handle_help(interaction)
            
            # Configuration commands
            @self.tree.command(name="set_questions", description="Set the number of questions for the next quiz")
            async def set_questions_command(interaction: discord.Interaction, number: int):
                await self.handle_set_questions(interaction, number)
            
            @self.tree.command(name="random_order", description="Toggle between random and sequential question order")
            async def random_order_command(interaction: discord.Interaction):
                await self.handle_random_order(interaction)
            
            @self.tree.command(name="set_timer", description="Set the timer duration for each question (5-300 seconds)")
            async def set_timer_command(interaction: discord.Interaction, seconds: int):
                await self.handle_set_timer(interaction, seconds)
            
            @self.tree.command(name="ollama_mix", description="LLM integration (currently disabled)")
            async def ollama_mix_command(interaction: discord.Interaction):
                await self.handle_ollama_mix(interaction)
            
            # Quiz control commands
            @self.tree.command(name="start", description="Start a quiz with current settings")
            async def start_command(interaction: discord.Interaction):
                await self.handle_start(interaction)
            
            @self.tree.command(name="stop", description="Stop the current quiz session")
            async def stop_command(interaction: discord.Interaction):
                await self.handle_stop(interaction)
            
            @self.tree.command(name="pause", description="Pause the current quiz session")
            async def pause_command(interaction: discord.Interaction):
                await self.handle_pause(interaction)
            
            @self.tree.command(name="resume", description="Resume the paused quiz session")
            async def resume_command(interaction: discord.Interaction):
                await self.handle_resume(interaction)
            
            @self.tree.command(name="status", description="Show current quiz status and progress")
            async def status_command(interaction: discord.Interaction):
                await self.handle_status(interaction)
            
            logger.info("Slash commands registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")
            raise
    
    async def load_quiz_data(self):
        """Load quiz files from the quizzes directory"""
        try:
            quiz_directory = self.config_manager.get_quiz_directory()
            # Update data manager's quiz directory
            self.data_manager.quiz_directory = Path(quiz_directory)
            # Load quiz files and get the loaded quizzes dict
            loaded_quizzes = self.data_manager.load_quiz_files()
            quiz_count = len(loaded_quizzes)
            logger.info(f"Loaded {quiz_count} quiz files from {quiz_directory}")
            
        except Exception as e:
            logger.error(f"Error loading quiz data: {e}")
            # Don't raise - bot can still function with error handling
    
    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        try:
            logger.info(f"Bot is ready! Logged in as {self.user}")
            logger.info(f"Bot is in {len(self.guilds)} guilds")
            
            # Add clear console output as suggested by Reddit user
            print(f"🤖 {self.user} is Ready and Online!")
            print(f"📊 Connected to {len(self.guilds)} server(s)")
            
            # Sync slash commands
            try:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
                print(f"⚡ Synced {len(synced)} slash commands")
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")
                print(f"❌ Failed to sync slash commands: {e}")
                
        except Exception as e:
            logger.error(f"Error in on_ready event: {e}")
            print(f"❌ Error in on_ready event: {e}")
    
    async def on_error(self, event, *args, **kwargs):
        """Handle general bot errors"""
        logger.error(f"An error occurred in event {event}", exc_info=True)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors with comprehensive error handling"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        logger.error(f"Command error in {ctx.command}: {error}")
        
        # Send user-friendly error message with retry logic
        await self.send_error_response_with_retry(
            ctx.send, 
            "An error occurred while processing your command. Please try again.",
            "❌ Command Error"
        )
    
    async def send_error_response(self, interaction: discord.Interaction, message: str, title: str = "Error"):
        """Send error response to user with fallback handling"""
        try:
            embed = discord.Embed(
                title=title,
                description=message,
                color=0xff0000
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except discord.HTTPException as e:
            logger.error(f"Failed to send error embed: {e}")
            # Fallback to simple message
            try:
                simple_message = f"{title}: {message}"
                if interaction.response.is_done():
                    await interaction.followup.send(simple_message, ephemeral=True)
                else:
                    await interaction.response.send_message(simple_message, ephemeral=True)
            except discord.HTTPException:
                logger.error("Failed to send fallback error message")
        except Exception as e:
            logger.error(f"Unexpected error sending error response: {e}")
    
    async def send_error_response_with_retry(self, send_func: callable, message: str, title: str = "Error", max_retries: int = 3):
        """Send error response with retry logic for Discord API failures"""
        for attempt in range(max_retries):
            try:
                embed = discord.Embed(
                    title=title,
                    description=message,
                    color=0xff0000
                )
                await send_func(embed=embed)
                return
                
            except discord.HTTPException as e:
                if attempt == max_retries - 1:
                    # Last attempt - try simple message
                    try:
                        await send_func(f"{title}: {message}")
                        return
                    except discord.HTTPException:
                        logger.error(f"All retry attempts failed for error message: {e}")
                        return
                
                # Wait before retry with exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Discord API error (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Unexpected error in retry logic: {e}")
                return
    
    async def handle_discord_api_error(self, error: Exception, operation: str, interaction: discord.Interaction = None) -> bool:
        """
        Handle Discord API errors with appropriate retry logic and user feedback.
        
        Args:
            error: The Discord API error
            operation: Description of the operation that failed
            interaction: Discord interaction object (optional)
            
        Returns:
            True if error was handled and operation should be retried, False otherwise
        """
        if isinstance(error, discord.HTTPException):
            if error.status == 429:  # Rate limited
                retry_after = getattr(error, 'retry_after', 5)
                logger.warning(f"Rate limited during {operation}, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return True
                
            elif error.status in [500, 502, 503, 504]:  # Server errors
                logger.warning(f"Discord server error during {operation}: {error.status}")
                await asyncio.sleep(2)
                return True
                
            elif error.status == 403:  # Forbidden
                logger.error(f"Permission denied during {operation}: {error}")
                if interaction:
                    await self.send_error_response(
                        interaction,
                        "Bot doesn't have permission to perform this action. Please check bot permissions.",
                        "❌ Permission Error"
                    )
                return False
                
            elif error.status == 404:  # Not found
                logger.error(f"Resource not found during {operation}: {error}")
                if interaction:
                    await self.send_error_response(
                        interaction,
                        "Channel or message not found. Please try again.",
                        "❌ Not Found"
                    )
                return False
                
            else:
                logger.error(f"Discord API error during {operation}: {error}")
                if interaction:
                    await self.send_error_response(
                        interaction,
                        "Discord API error occurred. Please try again in a moment.",
                        "❌ Discord Error"
                    )
                return False
        
        elif isinstance(error, discord.ConnectionClosed):
            logger.warning(f"Discord connection closed during {operation}")
            return True  # Will be handled by discord.py reconnection
            
        elif isinstance(error, asyncio.TimeoutError):
            logger.warning(f"Timeout during {operation}")
            if interaction:
                await self.send_error_response(
                    interaction,
                    "Operation timed out. Please try again.",
                    "❌ Timeout Error"
                )
            return False
            
        else:
            logger.error(f"Unexpected error during {operation}: {error}")
            if interaction:
                await self.send_error_response(
                    interaction,
                    "An unexpected error occurred. Please try again.",
                    "❌ Unexpected Error"
                )
            return False
    
    # Command handler stubs
    async def handle_help(self, interaction: discord.Interaction):
        """Handle /help command"""
        try:
            help_embed = discord.Embed(
                title="🎯 Команды Квиз Бота",
                description="Доступные команды для управления и проведения викторин",
                color=0x00ff00
            )
            
            # Configuration commands
            help_embed.add_field(
                name="📋 Команды Настройки",
                value=(
                    "`/help` - Показать это справочное сообщение\n"
                    "`/set_questions <число>` - Установить количество вопросов для следующей викторины\n"
                    "`/set_timer <секунды>` - Установить продолжительность таймера для каждого вопроса (5-300 сек)\n"
                    "`/random_order` - Переключить между случайным и последовательным порядком вопросов\n"
                    "`/ollama_mix` - Интеграция с LLM (в настоящее время отключена)"
                ),
                inline=False
            )
            
            # Quiz control commands
            help_embed.add_field(
                name="🎮 Команды Управления Викториной",
                value=(
                    "`/start` - Начать викторину с текущими настройками\n"
                    "`/stop` - Остановить текущую сессию викторины\n"
                    "`/pause` - Приостановить текущую сессию викторины\n"
                    "`/resume` - Возобновить приостановленную сессию викторины\n"
                    "`/status` - Показать текущий статус и прогресс викторины"
                ),
                inline=False
            )
            
            # Current settings
            settings_summary = self.config_manager.get_settings_summary()
            help_embed.add_field(
                name="⚙️ Текущие Настройки",
                value=f"```\n{settings_summary}\n```",
                inline=False
            )
            
            # Available quizzes
            available_quizzes = self.data_manager.get_available_quizzes()
            if available_quizzes:
                quiz_list = ", ".join(available_quizzes[:10])  # Show first 10
                if len(available_quizzes) > 10:
                    quiz_list += f" ... и ещё {len(available_quizzes) - 10}"
                help_embed.add_field(
                    name="📚 Доступные Викторины",
                    value=f"```\n{quiz_list}\n```",
                    inline=False
                )
            else:
                help_embed.add_field(
                    name="📚 Доступные Викторины",
                    value="```\nФайлы викторин не найдены. Добавьте JSON файлы в папку quizzes.\n```",
                    inline=False
                )
            
            help_embed.set_footer(text="Используйте слэш-команды для взаимодействия с ботом")
            
            await interaction.response.send_message(embed=help_embed)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await self.send_error_response(interaction, "Не удалось отобразить справочную информацию", "❌ Ошибка Справки")
    
    async def handle_set_questions(self, interaction: discord.Interaction, number: int):
        """Handle /set_questions command with enhanced error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use enhanced config manager validation
                result = self.config_manager.set_question_count(number)
                
                if result['success']:
                    # Success - provide confirmation with context
                    available_quizzes = self.data_manager.get_available_quizzes()
                    
                    # Check for data loading errors
                    if self.data_manager.has_load_errors():
                        load_errors = self.data_manager.get_load_errors()
                        logger.warning(f"Data loading errors present: {load_errors}")
                    
                    if available_quizzes:
                        # Show how this affects available quizzes
                        quiz_info = []
                        for quiz_name in available_quizzes[:5]:  # Show first 5 quizzes
                            quiz_count = self.data_manager.get_question_count(quiz_name)
                            actual_questions = min(number, quiz_count)
                            quiz_info.append(f"• {quiz_name}: {actual_questions}/{quiz_count} questions")
                        
                        quiz_info_text = "\n".join(quiz_info)
                        if len(available_quizzes) > 5:
                            quiz_info_text += f"\n... and {len(available_quizzes) - 5} more quizzes"
                        
                        embed = discord.Embed(
                            title="✅ Question Count Updated",
                            description=f"Set to use **{number}** questions per quiz",
                            color=0x00ff00
                        )
                        embed.add_field(
                            name="Impact on Available Quizzes",
                            value=quiz_info_text,
                            inline=False
                        )
                        
                        # Add warning if there were loading errors
                        if self.data_manager.has_load_errors():
                            embed.add_field(
                                name="⚠️ Loading Issues",
                                value="Some quiz files had loading errors. Check logs for details.",
                                inline=False
                            )
                        
                        await interaction.response.send_message(embed=embed)
                    else:
                        # No quizzes available - provide helpful guidance
                        embed = discord.Embed(
                            title="✅ Question Count Updated",
                            description=f"Set to use **{number}** questions per quiz",
                            color=0xffaa00
                        )
                        embed.add_field(
                            name="⚠️ No Quiz Files Found",
                            value="Add JSON files to the quizzes directory to start using quizzes.",
                            inline=False
                        )
                        
                        # Show loading errors if any
                        if self.data_manager.has_load_errors():
                            error_summary = "\n".join(self.data_manager.get_load_errors()[:3])
                            if len(self.data_manager.get_load_errors()) > 3:
                                error_summary += "\n... and more"
                            embed.add_field(
                                name="Loading Errors",
                                value=f"```\n{error_summary}\n```",
                                inline=False
                            )
                        
                        await interaction.response.send_message(embed=embed)
                else:
                    # Config manager validation failed
                    await interaction.response.send_message(
                        result.get('user_message', f"❌ Failed to set question count: {result.get('error', 'Unknown error')}"),
                        ephemeral=True
                    )
                
                return  # Success, exit retry loop
                
            except discord.HTTPException as e:
                if await self.handle_discord_api_error(e, "set_questions", interaction):
                    if attempt < max_retries - 1:
                        continue  # Retry
                return  # Don't retry further
                
            except Exception as e:
                logger.error(f"Error in set_questions command (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await self.send_error_response(interaction, "Failed to set question count", "❌ Configuration Error")
                else:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def handle_random_order(self, interaction: discord.Interaction):
        """Handle /random_order command with enhanced error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Toggle the random order setting with enhanced error handling
                result = self.config_manager.toggle_random_order()
                
                if result['success']:
                    new_value = result['new_value']
                    
                    # Create response with state feedback
                    order_type = "🔀 Random" if new_value else "📋 Sequential"
                    status_emoji = "✅" if new_value else "📝"
                    
                    embed = discord.Embed(
                        title=f"{status_emoji} Question Order Updated",
                        description=f"Questions will now be presented in **{order_type.lower()}** order",
                        color=0x00ff00 if new_value else 0x0099ff
                    )
                    
                    # Add explanation of what this means
                    if new_value:
                        embed.add_field(
                            name="🔀 Random Order",
                            value="Questions will be shuffled before each quiz starts",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="📋 Sequential Order", 
                            value="Questions will be presented in the order they appear in the quiz file",
                            inline=False
                        )
                    
                    # Show current settings summary
                    settings = self.config_manager.get_quiz_settings()
                    question_count_str = str(settings.question_count) if settings.question_count else "all available"
                    embed.add_field(
                        name="⚙️ Current Settings",
                        value=f"Questions: {question_count_str} | Order: {order_type.lower()} | Timer: {settings.timer_duration}s",
                        inline=False
                    )
                    
                    # Check configuration health
                    health_check = self.config_manager.get_configuration_health_check()
                    if not health_check['healthy']:
                        embed.add_field(
                            name="⚠️ Configuration Issues",
                            value="Some configuration issues detected. Use `/help` for details.",
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    # Configuration error
                    await interaction.response.send_message(
                        result.get('user_message', f"❌ Failed to toggle random order: {result.get('error', 'Unknown error')}"),
                        ephemeral=True
                    )
                
                return  # Success, exit retry loop
                
            except discord.HTTPException as e:
                if await self.handle_discord_api_error(e, "random_order", interaction):
                    if attempt < max_retries - 1:
                        continue  # Retry
                return  # Don't retry further
                
            except Exception as e:
                logger.error(f"Error in random_order command (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await self.send_error_response(interaction, "Failed to toggle random order", "❌ Configuration Error")
                else:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def handle_set_timer(self, interaction: discord.Interaction, seconds: int):
        """Handle /set_timer command with enhanced error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use enhanced config manager validation
                result = self.config_manager.set_timer_duration(seconds)
                
                if result['success']:
                    # Success - provide confirmation with context
                    embed = discord.Embed(
                        title="✅ Timer Duration Updated",
                        description=f"Each question will now have **{seconds} seconds** before the answer is revealed",
                        color=0x00ff00
                    )
                    
                    # Add helpful context about the timer setting
                    if seconds <= 10:
                        embed.add_field(
                            name="⚡ Quick Timer",
                            value="Fast-paced quiz! Players will need to think quickly.",
                            inline=False
                        )
                    elif seconds <= 30:
                        embed.add_field(
                            name="⏱️ Standard Timer",
                            value="Good balance between thinking time and quiz pace.",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🕐 Extended Timer",
                            value="Plenty of time for careful consideration of answers.",
                            inline=False
                        )
                    
                    # Show current settings summary
                    settings = self.config_manager.get_quiz_settings()
                    question_count_str = str(settings.question_count) if settings.question_count else "all available"
                    order_str = "random" if settings.random_order else "sequential"
                    
                    embed.add_field(
                        name="⚙️ Current Settings",
                        value=f"Questions: {question_count_str} | Order: {order_str} | Timer: {seconds}s",
                        inline=False
                    )
                    
                    # Check configuration health
                    health_check = self.config_manager.get_configuration_health_check()
                    if not health_check['healthy']:
                        embed.add_field(
                            name="⚠️ Configuration Issues",
                            value="Some configuration issues detected. Use `/help` for details.",
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    # Config manager validation failed
                    await interaction.response.send_message(
                        result.get('user_message', f"❌ Failed to set timer duration: {result.get('error', 'Unknown error')}"),
                        ephemeral=True
                    )
                
                return  # Success, exit retry loop
                
            except discord.HTTPException as e:
                if await self.handle_discord_api_error(e, "set_timer", interaction):
                    if attempt < max_retries - 1:
                        continue  # Retry
                return  # Don't retry further
                
            except Exception as e:
                logger.error(f"Error in set_timer command (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await self.send_error_response(interaction, "Failed to set timer duration", "❌ Configuration Error")
                else:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def handle_ollama_mix(self, interaction: discord.Interaction):
        """Handle /ollama_mix command"""
        try:
            # As per requirements, respond with specific message
            await interaction.response.send_message("LLM is not active at the moment. Select from existing quiz files instead")
        except Exception as e:
            logger.error(f"Error in ollama_mix command: {e}")
            await self.send_error_response(interaction, "Failed to process ollama_mix command", "❌ Command Error")
    
    async def handle_start(self, interaction: discord.Interaction):
        """Handle /start command with comprehensive error handling"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                channel_id = interaction.channel_id
                
                # Check data loading status
                loading_summary = self.data_manager.get_loading_summary()
                available_quizzes = loading_summary['available_quizzes']
                
                if not available_quizzes:
                    embed = discord.Embed(
                        title="❌ No Quizzes Available",
                        description="No quiz files found or all files failed to load.",
                        color=0xff0000
                    )
                    
                    # Show loading errors if any
                    if loading_summary['has_errors']:
                        error_text = "\n".join(loading_summary['errors'][:3])
                        if len(loading_summary['errors']) > 3:
                            error_text += "\n... and more"
                        embed.add_field(
                            name="Loading Errors",
                            value=f"```\n{error_text}\n```",
                            inline=False
                        )
                    
                    # Show fallback quiz info
                    if loading_summary['fallback_active']:
                        embed.add_field(
                            name="ℹ️ Fallback Quiz Available",
                            value="A basic fallback quiz is available for testing.",
                            inline=False
                        )
                    
                    embed.add_field(
                        name="How to add quizzes",
                        value="Add JSON files to the `quizzes/` directory with the following format:\n"
                              "```json\n"
                              "{\n"
                              '  "quiz": [\n'
                              '    {\n'
                              '      "question": "Your question here?",\n'
                              '      "answer": "Correct answer"\n'
                              '    }\n'
                              '  ]\n'
                              "}\n"
                              "```",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed)
                    return
                
                # For now, use the first available quiz (in future versions, we could add quiz selection)
                quiz_name = available_quizzes[0]
                
                # Start the quiz using the enhanced controller
                result = self.quiz_controller.start_quiz(channel_id, quiz_name)
                
                if result['success']:
                    session_info = result['session_info']
                    settings = session_info['settings']
                    
                    embed = discord.Embed(
                        title="🎯 Quiz Started!",
                        description=f"**{session_info['quiz_name']}**",
                        color=0x00ff00
                    )
                    
                    embed.add_field(
                        name="📊 Quiz Details",
                        value=(
                            f"Questions: {session_info['total_questions']}\n"
                            f"Order: {'🔀 Random' if settings['random_order'] else '📋 Sequential'}\n"
                            f"Timer: {settings['timer_duration']} seconds per question"
                        ),
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🎮 Controls",
                        value="Use `/pause` to pause, `/resume` to continue, or `/stop` to end the quiz",
                        inline=False
                    )
                    
                    # Add warning if using fallback quiz
                    if loading_summary['fallback_active']:
                        embed.add_field(
                            name="⚠️ Using Fallback Quiz",
                            value="This is a basic fallback quiz due to loading errors.",
                            inline=False
                        )
                    
                    embed.set_footer(text="Get ready for the first question!")
                    
                    await interaction.response.send_message(embed=embed)
                    
                    # Start presenting questions with error handling
                    await asyncio.sleep(2)  # Brief pause before first question
                    success = await self.quiz_controller.start_quiz_presentation(channel_id, interaction.channel)
                    
                    if not success:
                        # If presentation failed, send error message
                        error_embed = discord.Embed(
                            title="❌ Presentation Error",
                            description="Failed to start quiz presentation. The quiz session has been stopped.",
                            color=0xff0000
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
                        # Session is already cleaned up by the controller
                
                else:
                    # Handle error cases with user-friendly messages
                    user_message = result.get('user_message', result.get('message', 'Unknown error'))
                    
                    if result.get('recovery_attempted'):
                        if result.get('recovery_successful'):
                            # Recovery was successful, suggest retry
                            embed = discord.Embed(
                                title="⚠️ Issue Resolved",
                                description=f"{user_message}\n\nThe issue has been resolved. Please try starting the quiz again.",
                                color=0xffaa00
                            )
                        else:
                            # Recovery failed
                            embed = discord.Embed(
                                title="❌ Quiz Start Failed",
                                description=f"{user_message}\n\nAutomatic recovery was attempted but failed.",
                                color=0xff0000
                            )
                    else:
                        # No recovery attempted
                        embed = discord.Embed(
                            title="❌ Quiz Start Failed",
                            description=user_message,
                            color=0xff0000
                        )
                    
                    # Show current session info if available
                    session_info = self.quiz_controller.get_session_progress(channel_id)
                    if session_info:
                        embed.add_field(
                            name="Current Quiz",
                            value=f"**{session_info['quiz_name']}** - Question {session_info['current_question']}/{session_info['total_questions']}",
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                
                return  # Success, exit retry loop
                
            except discord.HTTPException as e:
                if await self.handle_discord_api_error(e, "start_quiz", interaction):
                    if attempt < max_retries - 1:
                        continue  # Retry
                return  # Don't retry further
                
            except Exception as e:
                logger.error(f"Error in start command (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await self.send_error_response(interaction, "Failed to start quiz", "❌ Quiz Start Error")
                else:
                    await asyncio.sleep(1)  # Brief pause before retry
    
    async def handle_stop(self, interaction: discord.Interaction):
        """Handle /stop command"""
        try:
            channel_id = interaction.channel_id
            
            # Stop the quiz using the controller
            result = self.quiz_controller.stop_quiz(channel_id)
            
            if result['success']:
                session_info = result['session_info']
                
                if session_info:
                    # Calculate completion percentage
                    completion_pct = int((session_info['current_question'] / session_info['total_questions']) * 100)
                    
                    # Calculate duration
                    duration = datetime.now() - session_info['start_time']
                    minutes = int(duration.total_seconds() // 60)
                    seconds = int(duration.total_seconds() % 60)
                    
                    embed = discord.Embed(
                        title="🛑 Quiz Stopped",
                        description=f"**{session_info['quiz_name']}** has been ended",
                        color=0xff6600
                    )
                    
                    embed.add_field(
                        name="📊 Final Stats",
                        value=(
                            f"Progress: {session_info['current_question']}/{session_info['total_questions']} questions ({completion_pct}%)\n"
                            f"Duration: {minutes}m {seconds}s"
                        ),
                        inline=False
                    )
                    
                    if completion_pct == 100:
                        embed.add_field(
                            name="🎉 Congratulations!",
                            value="You completed the entire quiz!",
                            inline=False
                        )
                    
                    embed.set_footer(text="Use /start to begin a new quiz")
                    
                    await interaction.response.send_message(embed=embed)
                else:
                    # Session info not available, simple confirmation
                    await interaction.response.send_message("✅ Quiz session stopped successfully.")
                    
            else:
                # No active session to stop
                embed = discord.Embed(
                    title="ℹ️ No Active Quiz",
                    description=result['message'],
                    color=0x6699ff
                )
                embed.add_field(
                    name="Start a Quiz",
                    value="Use `/start` to begin a new quiz session",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in stop command: {e}")
            await self.send_error_response(interaction, "Failed to stop quiz", "❌ Quiz Control Error")
    
    async def handle_pause(self, interaction: discord.Interaction):
        """Handle /pause command"""
        try:
            channel_id = interaction.channel_id
            
            # Pause the quiz using the controller
            result = self.quiz_controller.pause_quiz(channel_id)
            
            if result['success']:
                session_info = result['session_info']
                
                if "already paused" in result['message']:
                    embed = discord.Embed(
                        title="⏸️ Already Paused",
                        description="The quiz is already paused.",
                        color=0xffaa00
                    )
                else:
                    embed = discord.Embed(
                        title="⏸️ Quiz Paused",
                        description="The quiz has been paused.",
                        color=0xffaa00
                    )
                
                if session_info:
                    # Calculate progress percentage
                    progress_pct = int((session_info['current_question'] / session_info['total_questions']) * 100)
                    
                    embed.add_field(
                        name="📊 Current Progress",
                        value=(
                            f"Quiz: **{session_info['quiz_name']}**\n"
                            f"Question: {session_info['current_question']}/{session_info['total_questions']} ({progress_pct}%)\n"
                            f"Settings: {'🔀 Random' if session_info['settings']['random_order'] else '📋 Sequential'} | "
                            f"{session_info['settings']['timer_duration']}s timer"
                        ),
                        inline=False
                    )
                
                embed.add_field(
                    name="▶️ Resume",
                    value="Use `/resume` to continue the quiz",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # No active session to pause
                embed = discord.Embed(
                    title="ℹ️ No Active Quiz",
                    description=result['message'],
                    color=0x6699ff
                )
                embed.add_field(
                    name="Start a Quiz",
                    value="Use `/start` to begin a new quiz session",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in pause command: {e}")
            await self.send_error_response(interaction, "Failed to pause quiz", "❌ Quiz Control Error")
    
    async def handle_resume(self, interaction: discord.Interaction):
        """Handle /resume command"""
        try:
            channel_id = interaction.channel_id
            
            # Resume the quiz using the controller
            result = self.quiz_controller.resume_quiz(channel_id)
            
            if result['success']:
                session_info = result['session_info']
                
                if "not paused" in result['message']:
                    embed = discord.Embed(
                        title="▶️ Quiz Active",
                        description="The quiz is not paused and is currently active.",
                        color=0x00ff00
                    )
                else:
                    embed = discord.Embed(
                        title="▶️ Quiz Resumed",
                        description="The quiz has been resumed.",
                        color=0x00ff00
                    )
                
                if session_info:
                    # Calculate progress percentage
                    progress_pct = int((session_info['current_question'] / session_info['total_questions']) * 100)
                    
                    embed.add_field(
                        name="📊 Current Progress",
                        value=(
                            f"Quiz: **{session_info['quiz_name']}**\n"
                            f"Question: {session_info['current_question']}/{session_info['total_questions']} ({progress_pct}%)\n"
                            f"Settings: {'🔀 Random' if session_info['settings']['random_order'] else '📋 Sequential'} | "
                            f"{session_info['settings']['timer_duration']}s timer"
                        ),
                        inline=False
                    )
                
                embed.add_field(
                    name="🎮 Controls",
                    value="Use `/pause` to pause again or `/stop` to end the quiz",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # No active session to resume
                embed = discord.Embed(
                    title="ℹ️ No Active Quiz",
                    description=result['message'],
                    color=0x6699ff
                )
                embed.add_field(
                    name="Start a Quiz",
                    value="Use `/start` to begin a new quiz session",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in resume command: {e}")
            await self.send_error_response(interaction, "Failed to resume quiz", "❌ Quiz Control Error")
    
    async def handle_status(self, interaction: discord.Interaction):
        """Handle /status command"""
        try:
            channel_id = interaction.channel_id
            
            # Get session progress
            session_info = self.quiz_controller.get_session_progress(channel_id)
            
            if session_info is None:
                embed = discord.Embed(
                    title="ℹ️ No Active Quiz",
                    description="There is no active quiz session in this channel.",
                    color=0x6699ff
                )
                
                # Show available quizzes
                available_quizzes = self.data_manager.get_available_quizzes()
                if available_quizzes:
                    quiz_list = ", ".join(available_quizzes[:5])
                    if len(available_quizzes) > 5:
                        quiz_list += f" ... and {len(available_quizzes) - 5} more"
                    embed.add_field(
                        name="📚 Available Quizzes",
                        value=quiz_list,
                        inline=False
                    )
                
                embed.add_field(
                    name="🎯 Start a Quiz",
                    value="Use `/start` to begin a new quiz session",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Calculate progress percentage
            progress_pct = int((session_info['current_question'] / session_info['total_questions']) * 100)
            
            # Determine status color and emoji
            if session_info['is_paused']:
                status_color = 0xffaa00
                status_emoji = "⏸️"
                status_text = "Paused"
            elif session_info['is_active']:
                status_color = 0x00ff00
                status_emoji = "▶️"
                status_text = "Active"
            else:
                status_color = 0x6699ff
                status_emoji = "✅"
                status_text = "Completed"
            
            # Create status embed
            embed = discord.Embed(
                title=f"{status_emoji} Quiz Status - {status_text}",
                description=f"**{session_info['quiz_name']}**",
                color=status_color
            )
            
            # Add progress information
            embed.add_field(
                name="📊 Progress",
                value=(
                    f"Question: {session_info['current_question']}/{session_info['total_questions']}\n"
                    f"Completion: {progress_pct}%"
                ),
                inline=True
            )
            
            # Add timing information
            start_time = session_info['start_time']
            duration = datetime.now() - start_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            
            embed.add_field(
                name="⏱️ Timing",
                value=(
                    f"Duration: {minutes}m {seconds}s\n"
                    f"Timer: {session_info['settings']['timer_duration']}s per question"
                ),
                inline=True
            )
            
            # Add settings information
            embed.add_field(
                name="⚙️ Settings",
                value=(
                    f"Order: {'🔀 Random' if session_info['settings']['random_order'] else '📋 Sequential'}\n"
                    f"Questions: {session_info['settings']['question_count'] or 'All available'}"
                ),
                inline=True
            )
            
            # Add control information based on status
            if session_info['is_active'] and not session_info['is_paused']:
                embed.add_field(
                    name="🎮 Available Controls",
                    value="Use `/pause` to pause or `/stop` to end the quiz",
                    inline=False
                )
            elif session_info['is_paused']:
                embed.add_field(
                    name="🎮 Available Controls",
                    value="Use `/resume` to continue or `/stop` to end the quiz",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 Start New Quiz",
                    value="Use `/start` to begin a new quiz session",
                    inline=False
                )
            
            # Add timer status if there's an active timer
            timer_status = self.quiz_controller.quiz_engine.get_timer_status(str(channel_id))
            if timer_status and session_info['is_active'] and not session_info['is_paused']:
                embed.add_field(
                    name="⏰ Current Timer",
                    value=f"{timer_status['remaining_time']} seconds remaining",
                    inline=False
                )
            
            embed.set_footer(text="Use /help to see all available commands")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await self.send_error_response(interaction, "Failed to get quiz status", "❌ Status Error")
    
    async def send_error_response(self, interaction: discord.Interaction, message: str, title: str = "❌ Error"):
        """Send formatted error response to user"""
        try:
            embed = discord.Embed(
                title=title,
                description=message,
                color=0xff0000
            )
            embed.set_footer(text="If this error persists, try using /help for available commands")
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            logger.error("Failed to send error response to user")
    
    async def send_info_response(self, interaction: discord.Interaction, message: str, title: str = "ℹ️ Information"):
        """Send formatted info response to user"""
        try:
            embed = discord.Embed(
                title=title,
                description=message,
                color=0x6699ff
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            logger.error("Failed to send info response to user")
    
    async def send_warning_response(self, interaction: discord.Interaction, message: str, title: str = "⚠️ Warning"):
        """Send formatted warning response to user"""
        try:
            embed = discord.Embed(
                title=title,
                description=message,
                color=0xffaa00
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            logger.error("Failed to send warning response to user")

# Bot instance
async def run_bot(token=None, config=None):
    """Run the bot with proper error handling"""
    # Fall back to environment variable if no token provided
    if not token:
        token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        logger.error("No Discord bot token provided")
        return
    
    # Create bot instance with optional config
    bot = QuizBot(config)
    
    try:
        logger.info("Starting Discord Quiz Bot...")
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token provided")
    except discord.HTTPException as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        # Just log the error but don't treat it as fatal
        # The privileged intents message is a warning, not an error
        logger.warning(f"Bot startup message: {e}")
        print(f"ℹ️  Bot message: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(run_bot())