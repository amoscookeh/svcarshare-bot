# Import required packages
import pymongo
import telegram
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from datetime import datetime
from dotenv import load_dotenv
import os
import time


# Forcefully sleep bot to prevent multiple bot instances from running when hosted
# time.sleep(5)


# KEY ENV VARIABLES
load_dotenv()
TELEBOT_KEY = os.environ["TELEBOT_KEY"]
MONGODB_USERNAME = os.environ["MONGODB_USERNAME"]
MONGODB_PASSWORD = os.environ["MONGODB_PASSWORD"]

# Connect to the mongodb database
client = pymongo.MongoClient(f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@svcarsharecluster.wvsvd7v.mongodb.net/?retryWrites=true&w=majority")
db = client["vehicle_management"]

# Define the options for users
users = ["Amos", "David", "Ngee Feng", "Guo Jun"]
keyboard_options = [users + ["Others", "Done"]]
user_keyboard = ReplyKeyboardMarkup(
    keyboard_options, one_time_keyboard=True
)
user_without_options_keyboard = ReplyKeyboardMarkup(
    [users], one_time_keyboard=True
)
keyboard_options = [["Now"]]
date_keyboard = ReplyKeyboardMarkup(
    keyboard_options, one_time_keyboard=True
)

# Define the handler for the `/start` command
def start(update, context):
    # Prompt the user to select the users that utilised the car
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome. Commands: \n/indicate_usage - Indicate your usage \n/indicate_fuel - Indicate your fuel pump",
    )
    return ConversationHandler.END

# Define the handler for the `/indicate_usage` command
def indicate_usage(update, context):
    usage_users = context.user_data["usage_users"] = []
    return _indicate_usage(update, context)

def _indicate_usage(update, context):
    # Prompt the user to select the users that utilised the car
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please select the users that utilised the car:",
        reply_markup=user_keyboard
    )
    return "USAGE_USERS"

# Define the handler for receiving the user's response to the usage users prompt
def usage_users(update, context):
    # Extract the user's response
    response = update.message.text
    selected_users = context.user_data["usage_users"]
    # Check if the user's message is "Others"
    if response == "Others":
        # Send a message asking the user to enter a custom name
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please enter the name you would like to add:",
        )
        return "ADD_USER"
    elif response == "Done":
        # for user in selected_users:
        #     if user not in users:
        #         update.message.reply_text(f"Invalid user: {user}")
        #         return
        # Store the selected users in the user data
        usage_users = context.user_data["usage_users"] = selected_users
        # Prompt the user to enter the date of the usage
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Enter a date or select now:",
            reply_markup=date_keyboard
        )
        update.message.reply_text("Please enter the date of the usage (YYYY-MM-DD):")
        return "USAGE_DATE"
    else:
        # If the user's message is not "Others", assume it is a custom name
        # and add it to the list of names
        selected_users.append(update.message.text)

        # Send a message confirming that the name has been added
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"The name {response} has been added to the list ({str(selected_users)}).",
        )
        usage_users = context.user_data["usage_users"] = selected_users
        return _indicate_usage(update, context)

# Define the handler to add a custom user name to selected_users
def add_user(update, context):
    # Extract the user's response
    response = update.message.text
    # Add user to selected users
    selected_users = context.user_data["usage_users"]
    selected_users.append(response)
    context.user_data["usage_users"] = selected_users
    # Send a message confirming that the name has been added
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"The name {response} has been added to the list ({str(selected_users)}).",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please select the users that utilised the car:",
        reply_markup=user_keyboard
    )
    return "USAGE_USERS"

# Define the handler for receiving the user's response to the usage date prompt
def usage_date(update, context):
    # Extract the user's response
    response = update.message.text
    # Validate the response
    try:
        if response == "Now":
            usage_date = datetime.now()
        else:
            usage_date = datetime.strptime(response, "%Y-%m-%d")
    except ValueError:
        update.message.reply_text("Invalid date format. Please enter the date in the format YYYY-MM-DD.")
        return
    # Store the usage date in the user data
    context.user_data["usage_date"] = usage_date
    # Prompt the user to enter the total miles driven
    update.message.reply_text("Please enter the current number of miles shown on the dashboard:")
    return "USAGE_MILES"

