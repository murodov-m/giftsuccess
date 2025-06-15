import asyncio
import os
import re
from datetime import datetime
import logging

from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from telethon import TelegramClient, events
from telethon.tl.types import MessageService, MessageActionPaymentSent, InputPeerSelf, InputUser, InputStorePaymentPremiumGiftCode
# DataJSON might not be directly needed if we pass structured data that Telethon serializes.
# from telethon.tl.types import DataJSON
from telethon.tl.functions.payments import GetPremiumGiftCodeOptionsRequest, PurchasePremiumGiftCodeRequest
from telethon.errors import RPCError

# Load environment variables
load_dotenv()

# Global variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_NAME = "stars_bot_session"
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
MONGO_DATABASE_NAME = os.getenv("MONGO_DATABASE_NAME", "telegram_gift_bot")
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", 300)) # Default to 5 minutes

# Initialize TelegramClient
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# MongoDB database instance
db = None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Collections conceptual definition:
# users: {
# 'user_id': int, # Telegram User ID, Primary Key
# 'star_balance': int, # Current number of stars the user has
# 'last_activity_timestamp': datetime, # Timestamp of the last user activity
# 'preferred_gift_ids': list, # List of gift IDs the user prefers
# 'in_gift_queue': bool # Whether the user is currently in the gift queue
# }
# app_config: {
# 'key': str, # Configuration key, e.g., "last_checked_gift_timestamp"
# 'value': any # Configuration value
# }

