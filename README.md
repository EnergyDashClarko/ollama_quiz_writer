# Discord Quiz Bot

An interactive Discord bot that conducts timed quizzes using questions from JSON files. Perfect for educational servers, trivia nights, or just having fun with friends!

## Features

- 🎯 **Interactive Quizzes**: Timed questions with automatic answer reveals
- 📚 **Multiple Quiz Files**: Support for different themed quizzes
- ⚙️ **Configurable Settings**: Customize question count, order, and timing
- 🔀 **Random or Sequential**: Choose how questions are presented
- ⏱️ **Countdown Timers**: Real-time countdown with visual updates
- 🎮 **Session Control**: Start, stop, pause, and resume quizzes
- 📊 **Status Tracking**: Monitor quiz progress and settings
- 🛡️ **Error Handling**: Graceful handling of invalid files and network issues

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- A Discord bot token ([Get one here](https://discord.com/developers/applications))

### 2. Installation

```bash
# Clone or download the project
git clone <repository-url>
cd discord-quiz-bot

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

#### Option A: Using config.json (Recommended)
1. Edit `config.json` and replace `YOUR_DISCORD_BOT_TOKEN_HERE` with your actual bot token
2. Customize other settings as needed

#### Option B: Using Environment Variables
1. Copy `.env.example` to `.env`
2. Set your `DISCORD_BOT_TOKEN` in the `.env` file

### 4. Run the Bot

#### Option A: Direct Python Execution
```bash
python main.py
```

#### Option B: Docker Deployment (Recommended for Production)

**Quick Docker Setup:**
```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your Discord bot token
# DISCORD_BOT_TOKEN=your_actual_bot_token_here

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

**For detailed Docker deployment instructions, see [Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md)**

## Discord Server Setup

### Bot Permissions

Your bot needs the following permissions in your Discord server:

**Required Permissions:**
- `Send Messages` - To send quiz questions and responses
- `Use Slash Commands` - To register and respond to slash commands
- `Embed Links` - To send formatted quiz messages
- `Read Message History` - To edit countdown messages

**Recommended Permissions:**
- `Manage Messages` - To clean up quiz messages (optional)

### Inviting the Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application/bot
3. Go to "OAuth2" → "URL Generator"
4. Select scopes: `bot` and `applications.commands`
5. Select the permissions listed above
6. Use the generated URL to invite your bot to your server

## Usage

### Available Commands

#### Configuration Commands
- `/help` - Display all available commands and current settings
- `/set_questions <number>` - Set how many questions to use per quiz
- `/set_timer <seconds>` - Set timer duration for each question (5-300 seconds)
- `/random_order` - Toggle between random and sequential question order
- `/ollama_mix` - LLM integration (currently disabled)

#### Quiz Control Commands
- `/start` - Start a quiz with current settings
- `/stop` - Stop the current quiz session
- `/pause` - Pause the current quiz
- `/resume` - Resume a paused quiz
- `/status` - Show current quiz status and progress

### Example Usage

```
/set_questions 5          # Use 5 questions per quiz
/set_timer 45             # Set 45 seconds per question
/random_order             # Enable random question order
/start                    # Start the quiz
```

## Quiz Files

### File Format

Quiz files are JSON files stored in the `quizzes/` directory. Here's the format:

```json
{
  "quiz": [
    {
      "question": "What is the capital of France?",
      "answer": "Paris",
      "options": ["London", "Berlin", "Paris", "Madrid"]
    },
    {
      "question": "What is 2 + 2?",
      "answer": "4"
    }
  ]
}
```

### Field Descriptions

- `question` (required): The question text
- `answer` (required): The correct answer
- `options` (optional): Multiple choice options (reserved for future use)

### Sample Quiz Files

The bot comes with several sample quiz files:

- `sample_quiz.json` - Basic example questions
- `science_quiz.json` - Science and nature questions
- `history_quiz.json` - Historical events and figures
- `basic_test_quiz.json` - Simple questions for testing

### Creating Your Own Quizzes

1. Create a new `.json` file in the `quizzes/` directory
2. Follow the format shown above
3. Restart the bot or use `/help` to see the new quiz in the available list

### Quiz File Guidelines

- **File naming**: Use descriptive names like `geography_quiz.json`
- **Question length**: Keep questions concise but clear
- **Answer format**: Answers should be exact matches (case-insensitive)
- **File size**: No strict limit, but consider user experience for very long quizzes

## Configuration

### config.json Structure

```json
{
  "bot": {
    "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
    "command_prefix": "!",
    "description": "Discord Quiz Bot - Interactive quiz sessions"
  },
  "quiz": {
    "default_question_count": null,
    "default_random_order": false,
    "default_timer_duration": 10,
    "quiz_directory": "./quizzes/"
  },
  "logging": {
    "level": "INFO",
    "log_directory": "./logs/",
    "max_log_files": 5,
    "max_log_size_mb": 10
  }
}
```

### Configuration Options

#### Bot Settings
- `token`: Your Discord bot token
- `command_prefix`: Prefix for text commands (mainly uses slash commands)
- `description`: Bot description

#### Quiz Settings
- `default_question_count`: Default number of questions (null = all questions)
- `default_random_order`: Whether to randomize questions by default
- `default_timer_duration`: Seconds per question (5-300)
- `quiz_directory`: Path to quiz files directory

#### Logging Settings
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `log_directory`: Where to store log files
- `max_log_files`: Maximum number of log files to keep
- `max_log_size_mb`: Maximum size per log file

## Troubleshooting

### Common Issues

#### "No Discord bot token provided"
- **Solution**: Set your token in `config.json` or as an environment variable

#### "No quiz files found"
- **Solution**: Add `.json` files to the `quizzes/` directory
- **Check**: File format matches the required structure

#### "Bot doesn't respond to commands"
- **Solution**: Ensure the bot has proper permissions in your server
- **Check**: Bot is online and slash commands are synced

#### "Invalid JSON in quiz file"
- **Solution**: Validate your JSON syntax using a JSON validator
- **Check**: All quotes are properly closed and commas are correct

### Log Files

The bot creates detailed logs in the `logs/` directory:

- `bot.log` - General bot activity and information
- `errors.log` - Error-specific logs for debugging

### Getting Help

1. Check the logs in the `logs/` directory
2. Use `/help` command to see current bot status
3. Verify your quiz files are valid JSON
4. Ensure bot permissions are correctly set

## Docker Deployment

### Quick Docker Start

The easiest way to deploy the bot is using Docker:

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env and add your DISCORD_BOT_TOKEN

# 2. Start the bot
docker-compose up -d

# 3. Monitor logs
docker-compose logs -f

# 4. Stop the bot
docker-compose down
```

### Docker Deployment Options

- **Development**: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d`
- **Production**: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

### Docker Benefits

- ✅ **Isolated Environment**: No Python version conflicts
- ✅ **Easy Deployment**: One command to start
- ✅ **Automatic Restarts**: Bot restarts if it crashes
- ✅ **Resource Limits**: Controlled memory and CPU usage
- ✅ **Log Management**: Automatic log rotation
- ✅ **Security**: Runs as non-root user

For comprehensive Docker deployment instructions, troubleshooting, and advanced configurations, see the **[Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md)**.

## Development

### Project Structure

```
discord-quiz-bot/
├── src/                    # Source code
│   ├── bot.py             # Main bot class and Discord integration
│   ├── quiz_controller.py # Quiz session management
│   ├── quiz_engine.py     # Quiz logic and timing
│   ├── data_manager.py    # JSON file handling
│   ├── config_manager.py  # Configuration management
│   └── models.py          # Data models
├── tests/                 # Test files
├── quizzes/              # Quiz JSON files
├── logs/                 # Log files (created automatically)
├── config.json           # Configuration file
├── requirements.txt      # Python dependencies
└── main.py              # Entry point
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_quiz_engine.py

# Run with coverage
python -m pytest tests/ --cov=src
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is open source. See the LICENSE file for details.

## Support

For support, please:
1. Check this README and troubleshooting section
2. Review the log files for error details
3. Open an issue on the project repository