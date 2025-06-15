# Telegram Stars Gift Bot

## Project Overview

The Telegram Stars Gift Bot is designed to automate the process of gifting Telegram Premium subscriptions to users using Telegram Stars. It periodically checks for available limited-time gift options on Telegram, allows users to express their gift preferences, and automatically attempts to purchase and send these gifts to eligible users based on their star balance and queue status.

Users can send Stars to the bot, check their balance, manage their gift preferences, and opt-in or opt-out of the automatic gifting queue.

## Features

*   Receive Stars from users and update their balance.
*   Periodically discover available limited Telegram Premium gift options.
*   Allow users to set preferred gifts.
*   Automatically purchase gifts for users in a queue, prioritizing preferences and then affordability.
*   User commands to check balance, manage preferences, and control queue status.
*   Configurable via environment variables.
*   Logging for monitoring and troubleshooting.

## Prerequisites

*   Python 3.8+
*   A Telegram account.
*   A MongoDB instance (e.g., a free tier on MongoDB Atlas or a self-hosted instance).

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <your_repository_url> # Replace <your_repository_url> with the actual URL
    cd telegram-stars-gift-bot # Or your repository's directory name
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate    # On Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the environment file:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file with your specific credentials and configuration.

5.  **Obtain Telegram API Credentials:**
    *   Go to [my.telegram.org](https://my.telegram.org/apps).
    *   Log in with your Telegram account.
    *   Click on "API development tools" and fill out the form.
    *   You will receive your `API_ID` and `API_HASH`. Add these to your `.env` file.

6.  **Create a Telegram Bot and Get Token:**
    *   Open Telegram and search for `@BotFather`.
    *   Start a chat with BotFather and send the `/newbot` command.
    *   Follow the instructions to choose a name and username for your bot.
    *   BotFather will provide you with a `BOT_TOKEN`. Add this to your `.env` file.

7.  **Set up MongoDB:**
    *   **Option 1: MongoDB Atlas (Cloud - Recommended for ease of use):**
        *   Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and create a free account.
        *   Create a new free tier cluster (e.g., M0).
        *   In your cluster, go to "Database Access" and create a new database user with a username and password.
        *   Go to "Network Access" and add your current IP address to the IP whitelist (or allow access from anywhere: `0.0.0.0/0` - less secure, use with caution).
        *   Go to "Databases", click "Connect" for your cluster, choose "Connect your application", and select "Python" as the driver. Copy the connection string.
        *   Replace `<username>`, `<password>`, and other placeholders in the connection string with your actual credentials. This is your `MONGO_CONNECTION_STRING`.
        *   Choose a name for your database (e.g., `telegram_gift_bot`). This is your `MONGO_DATABASE_NAME`.
    *   **Option 2: Self-hosted MongoDB:**
        *   Install and run a MongoDB server.
        *   Create a database and a user with read/write permissions to that database.
        *   Construct your `MONGO_CONNECTION_STRING` (e.g., `mongodb://username:password@localhost:27017/your_database_name`).
        *   Set `MONGO_DATABASE_NAME` to your chosen database name.
    *   Add `MONGO_CONNECTION_STRING` and `MONGO_DATABASE_NAME` to your `.env` file.

## Configuration

The bot is configured using environment variables defined in the `.env` file:

*   `API_ID`: Your Telegram API ID.
*   `API_HASH`: Your Telegram API Hash.
*   `BOT_TOKEN`: Your Telegram Bot Token.
*   `MONGO_CONNECTION_STRING`: Connection string for your MongoDB instance.
    *   Example: `mongodb+srv://<username>:<password>@<cluster-url>/<default_db_name>?retryWrites=true&w=majority` (for Atlas)
    *   Example: `mongodb://localhost:27017/` (for local MongoDB without auth)
*   `MONGO_DATABASE_NAME`: The name of the MongoDB database the bot will use (e.g., `telegram_gift_bot`).
*   `POLLING_INTERVAL_SECONDS`: Interval in seconds for checking for new gifts (e.g., `300` for 5 minutes). Defaults to `300`.
*   `LOG_LEVEL`: Logging level for the application (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`). Defaults to `INFO`.

## Running the Bot

Once you have set up your `.env` file, you can run the bot with:

```bash
python bot.py
```

The bot will log its activities to the console.

## Available Commands

*   `/start`: Shows a welcome message and basic instructions.
*   `/help`: Lists all available commands and their functions.
*   `/mystars`: Check your current star balance.
*   `/set_preferred_gift <gift_id>`: Add a specific gift ID to your preferences. `<gift_id>` is a numerical ID of a Telegram Premium gift option.
*   `/my_preferences`: Show your currently set gift preferences.
*   `/clear_my_preferences`: Clear all your saved gift preferences.
*   `/join_queue`: Opt-in to be considered for automatic gift purchases by the bot.
*   `/leave_queue`: Opt-out from being considered for automatic gift purchases.

## Troubleshooting (Basic)

*   **Bot not starting / Authentication errors**:
    *   Double-check your `API_ID`, `API_HASH`, and `BOT_TOKEN` in the `.env` file.
    *   Ensure your bot token is correct and the bot hasn't been revoked.
*   **Database connection errors**:
    *   Verify your `MONGO_CONNECTION_STRING` is correct.
    *   If using MongoDB Atlas, ensure your IP address is whitelisted and the user credentials are correct.
    *   Ensure your MongoDB server is running if self-hosting.
*   **Command not working**:
    *   Check the bot logs (`python bot.py` output) for any error messages.
    *   Ensure you are using the commands correctly as listed in `/help`.
*   **Telethon Session File (`.session`)**:
    *   Telethon creates a session file (e.g., `stars_bot_session.session`) to store authorization keys. This file should ideally be persisted in a deployment environment or be excluded via `.gitignore` if you intend for the bot to re-authenticate (which is usually seamless for bot tokens). For user accounts, losing this file requires re-login.
*   **Permissions**: Ensure the bot has necessary permissions in chats if it's part of any groups (though this bot primarily interacts via direct messages).

---

This README provides a comprehensive guide to setting up and running the Telegram Stars Gift Bot.