# Define the handler for receiving the user's response to the usage miles prompt
def usage_miles(update, context):
    # Extract the user's response
    response = update.message.text
    usage_date = context.user_data["usage_date"] 
    # Validate the response
    try:
        current_miles = int(response)
        if current_miles < 1000:
            update.message.reply_text("ERROR: Please enter the number of miles on the dashboard, not the number of miles driven.")
            return
        prev_record = db["usage"].find_one({
                    "date": {"$lt": usage_date}
                }, 
                sort=[("current_miles", -1)]
            )
        prev_miles = prev_record["current_miles"]
        usage_miles = current_miles - prev_miles
    except ValueError:
        update.message.reply_text("Invalid miles format. Please enter a number for the total miles driven.")
        return
    # Store the usage miles in the user data
    context.user_data["usage_miles"] = usage_miles
    context.user_data["current_miles"] = current_miles
    
    update.message.reply_text("Please enter the toll amount for this trip: ")
    return "USAGE_TOLLS"

def usage_tolls(update, context):
    try:
        response = int(update.message.text)
    except Exception:
        update.message.reply_text("Invalid toll amount")
    context.user_data["usage_toll"] = response
    # Prompt the user to enter a title for the usage
    update.message.reply_text("Please enter a title for the usage:")
    return "USAGE_TITLE"

#Define the handler for receiving the user's response to the usage title prompt
def usage_title(update, context):
    # Extract the user's response
    response = update.message.text
    # Validate the response
    if len(response) == 0:
        update.message.reply_text("Please enter a valid title for the usage.")
        return
    # Store the usage title in the user data
    context.user_data["usage_title"] = response
    # Retrieve the user data
    usage_users = context.user_data["usage_users"]
    usage_date = context.user_data["usage_date"]
    usage_miles = context.user_data["usage_miles"]
    current_miles = context.user_data["current_miles"]
    usage_toll = context.user_data["usage_toll"]
    usage_title = context.user_data["usage_title"]
    # Persist the usage data into the mongodb database
    usage_data = {
        "users": usage_users,
        "date": usage_date,
        "miles": usage_miles,
        "current_miles": current_miles,
        "toll": usage_toll,
        "title": usage_title
    }
    db["usage"].insert_one(usage_data)
    # Confirm the usage data has been saved
    update.message.reply_text("Usage data saved successfully.")
    # Clear the user data
    context.user_data.clear()
    return ConversationHandler.END

#Define the handler for the /indicate_fuel command
def indicate_fuel(update, context):
    # Prompt the user to select the user that paid for the fuel
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please select the user that paid for the fuel:",
        reply_markup=user_without_options_keyboard
    )
    # Wait for the user's response
    fuel_user = context.user_data["fuel_user"] = []
    return "FUEL_USER"

#Define the handler for receiving the user's response to the fuel user prompt
def fuel_user(update, context):
    # Extract the user's response
    response = update.message.text
    # Validate the response
    # if response not in users:
    #     update.message.reply_text(f"Invalid user: {response}")
    #     return
    # Store the selected user in the user data
    context.user_data["fuel_user"] = response
    # Prompt the user to enter the date of the fuel pump
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please enter the date of the fuel pump (YYYY-MM-DD) or select Now:",
            reply_markup=date_keyboard
        )
    return "FUEL_DATE"

#Define the handler for receiving the user's response to the fuel date prompt
def fuel_date(update, context):
    # Extract the user's response
    response = update.message.text
    # Validate the response
    try:
        if response == "Now":
            fuel_date = datetime.now()
        else:
            fuel_date = datetime.strptime(response, "%Y-%m-%d")
    except ValueError:
        update.message.reply_text("Invalid date format. Please enter the date in the format YYYY-MM-DD.")
        return
    # Store the fuel date in the user data
    context.user_data["fuel_date"] = fuel_date
    # Prompt the user to enter the cost of the fuel pump
    update.message.reply_text("Please enter the cost of the fuel pump:")
    return "FUEL_COST"