def get_mongo_db():
    """Initializes a MongoClient and returns the database instance."""
    mongo_client = MongoClient(MONGO_CONNECTION_STRING)
    return mongo_client[MONGO_DATABASE_NAME]

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handles the /start command."""
    # Example of how to interact with the database (optional here, can be expanded later)
    # user_id = event.sender_id
    # users_collection = db.users
    # user_data = await users_collection.find_one({'user_id': user_id})
    # if not user_data:
    #     await users_collection.insert_one({
    #         'user_id': user_id,
    #         'star_balance': 0,
    #         'last_activity_timestamp': datetime.utcnow(),
    #         'preferred_gift_ids': [],
    #         'in_gift_queue': True
    #     })
    await event.reply("Welcome to the Stars Bot! Here's how to get started:\n"
                      "- Use /mystars to check your star balance.\n"
                      "- Use /help to see all available commands.")

@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    """Handles the /help command."""
    await event.reply("Available commands:\n"
                      "- /start: Show welcome message and basic instructions.\n"
                      "- /help: Show this help message.\n"
                      "- /mystars: Check your current star balance.\n"
                      "- /set_preferred_gift <gift_id>: Add a gift ID to your preferences.\n"
                      "- /my_preferences: Show your current gift preferences.\n"
                      "- /clear_my_preferences: Clear all your gift preferences.\n"
                      "- /join_queue: Opt-in to be considered for automatic gift purchases.\n"
                      "- /leave_queue: Opt-out from being considered for automatic gift purchases.")

@client.on(events.NewMessage(pattern='/mystars'))
async def mystars_handler(event):
    """Handles the /mystars command to check star balance."""
    user_id = event.sender_id
    try:
        user_doc = await db.users.find_one({'user_id': user_id})
        if user_doc:
            star_balance = user_doc.get('star_balance', 0)
            await event.reply(f"Your current star balance is: {star_balance} Stars.")
        else:
            await event.reply("I don't have a record of your star balance yet. Try sending some Stars to the bot first, or use /join_queue to create a record!")
    except Exception as e:
        logging.error(f"Error in /mystars for user {user_id}: {e}", exc_info=True)
        await event.reply("Sorry, I couldn't retrieve your star balance at this time.")

@client.on(events.NewMessage(pattern='/join_queue'))
async def join_queue_handler(event):
    """Handles the /join_queue command."""
    user_id = event.sender_id
    try:
        update_result = await db.users.update_one(
            {'user_id': user_id},
            {
                '$set': {'in_gift_queue': True, 'last_activity_timestamp': datetime.utcnow()},
                '$setOnInsert': {'star_balance': 0, 'preferred_gift_ids': [], 'user_id': user_id}
            },
            upsert=True
        )
        if update_result.acknowledged:
            if update_result.upserted_id:
                logging.info(f"User {user_id} joined queue (new user created).")
                await event.reply("You are now in the queue and will be considered for gifts! Since you're new, your star balance is 0.")
            else:
                logging.info(f"User {user_id} re-joined or confirmed in queue.")
                await event.reply("You are now in the queue and will be considered for gifts.")
        else:
            logging.error(f"Failed to acknowledge /join_queue for user {user_id}")
            await event.reply("Sorry, there was an issue processing your request. Please try again.")
    except Exception as e:
        logging.error(f"Error in /join_queue for user {user_id}: {e}", exc_info=True)
        await event.reply("An error occurred while trying to join the queue. Please try again later.")

@client.on(events.NewMessage(pattern='/leave_queue'))
async def leave_queue_handler(event):
    """Handles the /leave_queue command."""
    user_id = event.sender_id
    try:
        update_result = await db.users.update_one(
            {'user_id': user_id},
            {
                '$set': {'in_gift_queue': False, 'last_activity_timestamp': datetime.utcnow()}
            },
            upsert=False # Do not create a user if they don't exist
        )
        if update_result.acknowledged:
            if update_result.matched_count > 0:
                logging.info(f"User {user_id} left queue.")
                await event.reply("You have been removed from the gift queue.")
            else:
                logging.info(f"User {user_id} tried to leave queue, but was not found or not in queue initially.")
                await event.reply("You were not in the queue, or I don't have a record for you.")
        else:
            logging.error(f"Failed to acknowledge /leave_queue for user {user_id}")
            await event.reply("Sorry, there was an issue processing your request. Please try again.")
    except Exception as e:
        logging.error(f"Error in /leave_queue for user {user_id}: {e}", exc_info=True)
        await event.reply("An error occurred while trying to leave the queue. Please try again later.")

@client.on(events.NewMessage(pattern=r'/set_preferred_gift(?: |$)(.*)'))
async def set_preference_handler(event):
    """Handles the /set_preferred_gift <gift_identifier> command."""
    user_id = event.sender_id
    gift_identifier_str = event.pattern_match.group(1).strip()

    if not gift_identifier_str:
        await event.reply("Please provide a gift identifier. Usage: /set_preferred_gift <gift_id>")
        return

    try:
        # Assuming gift_identifier is a numerical ID. Telegram PremiumGiftOption IDs are long.
        gift_identifier_long = int(gift_identifier_str)
    except ValueError:
        await event.reply("Invalid gift identifier. It must be a number.")
        return

    try:
        users_collection = db.users
        update_result = await users_collection.update_one(
            {'user_id': user_id},
            {
                '$addToSet': {'preferred_gift_ids': gift_identifier_long},
                '$set': {'last_activity_timestamp': datetime.utcnow()},
                '$setOnInsert': {
                    'star_balance': 0,
                    'in_gift_queue': True,
                    'user_id': user_id, # Ensure user_id is set on insert
                    # preferred_gift_ids will be handled by $addToSet
                }
            },
            upsert=True
        )

        if update_result.acknowledged:
            logging.info(f"User {user_id} added/updated gift preference: {gift_identifier_long}. Upserted: {update_result.upserted_id is not None}")
            await event.reply(f"Preference for gift ID {gift_identifier_long} has been saved.")
        else:
            logging.error(f"Failed to update preferences for user {user_id}.")
            await event.reply("Sorry, there was an issue saving your preference. Please try again.")

    except Exception as e:
        logging.error(f"Error in /set_preferred_gift for user {user_id}: {e}", exc_info=True)
        await event.reply("An error occurred while saving your preference. Please try again later.")

@client.on(events.NewMessage(pattern='/my_preferences'))
async def my_preferences_handler(event):
    """Handles the /my_preferences command."""
    user_id = event.sender_id
    try:
        users_collection = db.users
        user_data = await users_collection.find_one({'user_id': user_id})

        if user_data and user_data.get('preferred_gift_ids'):
            preferences = user_data['preferred_gift_ids']
            if preferences:
                pref_list_str = "\n".join(f"- {gid}" for gid in preferences)
                await event.reply(f"Your current gift preferences are:\n{pref_list_str}")
            else:
                await event.reply("You have no gift preferences set. Use /set_preferred_gift <gift_id> to add one.")
        else:
            await event.reply("You have no gift preferences set, or no record found. Use /set_preferred_gift <gift_id> to add one.")
            # Optionally, create a basic user record if none found, though /set_preferred_gift would also do this.
            # await users_collection.update_one(
            #     {'user_id': user_id},
            #     {'$setOnInsert': {'star_balance': 0, 'last_activity_timestamp': datetime.utcnow(), 'preferred_gift_ids': [], 'in_gift_queue': True, 'user_id': user_id}},
            #     upsert=True
            # )

    except Exception as e:
        logging.error(f"Error in /my_preferences for user {user_id}: {e}", exc_info=True)
        await event.reply("An error occurred while fetching your preferences. Please try again later.")

@client.on(events.NewMessage(pattern='/clear_my_preferences'))
async def clear_preferences_handler(event):
    """Handles the /clear_my_preferences command."""
    user_id = event.sender_id
    try:
        users_collection = db.users
        update_result = await users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {'preferred_gift_ids': [], 'last_activity_timestamp': datetime.utcnow()}
            }
            # No upsert needed; if the user doesn't exist, there's nothing to clear.
        )

        if update_result.acknowledged:
            if update_result.matched_count > 0:
                logging.info(f"Cleared gift preferences for user {user_id}.")
                await event.reply("Your gift preferences have been cleared.")
            else:
                logging.info(f"User {user_id} had no preferences to clear or no record found.")
                await event.reply("You had no preferences set, or no record was found.")
        else:
            logging.error(f"Failed to clear preferences for user {user_id}.")
            await event.reply("Sorry, there was an issue clearing your preferences. Please try again.")

    except Exception as e:
        logging.error(f"Error in /clear_my_preferences for user {user_id}: {e}", exc_info=True)
        await event.reply("An error occurred while clearing your preferences. Please try again later.")

@client.on(events.NewMessage(incoming=True))
async def handle_star_reception(event):
    """Handles incoming messages, specifically looking for Star payments."""
    if event.message and isinstance(event.message, MessageService) and isinstance(event.message.action, MessageActionPaymentSent):
        try:
            payment_action = event.message.action
            currency = payment_action.currency
            stars_received_amount = payment_action.total_amount

            if currency == 'XTR': # XTR is the currency code for Telegram Stars
                user_id = event.message.peer_id.user_id if event.message.peer_id else event.sender_id
                if not user_id:
                    logging.error("Could not extract user_id from star payment event.")
                    return

                logging.info(f"Received {stars_received_amount} Stars from user_id: {user_id}")

                users_collection = db.users
                update_result = await users_collection.update_one(
                    {'user_id': user_id},
                    {
                        '$inc': {'star_balance': stars_received_amount},
                        '$set': {'last_activity_timestamp': datetime.utcnow()},
                        '$setOnInsert': {
                            'preferred_gift_ids': [],
                            'in_gift_queue': True,
                            'user_id': user_id  # Ensure user_id is set on insert
                        }
                    },
                    upsert=True
                )

                if update_result.acknowledged:
                    logging.info(f"Database updated for user_id: {user_id}. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}, UpsertedId: {update_result.upserted_id}")

                    # Fetch the user's new balance
                    user_data = await users_collection.find_one({'user_id': user_id})
                    new_balance = user_data.get('star_balance', 0) if user_data else 0

                    await event.respond(f"Thank you! Received {stars_received_amount} Stars. Your new balance is {new_balance} Stars.")
                    logging.info(f"Sent acknowledgement to user_id: {user_id}. New balance: {new_balance}")
                else:
                    logging.error(f"Database update failed for user_id: {user_id}")
                    await event.respond("Sorry, there was an issue processing your Stars. Please contact support.")

            else:
                logging.info(f"Received payment in currency {currency}, not XTR. Ignoring.")

        except Exception as e:
            logging.error(f"Error processing star payment: {e}", exc_info=True)
            try:
                await event.respond("An error occurred while processing your payment. Please try again later or contact support.")
            except Exception as resp_e:
                logging.error(f"Error sending error response to user: {resp_e}")


async def main():
    """Main function to initialize the database and run the bot."""
    global db
    db = get_mongo_db()

    # Create indexes
    # For users collection, ensure user_id is unique and indexed for fast lookups
    # Make sure this is awaited if your pymongo version returns an awaitable
    if hasattr(db.users, 'create_index'): # For synchronous pymongo
        db.users.create_index('user_id', unique=True)
    else: # For motor or other async pymongo wrappers
        await db.users.create_index('user_id', unique=True)

    # For app_config collection, ensure key is unique (optional, depends on usage)
    # if hasattr(db.app_config, 'create_index'):
    #     db.app_config.create_index('key', unique=True)
    # else:
    #     await db.app_config.create_index('key', unique=True)


    await client.start(bot_token=BOT_TOKEN)
    print(f"Bot started successfully! Connected as: {await client.get_me()}")

    # --- Placeholder for testing discover_limited_gifts (now handled by polling_loop) ---
    # DEBUG_MODE = False # Or load from env
    # if DEBUG_MODE:
    #     logging.info("DEBUG_MODE: Attempting to discover limited gifts on startup...")
    #     try:
    #         limited_gifts = await discover_limited_gifts()
    #         if limited_gifts:
    #             logging.info(f"DEBUG_MODE: Found {len(limited_gifts)} limited and available gifts:")
    #             for gift in limited_gifts:
    #                 logging.info(f"  - ID: {gift['id']}, Stars: {gift['stars']}, Months: {gift['months']}, Product: {gift.get('store_product', 'N/A')}, Desc: {gift.get('description', 'N/A')}")
    #         else:
    #             logging.info("DEBUG_MODE: No limited and available gifts found or an error occurred.")
    #     except Exception as e:
    #         logging.error(f"DEBUG_MODE: Error calling discover_limited_gifts on startup: {e}", exc_info=True)
    # --- End of placeholder ---

    # Start the polling loop as a concurrent task
    logging.info(f"Creating polling loop task with interval: {POLLING_INTERVAL_SECONDS} seconds.")
    polling_task = asyncio.create_task(polling_loop())
    logging.info("Polling task created.")

    await client.run_until_disconnected()
    logging.info("Client disconnected. Waiting for polling task to complete...")
    await polling_task # Ensure polling task is awaited on graceful exit if it's not a daemon
    logging.info("Polling task finished.")


async def polling_loop():
    """Periodically discovers limited gifts and processes purchases."""
    while True:
        logging.info("Polling loop started a new cycle.")
        try:
            available_gifts = await discover_limited_gifts()
            if available_gifts:
                logging.info(f"Discovered {len(available_gifts)} limited gifts. Processing purchases...")
                await process_gift_purchases(available_gifts)
            else:
                logging.info("No limited gifts discovered in this cycle.")

        except Exception as e:
            logging.error(f"Polling loop encountered an error in its cycle: {e}", exc_info=True)

        logging.info(f"Polling cycle finished. Waiting for {POLLING_INTERVAL_SECONDS} seconds...")
        await asyncio.sleep(POLLING_INTERVAL_SECONDS)

async def discover_limited_gifts():
    """
    Discovers available limited (not sold out) Telegram Premium gift options.
    Returns a list of dictionaries, each representing an available limited gift.
    """
    available_limited_gifts = []
    try:
        # Construct the request. Using InputPeerSelf() to see general options.
        # If this needs a specific user context for limited gifts, this might need adjustment.
        request = GetPremiumGiftCodeOptionsRequest(peer=InputPeerSelf())
        result = await client(request)

        if not result or not hasattr(result, 'options'):
            logging.warning("discover_limited_gifts: No options found or unexpected result structure.")
            return []

        logging.info(f"discover_limited_gifts: Received {len(result.options)} total gift options from API.")

        for option in result.options:
            # Flags: option.flags
            # Bit 0 (0x1) seems to be 'limited'
            # Bit 1 (0x2) seems to be 'sold_out'
            is_limited = bool(option.flags & (1 << 0)) # Check if the 'limited' flag (bit 0) is set
            is_sold_out = bool(option.flags & (1 << 1)) # Check if the 'sold_out' flag (bit 1) is set

            # We are interested in gifts that are limited AND NOT sold_out
            if is_limited and not is_sold_out:
                gift_details = {
                    'id': option.id,
                    'stars': option.stars,
                    'months': option.months,
                    'currency': option.currency,
                    'amount': option.amount,
                    'store_product': option.store_product,
                    'description': option.description, # This might be a generic description
                    # 'sticker': option.sticker, # Could be useful for display
                    # 'video': option.video, # Could be useful for display
                    # 'video_mime_type': option.video_mime_type,
                    # 'video_duration': option.video_duration,
                    'raw_option': option # Store the raw option for any further details if needed
                }
                available_limited_gifts.append(gift_details)
                logging.info(f"discover_limited_gifts: Found available limited gift: ID={option.id}, Stars={option.stars}, Months={option.months}")
            # else:
            #     logging.debug(f"discover_limited_gifts: Skipping option ID={option.id}, limited={is_limited}, sold_out={is_sold_out}")


        logging.info(f"discover_limited_gifts: Found {len(available_limited_gifts)} limited and available gifts.")

    except RPCError as e:
        logging.error(f"discover_limited_gifts: Telegram API RPCError: {e.code} - {e.message}", exc_info=True)
    except Exception as e:
        logging.error(f"discover_limited_gifts: An unexpected error occurred: {e}", exc_info=True)

    return available_limited_gifts

async def process_gift_purchases(available_gifts: list):
    """
    Processes gift purchases for users based on their star balance, preferences, and available gifts.
    """
    if not available_gifts:
        logging.info("process_gift_purchases: No available gifts to process.")
        return

    try:
        # Fetch users who have star_balance > 0 and are in the gift queue
        # Sort by last_activity_timestamp (ascending) for FIFO, or by star_balance (descending) to prioritize high-balance users.
        # For now, let's do FIFO for users in queue.
        users_to_process_cursor = db.users.find({
            'star_balance': {'$gt': 0},
            'in_gift_queue': True
        }).sort('last_activity_timestamp', 1) # 1 for ascending

        users_processed_count = 0
        for user_doc_summary in await users_to_process_cursor.to_list(length=None): # Process all eligible users in one cycle for now
            user_id = user_doc_summary['user_id']

            # Get fresh user data, especially star balance, within the loop for atomicity
            user_doc = await db.users.find_one({'user_id': user_id})
            if not user_doc or not user_doc.get('in_gift_queue') or user_doc.get('star_balance', 0) <= 0:
                logging.info(f"process_gift_purchases: Skipping user {user_id}, no longer eligible (no balance, not in queue, or no doc).")
                continue

            current_star_balance = user_doc.get('star_balance', 0)
            preferred_gift_ids = user_doc.get('preferred_gift_ids', [])

            gift_to_purchase = None
            purchase_reason = ""
            selected_gift_details = None

            # A. Check Preferred Gifts
            if preferred_gift_ids:
                for pref_id in preferred_gift_ids:
                    gift_option = next((g for g in available_gifts if g['id'] == pref_id), None)
                    if gift_option and current_star_balance >= gift_option['stars']:
                        gift_to_purchase = gift_option['id'] # Store the ID
                        selected_gift_details = gift_option # Store full details
                        purchase_reason = "your preferred gift"
                        logging.info(f"process_gift_purchases: User {user_id} has enough stars for preferred gift ID {gift_to_purchase} (Cost: {selected_gift_details['stars']}).")
                        break

            # B. Fallback (If No Preferred Match or No Preferences)
            if not gift_to_purchase:
                # Find the cheapest gift in available_gifts that current_star_balance >= gift['stars']
                # Sort available_gifts by stars ascending to find the cheapest
                affordable_gifts = [g for g in available_gifts if current_star_balance >= g['stars']]
                if affordable_gifts:
                    cheapest_affordable_gift = min(affordable_gifts, key=lambda g: g['stars'])
                    gift_to_purchase = cheapest_affordable_gift['id']
                    selected_gift_details = cheapest_affordable_gift
                    purchase_reason = "an available limited gift"
                    logging.info(f"process_gift_purchases: User {user_id} - no preferred match. Found cheapest affordable gift ID {gift_to_purchase} (Cost: {selected_gift_details['stars']}).")

            # C. Attempt Purchase (if gift_to_purchase is set)
            if gift_to_purchase and selected_gift_details:
                try:
                    target_input_user = await client.get_input_entity(user_id)

                    # Construct the purpose object for the purchase request
                    # The 'amount' here is the cost in the smallest unit of the currency (e.g., cents for USD).
                    # For Stars (XTR), it's directly the number of stars.
                    payment_purpose = InputStorePaymentPremiumGiftCode(
                        users=[target_input_user], # The user(s) to receive the gift
                        currency='XTR',
                        amount=selected_gift_details['stars']
                        # gift_option_id=selected_gift_details['id'] # Not a direct param here, seems implied by amount or needs other method
                    )

                    # The `user_id` in PurchasePremiumGiftCodeRequest is the buyer (the bot itself)
                    # The `gift_id` parameter in PurchasePremiumGiftCodeRequest is the ID of the PremiumGiftOption
                    purchase_request = PurchasePremiumGiftCodeRequest(
                        user_id=InputPeerSelf(), # Bot buys for the user
                        gift_id=selected_gift_details['id'], # The specific gift option ID
                        purpose=payment_purpose
                    )

                    logging.info(f"process_gift_purchases: Attempting to purchase gift ID {selected_gift_details['id']} for user {user_id} for {selected_gift_details['stars']} Stars.")

                    # Make the purchase
                    purchase_result = await client(purchase_request)

                    logging.info(f"process_gift_purchases: Purchase API call for user {user_id}, gift ID {selected_gift_details['id']} result: {purchase_result}")

                    # Assuming success if no RPCError is raised.
                    # purchase_result is often an Updates object. We should inspect its contents if specific confirmation is needed.
                    # For example, it might contain information about the gifted subscriptions or codes.

                    # Deduct stars and update timestamp
                    new_balance_after_purchase = current_star_balance - selected_gift_details['stars']
                    db_update_result = await db.users.update_one(
                        {'user_id': user_id},
                        {
                            '$inc': {'star_balance': -selected_gift_details['stars']},
                            '$set': {'last_activity_timestamp': datetime.utcnow()}
                            # Optionally, remove user from queue or mark gift as processed for this cycle
                            # '$set': {'in_gift_queue': False} # Or some other status
                        }
                    )

                    if db_update_result.modified_count > 0:
                        logging.info(f"process_gift_purchases: Successfully updated user {user_id}'s star balance to {new_balance_after_purchase}.")
                        try:
                            await client.send_message(
                                user_id,
                                f"Congratulations! We've successfully acquired {purchase_reason}: '{selected_gift_details.get('description', 'a gift')}' "
                                f"for {selected_gift_details['stars']} Stars on your behalf.\n"
                                f"Your new star balance is {new_balance_after_purchase}.\n"
                                "You should receive a confirmation from Telegram shortly with the gift details."
                            )
                        except Exception as e_notify:
                            logging.error(f"process_gift_purchases: Failed to send success notification to user {user_id}: {e_notify}", exc_info=True)

                        users_processed_count += 1
                        # Decide if we break after one successful purchase globally per run, or per user.
                        # For now, let's allow processing multiple users, but one gift per user per cycle.
                        # If we want only one gift purchase in total per `process_gift_purchases` call:
                        # logging.info("process_gift_purchases: One gift processed successfully. Ending current cycle.")
                        # return # This would exit after the first successful purchase in the entire run.
                    else:
                        logging.error(f"process_gift_purchases: Failed to update star balance for user {user_id} after successful purchase. Manual check needed.")
                        # Potentially try to refund or hold, this is a critical error state.

                except RPCError as e:
                    logging.error(f"process_gift_purchases: Telegram API RPCError during purchase for user {user_id}, gift ID {selected_gift_details['id']}: {e.code} - {e.message}", exc_info=True)
                    # Notify user if it was a preferred gift attempt?
                    if purchase_reason == "your preferred gift":
                        try:
                            await client.send_message(user_id, f"We tried to get your preferred gift '{selected_gift_details.get('description', 'ID ' + str(selected_gift_details['id']))}' but encountered an issue: {e.message}. Please try again later or contact support.")
                        except Exception as e_notify_fail:
                            logging.error(f"process_gift_purchases: Failed to send purchase failure notification to user {user_id}: {e_notify_fail}", exc_info=True)
                except Exception as e:
                    logging.error(f"process_gift_purchases: An unexpected error occurred during purchase for user {user_id}, gift ID {selected_gift_details['id']}: {e}", exc_info=True)

            elif gift_to_purchase is None and selected_gift_details is None:
                 logging.info(f"process_gift_purchases: User {user_id} (balance: {current_star_balance}) - no affordable gift found (neither preferred nor fallback).")


        if users_processed_count > 0:
            logging.info(f"process_gift_purchases: Finished processing. Successfully purchased gifts for {users_processed_count} user(s).")
        else:
            logging.info("process_gift_purchases: Finished processing. No gifts were purchased in this cycle.")

    except Exception as e:
        logging.error(f"process_gift_purchases: An overall error occurred: {e}", exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
