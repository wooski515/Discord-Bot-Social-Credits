# Social Credit Bot for Discord

A Disnake-based Discord bot that implements a "Social Credit" system for your server. Admins can grant and deduct Social Credits, and all users can check anyone's credit score. The bot also features an automatic penalty system for using predefined forbidden words, assigns roles based on credit scores, and applies timeouts for very low scores.

## Features

*   **Social Credit Management**:
    *   Admins can `/socialcredit admin give <user> <amount>` credits.
    *   Admins can `/socialcredit admin take <user> <amount>` credits.
    *   Admins can `/socialcredit admin set <user> <amount>` credits to an exact value.
*   **Credit Checking**:
    *   Any user can `/socialcredit check [user]` to see their own or another user's credit score and rank.
*   **Social Ranks & Roles**:
    *   Users are assigned roles based on their Social Credit score (configurable).
*   **Automatic Penalties for Forbidden Words**:
    *   Automatically deducts credits if a user posts a message containing predefined forbidden words/patterns.
    *   The offending message is deleted.
    *   The user receives a DM and a public shaming message is posted.
*   **Dynamic Timeouts**:
    *   Users with significantly negative credit scores receive a timeout. The duration increases with lower scores (10 minutes per -1000 credits).
    *   Timeout is automatically lifted if credits become non-negative.
*   **Leaderboard**:
    *   `/socialcredit leaderboard [top_n]` shows the top citizens by Social Credit.
*   **Naughty List**:
    *   `/socialcredit naughtylist [top_n]` shows citizens who have used forbidden words most often.
*   **Data Persistence**:
    *   Social credits and forbidden word statistics are saved in JSON files (`social_credits.json`, `forbidden_word_stats.json`).
*   **Configurable**:
    *   Default starting credits.
    *   Forbidden words/patterns (using regular expressions).
    *   Penalty amount for forbidden words.
    *   Social ranks, their credit thresholds, icons, and associated role names.

## Prerequisites

*   Python 3.8 or higher.
*   A Discord Bot Token.
*   A Discord Server where you have administrative privileges.

## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
    cd YOUR_REPOSITORY_NAME
    ```

2.  **Create a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    The bot uses `disnake`.
    ```bash
    pip install disnake
    ```

4.  **Configure the Bot**:
    *   Open the bot's Python file (e.g., `social_credit_bot.py`).
    *   **Bot Token**: Find the line `BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"` and replace `"YOUR_BOT_TOKEN_HERE"` with your actual Discord bot token.
        *   *How to get a Bot Token*:
            1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
            2.  Create a "New Application".
            3.  Go to the "Bot" tab and click "Add Bot".
            4.  Under the "TOKEN" section, click "Copy". **Keep this token secret!**
    *   **(Optional) Default Credits**: Modify `DEFAULT_CREDITS = 1000` if you want a different starting amount.
    *   **(Crucial) Forbidden Words/Patterns**:
        *   Locate the `FORBIDDEN_PATTERN_REGEX` variable.
        *   Modify the regular expression to match the words/phrases you want to penalize.
            *Example*: To penalize "apple" and "banana" (case-insensitive, whole words):
            ```python
            FORBIDDEN_PATTERN_REGEX = re.compile(
                r"\b(apple|banana)\b",
                re.IGNORECASE | re.UNICODE
            )
            ```
        *   Adjust `FORBIDDEN_WORD_PENALTY = 1000` for the credit deduction amount.
    *   **(Crucial) Social Ranks and Roles**:
        *   Find the `SOCIAL_RANKS` list. Each entry is a tuple:
            `(credit_threshold, display_name, icon, server_role_name)`
        *   **You MUST create roles on your Discord server with names that EXACTLY match the `server_role_name` strings in this list.**
            *Example*: For `(-float('inf'), "Social Outcast", "🚫", "Social Outcast")`, you need a role named "Social Outcast" on your server.
        *   Adjust credit thresholds, display names, icons, and role names as needed.

5.  **Bot Permissions on Discord Developer Portal**:
    When inviting your bot or configuring it in the Developer Portal, ensure it has the following **Privileged Gateway Intents** enabled:
    *   `Presence Intent` (Not strictly needed for current features, but often useful)
    *   `Server Members Intent` (CRUCIAL for accessing member information)
    *   `Message Content Intent` (CRUCIAL for reading messages to detect forbidden words)

6.  **Invite the Bot to Your Server**:
    *   In the Discord Developer Portal, go to your application -> "OAuth2" -> "URL Generator".
    *   Select the following scopes:
        *   `bot`
        *   `applications.commands` (for slash commands)
    *   Select the following Bot Permissions:
        *   `Read Messages/View Channels`
        *   `Send Messages`
        *   `Embed Links`
        *   `Manage Messages` (to delete forbidden word messages)
        *   `Moderate Members` (to apply timeouts)
        *   `Manage Roles` (to assign rank roles)
        *   (Consider `Read Message History` if not covered by `Read Messages/View Channels` for your specific setup)
    *   Copy the generated URL and paste it into your browser to invite the bot to your server.
    *   **Important**: The bot's role in your server's role hierarchy must be higher than the rank roles it needs to manage.

7.  **Run the Bot**:
    ```bash
    python your_bot_file_name.py 
    ```
    (e.g., `python social_credit_bot.py`)

## Usage

All commands are slash commands.

### General Commands

*   `/socialcredit check [user]`
    *   Description: Checks the Social Credit score and rank of yourself or another specified user.
    *   Parameters:
        *   `user` (Optional): The user whose credits you want to check. If omitted, checks your own.

*   `/socialcredit leaderboard [top_n]`
    *   Description: Displays the top citizens by Social Credit score.
    *   Parameters:
        *   `top_n` (Optional): Number of users to display (default: 10, min: 3, max: 20).

*   `/socialcredit naughtylist [top_n]`
    *   Description: Displays citizens who have most frequently used forbidden words.
    *   Parameters:
        *   `top_n` (Optional): Number of users to display (default: 10, min: 3, max: 20).

### Admin Commands

*(Require Administrator permissions on the server)*

*   `/socialcredit admin give <user> <amount>`
    *   Description: Awards Social Credits to a specified user.
    *   Parameters:
        *   `user`: The user to give credits to.
        *   `amount`: The number of credits to give (must be positive).

*   `/socialcredit admin take <user> <amount>`
    *   Description: Deducts Social Credits from a specified user.
    *   Parameters:
        *   `user`: The user to take credits from.
        *   `amount`: The number of credits to take (must be positive).

*   `/socialcredit admin set <user> <amount>`
    *   Description: Sets a user's Social Credit score to an exact value.
    *   Parameters:
        *   `user`: The user whose credits to set.
        *   `amount`: The exact credit score to set.

## Data Storage

*   `social_credits.json`: Stores the Social Credit scores for users on each server.
*   `forbidden_word_stats.json`: Stores statistics about forbidden word usage by users on each server.

These files will be created automatically in the same directory as the bot script if they don't exist.


*This bot is intended for entertainment purposes. Please use responsibly.*