#Define the handler for receiving the user's response to the fuel cost prompt
def fuel_cost(update, context):
    # Extract the user's response
    response = update.message.text
    # Validate the response
    try:
        fuel_cost = float(response)
    except ValueError:
        update.message.reply_text("Invalid cost format. Please enter a number for the cost of the fuel pump.")
        return
    # Store the fuel cost in the user data
    context.user_data["fuel_cost"] = fuel_cost
    # Retrieve the user data
    fuel_user = context.user_data["fuel_user"]
    fuel_date = context.user_data["fuel_date"]
    fuel_cost = context.user_data["fuel_cost"]
    # Persist the fuel data into the mongodb database
    fuel_data = {
        "user": fuel_user,
        "date": fuel_date,
        "cost": fuel_cost
    }
    db["fuel"].insert_one(fuel_data)
    prev_fuel_record = db["fuel"].find_one({
            "date": {"$lt": fuel_date}
        }, 
        sort=[("date", -1)]
    )
    prev_fuel_date = prev_fuel_record["date"]
    # Calculate the amount to be paid by each user
    # Get the total number of miles driven by each user since the last fuel pump
    usage_data = db["usage"].find({
            "date": {
                "$lt": fuel_date,
                "$gt": prev_fuel_date
        },
    })
    user_miles = {}
    user_tolls = {}
    for usage in usage_data:
        usage_users = usage["users"]
        for user in usage_users:
            total_mileage = usage["miles"]
            mileage_per_user = total_mileage / len(usage_users)
            if user not in user_miles:
                user_miles[user] = 0
                user_miles[user] += mileage_per_user
            else:
                user_miles[user] += mileage_per_user
        for user in usage_users:
            total_toll = usage["toll"]
            toll_per_user = total_toll / len(usage_users)
            if user not in user_tolls:
                user_tolls[user] = 0
                user_tolls[user] += toll_per_user
            else:
                user_tolls[user] += toll_per_user
        
    # Calculate the amount to be paid by each user
    user_amounts = {}
    for user, miles in user_miles.items():
        user_amounts[user] = fuel_cost * miles / sum(user_miles.values())
    for user, toll in user_tolls.items():
        user_amounts[user] += toll
    # Show the amount to be paid by each user
    for user, amount in user_amounts.items():
        update.message.reply_text(f"{user}: ${amount:.2f}")
    # Clear the user data
    context.user_data.clear()
    return ConversationHandler.END


def view_records(update, context):
    output = ""
    # Query the collection for the latest 5 usage records
    latest_usage_records = db["usage"].find().sort("date", -1).limit(10)
    latest_fuel_records = db["fuel"].find().sort("date", -1).limit(10)

    output = output + "Usage Records"
    # Print the latest 10 usage records
    for record in latest_usage_records:
        output = output + f"\nDate: {record['date']} - Users: {record['users']} - Miles: {record['miles']}"
    
    output = output + "\n\nFuel Records"
    # Print the latest 10 usage records
    for record in latest_fuel_records:
        output = output + f"\nDate: {record['date']} - User: {record['user']} - Price: {record['cost']}"
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=output,
    )
    return ConversationHandler.END


def end_conv(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Conversation cancelled."
    )
    return ConversationHandler.END


def fallback(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, something went wrong."
    )
    return ConversationHandler.END

#Create the telegram bot
bot = telegram.Bot(token=TELEBOT_KEY)

#Create the Updater and pass the bot's token
updater = Updater(token=TELEBOT_KEY, use_context=True)

#Get the dispatcher to register the handlers
dispatcher = updater.dispatcher

#Create a conversation handler with the indicated usage and fuel commands
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CommandHandler("indicate_usage", indicate_usage),
        CommandHandler("indicate_fuel", indicate_fuel),
        CommandHandler("view_records", view_records),
    ],
    states={
            "USAGE_USERS": [MessageHandler(Filters.text & (~ Filters.command), usage_users)],
            "ADD_USER": [MessageHandler(Filters.text & (~ Filters.command), add_user)],
            "USAGE_DATE": [MessageHandler(Filters.text & (~ Filters.command), usage_date)],
            "USAGE_MILES": [MessageHandler(Filters.text & (~ Filters.command), usage_miles)],
            "USAGE_TOLLS": [MessageHandler(Filters.text & (~ Filters.command), usage_tolls)],
            "USAGE_TITLE": [MessageHandler(Filters.text & (~ Filters.command), usage_title)],
            "FUEL_USER": [MessageHandler(Filters.text & (~ Filters.command), fuel_user)],
            "FUEL_DATE": [MessageHandler(Filters.text & (~ Filters.command), fuel_date)],
            "FUEL_COST": [MessageHandler(Filters.text & (~ Filters.command), fuel_cost)]
        },
    fallbacks=[CommandHandler("cancel", end_conv), MessageHandler(Filters.all, fallback)],
)

#Add the conversation handler to the dispatcher
dispatcher.add_handler(conv_handler)

#Start the bot
updater.start_polling()
